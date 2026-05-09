from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import AgentRun


class AgentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        goal: str,
        company_profile_id: uuid.UUID | None,
    ) -> AgentRun:
        row = AgentRun(
            goal=goal,
            company_profile_id=company_profile_id,
            status="pending",
            steps=[],
            opportunities=[],
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get(self, run_id: uuid.UUID) -> AgentRun | None:
        return await self.session.get(AgentRun, run_id)

    async def append_step(self, run_id: uuid.UUID, step: dict[str, Any]) -> None:
        run = await self.session.get(AgentRun, run_id)
        if run is None:
            return
        run.steps = [*(run.steps or []), step]
        await self.session.commit()

    async def mark_completed(
        self,
        run_id: uuid.UUID,
        *,
        status: str,
        action_package_id: uuid.UUID | None = None,
    ) -> None:
        from datetime import datetime, timezone

        run = await self.session.get(AgentRun, run_id)
        if run is None:
            return
        run.status = status
        run.completed_at = datetime.now(timezone.utc)
        if action_package_id is not None:
            run.action_package_id = action_package_id
        await self.session.commit()
