"""§5.14 weekly opportunity send job.

Cron-fired Monday 14:00 UTC by `govcapture-cron-weekly.timer`. The
picker has already chosen the week's opportunity (or refused). For each
eligible recipient:

  1. Claim a `(email, week_key, "weekly_opportunity")` slot in
     `weekly_opportunity_email_log`. Slot already taken → skip silently
     (re-runs are safe).
  2. Mint the per-recipient unsubscribe token from `subscription_id +
     email`.
  3. Render the email via `api/email/render.py`.
  4. Call Resend (or honor EMAIL_DRY_RUN by not calling).
  5. Mark slot `sent` (with Resend message id) or `failed` (with reason).

Returns a structured summary the cron route forwards to systemd's
journald — `total_eligible`, `sent`, `skipped_already_sent`, `failed`,
plus `dry_run` so prod logs make the safety mode obvious.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from api.config import settings
from api.db import get_client
from api.email.render import render_weekly_opportunity
from api.jobs.auto_pick_weekly_opportunity import iso_week_key
from api.repositories.opportunity import OpportunityRepository
from api.repositories.waitlist import WaitlistRepository
from api.repositories.weekly_opportunity_email_log import (
    WeeklyOpportunityEmailLogRepository,
)
from api.repositories.weekly_opportunity_pick import (
    WeeklyOpportunityPickRepository,
)
from api.services import email_sender
from api.services.unsubscribe_token import mint as mint_unsubscribe_token

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SendSummary:
    week_key: str
    opportunity_id: str | None
    total_eligible: int
    sent: int
    skipped_already_sent: int
    failed: int
    dry_run: bool
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "week_key": self.week_key,
            "opportunity_id": self.opportunity_id,
            "total_eligible": self.total_eligible,
            "sent": self.sent,
            "skipped_already_sent": self.skipped_already_sent,
            "failed": self.failed,
            "dry_run": self.dry_run,
        }
        if self.note:
            out["note"] = self.note
        return out


async def send_weekly_opportunity(
    *, today: datetime | None = None
) -> SendSummary:
    """Run one weekly send. Idempotent on (email, week_key)."""
    moment = today or datetime.now(timezone.utc)
    week_key = iso_week_key(moment.date())
    dry_run = settings.email_dry_run

    db = await get_client()
    pick_repo = WeeklyOpportunityPickRepository(db)
    opp_repo = OpportunityRepository(db)
    waitlist_repo = WaitlistRepository(db)
    log_repo = WeeklyOpportunityEmailLogRepository(db)

    pick = await pick_repo.get_for_week(week_key)
    if pick is None or not pick.get("opportunity_id"):
        return SendSummary(
            week_key=week_key,
            opportunity_id=None,
            total_eligible=0,
            sent=0,
            skipped_already_sent=0,
            failed=0,
            dry_run=dry_run,
            note="no_pick_for_week",
        )

    opportunity = await opp_repo.get(uuid.UUID(pick["opportunity_id"]))
    if opportunity is None:
        return SendSummary(
            week_key=week_key,
            opportunity_id=pick["opportunity_id"],
            total_eligible=0,
            sent=0,
            skipped_already_sent=0,
            failed=0,
            dry_run=dry_run,
            note="opportunity_missing",
        )

    recipients = await waitlist_repo.list_eligible_for_weekly(
        require_confirmed=settings.email_require_double_opt_in,
    )

    sent_count = 0
    skipped = 0
    failed = 0

    initial_status: Literal["dry_run", "pending"] = (
        "dry_run" if dry_run else "pending"
    )

    for recipient in recipients:
        email = recipient["email"]
        subscription_id = recipient["id"]

        slot = await log_repo.claim_slot(
            email=email,
            week_key=week_key,
            email_type="weekly_opportunity",
            initial_status=initial_status,
        )
        if slot is None:
            skipped += 1
            continue

        token = mint_unsubscribe_token(subscription_id, email)
        rendered = render_weekly_opportunity(
            opportunity=opportunity,
            unsubscribe_token=token,
            week_key=week_key,
        )

        if dry_run:
            sent_count += 1
            continue

        try:
            result = await email_sender.send(
                to=email,
                subject=rendered.subject,
                html=rendered.html,
                text=rendered.text,
                headers=rendered.headers,
            )
        except email_sender.EmailSendError as exc:
            await log_repo.mark_failed(slot["id"], reason=str(exc))
            failed += 1
            continue
        except email_sender.EmailConfigError as exc:
            # Boot guard should have prevented this. Bail loudly.
            logger.exception("Email config error mid-send: %s", exc)
            await log_repo.mark_failed(slot["id"], reason=f"config:{exc}")
            failed += 1
            continue

        await log_repo.mark_sent(
            slot["id"],
            resend_message_id=result.message_id,
            sent_at_iso=datetime.now(timezone.utc).isoformat(),
        )
        sent_count += 1

    return SendSummary(
        week_key=week_key,
        opportunity_id=pick["opportunity_id"],
        total_eligible=len(recipients),
        sent=sent_count,
        skipped_already_sent=skipped,
        failed=failed,
        dry_run=dry_run,
    )
