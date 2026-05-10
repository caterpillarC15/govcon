"""score_fit — A6.

§5.7 fit-scoring rubric + §11.1 deterministic eligibility short-circuit.

The §11.1 short-circuit fires BEFORE any LLM call when extracted requirements include
a hard eligibility blocker (set-aside the company doesn't qualify for, clearance the
company doesn't hold, or a low/unknown-confidence eligibility requirement). When it
fires, score=0, decision=reject, and NO LLM call is made.

When no short-circuit triggers, the LLM is called with the §5.7 rubric prompt; its
returned decision is normalized strictly from total_score (decision band rule).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from api.llm import LLM, LLMMetrics

_PROMPT = (Path(__file__).parent / "prompt.txt").read_text()

# §11.1 enforcement
_ELIGIBILITY_TYPES = frozenset({"eligibility", "security", "certification"})
_SET_ASIDE_KEYWORDS = ("8(a)", "hubzone", "wosb", "edwosb", "sdvosb", "vosb")
_CLEARANCE_KEYWORDS = ("secret", "ts/sci", "top secret", "clearance")

_ZERO_BREAKDOWN = {
    "capability": 0,
    "eligibility": 0,
    "naics": 0,
    "past_performance": 0,
    "certification": 0,
    "insurance_bonding": 0,
    "deadline": 0,
    "complexity": 0,
    "geography": 0,
}


# §5.7 decision bands
def _band_from_score(score: int) -> str:
    if score >= 85:
        return "strong_pursue"
    if score >= 70:
        return "pursue"
    if score >= 55:
        return "maybe"
    return "reject"


def _detect_eligibility_blockers(profile: dict, requirements: list[dict]) -> list[str]:
    """Return list of human-readable blocker strings if §11.1 trips, else empty list."""
    blockers: list[str] = []
    company_certs = {c.lower() for c in profile.get("certifications", [])}
    company_clearance = (profile.get("clearance_status") or "none").lower()

    for req in requirements:
        if req.get("type") not in _ELIGIBILITY_TYPES:
            continue
        text = " ".join([
            str(req.get("title", "")),
            str(req.get("value", "")),
            str(req.get("description", "")),
            str(req.get("evidence_snippet", "")),
        ]).lower()

        # Set-aside mismatch
        for kw in _SET_ASIDE_KEYWORDS:
            if kw in text and not any(kw in c for c in company_certs):
                blockers.append(
                    f"Set-aside requires {kw.upper()}; company is not certified."
                )

        # Clearance mismatch
        if company_clearance == "none":
            for kw in _CLEARANCE_KEYWORDS:
                if kw in text:
                    blockers.append(
                        f"Clearance required ({req.get('title', 'unspecified')}) — company has none."
                    )
                    break

        # Low/unknown confidence on eligibility = treat as blocker
        if (
            req.get("type") == "eligibility"
            and req.get("confidence") in {"low", "unknown"}
        ):
            blockers.append(
                f"Eligibility uncertain: {req.get('title', '')} (low/unknown confidence)."
            )

        # Explicit is_blocker on eligibility-type requirement
        if req.get("is_blocker") and req.get("type") in _ELIGIBILITY_TYPES:
            title = req.get("title", "Unnamed eligibility blocker")
            if not any(title in b for b in blockers):
                blockers.append(title)

    # Dedupe preserving order
    seen: set[str] = set()
    return [b for b in blockers if not (b in seen or seen.add(b))]  # type: ignore[func-returns-value]


def _zero_metrics() -> LLMMetrics:
    """Synthetic metrics emitted when the short-circuit fires (no real LLM call)."""
    return LLMMetrics(
        model="none",
        latency_ms=0,
        cost_usd=0.0,
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        attempts=0,
    )


class _ScoreBreakdown(BaseModel):
    capability: int = 0
    eligibility: int = 0
    naics: int = 0
    past_performance: int = 0
    certification: int = 0
    insurance_bonding: int = 0
    deadline: int = 0
    complexity: int = 0
    geography: int = 0


class _ScoreFitOutput(BaseModel):
    total_score: int = Field(..., ge=0, le=100)
    decision: Literal["strong_pursue", "pursue", "maybe", "reject"]
    confidence: Literal["high", "medium", "low"]
    score_breakdown: _ScoreBreakdown
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommended_next_action: str = ""


async def score_fit(
    payload: dict[str, Any], *, llm: LLM
) -> tuple[dict[str, Any], LLMMetrics]:
    """Score how well a company fits an opportunity.

    Input shape:
        {"company_profile": {...}, "requirements": [{...}, ...]}

    Returns: (output_dict, metrics) where output_dict matches §5.7 + §11.1 contract.
    """
    profile = payload["company_profile"]
    requirements = payload["requirements"]

    # §11.1 deterministic short-circuit BEFORE any LLM call
    blockers = _detect_eligibility_blockers(profile, requirements)
    if blockers:
        return (
            {
                "total_score": 0,
                "decision": "reject",
                "confidence": "high",
                "score_breakdown": dict(_ZERO_BREAKDOWN),
                "strengths": [],
                "weaknesses": [],
                "blockers": blockers,
                "missing_information": [],
                "recommended_next_action": (
                    "Do not pursue. Critical eligibility blocker(s) present."
                ),
            },
            _zero_metrics(),
        )

    # No short-circuit → call LLM with rubric
    user_prompt = (
        "Company profile:\n"
        + json.dumps(profile, indent=2)
        + "\n\nExtracted requirements:\n"
        + json.dumps(requirements, indent=2)
        + "\n\nReturn JSON per the schema."
    )
    result, metrics = await llm.complete_structured(
        system=_PROMPT,
        user=user_prompt,
        output_model=_ScoreFitOutput,
    )

    # result is a Pydantic model — convert to dict and normalize decision from total_score
    out = result.model_dump()
    out["decision"] = _band_from_score(int(out.get("total_score", 0)))
    # score_breakdown is a nested model — ensure it's a plain dict
    if not isinstance(out["score_breakdown"], dict):
        out["score_breakdown"] = dict(out["score_breakdown"])
    return out, metrics
