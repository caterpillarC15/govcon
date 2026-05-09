from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ActionPackage


class ActionPackageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, package_id: uuid.UUID) -> ActionPackage | None:
        return await self.session.get(ActionPackage, package_id)

    async def create(self, payload: dict[str, Any]) -> ActionPackage:
        row = ActionPackage(**payload)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row
