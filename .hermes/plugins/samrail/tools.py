"""HTTP-wrapper tools for the samrail plugin.

Each handler does exactly one thing: serialize its `args` dict to JSON,
POST to `{SAMRAIL_API_BASE}/tools/<name>`, return the response body
via `tool_result()`. The pack-side route does input validation (Pydantic
422) and authentication (X-Internal-API-Key); this layer just forwards.

Schemas mirror `api/schemas/tool_requests.py` in the pack repo. They are
hand-written here rather than codegen-derived because (a) the codegen
target would need access to the pack's Python env, and (b) the pack-side
Pydantic model is the actual validator — these schemas are best-effort
hints to the LLM about valid argument shapes.
"""
from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from tools.registry import tool_error, tool_result


# ─── configuration ─────────────────────────────────────────────────────────

_DEFAULT_BASE = "http://localhost:8000"
_TIMEOUT_SECONDS = 60.0


def _api_base() -> str:
    return os.environ.get("SAMRAIL_API_BASE", _DEFAULT_BASE).rstrip("/")


def _api_key() -> str | None:
    # Match the pack's env var name. Empty / unset disables the toolset
    # via _check_samrail_available below.
    return os.environ.get("INTERNAL_API_KEY") or None


def _check_samrail_available() -> bool:
    """Hermes calls this before dispatching any tool in the toolset.
    Returns True only when an INTERNAL_API_KEY is configured.
    """
    return bool(_api_key())


# ─── HTTP forwarder ────────────────────────────────────────────────────────


def _post_tool(path: str, args: Dict[str, Any]) -> str:
    key = _api_key()
    if not key:
        return tool_error(
            "INTERNAL_API_KEY is not set. Configure it to match the pack's "
            "settings.internal_api_key, then retry."
        )
    url = f"{_api_base()}/tools/{path}"
    headers = {"X-Internal-API-Key": key, "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            resp = client.post(url, headers=headers, json=args)
    except httpx.HTTPError as exc:
        return tool_error(f"Could not reach pack at {url}: {exc}")

    if resp.status_code == 401:
        return tool_error("Pack rejected INTERNAL_API_KEY (401). Check the secret matches.")
    if resp.status_code == 422:
        return tool_error(f"Pack rejected payload (422): {resp.text}")
    if resp.status_code >= 300:
        return tool_error(
            f"Pack returned {resp.status_code}: {resp.text[:500]}"
        )
    try:
        return tool_result(resp.json())
    except ValueError:
        return tool_error(f"Pack returned non-JSON body: {resp.text[:500]}")


# ─── schemas (OpenAI function-call style) ──────────────────────────────────

SAMRAIL_PARSE_GOAL_SCHEMA = {
    "name": "samrail_parse_goal",
    "description": "Parse a natural-language federal-contracting goal into structured search criteria (keywords, NAICS hints, due window, set-aside preferences, etc.). LLM-backed.",
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Natural-language goal, e.g. 'Find FedRAMP cyber RFPs in the next 30 days'."},
            "company_profile": {"type": "object", "description": "Optional company context (NAICS codes, role, etc.)."},
        },
        "required": ["goal"],
    },
}

SAMRAIL_PARSE_PDF_SCHEMA = {
    "name": "samrail_parse_pdf",
    "description": "Deterministic page-aware PDF text extraction. NB: takes a server-local filesystem path. Cross-host callers must call samrail_fetch_attachment first.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute filesystem path on the pack's host."},
            "doc_id": {"type": "string", "description": "Optional document identifier; defaults to the file stem."},
        },
        "required": ["path"],
    },
}

SAMRAIL_EXTRACT_REQUIREMENTS_SCHEMA = {
    "name": "samrail_extract_requirements",
    "description": "Convert parsed PDF chunks into structured §10.1 requirements with evidence binding. LLM-backed; degrades to empty result on unparseable input.",
    "parameters": {
        "type": "object",
        "properties": {
            "parsed": {"type": "object", "description": "ParsePdfOutput dict from samrail_parse_pdf (chunks, doc_id, unparseable, etc.)."},
            "opportunity_metadata": {"type": "object", "description": "Optional opportunity context for the prompt."},
            "doc_id": {"type": "string", "description": "Optional document identifier override."},
        },
        "required": ["parsed"],
    },
}

SAMRAIL_SCORE_FIT_SCHEMA = {
    "name": "samrail_score_fit",
    "description": "Score how well a company fits an opportunity per §5.7 rubric. §11.1 deterministic short-circuit fires (score=0, decision=reject) when an eligibility blocker is present, skipping the LLM call entirely.",
    "parameters": {
        "type": "object",
        "properties": {
            "company_profile": {"type": "object"},
            "requirements": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["company_profile", "requirements"],
    },
}

SAMRAIL_DETECT_RISKS_SCHEMA = {
    "name": "samrail_detect_risks",
    "description": "Detect risks per the §5.8 taxonomy. Hallucinated categories are silently dropped; critical_blocker severity and legal_compliance_review category force human review.",
    "parameters": {
        "type": "object",
        "properties": {
            "company_profile": {"type": "object"},
            "opportunity": {"type": "object"},
            "requirements": {"type": "array", "items": {"type": "object"}},
        },
    },
}

SAMRAIL_GENERATE_ACTION_PACKAGE_SCHEMA = {
    "name": "samrail_generate_action_package",
    "description": "Synthesize the §5.11 action package. mode='full' calls the LLM; mode='reject_summary' is deterministic (no LLM) and used when score_fit returned decision=reject. The §5.13 invariant (non-empty human_approval_required) is enforced.",
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["full", "reject_summary"], "description": "Which mode to run."},
            "company_profile": {"type": "object"},
            "opportunity": {"type": "object"},
            "requirements": {"type": "array", "items": {"type": "object"}},
            "fit_score": {"type": "object"},
            "risks": {"type": "array", "items": {"type": "object"}},
        },
    },
}

SAMRAIL_SEARCH_SAM_SCHEMA = {
    "name": "samrail_search_sam",
    "description": "Query SAM.gov v2 search. Reads SAM_API_KEY on the pack side. Returns degraded=True with empty results on rate-limit, 5xx, or network error so the caller can fall back to samrail_load_seeded_opportunities.",
    "parameters": {
        "type": "object",
        "properties": {
            "keywords": {"type": "string"},
            "naics": {"type": "string"},
            "posted_from": {"type": "string", "description": "MM/dd/yyyy per SAM spec."},
            "set_aside": {"type": "string"},
            "state": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Default 20."},
        },
    },
}

SAMRAIL_FETCH_ATTACHMENT_SCHEMA = {
    "name": "samrail_fetch_attachment",
    "description": "Download a URL and persist its body to Supabase Storage at raw/<run_id>/<filename>. Used before samrail_parse_pdf when the PDF is not yet local.",
    "parameters": {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "description": "UUID of the agent run."},
            "url": {"type": "string", "description": "http(s) URL to the PDF."},
            "filename": {"type": "string", "description": "Optional override; derived from URL path if absent."},
        },
        "required": ["run_id", "url"],
    },
}

SAMRAIL_RANK_OPPORTUNITIES_SCHEMA = {
    "name": "samrail_rank_opportunities",
    "description": "Sort scored opportunities by (decision_band, -total_score, due_date_asc). Pure deterministic — no LLM, no I/O.",
    "parameters": {
        "type": "object",
        "properties": {
            "scored": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Each item should have opportunity_id, decision, total_score, due_date.",
            },
        },
        "required": ["scored"],
    },
}

SAMRAIL_LOAD_SEEDED_OPPORTUNITIES_SCHEMA = {
    "name": "samrail_load_seeded_opportunities",
    "description": "Read fixture manifests under /fixtures/ and persist opportunities. Idempotent on slug. Use as a fallback when SAM live queries fail (degraded=true).",
    "parameters": {
        "type": "object",
        "properties": {
            "slugs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of fixture slugs to load. Null/missing means load all.",
            },
        },
    },
}

SAMRAIL_QUERY_USASPENDING_SCHEMA = {
    "name": "samrail_query_usaspending",
    "description": "Query USASpending.gov for competitive intel on prior awards. Filters by NAICS and/or top-tier agency name. Returns normalized award records, deduped incumbent list, and total obligated dollars. Degrades gracefully on rate-limit / 5xx.",
    "parameters": {
        "type": "object",
        "properties": {
            "naics": {"type": "string", "description": "NAICS code"},
            "agency": {"type": "string", "description": "Top-tier agency name"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Default 25."},
            "award_type_codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "USASpending award type codes. Default: ['A','B','C','D'] (federal contracts: BPA Call, Purchase Order, Delivery Order, Definitive Contract). Override to query grants ['02','03','04','05'] etc.",
            },
        },
    },
}


# ─── handlers ──────────────────────────────────────────────────────────────


def _handle_parse_goal(args: dict, **_kw) -> str:
    return _post_tool("parse-goal", args)


def _handle_parse_pdf(args: dict, **_kw) -> str:
    return _post_tool("parse-pdf", args)


def _handle_extract_requirements(args: dict, **_kw) -> str:
    return _post_tool("extract-requirements", args)


def _handle_score_fit(args: dict, **_kw) -> str:
    return _post_tool("score-fit", args)


def _handle_detect_risks(args: dict, **_kw) -> str:
    return _post_tool("detect-risks", args)


def _handle_generate_action_package(args: dict, **_kw) -> str:
    return _post_tool("generate-action-package", args)


def _handle_search_sam(args: dict, **_kw) -> str:
    return _post_tool("search-sam", args)


def _handle_fetch_attachment(args: dict, **_kw) -> str:
    return _post_tool("fetch-attachment", args)


def _handle_rank_opportunities(args: dict, **_kw) -> str:
    return _post_tool("rank-opportunities", args)


def _handle_load_seeded_opportunities(args: dict, **_kw) -> str:
    return _post_tool("load-seeded-opportunities", args)


def _handle_query_usaspending(args: dict, **_kw) -> str:
    return _post_tool("query-usaspending", args)
