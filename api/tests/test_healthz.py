from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


async def test_healthz_ok(client) -> None:
    """Healthz pings Supabase via the FakeSupabase override + Redis (mocked)."""
    with patch("api.routes.healthz.redis_client") as mock_redis:
        mock_redis.ping = AsyncMock(return_value=True)
        r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
