"""parse_goal — input validator only (PRD v1.2.6).

Per the operating rule (devdocs/MICHAELA_SYSTEM_MODEL.md line 175 —
"mechanics in tools, judgment in agents"), parsing the user's
natural-language contracting goal into structured search criteria is
judgment work. Michaela performs that extraction in her own LLM
context before delegating to Scot for SAM discovery.

This skill validates the input envelope and passes the goal + profile
through unchanged. The downstream caller (Michaela's prompt) does the
keyword/NAICS/geography extraction.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ParseGoalInput(BaseModel):
    goal: str
    company_profile: dict[str, Any] | None = None


async def parse_goal(
    payload: ParseGoalInput | dict[str, Any],
) -> dict[str, Any]:
    """Pass-through validator.

    Returns the goal text + company_profile context for Michaela to
    consume in her agent context. No LLM call. Accepts dict for
    HTTP/eval flow compatibility.
    """
    if isinstance(payload, dict):
        payload = ParseGoalInput.model_validate(payload)
    return {
        "raw_goal": payload.goal,
        "company_profile": payload.company_profile or {},
    }
