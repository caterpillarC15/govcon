"""MCP server wrapping the GovCon /api/v1/tools/<name> public surface.

The 10 tools are thin HTTP wrappers — same pattern as the Hermes plugin
at .hermes/plugins/govcapture/. The pack-side route is the source of
truth; this module just adapts MCP tool calls into HTTP POSTs.

Configuration via environment variables:
  GOVCAPTURE_API_BASE   default https://api.govcapture.example
  GOVCAPTURE_API_KEY    required; gck_… key minted at /app/keys

Install in Claude Desktop with this entry in claude_desktop_config.json:

  {
    "mcpServers": {
      "govcapture": {
        "command": "mcp-server-govcapture",
        "env": { "GOVCAPTURE_API_KEY": "gck_..." }
      }
    }
  }
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("govcapture")

_DEFAULT_BASE = "https://api.govcapture.example"
_TIMEOUT_SECONDS = 60.0


def _api_base() -> str:
    return os.environ.get("GOVCAPTURE_API_BASE", _DEFAULT_BASE).rstrip("/")


def _api_key() -> str | None:
    return os.environ.get("GOVCAPTURE_API_KEY") or None


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST to /api/v1/tools/<path> and return the parsed JSON envelope.

    Raises RuntimeError on missing key, httpx.HTTPError on transport errors,
    and a RuntimeError with the body on 4xx/5xx so the MCP client surfaces
    the failure to the agent.
    """
    key = _api_key()
    if not key:
        raise RuntimeError(
            "GOVCAPTURE_API_KEY not set. Mint one at /app/keys and add it "
            "to your MCP client config."
        )
    url = f"{_api_base()}/api/v1/tools/{path}"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
        resp = client.post(url, headers=headers, json=payload)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"govcapture {path} returned {resp.status_code}: {resp.text[:500]}"
        )
    try:
        return resp.json()
    except ValueError as exc:
        raise RuntimeError(
            f"govcapture {path} returned non-JSON body: {resp.text[:500]}"
        ) from exc


@mcp.tool()
def parse_goal(
    goal: str,
    company_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse a natural-language GovCon goal into structured search criteria
    (keywords, NAICS hints, due window, set-aside preferences). LLM-backed."""
    return _post("parse-goal", {"goal": goal, "company_profile": company_profile or {}})


@mcp.tool()
def parse_pdf(path: str, doc_id: str | None = None) -> dict[str, Any]:
    """Deterministic page-aware PDF text extraction. NB: takes a server-local
    filesystem path. Cross-host callers should call fetch_attachment first."""
    return _post("parse-pdf", {"path": path, "doc_id": doc_id})


@mcp.tool()
def extract_requirements(
    parsed: dict[str, Any],
    opportunity_metadata: dict[str, Any] | None = None,
    doc_id: str | None = None,
) -> dict[str, Any]:
    """Convert parsed PDF chunks into structured §10.1 requirements with
    evidence binding. LLM-backed; degrades to empty result on unparseable input."""
    return _post(
        "extract-requirements",
        {
            "parsed": parsed,
            "opportunity_metadata": opportunity_metadata or {},
            "doc_id": doc_id,
        },
    )


@mcp.tool()
def score_fit(
    company_profile: dict[str, Any],
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score how well a company fits an opportunity per §5.7 rubric.
    §11.1 deterministic short-circuit fires (score=0, decision=reject)
    when an eligibility blocker is present, skipping the LLM call entirely."""
    return _post(
        "score-fit",
        {"company_profile": company_profile, "requirements": requirements},
    )


@mcp.tool()
def detect_risks(
    company_profile: dict[str, Any] | None = None,
    opportunity: dict[str, Any] | None = None,
    requirements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Detect risks per the §5.8 taxonomy. Hallucinated categories are
    silently dropped; critical_blocker severity and legal_compliance_review
    category force human review."""
    return _post(
        "detect-risks",
        {
            "company_profile": company_profile or {},
            "opportunity": opportunity or {},
            "requirements": requirements or [],
        },
    )


@mcp.tool()
def generate_action_package(
    mode: str = "full",
    company_profile: dict[str, Any] | None = None,
    opportunity: dict[str, Any] | None = None,
    requirements: list[dict[str, Any]] | None = None,
    fit_score: dict[str, Any] | None = None,
    risks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Synthesize the §5.11 action package. mode='full' calls the LLM;
    mode='reject_summary' is deterministic (no LLM) and used when score_fit
    returned decision=reject."""
    return _post(
        "generate-action-package",
        {
            "mode": mode,
            "company_profile": company_profile or {},
            "opportunity": opportunity or {},
            "requirements": requirements or [],
            "fit_score": fit_score or {},
            "risks": risks or [],
        },
    )


@mcp.tool()
def search_sam(
    keywords: str = "",
    naics: str | None = None,
    posted_from: str | None = None,
    set_aside: str | None = None,
    state: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Query SAM.gov v2 search. Reads SAM_API_KEY on the pack side. Returns
    degraded=True with empty results on rate-limit, 5xx, or network error so
    the caller can fall back to load_seeded_opportunities."""
    return _post(
        "search-sam",
        {
            "keywords": keywords,
            "naics": naics,
            "posted_from": posted_from,
            "set_aside": set_aside,
            "state": state,
            "limit": limit,
        },
    )


@mcp.tool()
def fetch_attachment(
    run_id: str,
    url: str,
    filename: str | None = None,
) -> dict[str, Any]:
    """Download a URL and persist its body to Supabase Storage at
    raw/<run_id>/<filename>. Use before parse_pdf when the PDF isn't local."""
    return _post(
        "fetch-attachment",
        {"run_id": run_id, "url": url, "filename": filename},
    )


@mcp.tool()
def rank_opportunities(scored: list[dict[str, Any]]) -> dict[str, Any]:
    """Sort scored opportunities by (decision_band, -total_score, due_date_asc).
    Pure deterministic — no LLM, no I/O."""
    return _post("rank-opportunities", {"scored": scored})


@mcp.tool()
def load_seeded_opportunities(
    slugs: list[str] | None = None,
) -> dict[str, Any]:
    """Read fixture manifests under /fixtures/ and persist opportunities.
    Idempotent on slug. Use as a fallback when SAM live queries fail."""
    return _post("load-seeded-opportunities", {"slugs": slugs})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
