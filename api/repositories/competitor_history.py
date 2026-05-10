"""Repo for competitor_history (Ledger's writeback).

Mirrors the per-opportunity write/read pattern used by
OpportunityRepository for risk_flags and fit_scores. Reads are scoped
to (opportunity_id, owner_profile_id) so even if FakeSupabase or RLS
were bypassed, the route layer still can't return another tenant's
rows.
"""
from __future__ import annotations

import uuid
from typing import Any, cast

from supabase import AsyncClient


class CompetitorHistoryRepository:
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def list_for_opportunity_owned(
        self, opportunity_id: uuid.UUID, owner_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        resp = await (
            self._client.table("competitor_history")
            .select("*")
            .eq("opportunity_id", str(opportunity_id))
            .eq("owner_profile_id", str(owner_id))
            .order("created_at", desc=True)
            .execute()
        )
        return cast("list[dict[str, Any]]", resp.data or [])

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = await (
            self._client.table("competitor_history").insert(payload).execute()
        )
        rows = cast("list[dict[str, Any]]", resp.data or [])
        if not rows:
            raise RuntimeError("competitor_history insert returned no row")
        return rows[0]
