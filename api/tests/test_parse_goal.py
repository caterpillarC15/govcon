"""parse_goal — deterministic pass-through validator (PRD v1.2.6).

The skill no longer calls an LLM. Michaela parses the natural-language
goal in her own agent context; this skill only validates the envelope
and returns {raw_goal, company_profile}.
"""
from __future__ import annotations

import pytest

from api.skills.parse_goal.skill import ParseGoalInput, parse_goal


@pytest.mark.asyncio
async def test_returns_raw_goal_and_profile_unchanged():
    payload = ParseGoalInput(
        goal="Find cybersecurity opportunities we can pursue in the next 60 days.",
        company_profile={"name": "DemoCo", "naics_codes": ["541512"]},
    )
    out = await parse_goal(payload)
    assert out["raw_goal"] == payload.goal
    assert out["company_profile"] == {
        "name": "DemoCo",
        "naics_codes": ["541512"],
    }


@pytest.mark.asyncio
async def test_company_profile_defaults_to_empty_dict():
    payload = ParseGoalInput(goal="Find cloud opportunities.")
    out = await parse_goal(payload)
    assert out["raw_goal"] == "Find cloud opportunities."
    assert out["company_profile"] == {}


@pytest.mark.asyncio
async def test_no_keyword_or_naics_extraction_in_skill():
    """Verify the skill does NOT mutate the goal text — that's Michaela's job."""
    payload = ParseGoalInput(
        goal="Find facilities maintenance contracts in Texas.",
        company_profile={"naics_codes": []},
    )
    out = await parse_goal(payload)
    # No keywords/geography/agencies inferred — the agent owns extraction.
    assert "keywords" not in out
    assert "geography" not in out
    assert "agencies" not in out
    # Raw goal preserved verbatim for the agent to parse.
    assert out["raw_goal"] == "Find facilities maintenance contracts in Texas."
