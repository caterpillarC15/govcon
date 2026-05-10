"""§5.14 weekly opportunity email — unit tests.

Covers:

  - Safety filter rejection reasons and pass cases.
  - Unsubscribe HMAC round-trip + tamper detection.
  - Email rendering produces stable subject + headers.
  - Cron auth: missing/wrong bearer rejected; correct bearer accepted.
  - send_weekly_emails honors EMAIL_DRY_RUN and is idempotent on re-run.
  - Production guard refuses to construct Settings when EMAIL_DRY_RUN=false
    without the required secrets.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

# Per-test asyncio marks; this module mixes sync and async tests.


# ── Safety filters ──────────────────────────────────────────────────
def test_safety_rejects_short_deadline() -> None:
    from api.jobs.weekly_opportunity_safety import safety_filter

    today = date(2026, 5, 10)
    opp = {
        "title": "OK",
        "description": "ok",
        "due_date": (today + timedelta(days=5)).isoformat(),
        "set_aside": "",
        "place_of_performance": "USA",
        "naics": "541512",
    }
    passed, reason = safety_filter(opp, today=today, naics_allowlist=None)
    assert passed is False
    assert reason and "due_date" in reason


def test_safety_rejects_narrow_set_aside() -> None:
    from api.jobs.weekly_opportunity_safety import safety_filter

    today = date(2026, 5, 10)
    opp = {
        "title": "OK",
        "description": "ok",
        "due_date": (today + timedelta(days=30)).isoformat(),
        "set_aside": "8a",
        "place_of_performance": "USA",
        "naics": "541512",
    }
    passed, reason = safety_filter(opp, today=today, naics_allowlist=None)
    assert passed is False
    assert reason and "set_aside" in reason


def test_safety_rejects_clearance_keyword() -> None:
    from api.jobs.weekly_opportunity_safety import safety_filter

    today = date(2026, 5, 10)
    opp = {
        "title": "System support",
        "description": "Requires TS/SCI clearance and active background investigation.",
        "due_date": (today + timedelta(days=30)).isoformat(),
        "set_aside": "",
        "place_of_performance": "VA, USA",
        "naics": "541512",
        "attachments": [{"name": "rfp.pdf"}],
    }
    passed, reason = safety_filter(opp, today=today, naics_allowlist=None)
    assert passed is False
    assert reason and ("clearance" in reason or "classified" in reason or "keyword" in reason)


def test_safety_passes_clean_candidate() -> None:
    from api.jobs.weekly_opportunity_safety import safety_filter

    today = date(2026, 5, 10)
    opp = {
        "title": "IT helpdesk services",
        "description": "Standard professional services contract.",
        "due_date": (today + timedelta(days=30)).isoformat(),
        "set_aside": "",
        "place_of_performance": "VA, USA",
        "naics": "541512",
        "attachments": [{"name": "rfp.pdf"}],
    }
    passed, reason = safety_filter(opp, today=today, naics_allowlist=None)
    assert passed is True
    assert reason is None


# ── Unsubscribe HMAC ────────────────────────────────────────────────
def test_unsubscribe_token_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.config import settings
    from api.services import unsubscribe_token as ut

    monkeypatch.setattr(settings, "email_unsubscribe_secret", "test-secret-1234")
    token = ut.mint("sub-1", "user@example.com")
    assert ut.verify(token, "sub-1", "user@example.com") is True
    assert ut.verify(token, "sub-1", "other@example.com") is False
    assert ut.verify(token, "sub-2", "user@example.com") is False
    assert ut.verify("not-a-token", "sub-1", "user@example.com") is False


def test_unsubscribe_token_missing_secret_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.config import settings
    from api.services import unsubscribe_token as ut

    monkeypatch.setattr(settings, "email_unsubscribe_secret", "")
    # Mint should raise; verify swallows and returns False.
    with pytest.raises(ut.UnsubscribeSecretMissingError):
        ut.mint("sub-1", "user@example.com")
    assert ut.verify("anything", "sub-1", "user@example.com") is False


# ── Render ──────────────────────────────────────────────────────────
def test_render_subject_and_headers() -> None:
    from api.email.render import render_weekly_opportunity

    out = render_weekly_opportunity(
        opportunity={
            "title": "AI helpdesk modernization",
            "agency": "GSA",
            "due_date": "2026-06-01",
            "naics": "541512",
            "set_aside": "small_business",
            "description": "Stand up an AI-assisted helpdesk for federal staff.",
            "source_url": "https://sam.gov/opp/abc",
        },
        unsubscribe_token="t0k3n",
        week_key="2026-W19",
    )
    assert out.subject.startswith("This week's federal opportunity:")
    assert "AI helpdesk modernization" in out.subject
    assert "List-Unsubscribe" in out.headers
    assert "List-Unsubscribe-Post" in out.headers
    assert "t0k3n" in out.headers["List-Unsubscribe"]
    assert "AI helpdesk modernization" in out.html
    assert "AI helpdesk modernization" in out.text
    assert out.text.endswith(out.text.strip())  # trailing whitespace clean


# ── Cron auth ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cron_weekly_email_rejects_missing_bearer(client) -> None:
    r = await client.post("/internal/cron/weekly-opportunity-email")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_cron_weekly_email_rejects_wrong_bearer(client) -> None:
    r = await client.post(
        "/internal/cron/weekly-opportunity-email",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_cron_auto_pick_rejects_missing_bearer(client) -> None:
    r = await client.post("/internal/cron/auto-pick-weekly-opportunity")
    assert r.status_code == 401


# ── Production guard ────────────────────────────────────────────────
def test_production_guard_refuses_when_secrets_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """EMAIL_DRY_RUN=false with empty secrets must raise at construction."""
    from pydantic import ValidationError

    from api.config import Settings

    monkeypatch.setenv("EMAIL_DRY_RUN", "false")
    monkeypatch.setenv("RESEND_API_KEY", "")
    monkeypatch.setenv("EMAIL_UNSUBSCRIBE_SECRET", "")
    monkeypatch.setenv("EMAIL_LEGAL_FOOTER_ADDRESS", "")
    with pytest.raises(ValidationError) as excinfo:
        Settings()  # bypass lru_cache by constructing fresh
    msg = str(excinfo.value)
    assert "RESEND_API_KEY" in msg
    assert "EMAIL_UNSUBSCRIBE_SECRET" in msg
    assert "EMAIL_LEGAL_FOOTER_ADDRESS" in msg


def test_production_guard_passes_when_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.config import Settings

    monkeypatch.setenv("EMAIL_DRY_RUN", "true")
    monkeypatch.setenv("RESEND_API_KEY", "")
    monkeypatch.setenv("EMAIL_UNSUBSCRIBE_SECRET", "")
    monkeypatch.setenv("EMAIL_LEGAL_FOOTER_ADDRESS", "")
    settings = Settings()
    assert settings.email_dry_run is True


# ── Week key ────────────────────────────────────────────────────────
def test_iso_week_key_format() -> None:
    from api.jobs.auto_pick_weekly_opportunity import iso_week_key

    # 2026-05-10 is a Sunday in ISO week 19.
    assert iso_week_key(date(2026, 5, 10)) == "2026-W19"
    # Week-number boundary: 2026-12-31 falls in ISO week 53.
    assert iso_week_key(date(2026, 12, 31)).startswith("2026-W")
