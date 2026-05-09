from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_opportunity_repo
from api.repositories.opportunity import OpportunityRepository
from api.schemas.extracted_requirement import ExtractedRequirement
from api.schemas.fit_score import FitScore
from api.schemas.opportunity import Opportunity
from api.schemas.risk_flag import RiskFlag

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
