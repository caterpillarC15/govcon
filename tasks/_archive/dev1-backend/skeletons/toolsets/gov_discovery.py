"""gov_discovery toolset — Capture Lead's tools."""
from __future__ import annotations
import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.schemas.opportunity import Opportunity
    from api.schemas.company_profile import CompanyProfile


# ─── parse_goal ─────────────────────────────────────────────────────────────
# A11 (split: this is a NEW skill added per AGENT_ARCHITECTURE.md)

async def parse_goal(user_goal: str, profile: "CompanyProfile") -> dict:
    """Parse natural-language goal into structured search criteria.

    Returns: {keywords, naics_hints, set_aside_preference, deadline_window_days,
              place_of_performance_states, agency_filter, opportunity_size_hint}

    Implementation: Haiku LLM call. Profile biases missing fields (e.g.,
    place_of_performance from profile.location).

    Cost: ~$0.001 per call.
    """
    raise NotImplementedError("A11 — Dev 1 implements as part of search/discovery skills")


# ─── search_sam_opportunities ───────────────────────────────────────────────
# A11

async def search_sam_opportunities(criteria: dict) -> list["Opportunity"]:
    """Live SAM.gov v2 search.

    May raise: RateLimited (429), ServerError (5xx). Caller (Capture Lead via
    discover_opportunities SKILL) catches and falls back to load_seeded_opportunities.

    Cache: results stored in opportunity_search_cache table; same-day repeat queries
    are served from cache.
    """
    raise NotImplementedError("A11 — Dev 1 implements during SAM.gov integration")


# ─── load_seeded_opportunities ──────────────────────────────────────────────
# A11

async def load_seeded_opportunities(criteria: dict) -> list["Opportunity"]:
    """Load opportunities from /fixtures/<slug>/opportunity.json files.

    Filtered by criteria (loose keyword/NAICS/state matching). Always available;
    the demo's stable path.

    When DEMO_USE_SEEDED_ONLY=true is set, the planner skips search_sam entirely
    and uses only this.
    """
    raise NotImplementedError("A11 — Dev 1 implements as part of seeded-opportunity loader")


# ─── rank_opportunities ─────────────────────────────────────────────────────
# A11.5 (NEW skill per AGENT_ARCHITECTURE.md)

def rank_opportunities(
    candidates: list["Opportunity"],
    criteria: dict,
    profile: "CompanyProfile",
) -> list["Opportunity"]:
    """Deterministic relevance + recency ranker. NO LLM CALL.

    Heuristic scoring:
        + 30 keyword overlap (title/description vs criteria.keywords)
        + 25 NAICS exact match
        + 20 set-aside compatibility with profile.certifications
        + 15 deadline within criteria.deadline_window_days
        - 25 deadline outside window
        + 10 place-of-performance match

    Returns same opportunities sorted by relevance_score descending,
    with relevance_score attached to each.

    Why deterministic: ranking is cheap, fast, debuggable, testable.
    Don't use an LLM for this.
    """
    raise NotImplementedError("A11.5 — NEW deterministic ranker; Dev 1 implements")


# ─── summarize_run ──────────────────────────────────────────────────────────
# Inline LLM call from Capture Lead; not a complex multi-step skill.

async def summarize_run(results: list[dict]) -> str:
    """Final briefing: 3-5 sentences synthesizing all Capture Analyst bundles.

    Cite specialist verdicts ("Compliance Officer scored X reject on clearance").
    Don't editorialize. Don't upgrade reject decisions.

    Cost: ~$0.001 on Haiku.
    """
    raise NotImplementedError("A9 — Dev 1 implements alongside Capture Lead orchestration")
