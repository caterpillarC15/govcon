from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ExtractedRequirement, FitScore, Opportunity, RiskFlag


class OpportunityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, opp_id: uuid.UUID) -> Opportunity | None:
        return await self.session.get(Opportunity, opp_id)

    async def list_by_ids(self, ids: list[uuid.UUID]) -> list[Opportunity]:
        if not ids:
            return []
        result = await self.session.execute(
            select(Opportunity).where(Opportunity.id.in_(ids))
        )
        return list(result.scalars().all())

    async def requirements(self, opp_id: uuid.UUID) -> list[ExtractedRequirement]:
        result = await self.session.execute(
            select(ExtractedRequirement)
            .where(ExtractedRequirement.opportunity_id == opp_id)
            .order_by(ExtractedRequirement.created_at)
        )
        return list(result.scalars().all())

    async def latest_fit_score(self, opp_id: uuid.UUID) -> FitScore | None:
        result = await self.session.execute(
            select(FitScore)
            .where(FitScore.opportunity_id == opp_id)
            .order_by(FitScore.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def risks(self, opp_id: uuid.UUID) -> list[RiskFlag]:
        result = await self.session.execute(
            select(RiskFlag)
            .where(RiskFlag.opportunity_id == opp_id)
            .order_by(RiskFlag.created_at)
        )
        return list(result.scalars().all())
