"""Runner entrypoint for GovCapture agent runs.

The full Hermes CLI/sub-agent execution mode will live behind this module. The
current implemented mode is the seeded Michaela bridge, which writes real rows
and emits the real SSE contract without claiming live SAM or LLM execution.
"""
from __future__ import annotations

import uuid

import redis.asyncio as aioredis
from supabase import AsyncClient

from api.agent.hermes_bridge import run_seeded_michaela_capture


async def run_michaela(
    *,
    redis: aioredis.Redis,
    client: AsyncClient,
    run_id: uuid.UUID,
) -> None:
    await run_seeded_michaela_capture(redis=redis, client=client, run_id=run_id)
