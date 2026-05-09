"""Happy-path integration tests for the 11 API endpoints (CONTRACTS.md §6).

Hits the live local Postgres + Redis. Each test cleans up the rows it creates.
"""
from __future__ import annotations

import asyncio
import json
import uuid

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

from api.db.models import (
    ActionPackage as ActionPackageModel,
)
from api.db.models import (
    AgentRun as AgentRunModel,
)
from api.db.models import (
    CompanyProfile as CompanyProfileModel,
)
from api.db.models import (
    ExtractedRequirement as ExtractedRequirementModel,
)
from api.db.models import (
    FitScore as FitScoreModel,
)
from api.db.models import (
    Opportunity as OpportunityModel,
)
from api.db.models import (
    RiskFlag as RiskFlagModel,
)
from api.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            yield c


@pytest_asyncio.fixture
async def db_session():
    """Direct DB access for setup/cleanup outside the route flow."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from api.config import settings

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    Maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with Maker() as s:
            yield s
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"DB unreachable: {exc}")
    finally:
        await engine.dispose()


# ─── /healthz ───────────────────────────────────────────────────────────────


async def test_healthz(client) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ─── /company-profiles ─────────────────────────────────────────────────────


async def test_company_profile_create_and_get(client, db_session) -> None:
    payload = {
        "name": "Acme Cyber LLC",
        "capabilities": ["RMF"],
        "small_business_status": True,
        "preferred_role": "either",
    }
    r = await client.post("/company-profiles", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    profile_id = body["id"]
    assert body["name"] == "Acme Cyber LLC"
    assert body["capabilities"] == ["RMF"]

    r2 = await client.get(f"/company-profiles/{profile_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == profile_id

    # cleanup
    row = await db_session.get(CompanyProfileModel, uuid.UUID(profile_id))
    if row:
        await db_session.delete(row)
        await db_session.commit()


async def test_company_profile_404(client) -> None:
    r = await client.get(f"/company-profiles/{uuid.uuid4()}")
    assert r.status_code == 404


# ─── /agent-runs ───────────────────────────────────────────────────────────


async def test_agent_run_create_with_profile_id(client, db_session) -> None:
    pr = await client.post("/company-profiles", json={"name": "Test"})
    profile_id = pr.json()["id"]

    r = await client.post(
        "/agent-runs",
        json={"goal": "cyber 60d", "profile_id": profile_id},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["goal"] == "cyber 60d"
    assert body["status"] == "pending"
    assert body["company_profile_id"] == profile_id
    run_id = body["id"]

    g = await client.get(f"/agent-runs/{run_id}")
    assert g.status_code == 200
    assert g.json()["id"] == run_id

    # Allow background task started by POST to fail-fast on closed redis;
    # cleanup of run + profile.
    row = await db_session.get(AgentRunModel, uuid.UUID(run_id))
    if row:
        await db_session.delete(row)
    pr_row = await db_session.get(CompanyProfileModel, uuid.UUID(profile_id))
    if pr_row:
        await db_session.delete(pr_row)
    await db_session.commit()


async def test_agent_run_create_with_inline_profile(client, db_session) -> None:
    r = await client.post(
        "/agent-runs",
        json={"goal": "cyber 60d", "profile": {"name": "Inline Co"}},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    run_id = body["id"]
    profile_id = body["company_profile_id"]
    assert profile_id is not None

    pr = await client.get(f"/company-profiles/{profile_id}")
    assert pr.status_code == 200
    assert pr.json()["name"] == "Inline Co"

    # cleanup
    row = await db_session.get(AgentRunModel, uuid.UUID(run_id))
    if row:
        await db_session.delete(row)
    pr_row = await db_session.get(CompanyProfileModel, uuid.UUID(profile_id))
    if pr_row:
        await db_session.delete(pr_row)
    await db_session.commit()


async def test_agent_run_bad_profile_id(client) -> None:
    r = await client.post(
        "/agent-runs",
        json={"goal": "cyber", "profile_id": str(uuid.uuid4())},
    )
    assert r.status_code == 400


async def test_agent_run_404(client) -> None:
    r = await client.get(f"/agent-runs/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_agent_run_opportunities_empty(client, db_session) -> None:
    pr = await client.post("/company-profiles", json={"name": "Test"})
    profile_id = pr.json()["id"]
    r = await client.post(
        "/agent-runs", json={"goal": "x", "profile_id": profile_id}
    )
    run_id = r.json()["id"]
    opps = await client.get(f"/agent-runs/{run_id}/opportunities")
    assert opps.status_code == 200
    assert opps.json() == []

    # cleanup
    run_row = await db_session.get(AgentRunModel, uuid.UUID(run_id))
    if run_row:
        await db_session.delete(run_row)
    pr_row = await db_session.get(CompanyProfileModel, uuid.UUID(profile_id))
    if pr_row:
        await db_session.delete(pr_row)
    await db_session.commit()


# ─── /opportunities ────────────────────────────────────────────────────────


async def test_opportunity_404(client) -> None:
    r = await client.get(f"/opportunities/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_opportunity_round_trip_with_children(client, db_session) -> None:
    """Seed opp + requirements + fit_score + risk via DB, hit each route."""
    profile_row = CompanyProfileModel(
        id=uuid.uuid4(),
        name="Seed Co",
        preferred_role="either",
    )
    opp_row = OpportunityModel(
        id=uuid.uuid4(),
        title="Seed RFP",
        agency="Seed Agency",
        solicitation_number="SEED-001",
        attachments=[],
    )
    req_row = ExtractedRequirementModel(
        id=uuid.uuid4(),
        opportunity_id=opp_row.id,
        type="security",
        title="Secret clearance",
        confidence="high",
        is_blocker=True,
    )
    fit_row = FitScoreModel(
        id=uuid.uuid4(),
        opportunity_id=opp_row.id,
        company_profile_id=profile_row.id,
        total_score=88,
        decision="strong_pursue",
        confidence="high",
        breakdown={
            "capability": 18, "eligibility": 14, "naics": 9,
            "past_performance": 13, "certification": 8, "insurance_bonding": 9,
            "deadline": 9, "complexity": 4, "geography": 4,
        },
        strengths=["NAICS aligned"],
        weaknesses=[],
        blockers=[],
        missing_info=[],
    )
    risk_row = RiskFlagModel(
        id=uuid.uuid4(),
        opportunity_id=opp_row.id,
        company_profile_id=profile_row.id,
        category="deadline_too_close",
        severity="major",
        title="Tight deadline",
        description="Submission due in 14 days.",
        requires_human_review=False,
    )
    db_session.add_all([profile_row, opp_row])
    await db_session.commit()
    db_session.add_all([req_row, fit_row, risk_row])
    await db_session.commit()

    try:
        opp = await client.get(f"/opportunities/{opp_row.id}")
        assert opp.status_code == 200
        assert opp.json()["title"] == "Seed RFP"

        reqs = await client.get(f"/opportunities/{opp_row.id}/requirements")
        assert reqs.status_code == 200
        assert len(reqs.json()) == 1
        assert reqs.json()[0]["title"] == "Secret clearance"

        fit = await client.get(f"/opportunities/{opp_row.id}/fit-score")
        assert fit.status_code == 200
        assert fit.json()["decision"] == "strong_pursue"

        risks = await client.get(f"/opportunities/{opp_row.id}/risks")
        assert risks.status_code == 200
        assert len(risks.json()) == 1
        assert risks.json()[0]["severity"] == "major"
    finally:
        # Cascade handles req/fit/risk
        await db_session.delete(opp_row)
        await db_session.delete(profile_row)
        await db_session.commit()


async def test_opportunity_fit_score_404(client) -> None:
    r = await client.get(f"/opportunities/{uuid.uuid4()}/fit-score")
    assert r.status_code == 404


# ─── /action-packages ──────────────────────────────────────────────────────


async def test_action_package_round_trip(client, db_session) -> None:
    profile_row = CompanyProfileModel(id=uuid.uuid4(), name="AP Co", preferred_role="either")
    opp_row = OpportunityModel(
        id=uuid.uuid4(),
        title="AP RFP",
        agency="AP Agency",
        solicitation_number="AP-001",
        attachments=[],
    )
    pkg_row = ActionPackageModel(
        id=uuid.uuid4(),
        opportunity_id=opp_row.id,
        company_profile_id=profile_row.id,
        executive_summary="Strong fit.",
        decision="strong_pursue",
        fit_score=88,
        fit_rationale="aligned",
        compliance_matrix=[],
        risk_register=[],
        proposal_checklist=[],
        timeline=[],
        partner_suggestions=[],
        approval_required=[],
    )
    db_session.add_all([profile_row, opp_row])
    await db_session.commit()
    db_session.add(pkg_row)
    await db_session.commit()

    try:
        r = await client.get(f"/action-packages/{pkg_row.id}")
        assert r.status_code == 200
        assert r.json()["executive_summary"] == "Strong fit."
    finally:
        await db_session.delete(pkg_row)
        await db_session.delete(opp_row)
        await db_session.delete(profile_row)
        await db_session.commit()


async def test_action_package_404(client) -> None:
    r = await client.get(f"/action-packages/{uuid.uuid4()}")
    assert r.status_code == 404


# ─── POST /opportunities/:id/requirements ──────────────────────────────────


async def test_post_requirement_201(client, db_session) -> None:
    """POST /opportunities/{id}/requirements creates and returns the requirement."""
    opp_row = OpportunityModel(
        id=uuid.uuid4(),
        title="Req POST RFP",
        agency="Agency A",
        solicitation_number="REQ-POST-001",
        attachments=[],
    )
    db_session.add(opp_row)
    await db_session.commit()

    payload = {
        "type": "security",
        "title": "TS/SCI Clearance Required",
        "confidence": "high",
        "is_blocker": True,
        "description": "Personnel must hold TS/SCI.",
        "value": None,
        "evidence_snippet": None,
        "source_document": None,
        "page_number": None,
    }
    try:
        r = await client.post(f"/opportunities/{opp_row.id}/requirements", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["title"] == "TS/SCI Clearance Required"
        assert body["type"] == "security"
        assert body["is_blocker"] is True
        assert body["opportunity_id"] == str(opp_row.id)
        assert "id" in body
        assert "created_at" in body
    finally:
        await db_session.delete(opp_row)
        await db_session.commit()


async def test_post_requirement_404(client) -> None:
    """POST /opportunities/{id}/requirements returns 404 for unknown opportunity."""
    payload = {
        "type": "eligibility",
        "title": "Must be 8(a)",
        "confidence": "high",
        "is_blocker": False,
    }
    r = await client.post(f"/opportunities/{uuid.uuid4()}/requirements", json=payload)
    assert r.status_code == 404


# ─── POST /opportunities/:id/fit-score ─────────────────────────────────────


async def test_post_fit_score_201(client, db_session) -> None:
    """POST /opportunities/{id}/fit-score creates and returns the fit score."""
    profile_row = CompanyProfileModel(id=uuid.uuid4(), name="FitPost Co", preferred_role="either")
    opp_row = OpportunityModel(
        id=uuid.uuid4(),
        title="FitScore POST RFP",
        agency="Agency B",
        solicitation_number="FIT-POST-001",
        attachments=[],
    )
    db_session.add_all([profile_row, opp_row])
    await db_session.commit()

    payload = {
        "company_profile_id": str(profile_row.id),
        "total_score": 75,
        "decision": "pursue",
        "confidence": "medium",
        "breakdown": {
            "capability": 15,
            "eligibility": 12,
            "naics": 8,
            "past_performance": 10,
            "certification": 7,
            "insurance_bonding": 7,
            "deadline": 8,
            "complexity": 4,
            "geography": 4,
        },
        "strengths": ["NAICS match"],
        "weaknesses": ["No past performance"],
        "blockers": [],
        "missing_info": ["Bonding capacity"],
        "recommended_next_action": "Start proposal",
    }
    try:
        r = await client.post(f"/opportunities/{opp_row.id}/fit-score", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["total_score"] == 75
        assert body["decision"] == "pursue"
        assert body["opportunity_id"] == str(opp_row.id)
        assert body["company_profile_id"] == str(profile_row.id)
        assert "id" in body
    finally:
        await db_session.delete(opp_row)
        await db_session.delete(profile_row)
        await db_session.commit()


async def test_post_fit_score_404(client) -> None:
    """POST /opportunities/{id}/fit-score returns 404 for unknown opportunity."""
    payload = {
        "company_profile_id": str(uuid.uuid4()),
        "total_score": 50,
        "decision": "maybe",
        "confidence": "low",
        "breakdown": {
            "capability": 10,
            "eligibility": 8,
            "naics": 5,
            "past_performance": 6,
            "certification": 5,
            "insurance_bonding": 5,
            "deadline": 5,
            "complexity": 3,
            "geography": 3,
        },
        "strengths": [],
        "weaknesses": [],
        "blockers": [],
        "missing_info": [],
    }
    r = await client.post(f"/opportunities/{uuid.uuid4()}/fit-score", json=payload)
    assert r.status_code == 404


# ─── POST /opportunities/:id/risks ─────────────────────────────────────────


async def test_post_risk_201(client, db_session) -> None:
    """POST /opportunities/{id}/risks creates and returns the risk flag."""
    profile_row = CompanyProfileModel(id=uuid.uuid4(), name="RiskPost Co", preferred_role="either")
    opp_row = OpportunityModel(
        id=uuid.uuid4(),
        title="Risk POST RFP",
        agency="Agency C",
        solicitation_number="RISK-POST-001",
        attachments=[],
    )
    db_session.add_all([profile_row, opp_row])
    await db_session.commit()

    payload = {
        "company_profile_id": str(profile_row.id),
        "category": "deadline_too_close",
        "severity": "major",
        "title": "Proposal due in 10 days",
        "description": "Insufficient time to prepare a compliant proposal.",
        "evidence": "Solicitation release date vs due date.",
        "mitigation": "Start immediately, assign full team.",
        "requires_human_review": True,
    }
    try:
        r = await client.post(f"/opportunities/{opp_row.id}/risks", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["title"] == "Proposal due in 10 days"
        assert body["severity"] == "major"
        assert body["opportunity_id"] == str(opp_row.id)
        assert body["company_profile_id"] == str(profile_row.id)
        assert "id" in body
    finally:
        await db_session.delete(opp_row)
        await db_session.delete(profile_row)
        await db_session.commit()


async def test_post_risk_404(client) -> None:
    """POST /opportunities/{id}/risks returns 404 for unknown opportunity."""
    payload = {
        "company_profile_id": str(uuid.uuid4()),
        "category": "scope_mismatch",
        "severity": "moderate",
        "title": "Scope out of range",
        "description": "Company capabilities do not match scope.",
        "requires_human_review": False,
    }
    r = await client.post(f"/opportunities/{uuid.uuid4()}/risks", json=payload)
    assert r.status_code == 404


# ─── POST /action-packages ──────────────────────────────────────────────────


async def test_post_action_package_201(client, db_session) -> None:
    """POST /action-packages creates and returns the action package."""
    profile_row = CompanyProfileModel(id=uuid.uuid4(), name="APPost Co", preferred_role="either")
    opp_row = OpportunityModel(
        id=uuid.uuid4(),
        title="AP POST RFP",
        agency="Agency D",
        solicitation_number="AP-POST-001",
        attachments=[],
    )
    db_session.add_all([profile_row, opp_row])
    await db_session.commit()

    payload = {
        "opportunity_id": str(opp_row.id),
        "company_profile_id": str(profile_row.id),
        "executive_summary": "Strong candidate — pursue.",
        "decision": "pursue",
        "fit_score": 78,
        "fit_rationale": "Capabilities align with scope.",
        "compliance_matrix": [
            {"requirement": "ISO 27001", "status": "met", "evidence": "Current cert", "next_action": None, "owner": None}
        ],
        "risk_register": [
            {"risk": "Deadline tight", "severity": "moderate", "explanation": "14 days only", "mitigation": "Mobilize team"}
        ],
        "proposal_checklist": ["Draft executive summary", "Gather past performance docs"],
        "timeline": [
            {"date": "2026-05-15", "task": "Submit proposal", "owner": "BD Lead"}
        ],
        "partner_suggestions": [],
        "outreach_draft": None,
        "approval_required": ["VP signature required"],
    }
    try:
        r = await client.post("/action-packages", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["executive_summary"] == "Strong candidate — pursue."
        assert body["fit_score"] == 78
        assert body["opportunity_id"] == str(opp_row.id)
        assert body["company_profile_id"] == str(profile_row.id)
        assert "id" in body
    finally:
        await db_session.delete(opp_row)
        await db_session.delete(profile_row)
        await db_session.commit()


async def test_post_action_package_omit_optional_fields(client, db_session) -> None:
    """POST /action-packages succeeds even when partner_suggestions + outreach_draft are omitted."""
    profile_row = CompanyProfileModel(id=uuid.uuid4(), name="APMin Co", preferred_role="either")
    opp_row = OpportunityModel(
        id=uuid.uuid4(),
        title="AP MIN RFP",
        agency="Agency E",
        solicitation_number="AP-MIN-001",
        attachments=[],
    )
    db_session.add_all([profile_row, opp_row])
    await db_session.commit()

    # No partner_suggestions or outreach_draft in payload
    payload = {
        "opportunity_id": str(opp_row.id),
        "company_profile_id": str(profile_row.id),
        "executive_summary": "Minimal payload.",
        "decision": "maybe",
        "fit_score": 55,
        "fit_rationale": "Partial match.",
        "compliance_matrix": [],
        "risk_register": [],
        "proposal_checklist": [],
        "timeline": [],
        "approval_required": [],
    }
    try:
        r = await client.post("/action-packages", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["fit_score"] == 55
        assert body["partner_suggestions"] == []
        assert body["outreach_draft"] is None
    finally:
        await db_session.delete(opp_row)
        await db_session.delete(profile_row)
        await db_session.commit()


async def test_post_action_package_404_missing_opportunity(client, db_session) -> None:
    """POST /action-packages returns 404 when opportunity_id doesn't exist."""
    profile_row = CompanyProfileModel(id=uuid.uuid4(), name="AP404 Co", preferred_role="either")
    db_session.add(profile_row)
    await db_session.commit()

    payload = {
        "opportunity_id": str(uuid.uuid4()),
        "company_profile_id": str(profile_row.id),
        "executive_summary": "Won't be stored.",
        "decision": "reject",
        "fit_score": 20,
        "fit_rationale": "Does not qualify.",
        "compliance_matrix": [],
        "risk_register": [],
        "proposal_checklist": [],
        "timeline": [],
        "approval_required": [],
    }
    try:
        r = await client.post("/action-packages", json=payload)
        assert r.status_code == 404
    finally:
        await db_session.delete(profile_row)
        await db_session.commit()


# ─── /agent-runs/:id/stream (SSE smoke) ────────────────────────────────────


async def test_sse_replays_first_event(client, db_session) -> None:
    """End-to-end: POST a run, connect to /stream, assert we get a properly-framed
    `run_started` SSE event back. This exercises the Redis pub/sub bridge and the
    pre-A9 replayer."""
    pr = await client.post("/company-profiles", json={"name": "SSE Co"})
    profile_id = pr.json()["id"]
    run_resp = await client.post(
        "/agent-runs", json={"goal": "sse smoke", "profile_id": profile_id}
    )
    run_id = run_resp.json()["id"]

    try:
        async with client.stream("GET", f"/agent-runs/{run_id}/stream") as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")

            event_lines: list[str] = []
            async for line in resp.aiter_lines():
                event_lines.append(line)
                # We need: `event: <type>`, `data: <json>`, blank
                if len(event_lines) >= 3:
                    break

        # Format: "event: run_started", "data: {...}", ""
        assert any(line.startswith("event: ") for line in event_lines)
        data_line = next((line for line in event_lines if line.startswith("data: ")), None)
        assert data_line is not None
        payload = json.loads(data_line[len("data: "):])
        assert payload["type"] == "run_started"
        assert payload["run_id"] == run_id
    finally:
        run_row = await db_session.get(AgentRunModel, uuid.UUID(run_id))
        if run_row:
            await db_session.delete(run_row)
        pr_row = await db_session.get(CompanyProfileModel, uuid.UUID(profile_id))
        if pr_row:
            await db_session.delete(pr_row)
        await db_session.commit()
