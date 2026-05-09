from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ActionPackage


class ActionPackageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, package_id: uuid.UUID) -> ActionPackage | None:
        return await self.session.get(ActionPackage, package_id)
