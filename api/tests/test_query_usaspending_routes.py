"""Tests for /tools/query-usaspending and /api/v1/tools/query-usaspending."""
from __future__ import annotations

from typing import Any

import pytest

from api.tests.conftest import TEST_INTERNAL_API_KEY

pytestmark = pytest.mark.asyncio

INTERNAL_HEADERS = {"X-Internal-API-Key": TEST_INTERNAL_API_KEY}


@pytest.fixture(autouse=True)
def _no_rate_limit(monkeypatch):
    async def _noop(*a: Any, **k: Any) -> None:
        return None

    monkeypatch.setattr("api.auth.acquire", _noop)


async def test_internal_route_happy_path(client, monkeypatch) -> None:
    async def _fake(payload, *, http=None):
        return {
            "awards": [],
            "incumbents": [],
            "total_obligated_usd": 0.0,
            "degraded": False,
            "error": "",
        }

    monkeypatch.setattr("api.routes.tools.query_usaspending", _fake)

    r = await client.post(
        "/tools/query-usaspending",
        json={"naics": "541512"},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["degraded"] is False
    assert body["metrics"] is None


async def test_v1_route_happy_path(client, monkeypatch) -> None:
    async def _fake(payload, *, http=None):
        return {
            "awards": [],
            "incumbents": [],
            "total_obligated_usd": 0.0,
            "degraded": False,
            "error": "",
        }

    monkeypatch.setattr("api.routes.v1_tools.query_usaspending", _fake)

    r = await client.post(
        "/api/v1/tools/query-usaspending",
        json={"naics": "541512"},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text


async def test_no_auth_returns_401(client) -> None:
    r = await client.post("/tools/query-usaspending", json={"naics": "x"})
    assert r.status_code == 401


async def test_invalid_limit_returns_422(client) -> None:
    r = await client.post(
        "/tools/query-usaspending",
        json={"naics": "x", "limit": 99999},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422


async def test_rejects_unknown_field(client) -> None:
    r = await client.post(
        "/tools/query-usaspending",
        json={"naics": "x", "unexpected": True},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422
