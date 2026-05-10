"""Tests for the query_usaspending skill."""
from __future__ import annotations

from typing import Any

import httpx
import pytest

from api.skills.query_usaspending.skill import query_usaspending

pytestmark = pytest.mark.asyncio


class _Resp:
    def __init__(self, status: int, body: Any = None) -> None:
        self.status_code = status
        self._body = body
        self.text = ""

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("no body")
        return self._body


class _StubClient:
    def __init__(self, resp: _Resp) -> None:
        self._resp = resp

    async def post(self, *a: Any, **k: Any) -> _Resp:
        return self._resp

    async def aclose(self) -> None:
        return None


async def test_happy_path_returns_normalized_awards() -> None:
    body = {
        "results": [
            {
                "Recipient Name": "Tetra Tech",
                "Award Amount": 1234567.89,
                "Period of Performance Start Date": "2024-01-01",
                "Award ID": "ABC-123",
            },
            {
                "Recipient Name": "Tetra Tech",  # dedup test
                "Award Amount": 50000.0,
                "Period of Performance Start Date": "2024-06-01",
                "Award ID": "ABC-456",
            },
        ]
    }
    out = await query_usaspending(
        {"naics": "541512", "limit": 25}, http=_StubClient(_Resp(200, body))
    )
    assert out["degraded"] is False
    assert out["error"] == ""
    assert len(out["awards"]) == 2
    assert out["incumbents"] == ["Tetra Tech"]
    assert out["total_obligated_usd"] == round(1234567.89 + 50000.0, 2)


async def test_rate_limit_returns_degraded() -> None:
    out = await query_usaspending(
        {"naics": "541512"}, http=_StubClient(_Resp(429))
    )
    assert out["degraded"] is True
    assert "rate limit" in out["error"].lower()
    assert out["awards"] == []


async def test_5xx_returns_degraded() -> None:
    out = await query_usaspending(
        {"naics": "541512"}, http=_StubClient(_Resp(503))
    )
    assert out["degraded"] is True
    assert out["awards"] == []


async def test_network_error_returns_degraded() -> None:
    class _BoomClient:
        async def post(self, *a: Any, **k: Any) -> _Resp:
            raise httpx.ConnectError("boom")

        async def aclose(self) -> None:
            return None

    out = await query_usaspending({"naics": "541512"}, http=_BoomClient())
    assert out["degraded"] is True
    assert "network" in out["error"]


async def test_limit_clamps_to_100() -> None:
    captured: dict[str, Any] = {}

    class _CaptureClient:
        async def post(
            self, url: str, *, json: dict[str, Any], timeout: float
        ) -> _Resp:
            captured.update(json)
            return _Resp(200, {"results": []})

        async def aclose(self) -> None:
            return None

    await query_usaspending(
        {"naics": "541512", "limit": 9999}, http=_CaptureClient()
    )
    assert captured["limit"] == 100


async def test_filters_built_from_naics_and_agency() -> None:
    captured: dict[str, Any] = {}

    class _CaptureClient:
        async def post(
            self, url: str, *, json: dict[str, Any], timeout: float
        ) -> _Resp:
            captured.update(json)
            return _Resp(200, {"results": []})

        async def aclose(self) -> None:
            return None

    await query_usaspending(
        {"naics": "541512", "agency": "Department of Defense"},
        http=_CaptureClient(),
    )
    assert captured["filters"]["naics_codes"] == ["541512"]
    assert captured["filters"]["agencies"] == [
        {"name": "Department of Defense", "tier": "toptier"}
    ]
