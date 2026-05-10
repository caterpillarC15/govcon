from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, cast

from supabase import AsyncClient


class AgentRunRepository:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def create(
        self,
        *,
        goal: str,
        profile_id: uuid.UUID,
        company_profile_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "goal": goal,
            "profile_id": str(profile_id),
            "company_profile_id": str(company_profile_id) if company_profile_id else None,
            "status": "pending",
            "steps": [],
            "opportunities": [],
        }
        resp = await self.client.table("agent_runs").insert(payload).execute()
        return cast(dict[str, Any], resp.data[0])

    async def get(self, run_id: uuid.UUID) -> dict[str, Any] | None:
        resp = await (
            self.client.table("agent_runs")
            .select("*")
            .eq("id", str(run_id))
            .maybe_single()
            .execute()
        )
        return cast("dict[str, Any] | None", resp.data) if resp else None

    async def get_owned(
        self,
        run_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        resp = await (
            self.client.table("agent_runs")
            .select("*")
            .eq("id", str(run_id))
            .eq("profile_id", str(profile_id))
            .maybe_single()
            .execute()
        )
        return cast("dict[str, Any] | None", resp.data) if resp else None

    async def append_step(self, run_id: uuid.UUID, step: dict[str, Any]) -> None:
        run = await self.get(run_id)
        if run is None:
            return
        steps = [*(run.get("steps") or []), step]
        await (
            self.client.table("agent_runs")
            .update({"steps": steps})
            .eq("id", str(run_id))
            .execute()
        )

    async def mark_running(self, run_id: uuid.UUID) -> None:
        await (
            self.client.table("agent_runs")
            .update({"status": "running"})
            .eq("id", str(run_id))
            .execute()
        )

    async def set_opportunities(
        self,
        run_id: uuid.UUID,
        opportunity_ids: list[uuid.UUID],
    ) -> None:
        await (
            self.client.table("agent_runs")
            .update({"opportunities": [str(opp_id) for opp_id in opportunity_ids]})
            .eq("id", str(run_id))
            .execute()
        )

    async def set_selected_opportunity(
        self,
        run_id: uuid.UUID,
        opportunity_id: uuid.UUID | None,
    ) -> None:
        await (
            self.client.table("agent_runs")
            .update(
                {
                    "selected_opportunity_id": (
                        str(opportunity_id) if opportunity_id is not None else None
                    )
                }
            )
            .eq("id", str(run_id))
            .execute()
        )

    async def mark_completed(
        self,
        run_id: uuid.UUID,
        *,
        status: str,
        action_package_id: uuid.UUID | None = None,
    ) -> None:
        update: dict[str, Any] = {
            "status": status,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        if action_package_id is not None:
            update["action_package_id"] = str(action_package_id)
        await (
            self.client.table("agent_runs")
            .update(update)
            .eq("id", str(run_id))
            .execute()
        )
