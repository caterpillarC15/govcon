"""Well-known agent-discoverability endpoints.

Public, auth-free routes that let AI crawlers, MCP clients, and other
agents discover what SamRail does and how to call it. Modeled
on the emerging /.well-known/agent.json + llms.txt conventions plus
FastAPI's auto-generated /openapi.json.

The endpoints are deliberately auth-free and CORS-permissive so any
agent can fetch them. They expose only metadata; no PII or per-tenant
content. Tool dispatch still requires X-Internal-API-Key (Sprint B) or
a per-agent gck_… key (Phase 8 follow-up).
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter(tags=["well-known"])


_TOOL_NAMES = (
    "parse-goal",
    "parse-pdf",
    "extract-requirements",
    "score-fit",
    "detect-risks",
    "generate-action-package",
    "search-sam",
    "fetch-attachment",
    "rank-opportunities",
    "load-seeded-opportunities",
)


@router.get("/.well-known/agent.json", response_class=JSONResponse)
async def agent_manifest() -> dict:
    """Agent-discoverability manifest.

    Format follows the de-facto /.well-known/agent.json convention used by
    zero.xyz and similar agent-native platforms. Stable URLs; field shape
    may evolve. `tools` lists the public route names; full schemas live
    in /openapi.json.
    """
    return {
        "name": "SamRail",
        "description": (
            "Federal contracting capability pack: a hired AI worker that "
            "finds federal contracts worth bidding on, decides "
            "pursue/skip, and produces a bid memo with a human-approval "
            "gate. Exposes 10 typed tools."
        ),
        "version": "1.0.0",
        "openapi_url": "/openapi.json",
        "docs_url": "/docs",
        "llms_url": "/.well-known/llms.txt",
        "tools_url": "/tools",
        "tools": [{"name": name, "path": f"/tools/{name}"} for name in _TOOL_NAMES],
        "auth": {
            "type": "bearer",
            "schemes": ["X-Internal-API-Key", "gck (planned)"],
            "notes": (
                "Internal callers use X-Internal-API-Key (header). Public "
                "per-agent gck_… keys are planned in a follow-up sprint."
            ),
        },
        "envelope": {
            "data": "skill output (dict or Pydantic model dump)",
        },
        "contact": {
            "support": "support@samrail.com",
            "agents": "agents@samrail.com",
        },
    }


_LLMS_TXT = """\
# SamRail

Federal contracting capability pack. A hired AI worker that finds federal
contracts worth bidding on, decides pursue/skip, and produces a bid memo
plus action plan with a human-approval gate before anything goes out the
door.

## What it is, in one sentence
A capability pack — callable specialist tools — exposed over HTTP that any
agent can use to do federal contracting work end-to-end without having to
re-implement SAM scraping, requirement extraction, eligibility checking,
fit scoring, risk detection, or bid memo synthesis.

## For agents

- Discovery: GET /.well-known/agent.json
- Schemas:   GET /openapi.json (FastAPI auto-generated)
- Docs:      GET /docs (Swagger UI)
- Tools:     POST /tools/<name> (10 endpoints; see manifest)

## Tools

Per PRD v1.2.6 every tool is **deterministic** — this pack holds
mechanics + validators only; LLM judgment lives in the calling
agent's context (see CAPABILITY_PACK_INTEGRATION.md).

| Tool | Purpose |
|---|---|
| parse-goal | input pass-through validator (caller does goal extraction) |
| parse-pdf | deterministic page-aware PDF text extraction |
| extract-requirements | parsed-PDF chunks emitter + §11 evidence-binding validator |
| score-fit | §11.1 short-circuit + decision-band normalizer (caller supplies total_score) |
| detect-risks | §5.8 risk taxonomy validator (caller supplies risks; skill enforces filtering + critical_blocker carry-forward) |
| generate-action-package | reject_summary mode (deterministic); full mode validates caller-supplied content + §5.13 enforcement |
| search-sam | SAM.gov v2 search; degraded fallback on rate-limit / 5xx |
| fetch-attachment | URL -> Supabase Storage at raw/<run_id>/<filename> |
| rank-opportunities | deterministic sort by (decision band, -score, due asc) |
| load-seeded-opportunities | fixture manifests into the opportunities table; idempotent |
| query-usaspending | USASpending HTTP query → competitor_history persistence |

## Conventions

- All responses share envelope: `{"data": ...}` — no `metrics` field
  (PRD v1.2.6: every skill is deterministic, no LLM cost to report).
  Cost + token tracking live with the caller (Michaela's bench).
- All requests are JSON bodies; required fields per /openapi.json
- 401 on missing/wrong auth header; 422 on malformed payload; 200 on success
- `decision` values: strong_pursue | pursue | maybe | reject | needs_score

## Auth

Today: internal-only with `X-Internal-API-Key: <secret>` (single shared
secret). Per-agent `gck_…` keys minted via /api/keys are planned. When
that lands, the same /tools/<name> routes accept either header.

## Stability + versioning

- Tool names are stable; new tools may be added.
- Request/response shapes are versioned via /openapi.json. Field
  additions are non-breaking; field removals or renames will bump a
  major version visible in /.well-known/agent.json `version`.
- Trace events emitted to Redis channel `agent-run:<run_id>` follow the
  taxonomy in /openapi.json (see TraceEvent shape).

## Contact

agents@samrail.com
"""


@router.get("/.well-known/llms.txt", response_class=PlainTextResponse)
async def llms_txt() -> str:
    """Natural-language description of the platform for AI crawlers.

    Follows the emerging llms.txt convention (analogous to robots.txt, but
    for LLM-driven crawlers). Plain text / markdown; intentionally
    self-contained — an LLM should be able to figure out how to use the
    platform from this file alone plus /openapi.json.
    """
    return _LLMS_TXT
