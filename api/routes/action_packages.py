from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_action_package_repo, get_company_profile_repo, get_opportunity_repo
from api.repositories.action_package import ActionPackageRepository
from api.repositories.company_profile import CompanyProfileRepository
from api.repositories.opportunity import OpportunityRepository
from api.schemas.action_package import ActionPackage
from api.schemas.action_package_create import ActionPackageCreate

router = APIRouter(prefix="/action-packages", tags=["action-packages"])


@router.post("", response_model=ActionPackage, status_code=201)
async def create_action_package(
    payload: ActionPackageCreate,
    repo: ActionPackageRepository = Depends(get_action_package_repo),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repo),
    profile_repo: CompanyProfileRepository = Depends(get_company_profile_repo),
) -> ActionPackage:
    opp = await opp_repo.get(payload.opportunity_id)
    if opp is None:
        raise HTTPException(404, "Opportunity not found")
    profile = await profile_repo.get(payload.company_profile_id)
    if profile is None:
        raise HTTPException(404, "Company profile not found")
    row = await repo.create(payload.model_dump())
    return ActionPackage.model_validate(row, from_attributes=True)


@router.get("/{package_id}", response_model=ActionPackage)
async def get_action_package(
    package_id: uuid.UUID,
    repo: ActionPackageRepository = Depends(get_action_package_repo),
) -> ActionPackage:
    row = await repo.get(package_id)
    if row is None:
        raise HTTPException(404, "Action package not found")
    return ActionPackage.model_validate(row, from_attributes=True)
