"""§5.14 LLM auto-picker for the weekly opportunity email.

Cron-fired Sunday 22:00 UTC by `govcapture-cron-auto-pick.timer`. Pulls
candidate opportunities from the last 7 days, applies deterministic
safety filters (`weekly_opportunity_safety.safety_filter`), then ranks
survivors via the existing `score_fit` skill against a clearly-labeled
synthetic SMB profile. Picks the top candidate with `total_score >=
EMAIL_AUTO_PICK_MIN_SCORE` and `confidence ∈ {high, medium}`.

If no candidate passes, no row is written to `weekly_opportunity_picks`
and the Monday send job exits clean — there is nothing to send. The
`picker_audit` JSONB column captures the full decision trace so a
curator can audit why each opportunity was rejected, kept, or skipped.

Manual override via `scripts/pick_weekly_opportunity.py` always wins
because the picks table has `UNIQUE (week_key)` and we use
`INSERT … ON CONFLICT DO NOTHING`.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from api.config import settings
from api.db import get_client
from api.jobs.weekly_opportunity_safety import safety_filter
from api.repositories.opportunity import OpportunityRepository
from api.repositories.weekly_opportunity_pick import (
    PickSource,
    WeeklyOpportunityPickRepository,
)

logger = logging.getLogger(__name__)

# Synthetic profile used for fit ranking. PRD §5.14 calls for a
# "clearly-labeled synthetic SMB" — the name field below carries the
# label so any debug log or picker_audit makes the synthetic origin
# obvious. No real subscriber data is referenced.
SYNTHETIC_SMB_PROFILE: dict[str, Any] = {
    "name": "synthetic-smb (PRD §5.14 weekly auto-picker)",
    "naics_codes": [],
    "certifications": [],
    "small_business_status": True,
    "clearance_status": "none",
    "capabilities": [
        "software development",
        "IT services",
        "professional services",
    ],
}


def iso_week_key(at: date) -> str:
    """Return PRD §5.14 ISO-8601 week key — `YYYY-Www`, UTC."""
    iso_year, iso_week, _ = at.isocalendar()
    return f"{iso_year:04d}-W{iso_week:02d}"


def _synth_requirements_from_opp(opp: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a minimal requirement set from opportunity metadata.

    The auto-picker doesn't have extracted_requirements for every
    candidate (that would mean parsing every PDF in advance). Instead
    we synthesize a small, honest set of requirements straight from
    the opportunity's structured fields. score_fit then ranks against
    these — capability match, NAICS, set-aside, and deadline. Plenty
    of signal for ranking, no LLM-extracted requirement noise.
    """
    requirements: list[dict[str, Any]] = []
    title = opp.get("title") or ""
    description = (opp.get("description") or "")[:400]
    naics = opp.get("naics") or ""
    set_aside = opp.get("set_aside") or ""

    if title or description:
        requirements.append(
            {
                "type": "technical",
                "title": title or "Scope of work",
                "value": description or title,
                "confidence": "high",
                "evidence_snippet": description or title,
                "source_document": "opportunity_metadata",
                "page_number": 0,
                "is_blocker": False,
            }
        )
    if naics:
        requirements.append(
            {
                "type": "technical",
                "title": f"NAICS {naics}",
                "value": f"Primary NAICS code: {naics}",
                "confidence": "high",
                "evidence_snippet": naics,
                "source_document": "opportunity_metadata",
                "page_number": 0,
                "is_blocker": False,
            }
        )
    if set_aside:
        requirements.append(
            {
                "type": "eligibility",
                "title": set_aside,
                "value": set_aside,
                "confidence": "high",
                "evidence_snippet": set_aside,
                "source_document": "opportunity_metadata",
                "page_number": 0,
                "is_blocker": False,
            }
        )
    return requirements


async def _score_candidate(
    opp: dict[str, Any],
) -> dict[str, Any] | None:
    """Run score_fit against a single candidate; return its output dict.

    PRD v1.2.6: score_fit is deterministic. Returns None only if
    score_fit raises on malformed input (logged as a rejection
    downstream).
    """
    from api.skills.score_fit.skill import score_fit

    # PRD v1.2.6: score_fit is deterministic. The auto-picker only
    # needs the §11.1 short-circuit + decision band — Lenny's full
    # rationale is not consulted here. We omit total_score so the
    # skill returns "needs_score" for non-blocker opportunities,
    # which the caller treats as "not auto-pickable, defer to a real
    # run." Blocker opportunities return decision=reject and get
    # filtered out.
    payload = {
        "company_profile": SYNTHETIC_SMB_PROFILE,
        "requirements": _synth_requirements_from_opp(opp),
    }
    try:
        out = await score_fit(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "score_fit failed on opportunity %s: %s", opp.get("id"), exc
        )
        return None
    return out


async def auto_pick_for_week(
    *,
    today: date | None = None,
    pretend_disable_llm: bool = False,
) -> dict[str, Any]:
    """Run the full auto-picker for the current ISO week.

    Args:
        today:                Override "today" for tests; defaults to UTC.
        pretend_disable_llm:  Test/dev knob — skip the score_fit call
                              entirely and treat every survivor as a
                              tie at score=70/medium. Lets us exercise
                              the pick path without an Anthropic key.

    Returns:
        Dict with keys `week_key`, `picked_opportunity_id`, `source`,
        `picker_audit`, `inserted` (true if the row landed; false if
        a curator had already pinned this week's pick).
    """
    today = today or datetime.now(timezone.utc).date()
    week_key = iso_week_key(today)
    since_iso = (today - timedelta(days=7)).isoformat() + "T00:00:00+00:00"

    db = await get_client()
    opp_repo = OpportunityRepository(db)
    pick_repo = WeeklyOpportunityPickRepository(db)

    candidates = await opp_repo.list_recent(
        since_iso=since_iso,
        limit=settings.email_auto_pick_max_candidates,
    )

    audit: dict[str, Any] = {
        "today": today.isoformat(),
        "week_key": week_key,
        "considered_count": len(candidates),
        "rejections": [],
        "ranked": [],
        "config": {
            "min_score": settings.email_auto_pick_min_score,
            "max_candidates": settings.email_auto_pick_max_candidates,
            "naics_allowlist": sorted(settings.email_naics_allowlist_set),
            "fixtures_only": settings.email_use_fixtures_for_auto_pick,
        },
    }

    naics_allowlist = settings.email_naics_allowlist_set or None
    survivors: list[dict[str, Any]] = []
    for opp in candidates:
        passed, reason = safety_filter(
            opp, today=today, naics_allowlist=naics_allowlist
        )
        if passed:
            survivors.append(opp)
        else:
            audit["rejections"].append(
                {"opportunity_id": opp.get("id"), "reason": reason}
            )

    if not survivors:
        return {
            "week_key": week_key,
            "picked_opportunity_id": None,
            "source": None,
            "picker_audit": audit,
            "inserted": False,
        }

    if pretend_disable_llm:
        ranked: list[tuple[dict[str, Any], int, str]] = [
            (opp, 70, "medium") for opp in survivors
        ]
    else:
        # PRD v1.2.6: score_fit is deterministic; no LLM client needed.
        # `pretend_disable_llm` retained as a manual-vs-auto picker
        # source distinction, not as an LLM-availability gate.
        ranked = []
        for opp in survivors:
            out = await _score_candidate(opp)
            if out is None:
                audit["rejections"].append(
                    {"opportunity_id": opp.get("id"), "reason": "score_fit_failed"}
                )
                continue
            ranked.append(
                (opp, int(out.get("total_score", 0)), str(out.get("confidence", "low")))
            )
        ranked.sort(key=lambda triple: -triple[1])
        audit["ranked"] = [
            {"opportunity_id": opp.get("id"), "score": score, "confidence": conf}
            for opp, score, conf in ranked
        ]

    pick: tuple[dict[str, Any], int, str] | None = next(
        (
            triple
            for triple in ranked
            if triple[1] >= settings.email_auto_pick_min_score
            and triple[2] in {"high", "medium"}
        ),
        None,
    )

    if pick is None:
        audit["pick"] = None
        return {
            "week_key": week_key,
            "picked_opportunity_id": None,
            "source": None,
            "picker_audit": audit,
            "inserted": False,
        }

    winner_opp, winner_score, winner_conf = pick
    audit["pick"] = {
        "opportunity_id": winner_opp.get("id"),
        "score": winner_score,
        "confidence": winner_conf,
    }
    inserted_row = await pick_repo.insert_if_absent(
        week_key=week_key,
        opportunity_id=winner_opp["id"],
        source="llm_auto" if not pretend_disable_llm else "manual",
        picker_audit=audit,
    )
    source: PickSource = "llm_auto" if not pretend_disable_llm else "manual"
    return {
        "week_key": week_key,
        "picked_opportunity_id": winner_opp["id"],
        "source": source,
        "picker_audit": audit,
        "inserted": inserted_row is not None,
    }
