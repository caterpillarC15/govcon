"""detect_risks — A7.

§5.8 risk taxonomy + severity calibration. The LLM identifies risks; we enforce:
- silent-drop on categories outside the allowed taxonomy
- forced human review on critical_blocker severity or legal_compliance_review category
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel
from api.llm import LLM, LLMMetrics

_PROMPT = (Path(__file__).parent / "prompt.txt").read_text()

_ALLOWED_CATEGORIES = frozenset({
    "clearance_required", "set_aside_mismatch", "certification_gap",
    "past_performance_weakness", "deadline_too_close", "missing_attachments",
    "submission_ambiguity", "insurance_bonding_gap", "scope_mismatch",
    "legal_compliance_review", "pricing_complexity", "missing_required_document",
})

_FORCE_HUMAN_REVIEW_CATEGORIES = frozenset({"legal_compliance_review"})


class _RiskFlag(BaseModel):
    category: str
    severity: Literal["critical_blocker", "major_risk", "moderate_risk", "minor_concern"]
    title: str
    description: str
    evidence: str
    mitigation: str
    requires_human_review: bool


class _DetectRisksOutput(BaseModel):
    risks: list[_RiskFlag]


async def detect_risks(
    payload: dict[str, Any],
    *,
    llm: LLM,
) -> tuple[dict[str, Any], LLMMetrics]:
    """Detect risks per §5.8 taxonomy.

    Input shape:
        {"company_profile": {...}, "requirements": [...], "opportunity": {...}}
    Output:
        ({"risks": [{...}, ...]}, LLMMetrics)
    """
    user_prompt = (
        "Company profile:\n" + json.dumps(payload.get("company_profile", {}), indent=2) +
        "\n\nOpportunity:\n" + json.dumps(payload.get("opportunity", {}), indent=2) +
        "\n\nRequirements:\n" + json.dumps(payload.get("requirements", []), indent=2) +
        "\n\nReturn JSON per the schema."
    )

    result, metrics = await llm.complete_structured(
        system=_PROMPT,
        user=user_prompt,
        output_model=_DetectRisksOutput,
    )

    risks_dump = result.model_dump()["risks"]
    filtered: list[dict] = []
    for r in risks_dump:
        if r["category"] not in _ALLOWED_CATEGORIES:
            continue  # silent drop on hallucinated category
        # Force human review on critical or legal-compliance
        if r["severity"] == "critical_blocker" or r["category"] in _FORCE_HUMAN_REVIEW_CATEGORIES:
            r["requires_human_review"] = True
        filtered.append(r)

    return ({"risks": filtered}, metrics)
