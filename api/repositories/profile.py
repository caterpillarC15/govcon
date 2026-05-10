from __future__ import annotations

import uuid
from typing import Any, cast

from supabase import AsyncClient


class ProfileRepository:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def get(self, profile_id: uuid.UUID) -> dict[str, Any] | None:
        resp = await (
            self.client.table("profiles")
            .select("*")
            .eq("id", str(profile_id))
            .maybe_single()
            .execute()
        )
        return cast("dict[str, Any] | None", resp.data) if resp else None

    async def upsert_user_profile(
        self,
        *,
        profile_id: uuid.UUID,
        email: str | None,
        full_name: str | None = None,
        company_name: str | None = None,
    ) -> dict[str, Any]:
        existing = await self.get(profile_id)
        payload: dict[str, Any] = {
            "id": str(profile_id),
            "email": email,
        }
        if full_name is not None:
            payload["full_name"] = full_name
        if company_name is not None:
            payload["company_name"] = company_name

        if existing is None:
            resp = await self.client.table("profiles").insert(payload).execute()
            return cast(dict[str, Any], resp.data[0])

        update = {k: v for k, v in payload.items() if k != "id"}
        resp = await (
            self.client.table("profiles")
            .update(update)
            .eq("id", str(profile_id))
            .execute()
        )
        rows = cast("list[dict[str, Any]]", resp.data or [])
        return rows[0] if rows else {**existing, **update}
