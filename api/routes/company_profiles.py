from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_company_profile_repo
from api.repositories.company_profile import CompanyProfileRepository
from api.schemas.company_profile import CompanyProfile
from api.schemas.company_profile_create import CompanyProfileCreate

router = APIRouter(prefix="/company-profiles", tags=["company-profiles"])


@router.post("", response_model=CompanyProfile, status_code=201)
async def create_profile(
    payload: CompanyProfileCreate,
    repo: CompanyProfileRepository = Depends(get_company_profile_repo),
) -> CompanyProfile:
    row = await repo.create(payload.model_dump(exclude_none=True))
    return CompanyProfile.model_validate(row, from_attributes=True)


@router.get("/{profile_id}", response_model=CompanyProfile)
async def get_profile(
    profile_id: uuid.UUID,
    repo: CompanyProfileRepository = Depends(get_company_profile_repo),
) -> CompanyProfile:
    row = await repo.get(profile_id)
    if row is None:
        raise HTTPException(404, "Company profile not found")
    return CompanyProfile.model_validate(row, from_attributes=True)
