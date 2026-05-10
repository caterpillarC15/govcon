"""POST /tools/<name> route tests — shape, auth, validation.

Each route gets three tests at minimum:
    - 200 happy path with a valid body and X-Internal-API-Key
    - 401 when the header is missing or wrong
    - 422 when the body is malformed

Skill-level correctness lives in test_<skill>.py — these tests verify only
the HTTP boundary, payload validation, and envelope shape.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Callable

import pytest
import pytest_asyncio

from api.deps import get_llm
from api.main import app
from api.tests.conftest import TEST_INTERNAL_API_KEY
from api.tests.fakes import FakeLLM

pytestmark = pytest.mark.asyncio

INTERNAL_HEADERS = {"X-Internal-API-Key": TEST_INTERNAL_API_KEY}


@pytest_asyncio.fixture
async def fake_llm_factory() -> AsyncIterator[Callable[[dict[str, Any]], FakeLLM]]:
    """Return a factory that builds a FakeLLM and registers it as the
    get_llm override for this test. Cleans up overrides on teardown.
    """
    created: list[FakeLLM] = []

    def _make(payload: dict[str, Any]) -> FakeLLM:
        f = FakeLLM(payload=payload)
        created.append(f)
        app.dependency_overrides[get_llm] = lambda: f
        return f

    try:
        yield _make
    finally:
        app.dependency_overrides.pop(get_llm, None)


async def test_tools_router_unknown_path_returns_404(client) -> None:
    """Router is registered; unknown path returns 404 regardless of auth."""
    r = await client.post("/tools/does-not-exist", json={}, headers=INTERNAL_HEADERS)
    assert r.status_code == 404
    r2 = await client.post("/tools/does-not-exist", json={})
    assert r2.status_code == 404


# ─── Shared auth + validation checks ───────────────────────────────────────


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/tools/parse-goal", {"goal": "find SOC contracts"}),
        ("/tools/parse-pdf", {"path": "/tmp/x.pdf"}),
        (
            "/tools/extract-requirements",
            {
                "parsed": {
                    "doc_id": "x",
                    "page_count": 0,
                    "unparseable": True,
                    "chunks": [],
                    "error": "file_not_found",
                }
            },
        ),
        (
            "/tools/score-fit",
            {"company_profile": {}, "requirements": []},
        ),
        ("/tools/detect-risks", {"requirements": []}),
        ("/tools/generate-action-package", {"mode": "reject_summary"}),
        ("/tools/search-sam", {"keywords": "cyber"}),
        (
            "/tools/fetch-attachment",
            {"run_id": "run-1", "url": "https://example.test/rfp.pdf"},
        ),
        ("/tools/rank-opportunities", {"scored": []}),
        ("/tools/load-seeded-opportunities", {"slugs": ["maybe"]}),
    ],
)
async def test_all_tools_require_internal_key(client, path, payload) -> None:
    r = await client.post(path, json=payload)
    assert r.status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/tools/parse-goal",
        "/tools/parse-pdf",
        "/tools/extract-requirements",
        "/tools/score-fit",
        "/tools/detect-risks",
        "/tools/generate-action-package",
        "/tools/search-sam",
        "/tools/fetch-attachment",
        "/tools/rank-opportunities",
        "/tools/load-seeded-opportunities",
    ],
)
async def test_all_tools_reject_unknown_fields(client, path) -> None:
    r = await client.post(
        path,
        json={"unexpected": True},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422


# ─── /tools/parse-goal ─────────────────────────────────────────────────────


async def test_parse_goal_happy_path(client) -> None:
    """PRD v1.2.6: parse_goal is a deterministic pass-through validator.

    Michaela does the keyword/NAICS/geography extraction in her own
    agent context. This skill just echoes the goal + profile back.
    """
    r = await client.post(
        "/tools/parse-goal",
        json={
            "goal": "Find cybersecurity contracts in Texas",
            "company_profile": {"naics_codes": ["541512"]},
        },
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["raw_goal"] == "Find cybersecurity contracts in Texas"
    assert body["data"]["company_profile"] == {"naics_codes": ["541512"]}
    # No LLM call → no metrics. Phase 7 drops the field entirely.
    assert body["metrics"] is None


# ─── /tools/rank-opportunities ─────────────────────────────────────────────


async def test_rank_opportunities_happy_path(client) -> None:
    payload = {
        "scored": [
            {"opportunity_id": "a", "decision": "maybe", "total_score": 60, "due_date": "2026-06-01"},
            {"opportunity_id": "b", "decision": "strong_pursue", "total_score": 92, "due_date": "2026-06-15"},
            {"opportunity_id": "c", "decision": "pursue", "total_score": 78, "due_date": "2026-05-20"},
        ]
    }
    r = await client.post("/tools/rank-opportunities", json=payload, headers=INTERNAL_HEADERS)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["metrics"] is None
    ranked = body["data"]["ranked"]
    assert [row["opportunity_id"] for row in ranked] == ["b", "c", "a"]


async def test_rank_opportunities_requires_internal_key(client) -> None:
    r = await client.post("/tools/rank-opportunities", json={"scored": []})
    assert r.status_code == 401


async def test_rank_opportunities_rejects_malformed(client) -> None:
    r = await client.post("/tools/rank-opportunities", json={}, headers=INTERNAL_HEADERS)
    assert r.status_code == 422


# ─── /tools/parse-pdf ──────────────────────────────────────────────────────


async def test_parse_pdf_returns_unparseable_for_missing_file(client, tmp_path) -> None:
    missing = tmp_path / "does-not-exist.pdf"
    r = await client.post(
        "/tools/parse-pdf",
        json={"path": str(missing)},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["metrics"] is None
    assert body["data"]["unparseable"] is True
    assert body["data"]["error"] == "file_not_found"


async def test_parse_pdf_requires_internal_key(client) -> None:
    r = await client.post("/tools/parse-pdf", json={"path": "/tmp/x.pdf"})
    assert r.status_code == 401


async def test_parse_pdf_rejects_empty_path(client) -> None:
    r = await client.post(
        "/tools/parse-pdf", json={"path": ""}, headers=INTERNAL_HEADERS
    )
    assert r.status_code == 422


# ─── /tools/extract-requirements ───────────────────────────────────────────


async def test_extract_requirements_unparseable_short_circuit(client) -> None:
    """PRD v1.2.6: deterministic skill. Unparseable PDF returns
    empty chunks + missing_fields=['all']; metrics is None."""
    payload = {
        "parsed": {
            "doc_id": "missing",
            "page_count": 0,
            "unparseable": True,
            "chunks": [],
            "error": "file_not_found",
        }
    }
    r = await client.post(
        "/tools/extract-requirements",
        json=payload,
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["chunks"] == []
    assert body["data"]["missing_fields"] == ["all"]
    assert body["data"]["requirements"] == []
    assert body["metrics"] is None


# ─── /tools/score-fit ──────────────────────────────────────────────────────


async def test_score_fit_eligibility_short_circuit(client, fake_llm_factory) -> None:
    fake_llm_factory(
        {
            "total_score": 80,
            "decision": "pursue",
            "confidence": "high",
            "score_breakdown": {},
        }
    )
    payload = {
        "company_profile": {"clearance_status": "none", "certifications": []},
        "requirements": [
            {
                "type": "security",
                "title": "Secret clearance required",
                "value": "Secret",
                "confidence": "high",
            }
        ],
    }
    r = await client.post(
        "/tools/score-fit",
        json=payload,
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["decision"] == "reject"
    assert body["data"]["total_score"] == 0
    assert body["metrics"]["model"] == "none"


# ─── /tools/detect-risks ───────────────────────────────────────────────────


async def test_detect_risks_happy_path(client, fake_llm_factory) -> None:
    fake_llm_factory(
        {
            "risks": [
                {
                    "category": "deadline_too_close",
                    "severity": "major_risk",
                    "title": "Tight deadline",
                    "description": "Response window is short.",
                    "evidence": "Due soon.",
                    "mitigation": "Assign capture owner today.",
                    "requires_human_review": False,
                }
            ]
        }
    )
    r = await client.post(
        "/tools/detect-risks",
        json={"requirements": [{"type": "deadline", "title": "Due soon"}]},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["risks"][0]["category"] == "deadline_too_close"
    assert body["metrics"]["model"] == "claude-haiku-4-5-20251001"


# ─── /tools/generate-action-package ────────────────────────────────────────


async def test_generate_action_package_reject_summary(client, fake_llm_factory) -> None:
    fake_llm_factory(
        {
            "executive_summary": "unused",
            "decision": "reject",
            "fit_score": 0,
            "fit_rationale": "unused",
            "compliance_matrix": [],
            "risk_register": [],
            "proposal_checklist": [],
            "timeline": [],
            "partner_suggestions": [],
            "outreach_draft": None,
            "human_approval_required": ["unused"],
        }
    )
    r = await client.post(
        "/tools/generate-action-package",
        json={
            "mode": "reject_summary",
            "opportunity": {"title": "Secret RFP"},
            "fit_score": {"total_score": 0, "blockers": ["Secret required"]},
        },
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["decision"] == "reject"
    assert body["data"]["human_approval_required"]
    assert body["metrics"]["model"] == "none"


async def test_generate_action_package_rejects_unknown_mode(client) -> None:
    r = await client.post(
        "/tools/generate-action-package",
        json={"mode": "maybe_later"},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422


# ─── /tools/search-sam ─────────────────────────────────────────────────────


async def test_search_sam_returns_degraded_envelope(client, monkeypatch) -> None:
    """When the skill reports degraded=True, the route surfaces it intact in the envelope.
    The skill is replaced wholesale to avoid any real network call.
    """
    from api.routes import tools as tools_module

    async def _fake_search(payload, *, api_key, http=None):
        return {"opportunities": [], "degraded": True, "error": "SAM client error: 401"}

    monkeypatch.setattr(tools_module, "search_sam_opportunities", _fake_search)

    r = await client.post(
        "/tools/search-sam",
        json={"keywords": "cyber"},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["degraded"] is True
    assert body["metrics"] is None


async def test_search_sam_requires_internal_key(client) -> None:
    r = await client.post("/tools/search-sam", json={"keywords": "x"})
    assert r.status_code == 401


async def test_search_sam_rejects_oversized_limit(client) -> None:
    r = await client.post(
        "/tools/search-sam",
        json={"keywords": "x", "limit": 10_000},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422


# ─── /tools/fetch-attachment ───────────────────────────────────────────────


async def test_fetch_attachment_happy_path(client, monkeypatch) -> None:
    from api.routes import tools as tools_module

    async def _fake_fetch(payload, *, storage, http=None):
        return {
            "storage_path": f"raw/{payload['run_id']}/{payload['filename']}",
            "bytes_downloaded": 123,
        }

    monkeypatch.setattr(tools_module, "fetch_attachment", _fake_fetch)

    r = await client.post(
        "/tools/fetch-attachment",
        json={
            "run_id": "run-1",
            "url": "https://example.test/rfp.pdf",
            "filename": "rfp.pdf",
        },
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["storage_path"] == "raw/run-1/rfp.pdf"
    assert body["metrics"] is None


# ─── /tools/load-seeded-opportunities ──────────────────────────────────────


async def test_load_seeded_opportunities_happy_path(client) -> None:
    r = await client.post(
        "/tools/load-seeded-opportunities",
        json={"slugs": ["maybe"]},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["opportunities"][0]["slug"] == "maybe"
    assert body["metrics"] is None


# ─── /tools/load-seeded-opportunities ──────────────────────────────────────


async def test_load_seeded_returns_loaded_list(client, monkeypatch) -> None:
    from api.routes import tools as tools_module

    async def _fake_load(payload, *, client, fixtures_dir=None):
        return {
            "opportunities": [
                {"id": "00000000-0000-4000-8000-000000000aaa", "slug": "strong-pursue", "title": "Stub"}
            ]
        }

    monkeypatch.setattr(tools_module, "load_seeded_opportunities", _fake_load)

    r = await client.post(
        "/tools/load-seeded-opportunities",
        json={"slugs": ["strong-pursue"]},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["opportunities"][0]["slug"] == "strong-pursue"
    assert body["metrics"] is None


async def test_load_seeded_requires_internal_key(client) -> None:
    r = await client.post("/tools/load-seeded-opportunities", json={})
    assert r.status_code == 401


async def test_load_seeded_rejects_unknown_field(client) -> None:
    r = await client.post(
        "/tools/load-seeded-opportunities",
        json={"slug": "x"},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422
