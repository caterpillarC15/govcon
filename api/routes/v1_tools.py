"""Public agent-callable mirror of /tools/<name> at /api/v1/tools/<name>.

Same dispatch as api/routes/tools.py, but the auth dep accepts EITHER
the shared INTERNAL_API_KEY (Sprint B compatibility) OR a per-user
gck_ bearer key. Per-key rate limiting happens inside the auth dep.

The ToolResponse envelope is reused from api.routes.tools — do NOT
redefine it here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from supabase import AsyncClient

from api.auth import AgentActor, require_agent_or_internal
from api.config import settings
from api.deps import get_llm, get_storage, get_supabase
from api.routes.tools import ToolResponse
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
from api.skills.parse_goal.skill import parse_goal
from api.skills.parse_pdf.skill import parse_pdf
from api.skills.query_usaspending.skill import query_usaspending
from api.skills.rank_opportunities.skill import rank_opportunities
from api.skills.score_fit.skill import score_fit
from api.skills.search_sam.skill import search_sam_opportunities
from api.storage_adapter import StorageAdapter

router = APIRouter(prefix="/api/v1/tools", tags=["v1-tools"])


@router.post("/parse-goal", response_model=ToolResponse)
async def parse_goal_route(
    payload: ParseGoalRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
    llm=Depends(get_llm),
) -> ToolResponse:
    data, metrics = await parse_goal(payload.model_dump(), llm=llm)
    return ToolResponse(data=data, metrics=metrics)


@router.post("/rank-opportunities", response_model=ToolResponse)
async def rank_opportunities_route(
    payload: RankOpportunitiesRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
) -> ToolResponse:
    out = rank_opportunities(payload.model_dump())
    return ToolResponse(data=out)


@router.post("/parse-pdf", response_model=ToolResponse)
async def parse_pdf_route(
    payload: ParsePdfRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
) -> ToolResponse:
    out = parse_pdf(payload.to_skill_input())
    return ToolResponse(data=out.model_dump())


@router.post("/extract-requirements", response_model=ToolResponse)
async def extract_requirements_route(
    payload: ExtractRequirementsRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
    llm=Depends(get_llm),
) -> ToolResponse:
    data, metrics = await extract_requirements(payload.to_skill_input(), llm=llm)
    return ToolResponse(data=data.model_dump(), metrics=metrics)


@router.post("/score-fit", response_model=ToolResponse)
async def score_fit_route(
    payload: ScoreFitRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
    llm=Depends(get_llm),
) -> ToolResponse:
    data, metrics = await score_fit(payload.model_dump(), llm=llm)
    return ToolResponse(data=data, metrics=metrics)


@router.post("/detect-risks", response_model=ToolResponse)
async def detect_risks_route(
    payload: DetectRisksRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
    llm=Depends(get_llm),
) -> ToolResponse:
    data, metrics = await detect_risks(payload.model_dump(), llm=llm)
    return ToolResponse(data=data, metrics=metrics)


@router.post("/generate-action-package", response_model=ToolResponse)
async def generate_action_package_route(
    payload: GenerateActionPackageRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
    llm=Depends(get_llm),
) -> ToolResponse:
    data, metrics = await generate_action_package(payload.model_dump(), llm=llm)
    return ToolResponse(data=data, metrics=metrics)


@router.post("/search-sam", response_model=ToolResponse)
async def search_sam_route(
    payload: SearchSamRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
) -> ToolResponse:
    out = await search_sam_opportunities(
        payload.model_dump(exclude_none=False),
        api_key=settings.sam_api_key,
    )
    return ToolResponse(data=out)


@router.post("/fetch-attachment", response_model=ToolResponse)
async def fetch_attachment_route(
    payload: FetchAttachmentRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
    storage: StorageAdapter = Depends(get_storage),
) -> ToolResponse:
    data = await fetch_attachment(payload.model_dump(), storage=storage)
    return ToolResponse(data=data)


@router.post("/load-seeded-opportunities", response_model=ToolResponse)
async def load_seeded_opportunities_route(
    payload: LoadSeededOpportunitiesRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
    client: AsyncClient = Depends(get_supabase),
) -> ToolResponse:
    data = await load_seeded_opportunities(payload.model_dump(), client=client)
    return ToolResponse(data=data)


@router.post("/query-usaspending", response_model=ToolResponse)
async def query_usaspending_v1(
    payload: QueryUsaspendingRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
) -> ToolResponse:
    out = await query_usaspending(payload.model_dump(exclude_none=False))
    return ToolResponse(data=out)
