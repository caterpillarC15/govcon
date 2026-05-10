from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.auth import AuthenticatedUser, require_user
from api.deps import get_company_profile_repo
from api.repositories.company_profile import CompanyProfileRepository
from api.schemas.company_profile import CompanyProfile
from api.schemas.company_profile_create import CompanyProfileCreate

router = APIRouter(prefix="/company-profiles", tags=["company-profiles"])


@router.get("", response_model=list[CompanyProfile])
async def list_profiles(
    user: AuthenticatedUser = Depends(require_user),
    repo: CompanyProfileRepository = Depends(get_company_profile_repo),
) -> list[CompanyProfile]:
    rows = await repo.list_owned(user.id)
    return [CompanyProfile.model_validate(row) for row in rows]


@router.post("", response_model=CompanyProfile, status_code=201)
async def create_profile(
    payload: CompanyProfileCreate,
    user: AuthenticatedUser = Depends(require_user),
    repo: CompanyProfileRepository = Depends(get_company_profile_repo),
) -> CompanyProfile:
    data = payload.model_dump(exclude_none=True)
    data["owner_profile_id"] = str(user.id)
    row = await repo.create(data)
    return CompanyProfile.model_validate(row)


@router.get("/{profile_id}", response_model=CompanyProfile)
async def get_profile(
    profile_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    repo: CompanyProfileRepository = Depends(get_company_profile_repo),
) -> CompanyProfile:
    row = await repo.get_owned(profile_id, user.id)
    if row is None:
        raise HTTPException(404, "Company profile not found")
    return CompanyProfile.model_validate(row)
