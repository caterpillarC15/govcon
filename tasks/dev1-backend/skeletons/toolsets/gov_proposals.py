"""gov_proposals toolset — Proposal Strategist's tools."""
from __future__ import annotations
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from api.schemas.company_profile import CompanyProfile
    from api.schemas.opportunity import Opportunity
    from api.schemas.extracted_requirement import ExtractedRequirement
    from api.schemas.fit_score import FitScoreOutput
    from api.schemas.risk_flag import RiskFlag
    from api.schemas.action_package import ActionPackageOutput


# ─── generate_action_package ────────────────────────────────────────────────
# A8 — see tasks/dev1-backend/tasks/A8.md and prompts/generate_action_package.md

PackageMode = Literal["full", "reject_summary"]


async def generate_action_package(
    profile: "CompanyProfile",
    opportunity: "Opportunity",
    requirements: list["ExtractedRequirement"],
    fit_score: "FitScoreOutput",
    risks: list["RiskFlag"],
    *,
    mode: PackageMode = "full",
) -> "ActionPackageOutput":
    """Produce the §10.3 action package.

    TWO MODES:

        mode="full" (pursue / strong_pursue / maybe):
            - LLM-backed (Sonnet).
            - All 11 §10.3 sections.
            - Compliance matrix constructed deterministically where profile
              data clearly satisfies requirements; LLM fills "unclear" rows
              and next_action / owner.
            - Outreach draft uses generic salutation only.
            - human_approval_required has ≥ 4 entries (wrapper appends defaults).

        mode="reject_summary" (reject):
            - DETERMINISTIC. NO LLM CALL.
            - Slim shape: executive_summary, decision, fit_score, fit_rationale,
              compliance_matrix (blockers only), risk_register (criticals only),
              human_approval_required.
            - All "prep work" sections empty: proposal_checklist=[], timeline=[],
              partner_suggestions=[], outreach_draft={subject:"", body:""}.
            - Approval-required messages include "Do not pursue without overriding
              the eligibility analysis."

    The Capture Analyst sets the mode based on fit_score.decision. If
    decision == "reject" and mode == "full", the skill should refuse (raises
    ValueError) — that combination violates §11.1 enforcement.

    Cost:
        full mode:           ~$0.04-0.05 on Sonnet
        reject_summary mode: ~$0 (deterministic)

    See: SKILL.md at:
        .hermes/skills/govcapture/generate_full_action_package/
        .hermes/skills/govcapture/generate_reject_summary/
    """
    if mode == "reject_summary" and fit_score.decision != "reject":
        raise ValueError(
            f"reject_summary mode is for decision=reject only; got {fit_score.decision}"
        )
    if mode == "full" and fit_score.decision == "reject":
        raise ValueError(
            "full mode for decision=reject violates PRD §11.1 enforcement. "
            "Use mode=reject_summary instead."
        )
    raise NotImplementedError(
        "A8 — Dev 1 implements during generate_action_package task. "
        "Reference: tasks/dev1-backend/tasks/A8.md."
    )
