"""rank_opportunities — pure deterministic sort."""
from __future__ import annotations

from api.skills.rank_opportunities import rank_opportunities


def test_orders_by_band_then_score_then_deadline():
    """Within same band, higher score wins; within same band+score, earlier due wins."""
    scored = [
        {"opportunity_id": "a", "decision": "maybe", "total_score": 60, "due_date": "2026-06-01"},
        {"opportunity_id": "b", "decision": "strong_pursue", "total_score": 88, "due_date": "2026-07-01"},
        {"opportunity_id": "c", "decision": "strong_pursue", "total_score": 92, "due_date": "2026-08-01"},
        {"opportunity_id": "d", "decision": "reject", "total_score": 0, "due_date": "2026-05-15"},
    ]
    out = rank_opportunities({"scored": scored})
    assert [r["opportunity_id"] for r in out["ranked"]] == ["c", "b", "a", "d"]


def test_same_score_breaks_tie_by_earlier_deadline():
    """Same band, same score → earlier due_date ranked higher."""
    scored = [
        {"opportunity_id": "later", "decision": "pursue", "total_score": 75, "due_date": "2026-08-01"},
        {"opportunity_id": "earlier", "decision": "pursue", "total_score": 75, "due_date": "2026-06-01"},
    ]
    out = rank_opportunities({"scored": scored})
    assert [r["opportunity_id"] for r in out["ranked"]] == ["earlier", "later"]


def test_missing_due_date_sorted_last_within_band():
    """Opportunities without a due_date go to the end of their band."""
    scored = [
        {"opportunity_id": "no-date", "decision": "maybe", "total_score": 60, "due_date": None},
        {"opportunity_id": "with-date", "decision": "maybe", "total_score": 60, "due_date": "2026-09-01"},
    ]
    out = rank_opportunities({"scored": scored})
    assert [r["opportunity_id"] for r in out["ranked"]] == ["with-date", "no-date"]


def test_unknown_decision_band_sorted_last():
    """Defensive: a decision value outside the 4 bands sorts after all known bands."""
    scored = [
        {"opportunity_id": "weird", "decision": "unknown_band", "total_score": 99, "due_date": "2026-06-01"},
        {"opportunity_id": "normal", "decision": "maybe", "total_score": 60, "due_date": "2026-07-01"},
    ]
    out = rank_opportunities({"scored": scored})
    assert [r["opportunity_id"] for r in out["ranked"]] == ["normal", "weird"]


def test_empty_input():
    out = rank_opportunities({"scored": []})
    assert out["ranked"] == []


def test_input_not_mutated():
    """The original list must not be mutated by the sort."""
    scored = [
        {"opportunity_id": "a", "decision": "maybe", "total_score": 60, "due_date": "2026-06-01"},
        {"opportunity_id": "b", "decision": "strong_pursue", "total_score": 88, "due_date": "2026-07-01"},
    ]
    original_order = [d["opportunity_id"] for d in scored]
    rank_opportunities({"scored": scored})
    assert [d["opportunity_id"] for d in scored] == original_order
