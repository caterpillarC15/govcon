from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CompanyProfile


class CompanyProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: dict[str, Any]) -> CompanyProfile:
        row = CompanyProfile(**payload)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get(self, profile_id: uuid.UUID) -> CompanyProfile | None:
        return await self.session.get(CompanyProfile, profile_id)

    async def list(self, limit: int = 100) -> list[CompanyProfile]:
        result = await self.session.execute(
            select(CompanyProfile).order_by(CompanyProfile.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
