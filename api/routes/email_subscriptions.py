"""§5.14 weekly opportunity email — public unsubscribe + internal cron routes.

Two endpoints:

- `GET  /email-subscriptions/unsubscribe?sid=…&token=…` — public, no auth.
  Verifies the HMAC token, marks `waitlist_signups.unsubscribed_at = now()`,
  returns a small inline HTML confirmation page (no Next.js round-trip).
- `POST /email-subscriptions/unsubscribe?sid=…&token=…` — same logic, returns
  204 No Content. Serves the RFC 8058 List-Unsubscribe-Post one-click flow.

- `POST /internal/cron/weekly-opportunity-email` — internal, Bearer
  INTERNAL_API_KEY auth (constant-time compare). Drives the Monday send
  job. nginx 404s `/internal/*` at the edge so this is loopback-only
  from the systemd timer.
"""
from __future__ import annotations

import logging
import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import HTMLResponse, Response

from api.config import settings
from api.deps import get_waitlist_repo
from api.jobs.auto_pick_weekly_opportunity import auto_pick_for_week
from api.jobs.weekly_opportunity_email import send_weekly_opportunity
from api.repositories.waitlist import WaitlistRepository
from api.services.unsubscribe_token import verify as verify_token

logger = logging.getLogger(__name__)

router = APIRouter()


_UNSUB_OK_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Unsubscribed</title></head>
<body style="margin:0;padding:48px 24px;background:#f7f7f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#0f172a;text-align:center;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:32px;border:1px solid #e2e8f0;">
    <h1 style="margin:0 0 12px;font-size:20px;">You're unsubscribed.</h1>
    <p style="margin:0;font-size:14px;color:#475569;line-height:1.5;">
      We won't send any more weekly opportunity emails to this address.
      You can rejoin anytime at <a href="https://samrail.com" style="color:#1e3a8a;">samrail.com</a>.
    </p>
  </div>
</body></html>"""


_UNSUB_INVALID_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Invalid unsubscribe link</title></head>
<body style="margin:0;padding:48px 24px;background:#f7f7f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#0f172a;text-align:center;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:32px;border:1px solid #e2e8f0;">
    <h1 style="margin:0 0 12px;font-size:20px;">Invalid unsubscribe link.</h1>
    <p style="margin:0;font-size:14px;color:#475569;line-height:1.5;">
      The link you followed doesn't validate. If you wanted to unsubscribe,
      reply to any SamRail email with "unsubscribe" and we'll handle it
      manually.
    </p>
  </div>
</body></html>"""


async def _verified_subscriber_email(
    sid: str,
    token: str,
    repo: WaitlistRepository,
) -> str | None:
    """Return the subscriber's email iff the HMAC verifies, else None.

    The HMAC binds (sid, email) so we fetch the row by sid first, then
    verify. The waitlist repo doesn't have an id-keyed getter (it's
    email-keyed for the create path), so we go through the supabase
    client directly for this single lookup.
    """
    if not sid or not token:
        return None
    resp = await (
        repo.client.table("waitlist_signups")
        .select("id, email")
        .eq("id", sid)
        .maybe_single()
        .execute()
    )
    row = resp.data if resp else None
    if not isinstance(row, dict):
        return None
    email_value = row.get("email")
    if not isinstance(email_value, str) or not email_value:
        return None
    if not verify_token(token, sid, email_value):
        return None
    return email_value


@router.get("/email-subscriptions/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_get(
    sid: Annotated[str, Query(...)],
    token: Annotated[str, Query(...)],
    repo: WaitlistRepository = Depends(get_waitlist_repo),
) -> HTMLResponse:
    email = await _verified_subscriber_email(sid, token, repo)
    if email is None:
        return HTMLResponse(_UNSUB_INVALID_HTML, status_code=400)
    await repo.mark_unsubscribed(sid, reason="user_one_click")
    return HTMLResponse(_UNSUB_OK_HTML, status_code=200)


@router.post("/email-subscriptions/unsubscribe")
async def unsubscribe_post(
    sid: Annotated[str, Query(...)],
    token: Annotated[str, Query(...)],
    repo: WaitlistRepository = Depends(get_waitlist_repo),
) -> Response:
    """RFC 8058 List-Unsubscribe-Post one-click. Always returns 204 on a
    valid token; returns 400 on tampering. Body is empty either way."""
    email = await _verified_subscriber_email(sid, token, repo)
    if email is None:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    await repo.mark_unsubscribed(sid, reason="user_one_click_post")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _require_internal_bearer(authorization: str | None) -> None:
    """Bearer-token gate shared by the two §5.14 cron routes."""
    configured = settings.internal_api_key
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API key is not configured",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )
    presented = authorization.split(" ", 1)[1].strip()
    if not secrets.compare_digest(presented, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )


@router.post("/internal/cron/auto-pick-weekly-opportunity")
async def cron_auto_pick_weekly_opportunity(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, Any]:
    """Sunday 22:00 UTC picker. Idempotent on `week_key`."""
    _require_internal_bearer(authorization)
    result = await auto_pick_for_week()
    logger.info(
        "auto_pick cron — week %s picked=%s inserted=%s",
        result.get("week_key"),
        result.get("picked_opportunity_id"),
        result.get("inserted"),
    )
    return result


@router.post("/internal/cron/weekly-opportunity-email")
async def cron_weekly_opportunity_email(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, Any]:
    """Monday 14:00 UTC send. nginx 404s /internal/* at the edge — loopback only."""
    _require_internal_bearer(authorization)
    summary = await send_weekly_opportunity()
    logger.info(
        "weekly_opportunity_email cron — week %s sent=%d skipped=%d failed=%d dry_run=%s",
        summary.week_key,
        summary.sent,
        summary.skipped_already_sent,
        summary.failed,
        summary.dry_run,
    )
    return summary.to_dict()
