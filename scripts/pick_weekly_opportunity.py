"""§5.14 curator override — pin a specific opportunity for a week.

Usage:

    uv run python scripts/pick_weekly_opportunity.py \\
      --week 2026-W19 \\
      --opportunity-id <uuid>

    # Optional: allow fixture / seeded opportunities (off by default).
    uv run python scripts/pick_weekly_opportunity.py \\
      --week 2026-W19 --opportunity-id <uuid> --allow-fixture

Behavior (PRD §5.14):

* Validates `--week` is YYYY-Www (ISO 8601, UTC). Refuses other shapes.
* Looks up the opportunity by id. Refuses if missing.
* Refuses if `opportunities.source = 'seed'` and `--allow-fixture` was
  not passed — fixture-sourced rows are great for dev/demo but should
  not be sent to real subscribers.
* Inserts into `weekly_opportunity_picks` with `source='manual'` via
  `INSERT … ON CONFLICT (week_key) DO NOTHING`. Manual override wins
  the race against the Sunday 22:00 UTC auto-picker because
  `(week_key)` is the primary key — the auto-picker silently skips.

Exit codes:
  0 — pick inserted (or already pinned to this opportunity)
  1 — refused (fixture, missing opp, malformed week, conflict on a
       different opportunity already pinned)
  2 — invalid CLI args
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from typing import Any

from api.db import get_client
from api.repositories.opportunity import OpportunityRepository
from api.repositories.weekly_opportunity_pick import (
    WeeklyOpportunityPickRepository,
)

_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pin a specific opportunity for a given week (PRD §5.14)."
    )
    parser.add_argument("--week", required=True, help="ISO week, e.g. 2026-W19.")
    parser.add_argument(
        "--opportunity-id",
        required=True,
        help="UUID of the opportunity to pin.",
    )
    parser.add_argument(
        "--allow-fixture",
        action="store_true",
        help="Allow opportunities with source='seed' (off by default).",
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    if not _WEEK_RE.match(args.week):
        print(
            f"error: --week must be ISO format YYYY-Www (got {args.week!r})",
            file=sys.stderr,
        )
        return 2
    try:
        opp_uuid = uuid.UUID(args.opportunity_id)
    except ValueError:
        print(
            f"error: --opportunity-id must be a UUID (got {args.opportunity_id!r})",
            file=sys.stderr,
        )
        return 2

    client = await get_client()
    opp_repo = OpportunityRepository(client)
    pick_repo = WeeklyOpportunityPickRepository(client)

    opp: dict[str, Any] | None = await opp_repo.get(opp_uuid)
    if opp is None:
        print(
            f"error: opportunity {opp_uuid} not found in `opportunities` table",
            file=sys.stderr,
        )
        return 1

    source_field = (opp.get("source") or "").lower()
    if source_field == "seed" and not args.allow_fixture:
        print(
            "error: this opportunity is fixture-sourced (source='seed').\n"
            "       Pass --allow-fixture to override (dev / demo only).",
            file=sys.stderr,
        )
        return 1

    existing = await pick_repo.get_for_week(args.week)
    if existing is not None:
        existing_opp_id = existing.get("opportunity_id")
        if str(existing_opp_id) == str(opp_uuid):
            print(
                f"already pinned: week {args.week} → opportunity {opp_uuid} "
                f"(source={existing.get('source')})"
            )
            return 0
        print(
            f"error: week {args.week} already pinned to a DIFFERENT opportunity "
            f"({existing_opp_id}, source={existing.get('source')}).\n"
            f"       To replace it, delete the existing row first:\n"
            f"       supabase db query \"DELETE FROM weekly_opportunity_picks "
            f"WHERE week_key = '{args.week}'\"",
            file=sys.stderr,
        )
        return 1

    audit = {
        "source": "curator_override",
        "actor": "scripts/pick_weekly_opportunity.py",
        "title": opp.get("title"),
        "agency": opp.get("agency"),
        "due_date": opp.get("due_date"),
        "allow_fixture_used": bool(args.allow_fixture),
    }
    inserted = await pick_repo.insert_if_absent(
        week_key=args.week,
        opportunity_id=opp_uuid,
        source="manual",
        picker_audit=audit,
    )
    if inserted is None:
        print(
            f"error: race lost — week {args.week} was just pinned by another writer.",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "week": args.week,
                "opportunity_id": str(opp_uuid),
                "source": "manual",
                "title": opp.get("title"),
                "agency": opp.get("agency"),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
