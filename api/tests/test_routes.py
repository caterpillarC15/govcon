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


# ─── POST analysis writes (Task 0.1) ───────────────────────────────────────


async def _seed_opp_and_profile(db_session) -> tuple[OpportunityModel, CompanyProfileModel]:
    profile = CompanyProfileModel(
        id=uuid.uuid4(), name="POST Co", preferred_role="either"
    )
    opp = OpportunityModel(
        id=uuid.uuid4(),
        title="POST RFP",
        agency="POST Agency",
        solicitation_number="POST-001",
        attachments=[],
    )
    db_session.add_all([profile, opp])
    await db_session.commit()
    return opp, profile


async def test_post_requirement_persists_and_returns_201(client, db_session) -> None:
    opp, profile = await _seed_opp_and_profile(db_session)
    payload = {
        "type": "eligibility",
        "title": "Small business set-aside",
        "value": "Total small business set-aside",
        "description": "Reserved per FAR 19.502-2.",
        "confidence": "high",
        "evidence_snippet": "Set aside for small businesses.",
        "source_document": "RFP-001.pdf",
        "page_number": 3,
        "is_blocker": False,
    }
    try:
        r = await client.post(f"/opportunities/{opp.id}/requirements", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["title"] == "Small business set-aside"
        assert body["confidence"] == "high"
        assert body["opportunity_id"] == str(opp.id)
        assert "id" in body
    finally:
        await db_session.delete(opp)
        await db_session.delete(profile)
        await db_session.commit()


async def test_post_requirement_404_on_unknown_opportunity(client) -> None:
    payload = {
        "type": "eligibility",
        "title": "X",
        "confidence": "high",
        "is_blocker": False,
    }
    r = await client.post(f"/opportunities/{uuid.uuid4()}/requirements", json=payload)
    assert r.status_code == 404


async def test_post_fit_score_persists_and_returns_201(client, db_session) -> None:
    opp, profile = await _seed_opp_and_profile(db_session)
    payload = {
        "company_profile_id": str(profile.id),
        "total_score": 88,
        "decision": "strong_pursue",
        "confidence": "high",
        "breakdown": {
            "capability": 18, "eligibility": 14, "naics": 9,
            "past_performance": 12, "certification": 9,
            "insurance_bonding": 8, "deadline": 10, "complexity": 4,
            "geography": 4,
        },
        "strengths": ["AWS GovCloud experience"],
        "weaknesses": [],
        "blockers": [],
        "missing_info": [],
        "recommended_next_action": "Begin proposal drafting.",
    }
    try:
        r = await client.post(f"/opportunities/{opp.id}/fit-score", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["total_score"] == 88
        assert body["decision"] == "strong_pursue"
        assert body["opportunity_id"] == str(opp.id)
    finally:
        await db_session.delete(opp)
        await db_session.delete(profile)
        await db_session.commit()


async def test_post_risk_persists_and_returns_201(client, db_session) -> None:
    opp, profile = await _seed_opp_and_profile(db_session)
    payload = {
        "company_profile_id": str(profile.id),
        "category": "deadline_too_close",
        "severity": "major",
        "title": "Tight deadline",
        "description": "Submission due in 5 days.",
        "evidence": "Section L: 5 days from posting.",
        "mitigation": "Decline or compress drafting.",
        "requires_human_review": True,
    }
    try:
        r = await client.post(f"/opportunities/{opp.id}/risks", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["category"] == "deadline_too_close"
        assert body["severity"] == "major"
        assert body["requires_human_review"] is True
    finally:
        await db_session.delete(opp)
        await db_session.delete(profile)
        await db_session.commit()


async def test_post_action_package_persists_and_returns_201(client, db_session) -> None:
    opp, profile = await _seed_opp_and_profile(db_session)
    payload = {
        "opportunity_id": str(opp.id),
        "company_profile_id": str(profile.id),
        "executive_summary": "Strong fit. Proceed to drafting.",
        "decision": "strong_pursue",
        "fit_score": 88,
        "fit_rationale": "NAICS aligned, capabilities match.",
        "compliance_matrix": [
            {"requirement": "Small business", "status": "met",
             "evidence": "Self-cert in SAM", "next_action": None, "owner": "Capture"}
        ],
        "risk_register": [],
        "proposal_checklist": ["Verify SAM registration"],
        "timeline": [{"date": "2026-06-01", "task": "Kickoff", "owner": "PM"}],
        "approval_required": ["Authorized review required before submission."],
    }
    pkg_id = None
    try:
        r = await client.post("/action-packages", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        pkg_id = uuid.UUID(body["id"])
        assert body["decision"] == "strong_pursue"
        assert body["executive_summary"] == "Strong fit. Proceed to drafting."
        assert body["opportunity_id"] == str(opp.id)
    finally:
        if pkg_id:
            pkg_row = await db_session.get(ActionPackageModel, pkg_id)
            if pkg_row:
                await db_session.delete(pkg_row)
        await db_session.delete(opp)
        await db_session.delete(profile)
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
