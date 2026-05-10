"""query_usaspending — Ledger's competitive-intel skill.

Calls USASpending.gov's award-search endpoint. No LLM. On rate-limit /
5xx / network error, returns degraded=True with empty awards/incumbents
so the caller can fall back to other intel sources.

USASpending API docs: https://api.usaspending.gov/api/v2/search/spending_by_award/
"""
from __future__ import annotations

from typing import Any

import httpx

USASPENDING_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# USASpending requires `filters.award_type_codes` to disambiguate prime
# contracts from grants/loans/IDVs. Default to all federal-contract codes:
#   A — BPA Call          (Blanket Purchase Agreement task order)
#   B — Purchase Order
#   C — Delivery Order    (against an existing IDV)
#   D — Definitive Contract
# The caller can override via payload["award_type_codes"].
_DEFAULT_AWARD_TYPE_CODES = ["A", "B", "C", "D"]


async def query_usaspending(
    payload: dict[str, Any],
    *,
    http: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Query USASpending awards.

    Input shape:
        {
          "naics": str | None,
          "agency": str | None,         # toptier agency name
          "limit": int,                 # default 25, max 100
          "award_type_codes": list[str] | None,  # default A/B/C/D (contracts)
        }

    Output:
        {
          "awards": list[dict],         # normalized; empty if degraded
          "incumbents": list[str],      # deduped Recipient Name; empty if degraded
          "total_obligated_usd": float, # sum of Award Amount; 0.0 if degraded
          "degraded": bool,
          "error": str,                 # empty if not degraded
        }

    Per-record normalized fields: recipient_name, award_amount,
    period_start, award_id, raw (the original record).
    """
    body: dict[str, Any] = {
        "filters": {
            "award_type_codes": list(
                payload.get("award_type_codes") or _DEFAULT_AWARD_TYPE_CODES
            ),
        },
        "fields": [
            "Recipient Name",
            "Award Amount",
            "Period of Performance Start Date",
            "Award ID",
        ],
        "limit": min(int(payload.get("limit") or 25), 100),
    }
    if payload.get("naics"):
        body["filters"]["naics_codes"] = [str(payload["naics"])]
    if payload.get("agency"):
        body["filters"]["agencies"] = [
            {"name": str(payload["agency"]), "tier": "toptier"}
        ]

    owns = http is None
    client = http or httpx.AsyncClient()
    try:
        try:
            resp = await client.post(USASPENDING_URL, json=body, timeout=20.0)
        except httpx.HTTPError as exc:
            return _degraded(f"network: {exc}")
        if resp.status_code == 429:
            return _degraded("USASpending rate limit (429)")
        if resp.status_code >= 500:
            return _degraded(f"USASpending 5xx: {resp.status_code}")
        if resp.status_code >= 400:
            return _degraded(
                f"USASpending client error: {resp.status_code} {resp.text[:300]}"
            )
        try:
            data = resp.json()
        except ValueError:
            return _degraded("USASpending returned non-JSON body")

        results = data.get("results") or []
        awards = [_normalize(rec) for rec in results]
        incumbents = sorted(
            {a["recipient_name"] for a in awards if a.get("recipient_name")}
        )
        total = sum(float(a.get("award_amount") or 0.0) for a in awards)
        return {
            "awards": awards,
            "incumbents": incumbents,
            "total_obligated_usd": round(total, 2),
            "degraded": False,
            "error": "",
        }
    finally:
        if owns:
            await client.aclose()


def _degraded(reason: str) -> dict[str, Any]:
    return {
        "awards": [],
        "incumbents": [],
        "total_obligated_usd": 0.0,
        "degraded": True,
        "error": reason,
    }


def _normalize(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "recipient_name": rec.get("Recipient Name") or "",
        "award_amount": rec.get("Award Amount"),
        "period_start": rec.get("Period of Performance Start Date"),
        "award_id": rec.get("Award ID"),
        "raw": rec,
    }
