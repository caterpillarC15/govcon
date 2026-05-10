"""Token-bucket smoke test using a fake redis client."""
from __future__ import annotations

import pytest

from api.rate_limit import RateLimitError

pytestmark = pytest.mark.asyncio


class _FakeRedis:
    def __init__(self) -> None:
        self.state: dict[str, dict[str, str]] = {}

    async def eval(self, lua: str, num_keys: int, *args):
        # Reimplement the Lua logic in Python for testing purposes.
        import math

        key = args[0]
        cap = float(args[1])
        refill = float(args[2])
        now = float(args[3])
        b = self.state.get(key, {})
        tokens = float(b.get("tokens", cap))
        ts = float(b.get("ts", now))
        tokens = min(cap, tokens + (now - ts) * refill)
        if tokens < 1:
            self.state[key] = {"tokens": str(tokens), "ts": str(now)}
            need = 1 - tokens
            return -1 * math.ceil(need / refill)
        self.state[key] = {"tokens": str(tokens - 1), "ts": str(now)}
        return 0


async def test_acquire_then_exhaust(monkeypatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr("api.rate_limit.redis_client", fake)
    from api.rate_limit import acquire

    # Tiny capacity to exhaust quickly.
    for _ in range(3):
        await acquire("test:k1", capacity=3, refill_per_sec=0.001)
    with pytest.raises(RateLimitError) as exc_info:
        await acquire("test:k1", capacity=3, refill_per_sec=0.001)
    assert exc_info.value.retry_after >= 1
