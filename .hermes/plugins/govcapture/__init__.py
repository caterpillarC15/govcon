"""govcapture Hermes plugin.

Registers 10 tools that wrap the GovCon Bid Desk capability pack's
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
  - GOVCAPTURE_API_BASE (default: http://localhost:8000)
  - INTERNAL_API_KEY (required; must match the pack's settings.internal_api_key)
"""
from __future__ import annotations

from plugins.govcapture.tools import (
    GOVCAPTURE_DETECT_RISKS_SCHEMA,
    GOVCAPTURE_EXTRACT_REQUIREMENTS_SCHEMA,
    GOVCAPTURE_FETCH_ATTACHMENT_SCHEMA,
    GOVCAPTURE_GENERATE_ACTION_PACKAGE_SCHEMA,
    GOVCAPTURE_LOAD_SEEDED_OPPORTUNITIES_SCHEMA,
    GOVCAPTURE_PARSE_GOAL_SCHEMA,
    GOVCAPTURE_PARSE_PDF_SCHEMA,
    GOVCAPTURE_RANK_OPPORTUNITIES_SCHEMA,
    GOVCAPTURE_SCORE_FIT_SCHEMA,
    GOVCAPTURE_SEARCH_SAM_SCHEMA,
    _check_govcapture_available,
    _handle_detect_risks,
    _handle_extract_requirements,
    _handle_fetch_attachment,
    _handle_generate_action_package,
    _handle_load_seeded_opportunities,
    _handle_parse_goal,
    _handle_parse_pdf,
    _handle_rank_opportunities,
    _handle_score_fit,
    _handle_search_sam,
)

_TOOLS = (
    ("govcapture_parse_goal",                  GOVCAPTURE_PARSE_GOAL_SCHEMA,                  _handle_parse_goal,                  "🎯"),
    ("govcapture_parse_pdf",                   GOVCAPTURE_PARSE_PDF_SCHEMA,                   _handle_parse_pdf,                   "📄"),
    ("govcapture_extract_requirements",        GOVCAPTURE_EXTRACT_REQUIREMENTS_SCHEMA,        _handle_extract_requirements,        "📋"),
    ("govcapture_score_fit",                   GOVCAPTURE_SCORE_FIT_SCHEMA,                   _handle_score_fit,                   "🎯"),
    ("govcapture_detect_risks",                GOVCAPTURE_DETECT_RISKS_SCHEMA,                _handle_detect_risks,                "⚠️"),
    ("govcapture_generate_action_package",     GOVCAPTURE_GENERATE_ACTION_PACKAGE_SCHEMA,     _handle_generate_action_package,     "📦"),
    ("govcapture_search_sam",                  GOVCAPTURE_SEARCH_SAM_SCHEMA,                  _handle_search_sam,                  "🔎"),
    ("govcapture_fetch_attachment",            GOVCAPTURE_FETCH_ATTACHMENT_SCHEMA,            _handle_fetch_attachment,            "⬇️"),
    ("govcapture_rank_opportunities",          GOVCAPTURE_RANK_OPPORTUNITIES_SCHEMA,          _handle_rank_opportunities,          "📊"),
    ("govcapture_load_seeded_opportunities",   GOVCAPTURE_LOAD_SEEDED_OPPORTUNITIES_SCHEMA,   _handle_load_seeded_opportunities,   "🌱"),
)


def register(ctx) -> None:
    """Register all govcapture tools. Called once by the plugin loader."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="govcapture",
            schema=schema,
            handler=handler,
            check_fn=_check_govcapture_available,
            requires_env=["INTERNAL_API_KEY"],
            emoji=emoji,
        )
