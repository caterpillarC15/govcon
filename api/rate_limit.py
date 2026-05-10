"""Per-key token-bucket rate limiter.

State is one Redis hash per key with fields {tokens, ts}. Refill is
continuous (linear by elapsed time). The Lua script makes the read +
update atomic; without it, racing clients can over-spend the bucket.
"""
from __future__ import annotations

import time
from typing import Any, cast

from api.redis import redis_client


class RateLimitError(Exception):
    """Raised by acquire() when a key is rate-limited.

    `retry_after` is seconds until the next token is available
    (rounded up). The caller should pass this through to the HTTP 429
    response's Retry-After header.
    """

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"rate limited; retry after {retry_after}s")
        self.retry_after = retry_after


_LUA = """
local key = KEYS[1]
local cap = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local b = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(b[1]) or cap
local ts = tonumber(b[2]) or now
tokens = math.min(cap, tokens + (now - ts) * refill)
if tokens < 1 then
  redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
  redis.call('EXPIRE', key, 600)
  local need = 1 - tokens
  return -1 * math.ceil(need / refill)
end
redis.call('HMSET', key, 'tokens', tokens - 1, 'ts', now)
redis.call('EXPIRE', key, 600)
return 0
"""


async def acquire(key: str, *, capacity: int, refill_per_sec: float) -> None:
    """Try to take 1 token. Raise RateLimitError on empty bucket."""
    now = time.time()
    raw: Any = await cast(
        Any,
        redis_client.eval(_LUA, 1, key, capacity, refill_per_sec, now),
    )
    if isinstance(raw, bytes):
        result = int(raw.decode())
    else:
        result = int(raw)
    if result < 0:
        raise RateLimitError(retry_after=int(-result))
