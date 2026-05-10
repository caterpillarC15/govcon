"""samrail Hermes plugin.

Registers 10 tools that wrap the SamRail capability pack's
`POST /tools/<name>` HTTP surface (Sprint B). Each tool serializes its
arguments, posts to the pack's API, and returns the JSON envelope
`{"data": ..., "metrics": ...}` to the agent.

Why HTTP instead of in-process Python imports:

The pack runs Python 3.12 with FastAPI + supabase-py + anthropic SDK +
its own dep tree. Hermes runs Python 3.11 in its own venv. Coupling the
two interpreter envs is fragile (matching versions, conflicting deps,
package install state).

The HTTP wrapper costs ~1ms per call on local-loopback and gives us:
  - Process isolation (orchestrator crash != pack crash)
  - One canonical code path (Sprint B routes are already tested)
  - Works against any pack deployment (local dev, prod VX1)
  - No Python-version coupling between Hermes and the pack

Configuration via environment variables:
  - SAMRAIL_API_BASE (default: http://localhost:8000)
  - INTERNAL_API_KEY (required; must match the pack's settings.internal_api_key)
"""
from __future__ import annotations

from plugins.samrail.tools import (
    SAMRAIL_DETECT_RISKS_SCHEMA,
    SAMRAIL_EXTRACT_REQUIREMENTS_SCHEMA,
    SAMRAIL_FETCH_ATTACHMENT_SCHEMA,
    SAMRAIL_GENERATE_ACTION_PACKAGE_SCHEMA,
    SAMRAIL_LOAD_SEEDED_OPPORTUNITIES_SCHEMA,
    SAMRAIL_PARSE_GOAL_SCHEMA,
    SAMRAIL_PARSE_PDF_SCHEMA,
    SAMRAIL_QUERY_USASPENDING_SCHEMA,
    SAMRAIL_RANK_OPPORTUNITIES_SCHEMA,
    SAMRAIL_SCORE_FIT_SCHEMA,
    SAMRAIL_SEARCH_SAM_SCHEMA,
    _check_samrail_available,
    _handle_detect_risks,
    _handle_extract_requirements,
    _handle_fetch_attachment,
    _handle_generate_action_package,
    _handle_load_seeded_opportunities,
    _handle_parse_goal,
    _handle_parse_pdf,
    _handle_query_usaspending,
    _handle_rank_opportunities,
    _handle_score_fit,
    _handle_search_sam,
)

_TOOLS = (
    ("samrail_parse_goal",                  SAMRAIL_PARSE_GOAL_SCHEMA,                  _handle_parse_goal,                  "🎯"),
    ("samrail_parse_pdf",                   SAMRAIL_PARSE_PDF_SCHEMA,                   _handle_parse_pdf,                   "📄"),
    ("samrail_extract_requirements",        SAMRAIL_EXTRACT_REQUIREMENTS_SCHEMA,        _handle_extract_requirements,        "📋"),
    ("samrail_score_fit",                   SAMRAIL_SCORE_FIT_SCHEMA,                   _handle_score_fit,                   "🎯"),
    ("samrail_detect_risks",                SAMRAIL_DETECT_RISKS_SCHEMA,                _handle_detect_risks,                "⚠️"),
    ("samrail_generate_action_package",     SAMRAIL_GENERATE_ACTION_PACKAGE_SCHEMA,     _handle_generate_action_package,     "📦"),
    ("samrail_search_sam",                  SAMRAIL_SEARCH_SAM_SCHEMA,                  _handle_search_sam,                  "🔎"),
    ("samrail_fetch_attachment",            SAMRAIL_FETCH_ATTACHMENT_SCHEMA,            _handle_fetch_attachment,            "⬇️"),
    ("samrail_rank_opportunities",          SAMRAIL_RANK_OPPORTUNITIES_SCHEMA,          _handle_rank_opportunities,          "📊"),
    ("samrail_load_seeded_opportunities",   SAMRAIL_LOAD_SEEDED_OPPORTUNITIES_SCHEMA,   _handle_load_seeded_opportunities,   "🌱"),
    ("samrail_query_usaspending",           SAMRAIL_QUERY_USASPENDING_SCHEMA,           _handle_query_usaspending,           "💰"),
)


def register(ctx) -> None:
    """register all samrail tools. Called once by the plugin loader."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="samrail",
            schema=schema,
            handler=handler,
            check_fn=_check_samrail_available,
            requires_env=["INTERNAL_API_KEY"],
            emoji=emoji,
        )
