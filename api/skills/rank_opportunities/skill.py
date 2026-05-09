"""rank_opportunities — deterministic ordering for the timeline UI.

Pure function. No LLM, no I/O. Sorts a list of scored opportunity dicts by
(decision_band_priority, -total_score, due_date_asc).
"""
from __future__ import annotations

from typing import Any

_BAND_ORDER = {"strong_pursue": 0, "pursue": 1, "maybe": 2, "reject": 3}


def rank_opportunities(payload: dict[str, Any]) -> dict[str, Any]:
    """Sort scored opportunities.

    Input shape:
        {"scored": [{"opportunity_id": str, "decision": str, "total_score": int, "due_date": str}, ...]}

    Output:
        {"ranked": [...]}  (same dicts, ordered)
    """
    scored = list(payload.get("scored", []))
    ranked = sorted(
        scored,
        key=lambda x: (
            _BAND_ORDER.get(x.get("decision"), 99),
            -int(x.get("total_score", 0)),
            x.get("due_date") or "9999-12-31",
        ),
    )
    return {"ranked": ranked}
