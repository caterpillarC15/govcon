"""FastAPI dependency providers."""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from supabase import AsyncClient

from api.db import get_client
from api.llm import LLM
from api.repositories.action_package import ActionPackageRepository
from api.repositories.agent_run import AgentRunRepository
from api.repositories.company_profile import CompanyProfileRepository
from api.repositories.opportunity import OpportunityRepository
from api.repositories.profile import ProfileRepository
from api.repositories.waitlist import WaitlistRepository
from api.storage_adapter import StorageAdapter


async def get_supabase() -> AsyncClient:
    return await get_client()


def get_company_profile_repo(
    client: AsyncClient = Depends(get_supabase),
) -> CompanyProfileRepository:
    return CompanyProfileRepository(client)


def get_agent_run_repo(
    client: AsyncClient = Depends(get_supabase),
) -> AgentRunRepository:
    return AgentRunRepository(client)


def get_opportunity_repo(
    client: AsyncClient = Depends(get_supabase),
) -> OpportunityRepository:
    return OpportunityRepository(client)


def get_action_package_repo(
    client: AsyncClient = Depends(get_supabase),
) -> ActionPackageRepository:
    return ActionPackageRepository(client)


def get_profile_repo(
    client: AsyncClient = Depends(get_supabase),
) -> ProfileRepository:
    return ProfileRepository(client)


def get_waitlist_repo(
    client: AsyncClient = Depends(get_supabase),
) -> WaitlistRepository:
    return WaitlistRepository(client)


@lru_cache
def _llm_singleton() -> LLM:
    return LLM()


def get_llm() -> LLM:
    return _llm_singleton()


def get_storage() -> StorageAdapter:
    return StorageAdapter()
