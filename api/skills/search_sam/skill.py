"""search_sam_opportunities — A11.

Calls SAM.gov Opportunities v2 search API. Normalizes hits to the project's
opportunity dict shape. On rate-limit/5xx/network error, returns degraded=True
with empty results so the planner can fall back to load_seeded_opportunities
(PRD §5.4 fallback hierarchy: live → cached → seeded).
"""
from __future__ import annotations
from typing import Any
import httpx

SAM_URL = "https://api.sam.gov/opportunities/v2/search"


async def search_sam_opportunities(
    payload: dict[str, Any],
    *,
    api_key: str,
    http: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Query SAM.gov v2 search.

    Input shape:
        {
          "keywords": str,                 # required (can be empty)
          "naics": str | None,
          "posted_from": str | None,       # MM/dd/yyyy per SAM spec
          "set_aside": str | None,
          "state": str | None,
          "limit": int,                    # default 20
        }

    Output:
        {
          "opportunities": list[dict],     # normalized to project schema
          "degraded": bool,
          "error": str,                    # empty if not degraded
        }
    """
    params: dict[str, Any] = {
        "api_key": api_key,
        "limit": payload.get("limit", 20),
        "q": payload.get("keywords", ""),
    }
    if payload.get("naics"):
        params["naicsCode"] = payload["naics"]
    if payload.get("posted_from"):
        params["postedFrom"] = payload["posted_from"]
    if payload.get("set_aside"):
        params["typeOfSetAside"] = payload["set_aside"]
    if payload.get("state"):
        params["state"] = payload["state"]

    owns_client = http is None
    client = http or httpx.AsyncClient()
    try:
        try:
            resp = await client.get(SAM_URL, params=params, timeout=20.0)
        except httpx.HTTPError as e:
            return {"opportunities": [], "degraded": True, "error": f"network: {e}"}

        if resp.status_code == 429:
            return {"opportunities": [], "degraded": True, "error": "SAM rate limit (429)"}
        if resp.status_code >= 500:
            return {"opportunities": [], "degraded": True, "error": f"SAM 5xx: {resp.status_code}"}
        if resp.status_code >= 400:
            return {"opportunities": [], "degraded": True, "error": f"SAM client error: {resp.status_code}"}

        data = resp.json()
        normalized = [_normalize(rec) for rec in data.get("opportunitiesData", [])]
        return {"opportunities": normalized, "degraded": False, "error": ""}
    finally:
        if owns_client:
            await client.aclose()


def _normalize(rec: dict[str, Any]) -> dict[str, Any]:
    """Map SAM v2 record to project's opportunity dict shape."""
    return {
        "title": rec.get("title", ""),
        "agency": (rec.get("fullParentPathName") or "").split(".")[0],
        "solicitation_number": rec.get("noticeId", ""),
        "source_url": rec.get("uiLink", ""),
        "due_date": (rec.get("responseDeadLine") or "")[:10],
        "naics": rec.get("naicsCode", ""),
        "set_aside": rec.get("typeOfSetAsideDescription") or "None",
        "place_of_performance": (
            (rec.get("placeOfPerformance") or {}).get("city", {}).get("name", "")
        ),
        "description": (rec.get("description") or "")[:1000],
        "attachments": [],
        "raw_payload": rec,
    }
