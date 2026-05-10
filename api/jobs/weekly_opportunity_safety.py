"""§5.14 hard safety filters for the weekly opportunity auto-picker.

Deterministic — no LLM. Honors the spirit of PRD §11.1 across an audience
the agent doesn't have CompanyProfile data for: when the configuration of
an opportunity introduces uncertainty about whether the recipient could
even bid, we exclude it rather than emit a misleading "this might be a
fit" recommendation. Filters here are AND-composed; one rejection drops
the row.

Returned rejection reasons are short structured strings stored in the
`picker_audit` JSONB column so a curator can audit why specific
opportunities didn't make it.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

# US state postal codes + DC + territories. Pre-compiled set for hot-path use.
_US_STATES: frozenset[str] = frozenset(
    {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC", "PR", "GU", "VI", "AS", "MP",
    }
)

# Set-asides we accept. Anything narrower (8(a), HUBZone, WOSB, EDWOSB,
# SDVOSB, VOSB) needs per-subscriber eligibility data we don't have.
_ACCEPTABLE_SET_ASIDES: frozenset[str] = frozenset(
    {
        "",
        "none",
        "total small business",
        "total small business set-aside",
        "small business",
    }
)

# Whole-word case-insensitive denylist for description text.
# Matches across word boundaries; "secrets management" wouldn't catch
# "secret" as a standalone, but "Top Secret clearance required" would.
_DESCRIPTION_DENY_PATTERN = re.compile(
    r"\b("
    r"top\s+secret"
    r"|secret"
    r"|clearance"
    r"|cleared\s+personnel"
    r"|CUI"
    r"|controlled\s+unclassified"
    r"|ITAR"
    r"|classified"
    r")\b",
    re.IGNORECASE,
)

# Minimum days from "today" to deadline. PRD §5.14: recipient needs
# time to act on the email.
_MIN_DAYS_UNTIL_DUE = 14


def _parse_due_date(value: Any) -> date | None:
    """Parse a due-date value into a date. Returns None if unparseable."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _normalized_set_aside(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _place_is_us(value: Any) -> bool:
    """Return True if the place_of_performance string mentions a US state.

    Generous matcher: looks for any 2-letter state postal code as a
    standalone token. NULL / empty is treated as US (federal contracting
    is US-centric by default).
    """
    if value is None or value == "":
        return True
    text = str(value).upper()
    for token in re.findall(r"\b[A-Z]{2}\b", text):
        if token in _US_STATES:
            return True
    return False


def safety_filter(
    opp: dict[str, Any],
    *,
    today: date | None = None,
    naics_allowlist: set[str] | None = None,
) -> tuple[bool, str | None]:
    """Run every safety filter against `opp`.

    Returns (True, None) if the opportunity passes every filter, or
    (False, reason) on the first failure. Rejections are short, stable
    strings safe to persist in the picker_audit JSONB column.
    """
    today = today or date.today()

    set_aside = _normalized_set_aside(opp.get("set_aside"))
    if set_aside not in _ACCEPTABLE_SET_ASIDES:
        return False, f"set_aside_too_narrow:{opp.get('set_aside')}"

    due = _parse_due_date(opp.get("due_date"))
    if due is None:
        return False, "due_date_missing_or_unparseable"
    if due < today + timedelta(days=_MIN_DAYS_UNTIL_DUE):
        return False, f"due_date_too_soon:{due.isoformat()}"

    if not _place_is_us(opp.get("place_of_performance")):
        return False, f"place_of_performance_not_us:{opp.get('place_of_performance')}"

    description = opp.get("description") or ""
    if isinstance(description, str) and _DESCRIPTION_DENY_PATTERN.search(description):
        return False, "description_contains_clearance_or_classified_keyword"

    if naics_allowlist:
        naics = str(opp.get("naics") or "").strip()
        if naics not in naics_allowlist:
            return False, f"naics_not_in_allowlist:{naics or 'empty'}"

    attachments = opp.get("attachments")
    if not attachments:
        return False, "attachments_empty"

    return True, None
