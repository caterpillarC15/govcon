"""Pre-A9 SSE replayer.

Until Hermes is wired in (A9), `POST /agent-runs` triggers `replay_example_run` to
publish the canned trace from `/schemas/trace-event.example.jsonl` onto Redis
pub/sub channel `agent-run:{run_id}`. The SSE endpoint forwards those events to
the browser, so Dev 2's timeline (B5) sees a real, well-shaped stream while the
real planner is still being built.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "schemas" / "trace-event.example.jsonl"


def _channel(run_id: uuid.UUID) -> str:
    return f"agent-run:{run_id}"


def _load_example_events() -> list[dict]:
    return [json.loads(line) for line in EXAMPLE_PATH.read_text().splitlines() if line.strip()]


async def replay_example_run(
    redis: aioredis.Redis,
    run_id: uuid.UUID,
    *,
    speed: float = 0.25,
    initial_delay: float = 0.25,
) -> None:
    """Publish the example trace onto `agent-run:{run_id}` with run_id rewritten.

    `speed` scales the inter-event delay; 1.0 = honor recorded timestamps,
    0.25 = 4x faster (better for demos/tests). Always at least 50ms between events.
    `initial_delay` defers the first publish so subscribers (the SSE handler) have
    time to connect after the POST that triggered this replay returns. Pubsub
    drops messages without listeners, so without this delay clients miss the
    `run_started` event.
    """
    events = _load_example_events()
    if not events:
        logger.warning("agent.replay: example file is empty: %s", EXAMPLE_PATH)
        return

    if initial_delay > 0:
        await asyncio.sleep(initial_delay)

    target = str(run_id)
    prev_ts: float | None = None

    for raw in events:
        event = dict(raw)
        if "run_id" in event:
            event["run_id"] = target

        if prev_ts is not None:
            try:
                from datetime import datetime as _dt
                this_ts = _dt.fromisoformat(event["ts"].replace("Z", "+00:00")).timestamp()
                gap = max(0.05, (this_ts - prev_ts) * speed)
            except (KeyError, ValueError):
                gap = 0.1
            await asyncio.sleep(min(gap, 5.0))
        try:
            from datetime import datetime as _dt
            prev_ts = _dt.fromisoformat(event["ts"].replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError):
            prev_ts = None

        await redis.publish(_channel(run_id), json.dumps(event))

    logger.info("agent.replay: published %d events for run %s", len(events), run_id)
