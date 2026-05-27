from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import os
from typing import Any
import urllib.parse
import urllib.request

from pydantic import BaseModel, Field

SAM_SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"
DEFAULT_TIMEOUT_SECONDS = 20


class SamOpportunity(BaseModel):
    notice_id: str
    title: str
    agency: str | None = None
    solicitation_number: str | None = None
    posted_date: str | None = None
    due_date: str | None = None
    naics: str | None = None
    opportunity_type: str | None = None
    set_aside: str | None = None
    place_of_performance: str | None = None
    description: str | None = None
    source_url: str | None = None
    attachments: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class SamSearchResult(BaseModel):
    total_records: int
    opportunities: list[SamOpportunity]
    degraded: bool = False
    error: str | None = None


def _load_api_key(api_key: str | None = None) -> str:
    if api_key:
        return api_key
    key = os.getenv("SAM_API_KEY")
    if key:
        return key
    # Lightweight .env fallback so scripts/tests work without python-dotenv.
    for candidate in (".env",):
        try:
            for line in open(candidate, encoding="utf-8"):
                if line.startswith("SAM_API_KEY="):
                    value = line.strip().split("=", 1)[1]
                    if value:
                        return value
        except FileNotFoundError:
            continue
    raise RuntimeError("SAM_API_KEY is required for live SAM.gov opportunity search")


def _fmt_sam_date(d: date) -> str:
    return d.strftime("%m/%d/%Y")


def _normalize_date(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    # SAM sometimes includes timezone with colon; fromisoformat handles that.
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return text[:10] if len(text) >= 10 else text


def _place_of_performance(raw: dict[str, Any]) -> str | None:
    pop = raw.get("placeOfPerformance") or {}
    if isinstance(pop, str):
        return pop
    parts: list[str] = []
    city = pop.get("city") if isinstance(pop, dict) else None
    state = pop.get("state") if isinstance(pop, dict) else None
    country = pop.get("country") if isinstance(pop, dict) else None
    if isinstance(city, dict) and city.get("name"):
        parts.append(city["name"])
    if isinstance(state, dict) and state.get("name"):
        parts.append(state["name"])
    if isinstance(country, dict) and country.get("name"):
        parts.append(country["name"])
    return ", ".join(parts) or None


def _source_url(raw: dict[str, Any]) -> str | None:
    if raw.get("uiLink"):
        return raw["uiLink"]
    links = raw.get("links")
    if isinstance(links, list) and links:
        href = links[0].get("href") if isinstance(links[0], dict) else links[0]
        if href:
            return str(href)
    notice_id = raw.get("noticeId")
    return f"https://sam.gov/opp/{notice_id}/view" if notice_id else None


def _attachments(raw: dict[str, Any]) -> list[str]:
    links = raw.get("resourceLinks") or []
    if isinstance(links, str):
        return [links]
    return [str(link) for link in links if link]


def _normalize_opportunity(raw: dict[str, Any]) -> SamOpportunity:
    return SamOpportunity(
        notice_id=str(raw.get("noticeId") or raw.get("id") or ""),
        title=str(raw.get("title") or "Untitled opportunity"),
        agency=raw.get("fullParentPathName") or raw.get("department") or raw.get("subTier"),
        solicitation_number=raw.get("solicitationNumber"),
        posted_date=_normalize_date(raw.get("postedDate")),
        due_date=_normalize_date(raw.get("responseDeadLine") or raw.get("responseDeadline")),
        naics=str(raw.get("naicsCode")) if raw.get("naicsCode") else None,
        opportunity_type=raw.get("type") or raw.get("baseType"),
        set_aside=raw.get("setAside"),
        place_of_performance=_place_of_performance(raw),
        description=raw.get("description"),
        source_url=_source_url(raw),
        attachments=_attachments(raw),
        raw=raw,
    )


def search_sam_opportunities(
    *,
    keyword: str,
    api_key: str | None = None,
    posted_from: date | None = None,
    posted_to: date | None = None,
    limit: int = 10,
    offset: int = 0,
    ptype: str = "o",
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> SamSearchResult:
    """Search SAM.gov opportunities and return normalized opportunity records.

    Defaults to the last 30 days. The API key is intentionally kept out of logs;
    callers should redact the resulting URL if they print it.
    """
    key = _load_api_key(api_key)
    today = date.today()
    posted_to = posted_to or today
    posted_from = posted_from or (posted_to - timedelta(days=30))
    params = {
        "api_key": key,
        "limit": str(limit),
        "offset": str(offset),
        "postedFrom": _fmt_sam_date(posted_from),
        "postedTo": _fmt_sam_date(posted_to),
        "ptype": ptype,
        "keyword": keyword,
    }
    url = SAM_SEARCH_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
    rows = payload.get("opportunitiesData") or []
    return SamSearchResult(
        total_records=int(payload.get("totalRecords") or len(rows)),
        opportunities=[_normalize_opportunity(row) for row in rows],
    )
