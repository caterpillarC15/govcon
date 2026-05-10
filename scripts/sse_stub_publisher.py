"""Publish a synthetic agent-run trace to Redis so /web's RunTimeline renders.

Lets you exercise the SSE pipeline end-to-end (Redis → FastAPI
GET /agent-runs/{id}/stream → /web EventSource) without depending on
/root/michealaai's orchestrator. Useful for:

- Phase 6 deploy smoke-testing (does prod's nginx + gunicorn stream SSE?)
- Phase 7 cross-repo coordination (compare against what the real
  orchestrator emits)
- Sprint C UI work (verifying the timeline renders all 8 event types)

Usage:

    # 1. In one terminal: start the API.
    uv run uvicorn api.main:app --reload --port 8000

    # 2. In /web: start the dev server and log in. Create a run via
    #    /app/goal — POST /agent-runs persists a row and returns its id.
    #    Note the id from the URL after redirect.

    # 3. In a third terminal: replay events to that run id.
    uv run python scripts/sse_stub_publisher.py <run-uuid>

    # 4. Watch /app/runs/<run-uuid> populate live.

The events match `schemas/trace-event.schema.json`. Tools called: the same
12 tools the orchestrator can call. Cadence is ~500ms per event so the UI
has time to render but the whole run completes in ~10s.

This is a *stub*: tool inputs/outputs are seeded values, not real LLM
output. The orchestrator (`/root/michealaai`) is the real emitter; this
script exists to let the pack be tested in isolation.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import redis.asyncio as redis_asyncio


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_events(run_id: str, profile_id: str | None) -> list[dict]:
    """Return a realistic 14-event run trace covering all 8 event types."""
    step_search = str(uuid.uuid4())
    step_parse = str(uuid.uuid4())
    step_score = str(uuid.uuid4())
    step_package = str(uuid.uuid4())
    opp_id = str(uuid.uuid4())

    return [
        {
            "type": "run_started",
            "run_id": run_id,
            "goal": "Find DC-area cloud migration RFPs in next 90 days for a 541512 small business.",
            "profile_id": profile_id,
            "ts": _now_iso(),
        },
        # ---- Step 1: search ----
        {"type": "step_started", "run_id": run_id, "step_id": step_search,
         "label": "Search opportunities", "ts": _now_iso()},
        {"type": "tool_called", "run_id": run_id, "step_id": step_search,
         "tool": "load_seeded_opportunities",
         "input": {"naics": ["541512"], "keywords": ["cloud", "migration"], "max_age_days": 90},
         "rationale": "Live SAM disabled in stub mode; load seeded fixtures.",
         "ts": _now_iso()},
        {"type": "tool_returned", "run_id": run_id, "step_id": step_search,
         "tool": "load_seeded_opportunities",
         "output": {"count": 1, "opportunity_ids": [opp_id]},
         "error": None, "latency_ms": 42, "cost_usd": 0, "ts": _now_iso()},
        {"type": "step_completed", "run_id": run_id, "step_id": step_search,
         "status": "complete", "ts": _now_iso()},
        # ---- Step 2: parse PDF ----
        {"type": "step_started", "run_id": run_id, "step_id": step_parse,
         "label": "Parse strong-pursue RFP", "ts": _now_iso()},
        {"type": "tool_called", "run_id": run_id, "step_id": step_parse,
         "tool": "parse_pdf",
         "input": {"path": "fixtures/strong-pursue/attachments/RFP-001.pdf"},
         "rationale": "Extract text + page boundaries for requirement extraction.",
         "ts": _now_iso()},
        {"type": "tool_returned", "run_id": run_id, "step_id": step_parse,
         "tool": "parse_pdf",
         "output": {"chunks": 24, "unparseable": False},
         "error": None, "latency_ms": 612, "cost_usd": 0, "ts": _now_iso()},
        {"type": "step_completed", "run_id": run_id, "step_id": step_parse,
         "status": "complete", "ts": _now_iso()},
        # ---- Step 3: score ----
        {"type": "step_started", "run_id": run_id, "step_id": step_score,
         "label": "Score fit + detect risks", "ts": _now_iso()},
        {"type": "tool_called", "run_id": run_id, "step_id": step_score,
         "tool": "score_fit",
         "input": {"company_profile": {"naics_codes": ["541512"]}, "requirements_count": 3},
         "rationale": "Apply §5.7 rubric.", "ts": _now_iso()},
        {"type": "tool_returned", "run_id": run_id, "step_id": step_score,
         "tool": "score_fit",
         "output": {"total_score": 88, "decision": "strong_pursue"},
         "error": None, "latency_ms": 1842, "cost_usd": 0.012, "ts": _now_iso()},
        {"type": "opportunity_ranked", "run_id": run_id, "opportunity_id": opp_id,
         "score": 88, "decision": "strong_pursue", "ts": _now_iso()},
        {"type": "step_completed", "run_id": run_id, "step_id": step_score,
         "status": "complete", "ts": _now_iso()},
        # ---- Step 4: package ----
        {"type": "step_started", "run_id": run_id, "step_id": step_package,
         "label": "Generate action package", "ts": _now_iso()},
        {"type": "needs_human", "run_id": run_id,
         "question": "Confirm small-business set-aside qualification before submitting.",
         "context": {"opportunity_id": opp_id, "set_aside": "Total Small Business Set-Aside"},
         "ts": _now_iso()},
        {"type": "tool_called", "run_id": run_id, "step_id": step_package,
         "tool": "generate_action_package",
         "input": {"mode": "full", "opportunity_id": opp_id},
         "rationale": "Strong-pursue decision → full package.", "ts": _now_iso()},
        {"type": "tool_returned", "run_id": run_id, "step_id": step_package,
         "tool": "generate_action_package",
         "output": {"package_id": str(uuid.uuid4()), "approval_required_count": 4},
         "error": None, "latency_ms": 3214, "cost_usd": 0.041, "ts": _now_iso()},
        {"type": "step_completed", "run_id": run_id, "step_id": step_package,
         "status": "complete", "ts": _now_iso()},
        # ---- End ----
        {"type": "run_completed", "run_id": run_id, "status": "complete",
         "summary": "1 opportunity scored strong_pursue; action package ready for human approval.",
         "ts": _now_iso()},
    ]


async def publish(run_id: str, profile_id: str | None, redis_url: str, delay_ms: int) -> int:
    """Publish events to agent-run:{run_id}. Returns event count."""
    client: redis_asyncio.Redis = redis_asyncio.from_url(redis_url, decode_responses=True)
    channel = f"agent-run:{run_id}"
    events = _build_events(run_id, profile_id)
    print(f"Publishing {len(events)} events to {channel} on {redis_url}")
    print(f"Cadence: {delay_ms}ms between events; total ~{(len(events) * delay_ms) / 1000:.1f}s")
    print()
    try:
        for i, ev in enumerate(events, 1):
            payload = json.dumps(ev)
            await client.publish(channel, payload)
            label = ev.get("label") or ev.get("tool") or ev.get("status") or ev.get("question", "")[:40]
            print(f"  [{i:2d}/{len(events)}] {ev['type']:22s} {label}")
            if i < len(events):
                await asyncio.sleep(delay_ms / 1000)
    finally:
        await client.aclose()
    print()
    print(f"Done. Visit /app/runs/{run_id} to verify the timeline rendered.")
    return len(events)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Publish a stub agent-run trace to Redis for /web SSE testing.")
    p.add_argument("run_id", help="UUID of the agent_run row (created via POST /agent-runs).")
    p.add_argument("--profile-id", default=None, help="Optional profile UUID.")
    p.add_argument(
        "--redis-url",
        default=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        help="Redis URL. Defaults to $REDIS_URL or redis://localhost:6379/0.",
    )
    p.add_argument("--delay-ms", type=int, default=500,
                   help="Delay between events in ms. Default 500.")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    try:
        uuid.UUID(args.run_id)
    except ValueError:
        print(f"error: run_id must be a UUID, got {args.run_id!r}", file=sys.stderr)
        return 2
    if args.profile_id is not None:
        try:
            uuid.UUID(args.profile_id)
        except ValueError:
            print(f"error: profile_id must be a UUID, got {args.profile_id!r}", file=sys.stderr)
            return 2
    asyncio.run(publish(args.run_id, args.profile_id, args.redis_url, args.delay_ms))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
