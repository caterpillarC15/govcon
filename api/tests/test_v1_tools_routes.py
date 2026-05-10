"""Tests for /api/v1/tools/<name> public mirror.

Verifies the auth layer accepts both INTERNAL_API_KEY and gck_ keys.
Dispatch logic mirrors api/routes/tools.py and is exercised by
test_tools_routes.py — this file focuses on auth.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from api.tests.conftest import TEST_INTERNAL_API_KEY

pytestmark = pytest.mark.asyncio

INTERNAL_HEADERS = {"X-Internal-API-Key": TEST_INTERNAL_API_KEY}


@pytest_asyncio.fixture(autouse=True)
async def _no_rate_limit(monkeypatch):
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("api.auth.acquire", _noop)


async def _mint_gck(client) -> str:
    r = await client.post("/api/keys", json={"name": "test-key"})
    assert r.status_code == 201, r.text
    return r.json()["plaintext_key"]


async def test_internal_key_works(client) -> None:
    r = await client.post(
        "/api/v1/tools/rank-opportunities",
        json={"scored": []},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text


async def test_gck_key_works(client) -> None:
    plaintext = await _mint_gck(client)
    r = await client.post(
        "/api/v1/tools/rank-opportunities",
        json={"scored": []},
        headers={"Authorization": f"Bearer {plaintext}"},
    )
    assert r.status_code == 200, r.text


async def test_no_auth_returns_401(client) -> None:
    r = await client.post(
        "/api/v1/tools/rank-opportunities",
        json={"scored": []},
    )
    assert r.status_code == 401


async def test_non_gck_bearer_returns_401(client) -> None:
    r = await client.post(
        "/api/v1/tools/rank-opportunities",
        json={"scored": []},
        headers={"Authorization": "Bearer jwt-not-gck"},
    )
    assert r.status_code == 401


async def test_revoked_gck_key_returns_401(client) -> None:
    minted = (
        await client.post("/api/keys", json={"name": "revoked-key"})
    ).json()
    plaintext = minted["plaintext_key"]
    await client.delete(f"/api/keys/{minted['id']}")
    r = await client.post(
        "/api/v1/tools/rank-opportunities",
        json={"scored": []},
        headers={"Authorization": f"Bearer {plaintext}"},
    )
    assert r.status_code == 401
