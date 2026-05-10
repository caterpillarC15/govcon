"""detect_risks — §5.8 risk taxonomy + severity calibration + human-review enforcement."""
from __future__ import annotations
from api.skills.detect_risks import detect_risks
from api.tests.fakes import FakeLLM


def _req(**overrides) -> dict:
    base = {
        "type": "deadline", "title": "Due in 5 days",
        "value": "2026-05-14", "confidence": "high", "is_blocker": False,
        "evidence_snippet": "Due 2026-05-14",
        "source_document": "RFP.pdf", "page_number": 1,
        "description": "Submission deadline",
    }
    base.update(overrides)
    return base


async def test_deadline_too_close_calibrated_as_major():
    fake_llm = FakeLLM(payload={
        "risks": [{
            "category": "deadline_too_close",
            "severity": "major_risk",
            "title": "Deadline 5 days out",
            "description": "Insufficient runway for full proposal cycle.",
            "evidence": "Due 2026-05-14",
            "mitigation": "Decline or compress technical-volume drafting.",
            "requires_human_review": True,
        }]
    })
    out, _ = await detect_risks(
        {
            "company_profile": {"name": "X"},
            "requirements": [_req()],
            "opportunity": {"due_date": "2026-05-14"},
        },
        llm=fake_llm,
    )
    assert len(out["risks"]) == 1
    assert out["risks"][0]["category"] == "deadline_too_close"
    assert out["risks"][0]["severity"] == "major_risk"


async def test_invalid_category_filtered_out():
    """Risks with categories not in the allowed taxonomy must be silently dropped."""
    fake_llm = FakeLLM(payload={
        "risks": [
            {
                "category": "made_up_category",  # NOT in ALLOWED
                "severity": "minor_concern", "title": "X", "description": "Y",
                "evidence": "Z", "mitigation": "W", "requires_human_review": False,
            },
            {
                "category": "scope_mismatch",  # IS in ALLOWED
                "severity": "moderate_risk", "title": "Scope creep risk",
                "description": "Optional tasks in Section C.5 may stretch capacity.",
                "evidence": "Section C.5", "mitigation": "Plan to bid only base scope.",
                "requires_human_review": False,
            },
        ]
    })
    out, _ = await detect_risks(
        {"company_profile": {}, "requirements": [], "opportunity": {}},
        llm=fake_llm,
    )
    # Made-up category dropped, valid one kept
    assert len(out["risks"]) == 1
    assert out["risks"][0]["category"] == "scope_mismatch"


async def test_critical_severity_forces_human_review():
    """Any critical_blocker MUST set requires_human_review=True even if LLM forgot."""
    fake_llm = FakeLLM(payload={
        "risks": [{
            "category": "set_aside_mismatch",
            "severity": "critical_blocker",
            "title": "8(a) required, company not certified",
            "description": "Company lacks 8(a) certification.",
            "evidence": "8(a) set-aside per Section H.2",
            "mitigation": "Cannot bid as prime; consider partner.",
            "requires_human_review": False,  # LLM forgot — should be FORCED to True
        }]
    })
    out, _ = await detect_risks(
        {"company_profile": {}, "requirements": [], "opportunity": {}},
        llm=fake_llm,
    )
    assert out["risks"][0]["requires_human_review"] is True


async def test_legal_compliance_category_forces_human_review():
    """legal_compliance_review category ALWAYS forces requires_human_review=True."""
    fake_llm = FakeLLM(payload={
        "risks": [{
            "category": "legal_compliance_review",
            "severity": "moderate_risk",  # not critical
            "title": "Service Contract Act applies",
            "description": "SCA wage determinations apply to support staff.",
            "evidence": "Wage determinations referenced in Section K",
            "mitigation": "Engage labor counsel before pricing.",
            "requires_human_review": False,  # LLM forgot
        }]
    })
    out, _ = await detect_risks(
        {"company_profile": {}, "requirements": [], "opportunity": {}},
        llm=fake_llm,
    )
    # legal_compliance_review category forces human review even at moderate severity
    assert out["risks"][0]["requires_human_review"] is True
