"""gov_risks toolset — Risk Analyst's tools."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.schemas.company_profile import CompanyProfile
    from api.schemas.extracted_requirement import ExtractedRequirement
    from api.schemas.fit_score import FitScoreOutput
    from api.schemas.risk_flag import RiskFlag


# ─── detect_risks ───────────────────────────────────────────────────────────
# A7 — see tasks/dev1-backend/tasks/A7.md and prompts/detect_risks.md

async def detect_risks(
    profile: "CompanyProfile",
    requirements: list["ExtractedRequirement"],
    fit_score: "FitScoreOutput",
    *,
    model: str | None = None,
) -> list["RiskFlag"]:
    """Identify risks across PRD §5.8 categories with calibrated severity.

    Args:
        profile: company profile.
        requirements: extracted requirements from Compliance Officer.
        fit_score: fit score output (informs cross-check of blockers).
        model: defaults to Haiku (sufficient for classification).

    Returns:
        list of RiskFlag (max 8 — wrapper truncates by severity priority).

    Behavior:
        - LLM call with detect_risks prompt enumerating the 12 categories
          and severity calibration.
        - Validates output against /schemas/risk-flag.schema.json.
        - Cross-check: every blocker in fit_score.blockers MUST appear here
          as a critical_blocker risk. Wrapper deterministically appends
          missing ones.
        - Sets requires_human_review=true for criticals automatically.

    Cost: ~$0.001 per call on Haiku.

    Skipped for reject opportunities — the Capture Analyst's branch logic
    does not delegate to this skill when fit_score.decision == "reject".

    See: SKILL.md at .hermes/skills/govcapture/detect_risks_calibrated/
    """
    raise NotImplementedError(
        "A7 — Dev 1 implements during detect_risks task. "
        "Reference: tasks/dev1-backend/tasks/A7.md."
    )
