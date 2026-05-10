"""gov_compliance toolset — Compliance Officer's tools.

Two tools: extract_requirements and score_fit. Both implemented during
A5 and A6 respectively. The §11.1 eligibility short-circuit lives inside
score_fit's deterministic Phase A.

This file shows the function signatures Hermes expects. Real implementations
go in /api/skills/extract_requirements/implementation.py and
/api/skills/score_fit/implementation.py.
"""
from __future__ import annotations
import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Schema types codegen'd from /schemas/*.json (P0.2)
    from api.schemas.company_profile import CompanyProfile
    from api.schemas.extracted_requirement import (
        ExtractedRequirement,
        RequirementExtractionOutput,
    )
    from api.schemas.fit_score import FitScoreOutput


# ─── extract_requirements ───────────────────────────────────────────────────
# A5 — see tasks/dev1-backend/tasks/A5.md and prompts/extract_requirements.md

async def extract_requirements(
    parsed_chunks: list[dict],
    opportunity_metadata: dict,
    *,
    model: str | None = None,
) -> "RequirementExtractionOutput":
    """Extract structured requirements from parsed PDF chunks per PRD §10.1.

    Args:
        parsed_chunks: list of {page_number, text, doc_id} from parse_pdf.
        opportunity_metadata: dict with at least title, agency, solicitation_number.
        model: optional model override; defaults to settings.llm_dev_model.

    Returns:
        RequirementExtractionOutput per /schemas/extracted-requirement.schema.json.

    Behavior:
        - Calls Anthropic with the per-type extraction prompt
          (see /api/agent/prompts/extract_requirements.txt).
        - Validates response against §10.1 schema.
        - Retries once on invalid JSON with a stricter prompt reminder.
        - Post-validates evidence binding: every medium/high requirement MUST
          have non-empty evidence_snippet AND valid page_number that fuzzy-matches
          the source. Failures downgrade confidence to "low".
        - Returns degraded output on parser failure or extraction collapse.

    Cost: ~$0.02 per call on Sonnet, ~$0.005 on Haiku.

    See: SKILL.md at .hermes/skills/govcapture/extract_requirements_with_evidence/
    """
    raise NotImplementedError(
        "A5 — Dev 1 implements during the extract_requirements task. "
        "Reference: tasks/dev1-backend/tasks/A5.md."
    )


# ─── score_fit ──────────────────────────────────────────────────────────────
# A6 — see tasks/dev1-backend/tasks/A6.md and prompts/score_fit_rationale.md

async def score_fit(
    profile: "CompanyProfile",
    requirements: list["ExtractedRequirement"],
    opportunity_due_date: datetime.date | None = None,
) -> "FitScoreOutput":
    """Score fit per PRD §5.7 with §11.1 eligibility short-circuit.

    Args:
        profile: the company profile (from /company-profiles).
        requirements: list of extracted requirements (from extract_requirements).
        opportunity_due_date: opportunity's due_date, used for deadline scoring.

    Returns:
        FitScoreOutput per /schemas/fit-score.schema.json.

    Behavior — TWO PHASES:

        Phase A (PURE DETERMINISTIC, no LLM):
            For each of the 9 dimensions in §5.7, a Python function computes
            the score. Eligibility is special:

                blockers = []
                if set-aside required and profile lacks matching cert: blockers.append(...)
                if clearance required and profile.clearance_status mismatched: blockers.append(...)
                for req where is_blocker=True and confidence in {high, medium}: blockers.append(...)

                if blockers:
                    eligibility_score = 0
                    decision = "reject"          # FORCED — §11.1 short-circuit
                else:
                    eligibility_score = 15
                    decision = compute_band_from_total(total)

            Decision is FINAL after Phase A. The LLM cannot change it.

        Phase B (LLM rationale, Sonnet):
            Given the breakdown + decision (already final), generate
            strengths[], weaknesses[], missing_information[], recommended_next_action.
            The LLM is constrained to explain, not change.

    The §11.1 enforcement is the deterministic Phase A. Capability strengths
    cannot soften the decision. Eval harness (A12) asserts this on the
    reject fixture.

    Cost: Phase A is free (Python); Phase B ~$0.001 on Haiku, ~$0.005 on Sonnet.

    See: SKILL.md at .hermes/skills/govcapture/score_fit_with_eligibility_check/
    """
    raise NotImplementedError(
        "A6 — Dev 1 implements during the score_fit task. "
        "Reference: tasks/dev1-backend/tasks/A6.md. "
        "§11.1 enforcement test is mandatory and lives in the test file."
    )
