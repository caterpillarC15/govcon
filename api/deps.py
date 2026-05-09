"""FastAPI dependency providers."""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import SessionLocal
from api.repositories.action_package import ActionPackageRepository
from api.repositories.agent_run import AgentRunRepository
from api.repositories.company_profile import CompanyProfileRepository
from api.repositories.opportunity import OpportunityRepository


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def get_company_profile_repo(
    session: AsyncSession = Depends(get_session),
) -> CompanyProfileRepository:
    return CompanyProfileRepository(session)


def get_agent_run_repo(
    session: AsyncSession = Depends(get_session),
) -> AgentRunRepository:
    return AgentRunRepository(session)


def get_opportunity_repo(
    session: AsyncSession = Depends(get_session),
) -> OpportunityRepository:
    return OpportunityRepository(session)


def get_action_package_repo(
    session: AsyncSession = Depends(get_session),
) -> ActionPackageRepository:
    return ActionPackageRepository(session)
