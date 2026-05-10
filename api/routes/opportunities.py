from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.auth import AuthenticatedUser, InternalActor, require_internal_actor, require_user
from api.deps import get_company_profile_repo, get_opportunity_repo
from api.repositories.company_profile import CompanyProfileRepository
from api.repositories.opportunity import OpportunityRepository
from api.schemas.extracted_requirement import ExtractedRequirement
from api.schemas.extracted_requirement_create import ExtractedRequirementCreate
from api.schemas.fit_score import FitScore
from api.schemas.fit_score_create import FitScoreCreate
from api.schemas.opportunity import Opportunity
from api.schemas.risk_flag import RiskFlag
from api.schemas.risk_flag_create import RiskFlagCreate

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("/{opportunity_id}", response_model=Opportunity)
async def get_opportunity(
    opportunity_id: uuid.UUID,
    _user: AuthenticatedUser = Depends(require_user),
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> Opportunity:
    row = await repo.get(opportunity_id)
    if row is None:
        raise HTTPException(404, "Opportunity not found")
    return Opportunity.model_validate(row)


@router.get("/{opportunity_id}/requirements", response_model=list[ExtractedRequirement])
async def list_requirements(
    opportunity_id: uuid.UUID,
    _user: AuthenticatedUser = Depends(require_user),
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> list[ExtractedRequirement]:
    rows = await repo.requirements(opportunity_id)
    return [ExtractedRequirement.model_validate(r) for r in rows]


@router.post(
    "/{opportunity_id}/requirements",
    response_model=ExtractedRequirement,
    status_code=201,
)
async def create_requirement(
    opportunity_id: uuid.UUID,
    payload: ExtractedRequirementCreate,
    _actor: InternalActor = Depends(require_internal_actor),
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> ExtractedRequirement:
    if await repo.get(opportunity_id) is None:
        raise HTTPException(404, "Opportunity not found")
    row = await repo.create_requirement(opportunity_id, payload.model_dump())
    return ExtractedRequirement.model_validate(row)


@router.get("/{opportunity_id}/fit-score", response_model=FitScore)
async def get_fit_score(
    opportunity_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    repo: OpportunityRepository = Depends(get_opportunity_repo),
    profile_repo: CompanyProfileRepository = Depends(get_company_profile_repo),
) -> FitScore:
    row = await repo.latest_fit_score(opportunity_id)
    if row is None:
        raise HTTPException(404, "No fit score for this opportunity yet")
    profile_id = row.get("company_profile_id")
    if profile_id is None or await profile_repo.get_owned(uuid.UUID(str(profile_id)), user.id) is None:
        raise HTTPException(404, "No fit score for this opportunity yet")
    return FitScore.model_validate(row)


@router.post(
    "/{opportunity_id}/fit-score",
    response_model=FitScore,
    status_code=201,
)
async def create_fit_score(
    opportunity_id: uuid.UUID,
    payload: FitScoreCreate,
    _actor: InternalActor = Depends(require_internal_actor),
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> FitScore:
    if await repo.get(opportunity_id) is None:
        raise HTTPException(404, "Opportunity not found")
    row = await repo.create_fit_score(opportunity_id, payload.model_dump())
    return FitScore.model_validate(row)


@router.get("/{opportunity_id}/risks", response_model=list[RiskFlag])
async def list_risks(
    opportunity_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    repo: OpportunityRepository = Depends(get_opportunity_repo),
    profile_repo: CompanyProfileRepository = Depends(get_company_profile_repo),
) -> list[RiskFlag]:
    rows = await repo.risks(opportunity_id)
    owned_rows = []
    for row in rows:
        profile_id = row.get("company_profile_id")
        if profile_id is None:
            continue
        if await profile_repo.get_owned(uuid.UUID(str(profile_id)), user.id) is not None:
            owned_rows.append(row)
    return [RiskFlag.model_validate(r) for r in owned_rows]


@router.post(
    "/{opportunity_id}/risks",
    response_model=RiskFlag,
    status_code=201,
)
async def create_risk(
    opportunity_id: uuid.UUID,
    payload: RiskFlagCreate,
    _actor: InternalActor = Depends(require_internal_actor),
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> RiskFlag:
    if await repo.get(opportunity_id) is None:
        raise HTTPException(404, "Opportunity not found")
    row = await repo.create_risk(opportunity_id, payload.model_dump())
    return RiskFlag.model_validate(row)
