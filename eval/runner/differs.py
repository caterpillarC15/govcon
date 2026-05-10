"""Tolerant comparison primitives. LLM outputs aren't bit-stable, so
exact-equality is too strict; we use per-field tolerance rules."""
from __future__ import annotations

from typing import Any


def diff_within_tolerance(
    expected: dict[str, Any],
    actual: dict[str, Any],
    *,
    int_tolerance: int = 5,
    string_substr: bool = True,
) -> list[str]:
    """Return a list of human-readable mismatch lines. Empty list = pass.

    Per-field rules:
    - `total_score` (int): numeric ±int_tolerance.
    - `decision` (str): must match exactly.
    - `evidence_snippet` (str): substring match (first 60 chars of expected
      must appear in actual).
    - everything else: structural equality on present keys.
    """
    issues: list[str] = []
    for key in expected:
        if key not in actual:
            issues.append(f"missing: {key}")
            continue
        ev = expected[key]
        av = actual[key]
        if key == "total_score" and isinstance(ev, int):
            try:
                drift = abs(ev - int(av))
            except (TypeError, ValueError):
                issues.append(f"total_score not numeric: {av!r}")
                continue
            if drift > int_tolerance:
                issues.append(f"total_score drift: expected {ev}, got {av} (Δ={drift})")
        elif key == "decision":
            if ev != av:
                issues.append(f"decision mismatch: expected {ev!r}, got {av!r}")
        elif key == "evidence_snippet" and string_substr:
            if isinstance(ev, str) and isinstance(av, str) and ev[:60] not in av:
                issues.append(f"evidence_snippet missing substring: {ev[:60]!r}")
        elif ev != av:
            issues.append(f"{key}: {ev!r} != {av!r}")
    return issues
