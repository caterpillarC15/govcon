"""Strict diff for deterministic skill outputs (PRD v1.2.6).

Tolerance helpers that absorbed LLM drift were removed when the
skills became deterministic — drift is now a real bug, not noise.
Compares structural equality on every key in `expected`.
"""
from __future__ import annotations

from typing import Any


def diff_within_tolerance(
    expected: dict[str, Any],
    actual: dict[str, Any],
    *,
    # Kept for back-compat callers; ignored. Skills are deterministic.
    int_tolerance: int = 0,
    string_substr: bool = False,
) -> list[str]:
    """Return human-readable mismatch lines. Empty list = pass."""
    del int_tolerance, string_substr  # historical args, no-op
    issues: list[str] = []
    for key in expected:
        if key not in actual:
            issues.append(f"missing: {key}")
            continue
        if expected[key] != actual[key]:
            issues.append(f"{key}: {expected[key]!r} != {actual[key]!r}")
    return issues
