"""Tests for POST /action-packages/{id}/approve.

Per PRD v1.2.5+, action packages have approved_at + approved_by columns.
The orchestrator (in /root/michealaai) reads approved_at to gate any
external action that would follow user approval (CO email, submission).
The pack itself only writes the fields; gate enforcement is the
orchestrator's job.
"""
from __future__ import annotations

import uuid

import pytest

from api.tests.conftest import TEST_INTERNAL_API_KEY

INTERNAL_HEADERS = {"X-Internal-API-Key": TEST_INTERNAL_API_KEY}

# All tests use the shared `client` fixture — auto-authenticated as
# conftest.TEST_USER_ID.


def _action_package_payload(opp_id: str, profile_id: str) -> dict:
    """Minimal valid POST /action-packages body."""
    return {
        "opportunity_id": opp_id,
        "company_profile_id": profile_id,
        "executive_summary": "Strong fit.",
        "decision": "strong_pursue",
        "fit_score": 92,
        "fit_rationale": "Past performance matches.",
        "compliance_matrix": [],
        "risk_register": [],
        "proposal_checklist": [],
        "timeline": [],
        "approval_required": ["Confirm before contacting CO"],
    }


@pytest.mark.asyncio
async def test_approve_sets_approved_at_and_approved_by(client) -> None:
    """Happy path: a package owner approves their own package."""
    opp_id = str(uuid.uuid4())
    pr = await client.post("/company-profiles", json={"name": "Approve Co"})
    profile_id = pr.json()["id"]
    r = await client.post(
        "/action-packages",
        json=_action_package_payload(opp_id, profile_id),
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 201, r.text
    pkg_id = r.json()["id"]
    assert r.json().get("approved_at") is None

    approved = await client.post(f"/action-packages/{pkg_id}/approve")
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["approved_at"] is not None
    assert body["approved_by"] is not None  # set to caller's user id


@pytest.mark.asyncio
async def test_approve_returns_404_for_missing_package(client) -> None:
    """Unknown package id → 404, not 500."""
    missing = uuid.uuid4()
    r = await client.post(f"/action-packages/{missing}/approve")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_approve_persists_across_get(client) -> None:
    """After approve, GET /action-packages/{id} reflects approved_at."""
    opp_id = str(uuid.uuid4())
    pr = await client.post("/company-profiles", json={"name": "Persist Co"})
    profile_id = pr.json()["id"]
    r = await client.post(
        "/action-packages",
        json=_action_package_payload(opp_id, profile_id),
        headers=INTERNAL_HEADERS,
    )
    pkg_id = r.json()["id"]

    await client.post(f"/action-packages/{pkg_id}/approve")

    g = await client.get(f"/action-packages/{pkg_id}")
    assert g.status_code == 200
    body = g.json()
    assert body["approved_at"] is not None
    assert body["approved_by"] is not None
