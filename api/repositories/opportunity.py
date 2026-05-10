from __future__ import annotations

import uuid
from typing import Any, cast

from supabase import AsyncClient


class OpportunityRepository:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self.client.table("opportunities").insert(data).execute()
        return cast(dict[str, Any], resp.data[0])

    async def get(self, opp_id: uuid.UUID) -> dict[str, Any] | None:
        resp = await (
            self.client.table("opportunities")
            .select("*")
            .eq("id", str(opp_id))
            .maybe_single()
            .execute()
        )
        return cast("dict[str, Any] | None", resp.data) if resp else None

    async def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        resp = await (
            self.client.table("opportunities")
            .select("*")
            .eq("slug", slug)
            .maybe_single()
            .execute()
        )
        return cast("dict[str, Any] | None", resp.data) if resp else None

    async def list_by_ids(self, ids: list[uuid.UUID]) -> list[dict[str, Any]]:
        if not ids:
            return []
        resp = await (
            self.client.table("opportunities")
            .select("*")
            .in_("id", [str(i) for i in ids])
            .execute()
        )
        return cast("list[dict[str, Any]]", resp.data or [])

    async def list_recent(
        self, *, since_iso: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return opportunities ingested at or after `since_iso`, newest first.

        Used by the §5.14 weekly auto-picker to pull a candidate set
        from the last N days of cached opportunities. The caller decides
        what counts as "recent" by passing the cutoff timestamp.
        """
        resp = await (
            self.client.table("opportunities")
            .select("*")
            .gte("created_at", since_iso)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return cast("list[dict[str, Any]]", resp.data or [])

    async def requirements(self, opp_id: uuid.UUID) -> list[dict[str, Any]]:
        resp = await (
            self.client.table("extracted_requirements")
            .select("*")
            .eq("opportunity_id", str(opp_id))
            .order("created_at")
            .execute()
        )
        return cast("list[dict[str, Any]]", resp.data or [])

    async def latest_fit_score(self, opp_id: uuid.UUID) -> dict[str, Any] | None:
        resp = await (
            self.client.table("fit_scores")
            .select("*")
            .eq("opportunity_id", str(opp_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = cast("list[dict[str, Any]]", resp.data or [])
        return rows[0] if rows else None

    async def risks(self, opp_id: uuid.UUID) -> list[dict[str, Any]]:
        resp = await (
            self.client.table("risk_flags")
            .select("*")
            .eq("opportunity_id", str(opp_id))
            .order("created_at")
            .execute()
        )
        return cast("list[dict[str, Any]]", resp.data or [])

    async def create_requirement(
        self, opp_id: uuid.UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        resp = await (
            self.client.table("extracted_requirements")
            .insert({**data, "opportunity_id": str(opp_id)})
            .execute()
        )
        return cast(dict[str, Any], resp.data[0])

    async def create_fit_score(
        self, opp_id: uuid.UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        resp = await (
            self.client.table("fit_scores")
            .insert({**data, "opportunity_id": str(opp_id)})
            .execute()
        )
        return cast(dict[str, Any], resp.data[0])

    async def create_risk(
        self, opp_id: uuid.UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        resp = await (
            self.client.table("risk_flags")
            .insert({**data, "opportunity_id": str(opp_id)})
            .execute()
        )
        return cast(dict[str, Any], resp.data[0])
