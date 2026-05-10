"""detect_risks — taxonomy + human-review validator (PRD v1.2.6)."""
from __future__ import annotations

from api.skills.detect_risks.skill import DetectRisksInput, detect_risks


def _risk(**overrides) -> dict:
    base = {
        "category": "scope_mismatch",
        "severity": "moderate_risk",
        "title": "X",
        "description": "Y",
        "evidence": "Z",
        "mitigation": "W",
        "requires_human_review": False,
    }
    base.update(overrides)
    return base


async def test_valid_risk_passes_through():
    out = await detect_risks(
        DetectRisksInput(
            risks=[
                _risk(
                    category="deadline_too_close",
                    severity="major_risk",
                    title="Deadline 5 days out",
                    description="Insufficient runway.",
                    evidence="Due 2026-05-14",
                    mitigation="Decline or compress drafting.",
                    requires_human_review=True,
                )
            ]
        )
    )
    assert len(out["risks"]) == 1
    assert out["risks"][0]["category"] == "deadline_too_close"
    assert out["risks"][0]["severity"] == "major_risk"


async def test_invalid_category_silently_dropped():
    """Categories outside the §5.8 taxonomy are dropped without comment."""
    out = await detect_risks(
        DetectRisksInput(
            risks=[
                _risk(category="made_up_category"),
                _risk(category="scope_mismatch", title="Scope creep"),
            ]
        )
    )
    assert len(out["risks"]) == 1
    assert out["risks"][0]["category"] == "scope_mismatch"


async def test_critical_severity_forces_human_review():
    """critical_blocker → requires_human_review=True even if Gate forgot."""
    out = await detect_risks(
        DetectRisksInput(
            risks=[
                _risk(
                    category="set_aside_mismatch",
                    severity="critical_blocker",
                    requires_human_review=False,  # Gate forgot
                )
            ]
        )
    )
    assert out["risks"][0]["requires_human_review"] is True


async def test_legal_compliance_category_forces_human_review():
    """legal_compliance_review category always forces review, even at moderate."""
    out = await detect_risks(
        DetectRisksInput(
            risks=[
                _risk(
                    category="legal_compliance_review",
                    severity="moderate_risk",
                    requires_human_review=False,
                )
            ]
        )
    )
    assert out["risks"][0]["requires_human_review"] is True


async def test_empty_risks_returns_empty():
    out = await detect_risks(DetectRisksInput())
    assert out == {"risks": []}


async def test_dict_input_accepted():
    out = await detect_risks(
        {"risks": [_risk(category="scope_mismatch")]}
    )
    assert len(out["risks"]) == 1
