from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_waitlist_signup_persists_and_normalizes_email(client, fake_supabase) -> None:
    r = await client.post(
        "/waitlist",
        json={"email": " Founder@Example.COM ", "company": "Acme"},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"status": "ok", "already_registered": False}

    rows = list(fake_supabase._store["waitlist_signups"].values())
    assert rows[0]["email"] == "founder@example.com"
    assert rows[0]["company"] == "Acme"


async def test_waitlist_signup_is_idempotent(client) -> None:
    first = await client.post("/waitlist", json={"email": "founder@example.com"})
    second = await client.post("/waitlist", json={"email": "founder@example.com"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["already_registered"] is False
    assert second.json()["already_registered"] is True


async def test_waitlist_rejects_invalid_email(client) -> None:
    r = await client.post("/waitlist", json={"email": "not-an-email"})
    assert r.status_code == 422
