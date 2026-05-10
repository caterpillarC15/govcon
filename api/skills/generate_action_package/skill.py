"""generate_action_package — schema validator + reject_summary (PRD v1.2.6).

Two modes per §5.11:

- **reject_summary** (deterministic): slim package emitted when
  score_fit returns decision=reject. No LLM call, no judgment —
  just slot the blockers into a fixed shape with the §5.13 approval
  gate populated.

- **full** (validator): Roy synthesizes the bid memo content in her
  agent context (in /root/michealaai). This skill validates the §5.11
  shape, enforces §5.13 (human_approval_required non-empty), and
  echoes the agent-supplied content. No LLM call here.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

_DEFAULT_APPROVAL = (
    "Authorized review required before any external action "
    "(outreach, submission, claims of compliance)."
)


class _ComplianceRow(BaseModel):
    requirement: str
    status: str
    evidence: str = ""
    next_action: str = ""
    owner: str = ""


class _RiskRow(BaseModel):
    risk: str
    severity: str
    explanation: str = ""
    mitigation: str = ""


class _TimelineEntry(BaseModel):
    date: str
    task: str
    owner: str = ""


class _PartnerSuggestion(BaseModel):
    partner_type: str
    gap_solved: str
    why_needed: str = ""
    outreach_angle: str = ""
    confidence: str = "medium"


class _OutreachDraft(BaseModel):
    subject: str
    body: str


class _ActionPackageContent(BaseModel):
    """Roy emits this in her agent context for full-mode packages."""
    executive_summary: str
    decision: str
    fit_score: int = Field(..., ge=0, le=100)
    fit_rationale: str
    compliance_matrix: list[_ComplianceRow] = Field(default_factory=list)
    risk_register: list[_RiskRow] = Field(default_factory=list)
    proposal_checklist: list[str] = Field(default_factory=list)
    timeline: list[_TimelineEntry] = Field(default_factory=list)
    partner_suggestions: list[_PartnerSuggestion] = Field(default_factory=list)
    outreach_draft: _OutreachDraft | None = None
    human_approval_required: list[str] = Field(default_factory=list)


class GenerateActionPackageInput(BaseModel):
    mode: str = "full"
    company_profile: dict[str, Any] = Field(default_factory=dict)
    opportunity: dict[str, Any] = Field(default_factory=dict)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    fit_score: dict[str, Any] = Field(default_factory=dict)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    # Roy-supplied content for full mode.
    content: _ActionPackageContent | None = None


def _reject_summary(payload: GenerateActionPackageInput) -> dict[str, Any]:
    """Deterministic slim package for reject decisions."""
    fit = payload.fit_score
    blockers = fit.get("blockers", [])
    opp_title = payload.opportunity.get("title", "this opportunity")
    blocker_str = "; ".join(blockers) if blockers else "see fit-score blockers"

    return {
        "executive_summary": (
            f"Do not pursue {opp_title}. "
            f"Critical eligibility blocker(s): {blocker_str}."
        ),
        "decision": "reject",
        "fit_score": int(fit.get("total_score", 0)),
        "fit_rationale": (
            f"Eligibility short-circuit (§11.1). Blockers: {blockers}"
            if blockers
            else "Reject decision from fit scoring."
        ),
        "compliance_matrix": [],
        "risk_register": [
            {
                "risk": b,
                "severity": "critical",
                "explanation": "",
                "mitigation": (
                    "Out of scope — pursue only if certification/clearance acquired."
                ),
            }
            for b in blockers
        ],
        "proposal_checklist": [],
        "timeline": [],
        "partner_suggestions": [],
        "outreach_draft": None,
        "human_approval_required": [
            f"Critical eligibility blocker(s) detected for {opp_title}. "
            f"{_DEFAULT_APPROVAL}"
        ],
    }


def _validate_full(content: _ActionPackageContent) -> dict[str, Any]:
    """§5.13 enforcement: human_approval_required must be non-empty."""
    out = content.model_dump()
    if not out.get("human_approval_required"):
        out["human_approval_required"] = [_DEFAULT_APPROVAL]
    return out


def _empty_full_skeleton(payload: GenerateActionPackageInput) -> dict[str, Any]:
    """When Roy hasn't supplied content, return a skeleton signaling
    'needs_content' so the caller knows to fill it in.
    """
    fit = payload.fit_score
    return {
        "executive_summary": "",
        "decision": fit.get("decision", "needs_content"),
        "fit_score": int(fit.get("total_score", 0)),
        "fit_rationale": "",
        "compliance_matrix": [],
        "risk_register": [],
        "proposal_checklist": [],
        "timeline": [],
        "partner_suggestions": [],
        "outreach_draft": None,
        "human_approval_required": [_DEFAULT_APPROVAL],
    }


async def generate_action_package(
    payload: GenerateActionPackageInput | dict[str, Any],
) -> dict[str, Any]:
    """Generate the action package per §5.11 (deterministic).

    - mode="reject_summary": slim deterministic package built from
      fit_score blockers. Always populates §5.13 approval gate.
    - mode="full" + content supplied: validates the §5.11 shape and
      enforces §5.13. Roy's content passes through.
    - mode="full" + no content: returns an empty skeleton so the
      caller knows to compute and re-call.
    """
    if isinstance(payload, dict):
        payload = GenerateActionPackageInput.model_validate(payload)

    if payload.mode == "reject_summary":
        return _reject_summary(payload)

    if payload.content is None:
        return _empty_full_skeleton(payload)

    return _validate_full(payload.content)
