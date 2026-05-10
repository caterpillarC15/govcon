"""Internal HTTP surface for the SamRail skills.

Every endpoint POST /tools/<name> requires X-Internal-API-Key (InternalActor).
Responses share a uniform `{"data": ...}` envelope (per PRD v1.2.6 —
every skill is deterministic, no `metrics` field).

Routes intentionally hold no business logic — they validate input via
api.schemas.tool_requests, dispatch to the underlying skill, and return.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import AsyncClient

from api.auth import InternalActor, require_internal_actor
from api.config import settings
from api.deps import get_storage, get_supabase
from api.schemas.tool_requests import (
    DetectRisksRequest,
    ExtractRequirementsRequest,
    FetchAttachmentRequest,
    GenerateActionPackageRequest,
    LoadSeededOpportunitiesRequest,
    ParseGoalRequest,
    ParsePdfRequest,
    QueryUsaspendingRequest,
    RankOpportunitiesRequest,
    ScoreFitRequest,
    SearchSamRequest,
)
from api.skills.detect_risks.skill import detect_risks
from api.skills.extract_requirements.skill import extract_requirements
from api.skills.fetch_attachment.skill import fetch_attachment
from api.skills.generate_action_package.skill import generate_action_package
from api.skills.load_seeded_opportunities.skill import load_seeded_opportunities
from api.skills.parse_goal.skill import ParseGoalInput, parse_goal
from api.skills.parse_pdf.skill import parse_pdf
from api.skills.query_usaspending.skill import query_usaspending
from api.skills.rank_opportunities.skill import rank_opportunities
from api.skills.score_fit.skill import score_fit
from api.skills.search_sam.skill import search_sam_opportunities
from api.storage_adapter import StorageAdapter

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolResponse(BaseModel):
    data: Any


@router.post("/parse-goal", response_model=ToolResponse)
async def parse_goal_route(
    payload: ParseGoalRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    # PRD v1.2.6: parse_goal is now a deterministic input validator;
    # Michaela does the goal parsing in her own agent context.
    data = await parse_goal(
        ParseGoalInput(
            goal=payload.goal,
            company_profile=payload.company_profile,
        ),
    )
    return ToolResponse(data=data)


@router.post("/rank-opportunities", response_model=ToolResponse)
async def rank_opportunities_route(
    payload: RankOpportunitiesRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out = rank_opportunities(payload.model_dump())
    return ToolResponse(data=out)


@router.post("/parse-pdf", response_model=ToolResponse)
async def parse_pdf_route(
    payload: ParsePdfRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out = parse_pdf(payload.to_skill_input())
    return ToolResponse(data=out.model_dump())


@router.post("/extract-requirements", response_model=ToolResponse)
async def extract_requirements_route(
    payload: ExtractRequirementsRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    # PRD v1.2.6: skill is deterministic. Two flows:
    #  - omit `requirements` → returns chunks for Gate's agent context
    #  - include `requirements` → returns §11-validated set
    data = await extract_requirements(payload.to_skill_input())
    return ToolResponse(data=data)


@router.post("/score-fit", response_model=ToolResponse)
async def score_fit_route(
    payload: ScoreFitRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    # PRD v1.2.6: deterministic. §11.1 short-circuit + decision-band
    # normalizer. Lenny supplies total_score for non-blocker scoring.
    data = await score_fit(payload.model_dump())
    return ToolResponse(data=data)


@router.post("/detect-risks", response_model=ToolResponse)
async def detect_risks_route(
    payload: DetectRisksRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    # PRD v1.2.6: skill validates Gate-emitted risks; no LLM.
    data = await detect_risks(payload.model_dump())
    return ToolResponse(data=data)


@router.post("/generate-action-package", response_model=ToolResponse)
async def generate_action_package_route(
    payload: GenerateActionPackageRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    # PRD v1.2.6: deterministic. reject_summary mode unchanged;
    # full mode validates Roy's content + enforces §5.13.
    data = await generate_action_package(payload.model_dump())
    return ToolResponse(data=data)


@router.post("/search-sam", response_model=ToolResponse)
async def search_sam_route(
    payload: SearchSamRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out = await search_sam_opportunities(
        payload.model_dump(exclude_none=False),
        api_key=settings.sam_api_key,
    )
    return ToolResponse(data=out)


@router.post("/fetch-attachment", response_model=ToolResponse)
async def fetch_attachment_route(
    payload: FetchAttachmentRequest,
    _actor: InternalActor = Depends(require_internal_actor),
    storage: StorageAdapter = Depends(get_storage),
) -> ToolResponse:
    data = await fetch_attachment(payload.model_dump(), storage=storage)
    return ToolResponse(data=data)


@router.post("/load-seeded-opportunities", response_model=ToolResponse)
async def load_seeded_opportunities_route(
    payload: LoadSeededOpportunitiesRequest,
    _actor: InternalActor = Depends(require_internal_actor),
    client: AsyncClient = Depends(get_supabase),
) -> ToolResponse:
    data = await load_seeded_opportunities(payload.model_dump(), client=client)
    return ToolResponse(data=data)


@router.post("/query-usaspending", response_model=ToolResponse)
async def query_usaspending_route(
    payload: QueryUsaspendingRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out = await query_usaspending(payload.model_dump(exclude_none=False))
    return ToolResponse(data=out)
