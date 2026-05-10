"""Per-key token-bucket rate limiter.

State is one Redis hash per key with fields {tokens, ts}. Refill is
continuous (linear by elapsed time). The Lua script makes the read +
update atomic; without it, racing clients can over-spend the bucket.

Fails OPEN on Redis transport errors: a warning is logged and the
request is allowed through. Rate limiting is a best-effort defense
in v1; trading a few skipped checks for not crashing the auth path
during a Redis hiccup is the right call. A prolonged outage will be
visible in the warning log volume; downstream monitoring should alert
on that.
"""
from __future__ import annotations

import logging
import time
from typing import Any, cast

import redis.exceptions  # type: ignore[import-untyped]

from api.redis import redis_client

logger = logging.getLogger(__name__)


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
    """Try to take 1 token. Raise RateLimitError on empty bucket.

    Fails OPEN on Redis transport errors: logs a warning and returns
    normally (no raise). Trade-off: a brief Redis outage lets a small
    number of requests bypass the limit. Acceptable for v1; better than
    crashing the auth path with a 500.
    """
    now = time.time()
    try:
        raw: Any = await cast(
            Any,
            redis_client.eval(_LUA, 1, key, capacity, refill_per_sec, now),
        )
    except (redis.exceptions.RedisError, ConnectionError, TimeoutError, OSError) as exc:
        logger.warning(
            "rate_limit: Redis unavailable (%s); failing open for key=%s",
            exc.__class__.__name__,
            key,
        )
        return
    if isinstance(raw, bytes):
        result = int(raw.decode())
    else:
        result = int(raw)
    if result < 0:
        raise RateLimitError(retry_after=int(-result))
