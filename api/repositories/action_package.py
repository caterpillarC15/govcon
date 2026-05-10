from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, cast

from supabase import AsyncClient


class ActionPackageRepository:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def get(self, package_id: uuid.UUID) -> dict[str, Any] | None:
        resp = await (
            self.client.table("action_packages")
            .select("*")
            .eq("id", str(package_id))
            .maybe_single()
            .execute()
        )
        return cast("dict[str, Any] | None", resp.data) if resp else None

    async def get_owned(
        self,
        package_id: uuid.UUID,
        owner_profile_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        row = await self.get(package_id)
        if row is None:
            return None

        company_profile_id = row.get("company_profile_id")
        if company_profile_id is None:
            return None

        resp = await (
            self.client.table("company_profiles")
            .select("id")
            .eq("id", str(company_profile_id))
            .eq("owner_profile_id", str(owner_profile_id))
            .maybe_single()
            .execute()
        )
        return row if resp and resp.data else None

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self.client.table("action_packages").insert(data).execute()
        return cast(dict[str, Any], resp.data[0])

    async def approve(
        self,
        package_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Mark package approved by user.

        Caller is expected to have already validated ownership via
        get_owned; this method updates the row unconditionally and
        returns the updated row, or None if the id doesn't exist.
        """
        now = datetime.now(timezone.utc).isoformat()
        resp = await (
            self.client.table("action_packages")
            .update({"approved_at": now, "approved_by": str(user_id)})
            .eq("id", str(package_id))
            .execute()
        )
        rows = resp.data or []
        return cast(dict[str, Any], rows[0]) if rows else None
