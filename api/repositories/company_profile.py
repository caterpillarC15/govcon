from __future__ import annotations

import builtins
import uuid
from typing import Any, cast

from supabase import AsyncClient


class CompanyProfileRepository:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = await self.client.table("company_profiles").insert(payload).execute()
        return cast(dict[str, Any], resp.data[0])

    async def get(self, profile_id: uuid.UUID) -> dict[str, Any] | None:
        resp = await (
            self.client.table("company_profiles")
            .select("*")
            .eq("id", str(profile_id))
            .maybe_single()
            .execute()
        )
        return cast("dict[str, Any] | None", resp.data) if resp else None

    async def get_owned(
        self,
        profile_id: uuid.UUID,
        owner_profile_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        resp = await (
            self.client.table("company_profiles")
            .select("*")
            .eq("id", str(profile_id))
            .eq("owner_profile_id", str(owner_profile_id))
            .maybe_single()
            .execute()
        )
        return cast("dict[str, Any] | None", resp.data) if resp else None

    async def list(self, limit: int = 100) -> builtins.list[dict[str, Any]]:
        resp = await (
            self.client.table("company_profiles")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return cast("builtins.list[dict[str, Any]]", resp.data or [])

    async def list_owned(
        self,
        owner_profile_id: uuid.UUID,
        limit: int = 100,
    ) -> builtins.list[dict[str, Any]]:
        resp = await (
            self.client.table("company_profiles")
            .select("*")
            .eq("owner_profile_id", str(owner_profile_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return cast("builtins.list[dict[str, Any]]", resp.data or [])
