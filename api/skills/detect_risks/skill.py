"""detect_risks — risk validator (PRD v1.2.6).

Per the operating rule (devdocs/MICHAELA_SYSTEM_MODEL.md line 175),
emitting risks requires judgment — Gate produces them in her agent
context (in /root/michealaai). This skill is the deterministic gate
that enforces:

- silent-drop on categories outside the §5.8 allowed taxonomy
- forced human review on critical_blocker severity OR
  legal_compliance_review category (regardless of agent's flag)
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

_ALLOWED_CATEGORIES = frozenset(
    {
        "clearance_required",
        "set_aside_mismatch",
        "certification_gap",
        "past_performance_weakness",
        "deadline_too_close",
        "missing_attachments",
        "submission_ambiguity",
        "insurance_bonding_gap",
        "scope_mismatch",
        "legal_compliance_review",
        "pricing_complexity",
        "missing_required_document",
    }
)

_FORCE_HUMAN_REVIEW_CATEGORIES = frozenset({"legal_compliance_review"})


class _RiskFlag(BaseModel):
    category: str
    severity: Literal[
        "critical_blocker", "major_risk", "moderate_risk", "minor_concern"
    ]
    title: str
    description: str
    evidence: str
    mitigation: str
    requires_human_review: bool


class DetectRisksInput(BaseModel):
    company_profile: dict[str, Any] = {}
    opportunity: dict[str, Any] = {}
    requirements: list[dict[str, Any]] = []
    # Agent-emitted risks. Gate produces these in her LLM context.
    risks: list[_RiskFlag] = []


async def detect_risks(
    payload: DetectRisksInput | dict[str, Any],
) -> dict[str, Any]:
    """Validate Gate-emitted risks against the §5.8 taxonomy.

    - Drops any risk whose category isn't in _ALLOWED_CATEGORIES
      (silent — protects against agent hallucination).
    - Forces requires_human_review=True for critical_blocker
      severity OR legal_compliance_review category.
    """
    if isinstance(payload, dict):
        payload = DetectRisksInput.model_validate(payload)

    filtered: list[dict[str, Any]] = []
    for risk in payload.risks:
        if risk.category not in _ALLOWED_CATEGORIES:
            continue  # silent drop
        rdict = risk.model_dump()
        if (
            risk.severity == "critical_blocker"
            or risk.category in _FORCE_HUMAN_REVIEW_CATEGORIES
        ):
            rdict["requires_human_review"] = True
        filtered.append(rdict)

    return {"risks": filtered}
