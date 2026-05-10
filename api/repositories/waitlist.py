from __future__ import annotations

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
