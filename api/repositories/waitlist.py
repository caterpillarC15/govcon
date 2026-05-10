from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from supabase import AsyncClient


class WaitlistRepository:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        resp = await (
            self.client.table("waitlist_signups")
            .select("*")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        return cast("dict[str, Any] | None", resp.data) if resp else None

    async def create_or_get(self, data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        existing = await self.get_by_email(data["email"])
        if existing is not None:
            return existing, True

        try:
            resp = await self.client.table("waitlist_signups").insert(data).execute()
        except Exception as exc:  # noqa: BLE001
            if "duplicate" not in str(exc).lower() and "unique" not in str(exc).lower():
                raise
            duplicate = await self.get_by_email(data["email"])
            if duplicate is not None:
                return duplicate, True
            raise

        return cast(dict[str, Any], resp.data[0]), False

    async def list_eligible_for_weekly(
        self, *, require_confirmed: bool = False, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Return subscribers eligible for the §5.14 weekly opportunity email.

        Eligibility (PRD §5.14): weekly_opportunity_enabled AND
        unsubscribed_at IS NULL AND bounced_at IS NULL AND complained_at
        IS NULL. Per-week dedupe (the send-log slot check) is the send
        job's responsibility, not this query — keeping that check there
        lets the cron route's structured response distinguish "skipped
        because already sent" from "skipped because not eligible".

        When `require_confirmed=True` (driven by EMAIL_REQUIRE_DOUBLE_OPT_IN),
        also filters confirmed_at IS NOT NULL.
        """
        query = (
            self.client.table("waitlist_signups")
            .select("id, email")
            .eq("weekly_opportunity_enabled", True)
            .is_("unsubscribed_at", "null")
            .is_("bounced_at", "null")
            .is_("complained_at", "null")
        )
        if require_confirmed:
            query = query.not_.is_("confirmed_at", "null")
        if limit is not None:
            query = query.limit(limit)
        resp = await query.execute()
        return cast("list[dict[str, Any]]", resp.data or [])

    async def mark_unsubscribed(
        self, subscription_id: str, *, reason: str | None = None
    ) -> dict[str, Any] | None:
        """Set unsubscribed_at = now() (DB default) for the given row.

        Idempotent: a second call against an already-unsubscribed row
        returns the existing row unchanged. Used by the
        /email-subscriptions/unsubscribe handler after HMAC verifies.
        """
        resp = await (
            self.client.table("waitlist_signups")
            .update(
                {
                    "unsubscribed_at": datetime.now(timezone.utc).isoformat(),
                    "unsubscribed_reason": reason,
                }
            )
            .eq("id", subscription_id)
            .is_("unsubscribed_at", "null")
            .execute()
        )
        rows = resp.data or []
        return cast("dict[str, Any]", rows[0]) if rows else None
