"""score_fit — §11.1 short-circuit + decision-band normalizer (PRD v1.2.6).

Per the operating rule (devdocs/MICHAELA_SYSTEM_MODEL.md line 175),
the §5.7 fit-scoring rubric is judgment work — Lenny computes the
score breakdown + total in her agent context (in /root/michealaai).

This skill keeps two deterministic mechanics:

1. **§11.1 eligibility short-circuit** (always runs first). If the
   requirements include a hard eligibility blocker — set-aside the
   company doesn't qualify for, clearance the company doesn't hold,
   low/unknown-confidence eligibility item, or explicit is_blocker —
   returns decision=reject + total_score=0. Lenny cannot override.

2. **Decision-band normalizer**. When Lenny supplies a total_score
   computed in her agent context, the skill maps that score to the
   §5.7 decision band (strong_pursue / pursue / maybe / reject) and
   echoes back the agent-supplied strengths/weaknesses/etc.

Two-call contract:
- total_score=None → §11.1 only. Returns blockers (or empty) so
  Lenny knows whether to bother computing a score.
- total_score=N    → §11.1 first, then band normalization on N.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

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


def _detect_eligibility_blockers(
    profile: dict, requirements: list[dict]
) -> list[str]:
    """Return list of human-readable blocker strings if §11.1 trips."""
    blockers: list[str] = []
    company_certs = {c.lower() for c in profile.get("certifications", [])}
    company_clearance = (profile.get("clearance_status") or "none").lower()

    for req in requirements:
        if req.get("type") not in _ELIGIBILITY_TYPES:
            continue
        text = " ".join(
            [
                str(req.get("title", "")),
                str(req.get("value", "")),
                str(req.get("description", "")),
                str(req.get("evidence_snippet", "")),
            ]
        ).lower()

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
                        f"Clearance required ({req.get('title', 'unspecified')}) "
                        "— company has none."
                    )
                    break

        # Low/unknown confidence on eligibility = treat as blocker
        if (
            req.get("type") == "eligibility"
            and req.get("confidence") in {"low", "unknown"}
        ):
            blockers.append(
                f"Eligibility uncertain: {req.get('title', '')} "
                "(low/unknown confidence)."
            )

        # Explicit is_blocker on eligibility-type requirement
        if req.get("is_blocker") and req.get("type") in _ELIGIBILITY_TYPES:
            title = req.get("title", "Unnamed eligibility blocker")
            if not any(title in b for b in blockers):
                blockers.append(title)

    # Dedupe preserving order
    seen: set[str] = set()
    return [b for b in blockers if not (b in seen or seen.add(b))]  # type: ignore[func-returns-value]


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


Decision = Literal[
    "strong_pursue", "pursue", "maybe", "reject", "needs_score"
]


class ScoreFitInput(BaseModel):
    company_profile: dict[str, Any]
    requirements: list[dict[str, Any]]
    # Agent-supplied (Lenny computes in her LLM context):
    total_score: int | None = Field(None, ge=0, le=100)
    score_breakdown: _ScoreBreakdown | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommended_next_action: str = ""


async def score_fit(payload: ScoreFitInput | dict[str, Any]) -> dict[str, Any]:
    """§11.1 short-circuit + decision-band normalizer.

    Always evaluates blockers first. If any blocker fires, returns
    the deterministic reject regardless of supplied total_score
    (PRD §11.1 — eligibility is unforgiving).

    With no blockers and no total_score: returns decision="needs_score"
    so Lenny knows to compute the score and call back.

    With no blockers and total_score supplied: maps to §5.7 decision
    band and echoes the agent-supplied detail fields.
    """
    if isinstance(payload, dict):
        payload = ScoreFitInput.model_validate(payload)

    blockers = _detect_eligibility_blockers(
        payload.company_profile, payload.requirements
    )

    if blockers:
        # §11.1 deterministic reject — Lenny cannot override.
        return {
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
        }

    if payload.total_score is None:
        # No score yet — Lenny hasn't computed it. Return clean state
        # so she knows she's clear of §11.1 and should proceed.
        return {
            "total_score": 0,
            "decision": "needs_score",
            "confidence": "low",
            "score_breakdown": dict(_ZERO_BREAKDOWN),
            "strengths": [],
            "weaknesses": [],
            "blockers": [],
            "missing_information": [],
            "recommended_next_action": "",
        }

    # Score supplied → normalize to §5.7 band, pass agent fields through.
    breakdown = (
        payload.score_breakdown.model_dump()
        if payload.score_breakdown
        else dict(_ZERO_BREAKDOWN)
    )
    return {
        "total_score": payload.total_score,
        "decision": _band_from_score(payload.total_score),
        "confidence": "high",
        "score_breakdown": breakdown,
        "strengths": payload.strengths,
        "weaknesses": payload.weaknesses,
        "blockers": [],
        "missing_information": payload.missing_information,
        "recommended_next_action": payload.recommended_next_action,
    }
