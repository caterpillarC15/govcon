"""Repository for `weekly_opportunity_email_log` (PRD §5.14).

Two-phase claim pattern. The send job:

1. Calls `claim_slot(email, week_key, email_type)` which does
   `INSERT … ON CONFLICT DO NOTHING RETURNING id`. If the slot was
   already taken (someone else sent this week, or a previous run
   crashed mid-stream), returns None. Otherwise returns the new row
   in status `pending` (or `dry_run` if `EMAIL_DRY_RUN=true`).

2. Calls Resend (or skips, in dry-run).

3. On success calls `mark_sent(id, resend_message_id)`.
   On failure calls `mark_failed(id, reason)`. The next weekly run sees
   the row as already claimed and skips — re-attempt requires manual
   `DELETE`. Intentional: prevents runaway retries that look spammy.

The UNIQUE constraint is `(email, week_key, email_type)`. `email_type`
is mostly `"weekly_opportunity"` but `"unsubscribe_confirm"` is reserved
for the optional confirmation email.
"""
from __future__ import annotations

import uuid
from typing import Any, Literal, cast

from supabase import AsyncClient


EmailType = Literal["weekly_opportunity", "unsubscribe_confirm"]
LogStatus = Literal["dry_run", "pending", "sent", "failed"]


class WeeklyOpportunityEmailLogRepository:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def claim_slot(
        self,
        *,
        email: str,
        week_key: str,
        email_type: EmailType = "weekly_opportunity",
        initial_status: LogStatus = "pending",
    ) -> dict[str, Any] | None:
        """Atomically claim a (email, week_key, email_type) slot.

        Returns the new row on success. Returns None when the slot was
        already taken by a previous run — in that case, do nothing.
        """
        payload: dict[str, Any] = {
            "email": email,
            "week_key": week_key,
            "email_type": email_type,
            "status": initial_status,
        }
        try:
            resp = await (
                self.client.table("weekly_opportunity_email_log")
                .insert(payload)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                return None
            raise
        rows = resp.data or []
        return cast("dict[str, Any]", rows[0]) if rows else None

    async def mark_sent(
        self,
        log_id: uuid.UUID,
        *,
        resend_message_id: str | None,
        sent_at_iso: str,
    ) -> dict[str, Any] | None:
        """Mark a previously-claimed slot as `sent` after Resend acks."""
        resp = await (
            self.client.table("weekly_opportunity_email_log")
            .update(
                {
                    "status": "sent",
                    "resend_message_id": resend_message_id,
                    "sent_at": sent_at_iso,
                }
            )
            .eq("id", str(log_id))
            .execute()
        )
        rows = resp.data or []
        return cast("dict[str, Any]", rows[0]) if rows else None

    async def mark_failed(
        self,
        log_id: uuid.UUID,
        *,
        reason: str,
    ) -> dict[str, Any] | None:
        """Mark a slot as `failed`. Future runs see the slot as taken."""
        resp = await (
            self.client.table("weekly_opportunity_email_log")
            .update(
                {
                    "status": "failed",
                    "failure_reason": reason[:500],
                }
            )
            .eq("id", str(log_id))
            .execute()
        )
        rows = resp.data or []
        return cast("dict[str, Any]", rows[0]) if rows else None

    async def count_for_week(
        self, week_key: str, *, status: LogStatus | None = None
    ) -> int:
        """Return total log rows for a week, optionally filtered by status.

        The job uses this for the structured-JSON return value:
        `{week_key, total_eligible, sent, skipped_already_sent, failed, …}`.
        """
        query = (
            self.client.table("weekly_opportunity_email_log")
            .select("id")
            .eq("week_key", week_key)
        )
        if status is not None:
            query = query.eq("status", status)
        resp = await query.execute()
        return len(resp.data or [])
