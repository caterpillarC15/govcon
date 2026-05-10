"""Tests for /api/keys mint/list/revoke."""
from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def test_mint_returns_plaintext_once(client) -> None:
    r = await client.post("/api/keys", json={"name": "claude-desktop"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "claude-desktop"
    assert body["plaintext_key"].startswith("gck_")
    assert body["prefix"] == body["plaintext_key"][:12]


async def test_list_omits_plaintext(client) -> None:
    await client.post("/api/keys", json={"name": "k1"})
    await client.post("/api/keys", json={"name": "k2"})
    r = await client.get("/api/keys")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 2
    for row in rows:
        assert "plaintext_key" not in row
        assert "key_hash" not in row
        assert row["prefix"].startswith("gck_")


async def test_revoke_flips_revoked_at(client) -> None:
    minted = (
        await client.post("/api/keys", json={"name": "to-revoke"})
    ).json()
    r = await client.delete(f"/api/keys/{minted['id']}")
    assert r.status_code == 204
    listed = (await client.get("/api/keys")).json()
    target = next(row for row in listed if row["id"] == minted["id"])
    assert target["revoked_at"] is not None


async def test_revoke_404_on_unknown(client) -> None:
    r = await client.delete(f"/api/keys/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_post_rejects_empty_name(client) -> None:
    r = await client.post("/api/keys", json={"name": ""})
    assert r.status_code == 422
