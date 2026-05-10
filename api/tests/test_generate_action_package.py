"""generate_action_package — A8: full mode (LLM) + reject_summary mode (deterministic)."""
from __future__ import annotations

from api.skills.generate_action_package import generate_action_package
from api.tests.fakes import FakeLLM


async def test_reject_summary_mode_does_not_call_llm():
    """Reject mode must be deterministic — no LLM call, slim package, no checklist/timeline/outreach."""
    fake_llm = FakeLLM(should_not_be_called=True)
    out, _ = await generate_action_package(
        {
            "mode": "reject_summary",
            "company_profile": {"name": "DemoCo"},
            "opportunity": {"title": "Classified Net Defense"},
            "requirements": [],
            "fit_score": {
                "total_score": 0,
                "decision": "reject",
                "blockers": ["TS clearance required — company has none"],
            },
            "risks": [],
        },
        llm=fake_llm,
    )
    assert out["decision"] == "reject"
    assert "Do not pursue" in out["executive_summary"]
    assert out["compliance_matrix"] == []
    assert out["proposal_checklist"] == []
    assert out["timeline"] == []
    assert out["outreach_draft"] is None
    # Approval gate ALWAYS present, even in reject mode
    assert any(
        "eligibility" in s.lower() or "approval" in s.lower() or "review" in s.lower()
        for s in out["human_approval_required"]
    )
    assert fake_llm.call_count == 0


async def test_full_mode_calls_llm_and_includes_all_sections():
    """Full mode calls LLM once, returns full §5.11 package with all sections populated."""
    fake_llm = FakeLLM(
        payload={
            "executive_summary": "Strong fit. Proceed.",
            "decision": "strong_pursue",
            "fit_score": 88,
            "fit_rationale": "Capabilities + NAICS + cleared past performance align.",
            "compliance_matrix": [
                {
                    "requirement": "SAM registration",
                    "status": "met",
                    "evidence": "SAM #12345",
                    "next_action": "Confirm active",
                    "owner": "Capture",
                }
            ],
            "risk_register": [
                {
                    "risk": "Past performance gap",
                    "severity": "minor",
                    "explanation": "Need 1 more federal cloud reference",
                    "mitigation": "Highlight commercial GovCloud project as analog",
                }
            ],
            "proposal_checklist": [
                "Verify SAM active",
                "Draft Section L volume",
                "Get pricing review",
            ],
            "timeline": [
                {"date": "2026-06-01", "task": "Kickoff", "owner": "PM"},
                {"date": "2026-06-08", "task": "Tech volume draft", "owner": "Lead Engineer"},
            ],
            "partner_suggestions": [],
            "outreach_draft": {
                "subject": "Re: DOI-CMS-2026-001 — Cloud Migration Support",
                "body": "Hello, we're a small business focused on AWS GovCloud...",
            },
            "human_approval_required": [
                "Approve outreach draft before sending.",
                "Confirm pricing assumptions before final submission.",
            ],
        }
    )
    out, _ = await generate_action_package(
        {
            "mode": "full",
            "company_profile": {"name": "DemoCo"},
            "opportunity": {"title": "DOI Cloud Migration"},
            "requirements": [
                {
                    "title": "Cloud migration experience",
                    "type": "technical",
                    "confidence": "high",
                    "value": "AWS GovCloud preferred",
                    "evidence_snippet": "AWS GovCloud preferred",
                    "is_blocker": False,
                    "source_document": "RFP-001.pdf",
                    "page_number": 3,
                    "description": "...",
                }
            ],
            "fit_score": {"total_score": 88, "decision": "strong_pursue", "blockers": []},
            "risks": [],
        },
        llm=fake_llm,
    )
    assert out["decision"] == "strong_pursue"
    assert out["executive_summary"] == "Strong fit. Proceed."
    assert len(out["compliance_matrix"]) == 1
    assert len(out["proposal_checklist"]) == 3
    assert len(out["timeline"]) == 2
    assert out["outreach_draft"] is not None
    assert out["outreach_draft"]["subject"].startswith("Re:")
    assert len(out["human_approval_required"]) >= 2
    assert fake_llm.call_count == 1


async def test_human_approval_block_always_present_even_when_llm_omits():
    """§5.13 — human_approval_required MUST always be non-empty; if LLM returns empty,
    a default approval line MUST be injected."""
    fake_llm = FakeLLM(
        payload={
            "executive_summary": "Solid pursue.",
            "decision": "pursue",
            "fit_score": 75,
            "fit_rationale": "Capabilities align.",
            "compliance_matrix": [],
            "risk_register": [],
            "proposal_checklist": [],
            "timeline": [],
            "partner_suggestions": [],
            "outreach_draft": None,
            "human_approval_required": [],  # LLM forgot — controller MUST inject default
        }
    )
    out, _ = await generate_action_package(
        {
            "mode": "full",
            "company_profile": {},
            "opportunity": {"title": "X"},
            "requirements": [],
            "fit_score": {"total_score": 75, "decision": "pursue", "blockers": []},
            "risks": [],
        },
        llm=fake_llm,
    )
    assert len(out["human_approval_required"]) > 0  # default injected
    assert any(
        "authorized" in s.lower() or "approval" in s.lower() or "review" in s.lower()
        for s in out["human_approval_required"]
    )
