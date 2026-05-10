"""Resend HTTP-API client for the §5.14 weekly opportunity email.

Calls `POST https://api.resend.com/emails` directly with httpx — the
project already depends on httpx for `api/storage.py`, so adding the
`resend` Python SDK as a dep is unnecessary surface area.

Honors `EMAIL_DRY_RUN`: when true (default), `send()` returns a synthetic
`SendResult(message_id=None, dry_run=True)` and does NOT contact Resend.
This is the safety default so non-prod environments (and any first-time
production deploy) can never accidentally email subscribers. Production
must explicitly flip `EMAIL_DRY_RUN=false` after a verified-domain test.

Raises:
    EmailSendError      — Resend returned non-2xx; caller logs failure.
    EmailConfigError    — RESEND_API_KEY empty AND EMAIL_DRY_RUN=false
                          (defensive; the api/config.py guard normally
                          refuses to even start in this configuration).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from api.config import settings

RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_TIMEOUT_SECONDS = 15.0


class EmailSendError(RuntimeError):
    """Resend returned non-2xx. Message persists with status='failed'."""


class EmailConfigError(RuntimeError):
    """Misconfiguration that should have been caught at boot but wasn't."""


@dataclass(frozen=True)
class SendResult:
    """Outcome of a single send attempt.

    `message_id` is the Resend message ID when the email actually shipped.
    `dry_run` is true when EMAIL_DRY_RUN is set; in that mode no Resend
    call was made, no token was charged, and no recipient was emailed.
    """

    message_id: str | None
    dry_run: bool


async def send(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
    headers: dict[str, str] | None = None,
    reply_to: str | None = None,
) -> SendResult:
    """Send one email through Resend, or no-op in dry-run mode.

    Args:
        to:           Recipient address. Single recipient — this channel
                      doesn't fan out per call.
        subject:      Subject line. PRD §5.14 format
                      "This week's federal opportunity: {title[:60]}".
        html:         HTML body (full document).
        text:         Plain-text alternative; PRD §5.14 requires it
                      always go alongside HTML.
        headers:      List-Unsubscribe + List-Unsubscribe-Post + any
                      X-Entity-Ref-ID. Pass None when not applicable.
        reply_to:     Override `RESEND_REPLY_TO` settings default.

    Returns:
        SendResult.message_id is None when dry_run=True, otherwise the
        Resend message ID. Caller persists this in
        weekly_opportunity_email_log.resend_message_id.
    """
    if settings.email_dry_run:
        return SendResult(message_id=None, dry_run=True)

    if not settings.resend_api_key:
        # The api/config.py validator should have prevented start-up in
        # this configuration; raise loudly so a stack-trace surfaces.
        raise EmailConfigError(
            "RESEND_API_KEY is empty but EMAIL_DRY_RUN=false. "
            "Refusing to attempt a Resend call without credentials."
        )

    payload: dict[str, Any] = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    effective_reply_to = reply_to or settings.resend_reply_to
    if effective_reply_to:
        payload["reply_to"] = effective_reply_to
    if headers:
        # Resend documents this field as `headers`. Keys are case-sensitive
        # in the JSON body; standard "List-Unsubscribe" / "X-Entity-Ref-ID"
        # casing is what mailbox providers expect.
        payload["headers"] = headers

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        try:
            response = await client.post(
                RESEND_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
            )
        except httpx.RequestError as exc:
            raise EmailSendError(f"Resend network error: {exc}") from exc

    if response.status_code >= 400:
        # Surface the Resend body so the failed log row carries useful
        # forensics. Don't include the API key — httpx response object
        # doesn't expose request headers by default.
        raise EmailSendError(
            f"Resend returned {response.status_code}: {response.text[:500]}"
        )

    body = response.json()
    message_id = body.get("id") if isinstance(body, dict) else None
    return SendResult(message_id=message_id, dry_run=False)
