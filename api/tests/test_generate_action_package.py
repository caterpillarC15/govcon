"""generate_action_package — schema validator + reject_summary (PRD v1.2.6).

The skill no longer calls an LLM. Roy synthesizes content in her
agent context; this skill validates the §5.11 shape and enforces
§5.13 (non-empty approval gate). reject_summary mode is unchanged
(was already deterministic).
"""
from __future__ import annotations

from api.skills.generate_action_package.skill import (
    GenerateActionPackageInput,
    generate_action_package,
)


# ─── reject_summary mode (deterministic, unchanged) ────────────────────────


async def test_reject_summary_mode_returns_slim_package():
    out = await generate_action_package(
        GenerateActionPackageInput(
            mode="reject_summary",
            company_profile={"name": "DemoCo"},
            opportunity={"title": "Classified Net Defense"},
            fit_score={
                "total_score": 0,
                "decision": "reject",
                "blockers": ["TS clearance required — company has none"],
            },
        )
    )
    assert out["decision"] == "reject"
    assert "Do not pursue" in out["executive_summary"]
    assert out["compliance_matrix"] == []
    assert out["proposal_checklist"] == []
    assert out["timeline"] == []
    assert out["outreach_draft"] is None
    # §5.13: approval gate always present, even in reject mode
    assert any(
        "eligibility" in s.lower()
        or "approval" in s.lower()
        or "review" in s.lower()
        for s in out["human_approval_required"]
    )


async def test_reject_summary_no_blockers_falls_back_gracefully():
    out = await generate_action_package(
        GenerateActionPackageInput(
            mode="reject_summary",
            opportunity={"title": "Generic Opp"},
            fit_score={"total_score": 30, "decision": "reject"},
        )
    )
    assert out["decision"] == "reject"
    assert out["risk_register"] == []  # no blockers to expand
    assert len(out["human_approval_required"]) >= 1


# ─── full mode — Roy supplies content (validator path) ─────────────────────


async def test_full_mode_with_content_passes_through_and_validates():
    """Full mode: Roy supplies content; skill validates + echoes."""
    out = await generate_action_package(
        GenerateActionPackageInput(
            mode="full",
            opportunity={"title": "DOI Cloud Migration"},
            fit_score={
                "total_score": 88,
                "decision": "strong_pursue",
                "blockers": [],
            },
            content={
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
                "risk_register": [],
                "proposal_checklist": [
                    "Verify SAM active",
                    "Draft Section L volume",
                ],
                "timeline": [
                    {"date": "2026-06-01", "task": "Kickoff", "owner": "PM"}
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
            },
        )
    )
    assert out["decision"] == "strong_pursue"
    assert out["executive_summary"] == "Strong fit. Proceed."
    assert len(out["compliance_matrix"]) == 1
    assert len(out["proposal_checklist"]) == 2
    assert len(out["timeline"]) == 1
    assert out["outreach_draft"] is not None
    assert out["outreach_draft"]["subject"].startswith("Re:")
    assert len(out["human_approval_required"]) >= 2


async def test_full_mode_empty_approval_gate_gets_default_injected():
    """§5.13 invariant: human_approval_required MUST be non-empty.
    If Roy forgets, the skill injects a default."""
    out = await generate_action_package(
        GenerateActionPackageInput(
            mode="full",
            opportunity={"title": "X"},
            fit_score={"total_score": 75, "decision": "pursue", "blockers": []},
            content={
                "executive_summary": "Solid pursue.",
                "decision": "pursue",
                "fit_score": 75,
                "fit_rationale": "Capabilities align.",
                "human_approval_required": [],  # Roy forgot
            },
        )
    )
    assert len(out["human_approval_required"]) > 0
    assert any(
        "authorized" in s.lower()
        or "approval" in s.lower()
        or "review" in s.lower()
        for s in out["human_approval_required"]
    )


async def test_full_mode_no_content_returns_skeleton():
    """First call (no content): skill returns an empty skeleton so Roy
    knows she needs to synthesize content and call back."""
    out = await generate_action_package(
        GenerateActionPackageInput(
            mode="full",
            opportunity={"title": "X"},
            fit_score={
                "total_score": 75,
                "decision": "pursue",
                "blockers": [],
            },
        )
    )
    assert out["decision"] == "pursue"  # echoed from fit_score
    assert out["executive_summary"] == ""
    assert out["fit_score"] == 75
    # §5.13 default still injected so the skeleton is shape-valid.
    assert len(out["human_approval_required"]) >= 1
