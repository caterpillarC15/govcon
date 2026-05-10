"""generate_action_package — A8.

§5.11 action package synthesis with two modes:

- reject_summary: deterministic, no LLM. Slim package emitted when score_fit returns
  decision=reject (eligibility short-circuit). Avoids spending tokens fabricating
  reasons to engage an opportunity that's already disqualified.

- full: LLM-backed §5.11 sections (executive brief, decision rationale, compliance
  matrix, risk register, proposal checklist, timeline, partner suggestions, outreach
  draft, human approval gate).

§5.13 invariant: human_approval_required MUST always be non-empty. If the LLM forgets,
the controller injects a default approval line.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel
from api.llm import LLM, LLMMetrics

_PROMPT = (Path(__file__).parent / "prompt.txt").read_text()

_DEFAULT_APPROVAL = (
    "Authorized review required before any external action "
    "(outreach, submission, claims of compliance)."
)


class _ComplianceRow(BaseModel):
    requirement: str
    status: str
    evidence: str
    next_action: str
    owner: str


class _RiskRow(BaseModel):
    risk: str
    severity: str
    explanation: str
    mitigation: str


class _TimelineEntry(BaseModel):
    date: str
    task: str
    owner: str


class _PartnerSuggestion(BaseModel):
    partner_type: str
    gap_solved: str
    why_needed: str
    outreach_angle: str
    confidence: str


class _OutreachDraft(BaseModel):
    subject: str
    body: str


class _ActionPackageOutput(BaseModel):
    executive_summary: str
    decision: str
    fit_score: int
    fit_rationale: str
    compliance_matrix: list[_ComplianceRow]
    risk_register: list[_RiskRow]
    proposal_checklist: list[str]
    timeline: list[_TimelineEntry]
    partner_suggestions: list[_PartnerSuggestion]
    outreach_draft: _OutreachDraft | None = None
    human_approval_required: list[str]


def _zero_metrics() -> LLMMetrics:
    return LLMMetrics(
        model="none", latency_ms=0, cost_usd=0.0,
        input_tokens=0, output_tokens=0,
        cache_read_tokens=0, cache_creation_tokens=0,
        attempts=0,
    )


def _reject_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Deterministic slim package for reject decisions. NO LLM."""
    fit = payload.get("fit_score", {})
    blockers = fit.get("blockers", [])
    opp_title = payload.get("opportunity", {}).get("title", "this opportunity")
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
            if blockers else "Reject decision from fit scoring."
        ),
        "compliance_matrix": [],
        "risk_register": [
            {
                "risk": b,
                "severity": "critical",
                "explanation": "",
                "mitigation": "Out of scope — pursue only if certification/clearance acquired.",
            }
            for b in blockers
        ],
        "proposal_checklist": [],
        "timeline": [],
        "partner_suggestions": [],
        "outreach_draft": None,
        "human_approval_required": [
            f"Critical eligibility blocker(s) detected for {opp_title}. {_DEFAULT_APPROVAL}"
        ],
    }


async def generate_action_package(
    payload: dict[str, Any],
    *,
    llm: LLM,
) -> tuple[dict[str, Any], LLMMetrics]:
    """Generate the action package per §5.11.

    Input shape:
        {
          "mode": "full" | "reject_summary",
          "company_profile": {...},
          "opportunity": {...},
          "requirements": [...],
          "fit_score": {...},
          "risks": [...],
        }
    Output: ({...}, LLMMetrics)
    """
    mode = payload.get("mode", "full")

    if mode == "reject_summary":
        return _reject_summary(payload), _zero_metrics()

    # full mode: LLM-backed
    user_prompt = (
        "Opportunity:\n" + json.dumps(payload.get("opportunity", {}), indent=2) +
        "\n\nCompany profile:\n" + json.dumps(payload.get("company_profile", {}), indent=2) +
        "\n\nRequirements:\n" + json.dumps(payload.get("requirements", []), indent=2) +
        "\n\nFit score:\n" + json.dumps(payload.get("fit_score", {}), indent=2) +
        "\n\nRisks:\n" + json.dumps(payload.get("risks", []), indent=2) +
        "\n\nReturn JSON per the schema."
    )

    result, metrics = await llm.complete_structured(
        system=_PROMPT,
        user=user_prompt,
        output_model=_ActionPackageOutput,
    )
    out = result.model_dump()

    # §5.13 invariant: approval block MUST be non-empty
    if not out.get("human_approval_required"):
        out["human_approval_required"] = [_DEFAULT_APPROVAL]

    return out, metrics
