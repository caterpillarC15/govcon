"""Route-shape tests against the FakeSupabase in conftest.

Real Supabase integration tests live elsewhere; these guard the
FastAPI surface, payload validation, and 404 paths.
"""
from __future__ import annotations

import uuid

import pytest

from api.tests.conftest import TEST_INTERNAL_API_KEY, TEST_USER_ID

pytestmark = pytest.mark.asyncio

INTERNAL_HEADERS = {"X-Internal-API-Key": TEST_INTERNAL_API_KEY}


# ─── /company-profiles ─────────────────────────────────────────────────────


async def test_company_profile_create_and_get(client) -> None:
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


async def test_company_profile_list_is_owned(client) -> None:
    first = await client.post("/company-profiles", json={"name": "Owned Co"})
    assert first.status_code == 201

    listed = await client.get("/company-profiles")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Owned Co"


async def test_company_profile_404(client) -> None:
    r = await client.get(f"/company-profiles/{uuid.uuid4()}")
    assert r.status_code == 404


# ─── /agent-runs ───────────────────────────────────────────────────────────


async def test_agent_run_create_with_inline_profile(client) -> None:
    r = await client.post(
        "/agent-runs",
        json={"goal": "cyber 60d", "profile": {"name": "Inline Co"}},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["goal"] == "cyber 60d"
    assert body["status"] == "pending"
    assert body["company_profile_id"] is not None


async def test_agent_run_create_with_profile_id(client) -> None:
    pr = await client.post("/company-profiles", json={"name": "Test"})
    profile_id = pr.json()["id"]
    r = await client.post(
        "/agent-runs",
        json={"goal": "cyber 60d", "profile_id": profile_id},
    )
    assert r.status_code == 201, r.text
    assert r.json()["company_profile_id"] == profile_id


async def test_agent_run_bad_profile_id(client) -> None:
    r = await client.post(
        "/agent-runs",
        json={"goal": "cyber", "profile_id": str(uuid.uuid4())},
    )
    assert r.status_code == 400


async def test_agent_run_404(client) -> None:
    r = await client.get(f"/agent-runs/{uuid.uuid4()}")
    assert r.status_code == 404


# ─── /opportunities ────────────────────────────────────────────────────────


async def test_opportunity_404(client) -> None:
    r = await client.get(f"/opportunities/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_opportunity_round_trip_with_children(client, fake_supabase) -> None:
    profile_id = str(uuid.uuid4())
    opp_id = str(uuid.uuid4())
    fake_supabase._store["company_profiles"] = {
        profile_id: {
            "id": profile_id,
            "owner_profile_id": str(TEST_USER_ID),
            "name": "Seed Co",
            "preferred_role": "either",
            "capabilities": [],
            "industry_keywords": [],
            "service_area": [],
            "naics_codes": [],
            "certifications": [],
            "small_business_status": False,
            "past_performance": [],
        }
    }
    fake_supabase._store["opportunities"] = {
        opp_id: {
            "id": opp_id,
            "slug": "seed-rfp",
            "source": "seed",
            "active": True,
            "title": "Seed RFP",
            "agency": "Seed Agency",
            "solicitation_number": "SEED-001",
            "source_notice_id": None,
            "notice_type": None,
            "posted_date": None,
            "office_name": None,
            "psc_code": None,
            "resource_links": [],
            "opportunity_status": "open",
            "record_kind": None,
            "source_url": None,
            "due_date": None,
            "naics": None,
            "set_aside": None,
            "place_of_performance": None,
            "description": None,
            "attachments": [],
            "raw_payload": None,
            "created_at": "2026-05-09T14:00:00Z",
            "updated_at": "2026-05-09T14:00:00Z",
        }
    }

    req_payload = {
        "type": "security",
        "title": "Secret clearance",
        "confidence": "high",
        "is_blocker": True,
    }
    r = await client.post(
        f"/opportunities/{opp_id}/requirements",
        json=req_payload,
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 201, r.text

    fit_payload = {
        "company_profile_id": profile_id,
        "total_score": 88,
        "decision": "strong_pursue",
        "confidence": "high",
        "breakdown": {
            "capability": 18, "eligibility": 14, "naics": 9,
            "past_performance": 13, "certification": 8, "insurance_bonding": 9,
            "deadline": 9, "complexity": 4, "geography": 4,
        },
        "strengths": ["NAICS aligned"],
        "weaknesses": [],
        "blockers": [],
        "missing_info": [],
        "recommended_next_action": "Begin proposal drafting.",
    }
    r = await client.post(
        f"/opportunities/{opp_id}/fit-score",
        json=fit_payload,
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 201, r.text

    opp = await client.get(f"/opportunities/{opp_id}")
    assert opp.status_code == 200
    assert opp.json()["title"] == "Seed RFP"

    reqs = await client.get(f"/opportunities/{opp_id}/requirements")
    assert reqs.status_code == 200
    assert len(reqs.json()) == 1
    assert reqs.json()[0]["title"] == "Secret clearance"

    fit = await client.get(f"/opportunities/{opp_id}/fit-score")
    assert fit.status_code == 200
    assert fit.json()["decision"] == "strong_pursue"


async def test_opportunity_fit_score_404(client) -> None:
    r = await client.get(f"/opportunities/{uuid.uuid4()}/fit-score")
    assert r.status_code == 404


# ─── /action-packages ──────────────────────────────────────────────────────


async def test_action_package_post_and_get(client) -> None:
    opp_id = str(uuid.uuid4())
    pr = await client.post("/company-profiles", json={"name": "Package Co"})
    profile_id = pr.json()["id"]
    payload = {
        "opportunity_id": opp_id,
        "company_profile_id": profile_id,
        "executive_summary": "Strong fit.",
        "decision": "strong_pursue",
        "fit_score": 88,
        "fit_rationale": "aligned",
        "compliance_matrix": [],
        "risk_register": [],
        "proposal_checklist": [],
        "timeline": [],
        "approval_required": [],
    }
    r = await client.post("/action-packages", json=payload, headers=INTERNAL_HEADERS)
    assert r.status_code == 201, r.text
    pkg_id = r.json()["id"]

    g = await client.get(f"/action-packages/{pkg_id}")
    assert g.status_code == 200
    assert g.json()["executive_summary"] == "Strong fit."


async def test_action_package_404(client) -> None:
    r = await client.get(f"/action-packages/{uuid.uuid4()}")
    assert r.status_code == 404


# ─── POST analysis writes ──────────────────────────────────────────────────


async def test_post_requirement_404_on_unknown_opportunity(client) -> None:
    payload = {
        "type": "eligibility",
        "title": "X",
        "confidence": "high",
        "is_blocker": False,
    }
    r = await client.post(
        f"/opportunities/{uuid.uuid4()}/requirements",
        json=payload,
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 404


async def test_internal_write_rejects_missing_key(client) -> None:
    payload = {
        "type": "eligibility",
        "title": "X",
        "confidence": "high",
        "is_blocker": False,
    }
    r = await client.post(f"/opportunities/{uuid.uuid4()}/requirements", json=payload)
    assert r.status_code == 401


async def test_post_risk_persists_and_returns_201(client, fake_supabase) -> None:
    opp_id = str(uuid.uuid4())
    profile_id = str(uuid.uuid4())
    fake_supabase._store["opportunities"] = {
        opp_id: {
            "id": opp_id,
            "slug": "post-rfp",
            "source": "seed",
            "active": True,
            "title": "POST RFP",
            "agency": "POST Agency",
            "solicitation_number": "POST-001",
            "attachments": [],
            "resource_links": [],
            "opportunity_status": "open",
            "created_at": "2026-05-09T14:00:00Z",
            "updated_at": "2026-05-09T14:00:00Z",
        }
    }
    payload = {
        "company_profile_id": profile_id,
        "category": "deadline_too_close",
        "severity": "major",
        "title": "Tight deadline",
        "description": "Submission due in 5 days.",
        "evidence": "Section L: 5 days from posting.",
        "mitigation": "Decline or compress drafting.",
        "requires_human_review": True,
    }
    fake_supabase._store["company_profiles"] = {
        profile_id: {
            "id": profile_id,
            "owner_profile_id": str(TEST_USER_ID),
            "name": "Risk Co",
            "capabilities": [],
            "industry_keywords": [],
            "service_area": [],
            "naics_codes": [],
            "certifications": [],
            "small_business_status": False,
            "past_performance": [],
            "preferred_role": "either",
        }
    }
    r = await client.post(
        f"/opportunities/{opp_id}/risks",
        json=payload,
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["category"] == "deadline_too_close"
    assert body["severity"] == "major"
    assert body["requires_human_review"] is True
