"""parse_goal — Capture Lead's first move.

Converts a natural-language contracting goal into structured search criteria
that the SAM search skill (and the planner) can use.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from api.llm import LLM, LLMMetrics

_PROMPT = (Path(__file__).parent / "prompt.txt").read_text()


class _ParseGoalOutput(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    naics_hints: list[str] = Field(default_factory=list)
    due_window_days: int = 30
    set_aside_pref: str | None = None
    geography: str | None = None
    agencies: list[str] | None = None
    opportunity_type: str = "any"


async def parse_goal(
    payload: dict[str, Any],
    *,
    llm: LLM,
) -> tuple[dict[str, Any], LLMMetrics]:
    """Parse a goal string into structured search criteria.

    Input shape:
        {
          "goal": str,                  # natural-language goal
          "company_profile": {...},     # used for context (NAICS, role, etc.)
        }
    Output:
        ({
          "keywords": list[str],
          "naics_hints": list[str],
          "due_window_days": int,
          "set_aside_pref": str | None,
          "geography": str | None,
          "agencies": list[str] | None,
          "opportunity_type": str,       # "any" | "rfp" | "rfi" | "sources_sought"
        }, LLMMetrics)
    """
    profile_naics = payload.get("company_profile", {}).get("naics_codes", [])
    user_prompt = (
        f"Goal: {payload['goal']}\n"
        f"Company NAICS codes: {profile_naics}\n\n"
        "Return JSON per the schema."
    )

    result, metrics = await llm.complete_structured(
        system=_PROMPT,
        user=user_prompt,
        output_model=_ParseGoalOutput,
    )
    return result.model_dump(), metrics
