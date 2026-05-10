"""Repository for `weekly_opportunity_picks` (PRD §5.14).

One row per ISO week: which opportunity is THE pick for that week. The
table has a UNIQUE constraint on `week_key`, so two writers (the curator
script and the LLM auto-picker) race via `INSERT … ON CONFLICT (week_key)
DO NOTHING`. Manual override wins — the auto-picker silently skips when
the curator pinned a pick first.
"""
from __future__ import annotations

import uuid
from typing import Any, Literal, cast

from supabase import AsyncClient


PickSource = Literal["manual", "llm_auto"]


class WeeklyOpportunityPickRepository:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def get_for_week(self, week_key: str) -> dict[str, Any] | None:
        """Return the pick row for `week_key` or None if not yet picked."""
        resp = await (
            self.client.table("weekly_opportunity_picks")
            .select("*")
            .eq("week_key", week_key)
            .maybe_single()
            .execute()
        )
        return cast("dict[str, Any] | None", resp.data) if resp else None

    async def insert_if_absent(
        self,
        *,
        week_key: str,
        opportunity_id: uuid.UUID,
        source: PickSource,
        picker_audit: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Insert a new pick. Returns the row on success, None on conflict.

        On UNIQUE conflict (week_key already taken), returns None — the
        existing winner is left in place. Curator override pattern: call
        with `source="manual"` first, then the auto-picker calls with
        `source="llm_auto"` and the second call returns None.
        """
        payload: dict[str, Any] = {
            "week_key": week_key,
            "opportunity_id": str(opportunity_id),
            "source": source,
            "picker_audit": picker_audit or {},
        }
        try:
            resp = await (
                self.client.table("weekly_opportunity_picks")
                .insert(payload)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                return None
            raise
        rows = resp.data or []
        return cast("dict[str, Any]", rows[0]) if rows else None
