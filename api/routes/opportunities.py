from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_opportunity_repo
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
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> Opportunity:
    row = await repo.get(opportunity_id)
    if row is None:
        raise HTTPException(404, "Opportunity not found")
    return Opportunity.model_validate(row, from_attributes=True)


@router.get("/{opportunity_id}/requirements", response_model=list[ExtractedRequirement])
async def list_requirements(
    opportunity_id: uuid.UUID,
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> list[ExtractedRequirement]:
    rows = await repo.requirements(opportunity_id)
    return [ExtractedRequirement.model_validate(r, from_attributes=True) for r in rows]


@router.get("/{opportunity_id}/fit-score", response_model=FitScore)
async def get_fit_score(
    opportunity_id: uuid.UUID,
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> FitScore:
    row = await repo.latest_fit_score(opportunity_id)
    if row is None:
        raise HTTPException(404, "No fit score for this opportunity yet")
    return FitScore.model_validate(row, from_attributes=True)


@router.get("/{opportunity_id}/risks", response_model=list[RiskFlag])
async def list_risks(
    opportunity_id: uuid.UUID,
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> list[RiskFlag]:
    rows = await repo.risks(opportunity_id)
    return [RiskFlag.model_validate(r, from_attributes=True) for r in rows]


@router.post("/{opportunity_id}/requirements", response_model=ExtractedRequirement, status_code=201)
async def create_requirement(
    opportunity_id: uuid.UUID,
    payload: ExtractedRequirementCreate,
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> ExtractedRequirement:
    opp = await repo.get(opportunity_id)
    if opp is None:
        raise HTTPException(404, "Opportunity not found")
    row = await repo.create_requirement(opportunity_id, payload.model_dump(exclude_none=True))
    return ExtractedRequirement.model_validate(row, from_attributes=True)


@router.post("/{opportunity_id}/fit-score", response_model=FitScore, status_code=201)
async def create_fit_score(
    opportunity_id: uuid.UUID,
    payload: FitScoreCreate,
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> FitScore:
    opp = await repo.get(opportunity_id)
    if opp is None:
        raise HTTPException(404, "Opportunity not found")
    row = await repo.create_fit_score(opportunity_id, payload.model_dump())
    return FitScore.model_validate(row, from_attributes=True)


@router.post("/{opportunity_id}/risks", response_model=RiskFlag, status_code=201)
async def create_risk(
    opportunity_id: uuid.UUID,
    payload: RiskFlagCreate,
    repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> RiskFlag:
    opp = await repo.get(opportunity_id)
    if opp is None:
        raise HTTPException(404, "Opportunity not found")
    row = await repo.create_risk_flag(opportunity_id, payload.model_dump(exclude_none=True))
    return RiskFlag.model_validate(row, from_attributes=True)
