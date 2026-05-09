"""score_fit — §5.7 rubric + §11.1 deterministic short-circuit (pre-LLM).

All five tests are marked xfail(strict=True) until T2.2 implements the skill.
When the implementation lands and tests start passing, pytest will report XPASS
(strict=True turns that into a suite failure) — the signal to remove the markers.
"""
from __future__ import annotations

import pytest

from api.skills.score_fit import score_fit
from api.tests.fakes import FakeLLM


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


@pytest.mark.xfail(reason="implementation pending in T2.2", strict=True)
async def test_clearance_required_company_has_none_short_circuits(uncleared_company):
    """§11.1 — TS clearance required + company has none → score 0, decision reject, NO LLM."""
    requirements = [
        _req(
            type="security",
            title="TS clearance required",
            value="Top Secret + SCI",
            confidence="high",
            is_blocker=True,
            evidence_snippet="Top Secret + SCI required",
        )
    ]
    fake_llm = FakeLLM(should_not_be_called=True)
    out, _ = await score_fit(
        {"company_profile": uncleared_company, "requirements": requirements},
        llm=fake_llm,
    )
    assert out["decision"] == "reject"
    assert out["total_score"] == 0
    assert out["score_breakdown"]["eligibility"] == 0
    assert any("clearance" in b.lower() for b in out["blockers"])
    assert fake_llm.call_count == 0


@pytest.mark.xfail(reason="implementation pending in T2.2", strict=True)
async def test_set_aside_mismatch_short_circuits(cleared_company):
    """§11.1 — 8(a) set-aside + company not 8(a)-certified → reject, NO LLM."""
    requirements = [
        _req(
            type="eligibility",
            title="8(a) set-aside",
            value="8(a) participants only",
            confidence="high",
            is_blocker=True,
            evidence_snippet="reserved for 8(a) participants",
        )
    ]
    fake_llm = FakeLLM(should_not_be_called=True)
    out, _ = await score_fit(
        {"company_profile": cleared_company, "requirements": requirements},
        llm=fake_llm,
    )
    assert out["decision"] == "reject"
    assert out["total_score"] == 0
    assert any("8(a)" in b for b in out["blockers"])
    assert fake_llm.call_count == 0


@pytest.mark.xfail(reason="implementation pending in T2.2", strict=True)
async def test_eligibility_uncertain_treated_as_blocker(cleared_company):
    """§11.1: 'If eligibility is uncertain, score 0 and emit critical blocker.'

    Low/unknown confidence eligibility requirement → reject, NO LLM.
    """
    requirements = [
        _req(
            type="eligibility",
            title="Foreign ownership unclear",
            value="May require US-owned entity",
            confidence="low",
            is_blocker=False,
            evidence_snippet="...",
        )
    ]
    fake_llm = FakeLLM(should_not_be_called=True)
    out, _ = await score_fit(
        {"company_profile": cleared_company, "requirements": requirements},
        llm=fake_llm,
    )
    assert out["decision"] == "reject"
    assert out["score_breakdown"]["eligibility"] == 0
    assert fake_llm.call_count == 0


@pytest.mark.xfail(reason="implementation pending in T2.2", strict=True)
async def test_no_eligibility_blockers_calls_llm(cleared_company):
    """Clean fit — no blockers → LLM is called once, returns full score."""
    requirements = [
        _req(
            type="technical",
            title="Cloud migration experience",
            value="AWS GovCloud preferred",
            evidence_snippet="AWS GovCloud preferred",
            source_document="RFP-001.pdf",
            page_number=3,
        ),
        _req(
            type="deadline",
            title="Due 2026-06-15",
            value="2026-06-15",
            evidence_snippet="due 2026-06-15",
            source_document="RFP-001.pdf",
        ),
    ]
    fake_llm = FakeLLM(
        payload={
            "total_score": 88,
            "decision": "strong_pursue",
            "confidence": "high",
            "score_breakdown": {
                "capability": 18,
                "eligibility": 14,
                "naics": 9,
                "past_performance": 12,
                "certification": 9,
                "insurance_bonding": 8,
                "deadline": 10,
                "complexity": 4,
                "geography": 4,
            },
            "strengths": ["Strong AWS GovCloud experience"],
            "weaknesses": [],
            "blockers": [],
            "missing_information": [],
            "recommended_next_action": "Begin proposal drafting.",
        }
    )
    out, _ = await score_fit(
        {"company_profile": cleared_company, "requirements": requirements},
        llm=fake_llm,
    )
    assert out["decision"] == "strong_pursue"
    assert out["total_score"] == 88
    assert fake_llm.call_count == 1


@pytest.mark.xfail(reason="implementation pending in T2.2", strict=True)
async def test_decision_band_normalized_to_total(cleared_company):
    """Even if LLM returns inconsistent decision/score, the band rule from total_score wins.

    Band contract (encoded here as the spec for T2.2):
      0       → reject
      1–39    → no_pursue
      40–54   → pursue_with_caution
      55–69   → maybe
      70–84   → pursue
      85–100  → strong_pursue
    """
    requirements = [
        _req(
            type="technical",
            title="X",
            value="X",
            evidence_snippet="x",
            source_document="x.pdf",
        )
    ]
    fake_llm = FakeLLM(
        payload={
            "total_score": 60,
            "decision": "strong_pursue",  # inconsistent — LLM hallucinated the band
            "confidence": "high",
            "score_breakdown": {
                "capability": 12,
                "eligibility": 10,
                "naics": 6,
                "past_performance": 8,
                "certification": 6,
                "insurance_bonding": 6,
                "deadline": 6,
                "complexity": 3,
                "geography": 3,
            },
            "strengths": [],
            "weaknesses": [],
            "blockers": [],
            "missing_information": [],
            "recommended_next_action": "...",
        }
    )
    out, _ = await score_fit(
        {"company_profile": cleared_company, "requirements": requirements},
        llm=fake_llm,
    )
    # total_score=60 falls in the 55-69 band → "maybe", overrides LLM's "strong_pursue"
    assert out["decision"] == "maybe"
