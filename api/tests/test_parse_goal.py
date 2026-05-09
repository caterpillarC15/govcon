"""parse_goal — natural-language goal → structured search criteria."""
from __future__ import annotations
from api.skills.parse_goal import parse_goal
from api.tests.fakes import FakeLLM


async def test_parses_typical_goal():
    """Happy path: typical govcon goal returns structured criteria."""
    fake_llm = FakeLLM(payload={
        "keywords": ["cybersecurity", "infosec"],
        "naics_hints": ["541512", "541519"],
        "due_window_days": 60,
        "set_aside_pref": "small_business",
        "geography": None,
        "agencies": None,
        "opportunity_type": "any",
    })
    out, _ = await parse_goal(
        {
            "goal": "Find cybersecurity opportunities we can pursue in the next 60 days.",
            "company_profile": {"name": "DemoCo", "naics_codes": ["541512"]},
        },
        llm=fake_llm,
    )
    assert "cybersecurity" in out["keywords"]
    assert out["due_window_days"] == 60
    assert out["set_aside_pref"] == "small_business"
    assert fake_llm.call_count == 1


async def test_geography_extraction():
    fake_llm = FakeLLM(payload={
        "keywords": ["facilities maintenance"],
        "naics_hints": [],
        "due_window_days": 30,
        "set_aside_pref": None,
        "geography": "TX",
        "agencies": None,
        "opportunity_type": "any",
    })
    out, _ = await parse_goal(
        {
            "goal": "Find facilities maintenance contracts in Texas.",
            "company_profile": {"naics_codes": []},
        },
        llm=fake_llm,
    )
    assert out["geography"] == "TX"


async def test_defaults_due_window_to_30_when_unspecified():
    """Should accept LLM's default of 30 when no time horizon stated."""
    fake_llm = FakeLLM(payload={
        "keywords": ["cloud"],
        "naics_hints": ["541512"],
        "due_window_days": 30,  # default
        "set_aside_pref": None,
        "geography": None,
        "agencies": None,
        "opportunity_type": "any",
    })
    out, _ = await parse_goal(
        {"goal": "Find cloud opportunities.", "company_profile": {}},
        llm=fake_llm,
    )
    assert out["due_window_days"] == 30


async def test_named_agencies_extracted():
    fake_llm = FakeLLM(payload={
        "keywords": ["software development"],
        "naics_hints": ["541511"],
        "due_window_days": 90,
        "set_aside_pref": None,
        "geography": None,
        "agencies": ["DOI", "VA"],
        "opportunity_type": "rfp",
    })
    out, _ = await parse_goal(
        {
            "goal": "Find software RFPs at DOI or VA in the next 90 days.",
            "company_profile": {"naics_codes": ["541511"]},
        },
        llm=fake_llm,
    )
    assert out["agencies"] == ["DOI", "VA"]
    assert out["opportunity_type"] == "rfp"
