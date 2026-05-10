"""score_fit — §11.1 short-circuit + decision-band normalizer (PRD v1.2.6).

The skill no longer calls an LLM. Lenny computes the score in her
agent context; this skill enforces §11.1 (deterministic) and normalizes
the score to the §5.7 decision band.
"""
from __future__ import annotations

import pytest

from api.skills.score_fit.skill import ScoreFitInput, score_fit


@pytest.fixture
def cleared_company() -> dict:
    return {
        "name": "DemoCo",
        "naics_codes": ["541512"],
        "certifications": ["CMMC L2"],
        "small_business_status": True,
        "clearance_status": "none",
        "capabilities": ["cloud migration", "AWS GovCloud"],
    }


@pytest.fixture
def uncleared_company() -> dict:
    return {
        "name": "DemoCo",
        "naics_codes": ["541512"],
        "certifications": [],
        "small_business_status": True,
        "clearance_status": "none",
        "capabilities": ["network defense"],
    }


def _req(**overrides) -> dict:
    base = {
        "type": "technical",
        "title": "X",
        "value": "X",
        "description": "...",
        "confidence": "high",
        "evidence_snippet": "x",
        "source_document": "x.pdf",
        "page_number": 1,
        "is_blocker": False,
    }
    base.update(overrides)
    return base


# ─── §11.1 short-circuit (deterministic) ───────────────────────────────────


async def test_clearance_required_company_has_none_short_circuits(uncleared_company):
    """§11.1 — TS clearance required + company has none → score 0, reject."""
    out = await score_fit(
        ScoreFitInput(
            company_profile=uncleared_company,
            requirements=[
                _req(
                    type="security",
                    title="TS clearance required",
                    value="Top Secret + SCI",
                    is_blocker=True,
                    evidence_snippet="Top Secret + SCI required",
                )
            ],
        )
    )
    assert out["decision"] == "reject"
    assert out["total_score"] == 0
    assert out["score_breakdown"]["eligibility"] == 0
    assert any("clearance" in b.lower() for b in out["blockers"])


async def test_set_aside_mismatch_short_circuits(cleared_company):
    """§11.1 — 8(a) set-aside + company not 8(a)-certified → reject."""
    out = await score_fit(
        ScoreFitInput(
            company_profile=cleared_company,
            requirements=[
                _req(
                    type="eligibility",
                    title="8(a) set-aside",
                    value="8(a) participants only",
                    is_blocker=True,
                    evidence_snippet="reserved for 8(a) participants",
                )
            ],
        )
    )
    assert out["decision"] == "reject"
    assert out["total_score"] == 0
    assert any("8(a)" in b for b in out["blockers"])


async def test_eligibility_uncertain_treated_as_blocker(cleared_company):
    """§11.1: low/unknown-confidence eligibility → reject."""
    out = await score_fit(
        ScoreFitInput(
            company_profile=cleared_company,
            requirements=[
                _req(
                    type="eligibility",
                    title="Foreign ownership unclear",
                    value="May require US-owned entity",
                    confidence="low",
                    is_blocker=False,
                    evidence_snippet="...",
                )
            ],
        )
    )
    assert out["decision"] == "reject"
    assert out["score_breakdown"]["eligibility"] == 0


async def test_blocker_overrides_supplied_total_score(uncleared_company):
    """§11.1 is unforgiving: even if Lenny supplies a high score,
    a blocker forces reject."""
    out = await score_fit(
        ScoreFitInput(
            company_profile=uncleared_company,
            requirements=[
                _req(
                    type="security",
                    title="TS clearance required",
                    is_blocker=True,
                    evidence_snippet="TS required",
                )
            ],
            total_score=95,  # Lenny says high; §11.1 says no.
        )
    )
    assert out["decision"] == "reject"
    assert out["total_score"] == 0


# ─── needs_score (clean of blockers, no score yet) ─────────────────────────


async def test_no_blockers_no_score_returns_needs_score(cleared_company):
    """First call from Lenny: she's clear of §11.1, but hasn't yet
    computed a score. Skill tells her to come back with one."""
    out = await score_fit(
        ScoreFitInput(
            company_profile=cleared_company,
            requirements=[
                _req(
                    type="technical",
                    title="Cloud migration experience",
                    evidence_snippet="AWS GovCloud preferred",
                )
            ],
        )
    )
    assert out["decision"] == "needs_score"
    assert out["blockers"] == []


# ─── Decision-band normalization ───────────────────────────────────────────


async def test_band_strong_pursue_at_88(cleared_company):
    out = await score_fit(
        ScoreFitInput(
            company_profile=cleared_company,
            requirements=[_req(type="technical", title="X")],
            total_score=88,
            strengths=["AWS GovCloud experience"],
        )
    )
    assert out["decision"] == "strong_pursue"
    assert out["total_score"] == 88
    assert out["strengths"] == ["AWS GovCloud experience"]


async def test_band_pursue_at_72(cleared_company):
    out = await score_fit(
        ScoreFitInput(
            company_profile=cleared_company,
            requirements=[_req(type="technical", title="X")],
            total_score=72,
        )
    )
    assert out["decision"] == "pursue"


async def test_band_maybe_at_60(cleared_company):
    out = await score_fit(
        ScoreFitInput(
            company_profile=cleared_company,
            requirements=[_req(type="technical", title="X")],
            total_score=60,
        )
    )
    assert out["decision"] == "maybe"


async def test_band_reject_below_55(cleared_company):
    out = await score_fit(
        ScoreFitInput(
            company_profile=cleared_company,
            requirements=[_req(type="technical", title="X")],
            total_score=40,
        )
    )
    assert out["decision"] == "reject"
