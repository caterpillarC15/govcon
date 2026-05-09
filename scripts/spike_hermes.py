#!/usr/bin/env python3
"""Hermes spike — answer the 7 open questions in tasks/HERMES.md.

This script proves out the integration mechanics we need before writing A9.
It registers two trivial Python toolsets directly with Hermes' internal tool
registry, runs a child agent via delegate_task, and captures the trace via
the documented tool_*_callback hooks. Findings are written to
tasks/HERMES_SPIKE.md by hand after this prints.

Usage:
    cd /root/govcon
    ANTHROPIC_API_KEY=... python3 scripts/spike_hermes.py

The script is deliberately self-contained — no project deps required, no
docker, no FastAPI. Just Hermes + stdlib.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# ── Wire Hermes' internal modules onto sys.path ────────────────────────────
# Hermes installs to /usr/local/lib/hermes-agent (or wherever `pip install`
# put it). The agent modules live at the package root, not inside a
# top-level package, so we point sys.path at the install dir directly.
HERMES_INSTALL = Path("/usr/local/lib/hermes-agent")
if not HERMES_INSTALL.exists():
    raise SystemExit(f"Hermes install not found at {HERMES_INSTALL}")
sys.path.insert(0, str(HERMES_INSTALL))

# Imports must come AFTER sys.path injection.
from tools.registry import registry, tool_result, tool_error  # type: ignore  # noqa: E402
import toolsets as hermes_toolsets  # type: ignore  # noqa: E402

# Load Hermes' standard .env (~/.hermes/.env + project .env) so the spike
# sees ANTHROPIC_API_KEY the same way `hermes` itself does. Prefer the
# canonical loader; fall back to a tiny in-line parser when python-dotenv
# isn't on the system Python (Hermes' own venv ships it; system Python may
# not).
def _load_env_files() -> None:
    """Make ANTHROPIC_API_KEY available to Python.

    Hermes can store the key in three places:
        1. ~/.hermes/.env  (when the user pasted it via setup wizard)
        2. ~/.hermes/auth.json `credential_pool.anthropic[*].api_key`
           (when added via `hermes login` / `hermes auth`)
        3. The shell env (already in os.environ).

    We try all three so this script can run under any Python that imports
    Hermes' modules.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return

    # 1) ~/.hermes/.env (and project .env)
    candidates = [Path.home() / ".hermes" / ".env", Path.cwd() / ".env"]
    for env_path in candidates:
        if not env_path.is_file():
            continue
        for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ and value:
                os.environ[key] = value

    if os.environ.get("ANTHROPIC_API_KEY"):
        return

    # 2) ~/.hermes/auth.json credential pool
    auth_path = Path.home() / ".hermes" / "auth.json"
    if auth_path.is_file():
        try:
            data = json.loads(auth_path.read_text(encoding="utf-8"))
        except Exception:
            return
        pool = (data.get("credential_pool") or {}).get("anthropic") or []
        for entry in pool:
            # Hermes credential pool uses one of:
            #   - api_key (static API key)
            #   - access_token (OAuth bearer token, e.g. from Claude.ai account)
            #   - token (some legacy entries)
            api_key = entry.get("api_key") or entry.get("access_token") or entry.get("token")
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key
                if entry.get("auth_type") == "oauth" or entry.get("access_token"):
                    # OAuth tokens go in a different env var when used directly
                    # against the Anthropic SDK; export both so whichever the
                    # SDK reads first wins.
                    os.environ.setdefault("ANTHROPIC_AUTH_TOKEN", api_key)
                return


_load_env_files()


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Register two trivial custom toolsets.
#
# This proves Q3 (toolset registration mechanism). We register two functions
# under two distinct toolset names — `spike_math` and `spike_text` — using
# the same registry.register() call that the built-in tools use. The toolset
# string is what `delegate_task(toolsets=[...])` filters on.
# ─────────────────────────────────────────────────────────────────────────────

ADD_SCHEMA = {
    "name": "spike_add",
    "description": "Add two integers. Returns {'sum': a + b}.",
    "parameters": {
        "type": "object",
        "properties": {
            "a": {"type": "integer", "description": "First addend."},
            "b": {"type": "integer", "description": "Second addend."},
        },
        "required": ["a", "b"],
    },
}

ECHO_SCHEMA = {
    "name": "spike_echo",
    "description": "Return the input string verbatim. Returns {'echoed': s}.",
    "parameters": {
        "type": "object",
        "properties": {"s": {"type": "string", "description": "Text to echo."}},
        "required": ["s"],
    },
}


def _spike_add_handler(args: dict, **_kw) -> str:
    a = int(args.get("a", 0))
    b = int(args.get("b", 0))
    return tool_result({"sum": a + b}, message=f"{a} + {b} = {a + b}")


def _spike_echo_handler(args: dict, **_kw) -> str:
    s = str(args.get("s", ""))
    return tool_result({"echoed": s}, message=f"echoed {len(s)} chars")


registry.register(
    name="spike_add",
    toolset="spike_math",
    schema=ADD_SCHEMA,
    handler=_spike_add_handler,
    is_async=False,
    description=ADD_SCHEMA["description"],
    emoji="➕",
)
registry.register(
    name="spike_echo",
    toolset="spike_text",
    schema=ECHO_SCHEMA,
    handler=_spike_echo_handler,
    is_async=False,
    description=ECHO_SCHEMA["description"],
    emoji="📣",
)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Verify the toolsets resolve.
# ─────────────────────────────────────────────────────────────────────────────

def verify_toolset_registration() -> None:
    print("─" * 72)
    print("PHASE 1: Custom toolset registration via tools.registry")
    print("─" * 72)
    for ts in ("spike_math", "spike_text"):
        tools = hermes_toolsets.resolve_toolset(ts)
        ok = "✓" if tools else "✗"
        print(f"  {ok} toolset {ts!r:14}  → tools: {tools}")
        if not tools:
            raise SystemExit(f"Toolset {ts!r} registered no tools — registry bug.")


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Run an AIAgent in-process with trace callbacks.
#
# This proves Q1 (programmatic invocation, in-process), Q2 (trace events via
# documented callbacks), and Q3 (toolset restriction). We restrict the agent
# to a single toolset and ask it to compute something — Hermes' planner
# picks the tool, calls our handler, and the callbacks fire.
# ─────────────────────────────────────────────────────────────────────────────

def run_in_process_spike() -> list[dict]:
    print()
    print("─" * 72)
    print("PHASE 2: In-process AIAgent with tool_*_callback trace capture")
    print("─" * 72)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("  ⚠ ANTHROPIC_API_KEY not set — skipping in-process spike.")
        return []

    # Import lazily — AIAgent pulls a lot of optional deps at import time.
    from run_agent import AIAgent  # type: ignore

    captured: list[dict] = []

    def on_tool_start(tool_call_id: str, name: str, args: dict) -> None:
        captured.append({
            "type": "tool_called",
            "tool_call_id": tool_call_id,
            "tool": name,
            "input": args,
            "ts": time.time(),
        })

    def on_tool_complete(tool_call_id: str, name: str, args: dict, result: Any) -> None:
        captured.append({
            "type": "tool_returned",
            "tool_call_id": tool_call_id,
            "tool": name,
            "output_preview": str(result)[:200],
            "ts": time.time(),
        })

    agent = AIAgent(
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        max_iterations=8,
        enabled_toolsets=["spike_math"],   # ← Q3: restrict to one custom toolset
        quiet_mode=True,
        skip_context_files=True,           # don't load HERMES.md / SOUL.md for the spike
        skip_memory=True,                  # don't load MEMORY.md / USER.md
        platform="cli",
        tool_start_callback=on_tool_start,
        tool_complete_callback=on_tool_complete,
    )

    user_msg = (
        "Use the spike_add tool to compute 17 + 25, then tell me the result. "
        "Do not compute it yourself — call the tool."
    )
    print(f"  → running agent (toolsets=['spike_math']) ...")
    t0 = time.monotonic()
    final = agent.chat(user_msg)
    elapsed = time.monotonic() - t0
    print(f"  ← agent finished in {elapsed:.2f}s")
    print(f"  ← final response: {str(final)[:200]!r}")

    print()
    print(f"  Captured {len(captured)} trace events:")
    for ev in captured:
        if ev["type"] == "tool_called":
            print(f"    • tool_called   {ev['tool']:12} args={json.dumps(ev['input'])}")
        else:
            print(f"    • tool_returned {ev['tool']:12} {ev['output_preview']}")

    # Sanity check: the agent must have actually called spike_add.
    called = [ev for ev in captured if ev["type"] == "tool_called"]
    assert any(ev["tool"] == "spike_add" for ev in called), (
        f"Agent did not call spike_add — toolset restriction or registry "
        f"is broken. Captured: {[ev['tool'] for ev in called]}"
    )
    return captured


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Subprocess one-shot path + JSONL session inspection.
#
# This proves the production path: FastAPI shells out to `hermes -z` for each
# capture run. We then read the resulting session JSONL — that's the raw
# trace data the bridge will translate.
# ─────────────────────────────────────────────────────────────────────────────

def run_subprocess_spike() -> Path | None:
    print()
    print("─" * 72)
    print("PHASE 3: Subprocess (`hermes -z`) — production invocation path")
    print("─" * 72)

    sessions_dir = Path.home() / ".hermes" / "sessions"
    # Hermes records sessions both as conversation JSONL and as session_*.json
    # snapshots; the snapshot is what survives across runs and what the bridge
    # would tail in production. Watch for either.
    before_jsonl = set(sessions_dir.glob("*.jsonl"))
    before_json = set(sessions_dir.glob("session_*.json"))

    prompt = "Reply with the single word 'OK' and nothing else."
    cmd = [
        "hermes", "-z", prompt,
        "-m", "claude-haiku-4-5-20251001",
        "--provider", "anthropic",
        "--ignore-rules",        # don't load /root/HERMES.md (we're outside the project repo)
    ]
    print(f"  → {' '.join(cmd[:3])} <prompt>  (haiku, default Hermes config)")
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            env={**os.environ},
        )
    except subprocess.TimeoutExpired:
        print("  ✗ subprocess timed out after 120s")
        return None
    elapsed = time.monotonic() - t0
    print(f"  ← exited {proc.returncode} in {elapsed:.2f}s")
    print(f"  ← stdout (last 200 chars): {proc.stdout[-200:]!r}")
    if proc.returncode != 0:
        print(f"  ← stderr (last 400 chars): {proc.stderr[-400:]!r}")
        return None

    after_jsonl = set(sessions_dir.glob("*.jsonl"))
    after_json = set(sessions_dir.glob("session_*.json"))
    new_jsonl = after_jsonl - before_jsonl
    new_json = after_json - before_json

    chosen: Path | None = None
    if new_jsonl:
        chosen = sorted(new_jsonl, key=lambda p: p.stat().st_mtime)[-1]
        print(f"  ← new conversation jsonl: {chosen}")
    if new_json:
        snap = sorted(new_json, key=lambda p: p.stat().st_mtime)[-1]
        print(f"  ← new session snapshot:   {snap}")
        chosen = chosen or snap
    if not chosen:
        print("  (no new session files — `-z` may not record short sessions)")
        return None

    print(f"  ← inspecting:    {chosen}")
    print(f"  ← session size:  {chosen.stat().st_size} bytes")
    types: dict[str, int] = {}
    if chosen.suffix == ".jsonl":
        with chosen.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    role = rec.get("role", "?")
                    types[role] = types.get(role, 0) + 1
                except Exception:
                    pass
    else:
        try:
            data = json.loads(chosen.read_text())
            msgs = data.get("messages") or data.get("conversation") or []
            for rec in msgs:
                role = rec.get("role", "?")
                types[role] = types.get(role, 0) + 1
        except Exception as exc:
            print(f"  (could not parse json snapshot: {exc!r})")
    print(f"  ← message role counts: {types}")
    return chosen


# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Print summary that maps directly onto the 7 open questions.
# ─────────────────────────────────────────────────────────────────────────────

def print_findings_summary(in_process_events: list[dict], session: Path | None) -> None:
    print()
    print("═" * 72)
    print("FINDINGS — answers to the 7 open questions in tasks/HERMES.md")
    print("═" * 72)
    print()
    print("Q1 Programmatic invocation:")
    print("    Two stable paths:")
    print("    (a) IN-PROCESS — `from run_agent import AIAgent`; pass callbacks;")
    print("        call agent.chat(msg). Best for tests + the eval harness.")
    print(f"        Verified: {len(in_process_events)} events captured.")
    print("    (b) SUBPROCESS — `hermes -z <prompt>`. Best for the FastAPI runner;")
    print("        survives crashes; clean process boundary.")
    print(f"        Verified session: {session}")
    print("    DECISION: subprocess for /api/agent/hermes_runner.py (production);")
    print("              in-process for /eval/runner (tests).")
    print()
    print("Q2 Trace event format:")
    print("    Hermes does NOT emit a structured trace stream natively.")
    print("    Instead it offers callback hooks on AIAgent:")
    print("      • tool_start_callback(tool_call_id, name, args)")
    print("      • tool_complete_callback(tool_call_id, name, args, result)")
    print("      • tool_progress_callback(event, name, preview, args)")
    print("      • step_callback, thinking_callback, reasoning_callback")
    print("    For subprocess runs, the session JSONL under ~/.hermes/sessions/")
    print("    contains role=user|assistant|tool messages with tool_call_id linkage.")
    print("    DECISION: in-process callbacks for tests; for the FastAPI bridge,")
    print("              tail the session JSONL OR use the in-process path under")
    print("              uvicorn — pick based on Q4.")
    print()
    print("Q3 Toolset registration mechanism:")
    print("    Two paths:")
    print("    (a) DIRECT — `from tools.registry import registry; registry.register(")
    print("                   name='extract_requirements', toolset='gov_compliance', ...)`")
    print("        at module import time. Toolset string is whatever you want;")
    print("        delegate_task(toolsets=['gov_compliance']) filters on it.")
    print("        Verified above with spike_math + spike_text.")
    print("    (b) MCP SERVER — run our own stdio MCP server; tools auto-prefixed")
    print("        as `mcp_govcapture_<name>` and grouped under MCP toolset alias.")
    print("        Looser coupling but adds a process + JSON-RPC layer.")
    print("    DECISION: DIRECT registration for v1. Hermes is a Python lib already")
    print("              installed in the api container; importing tools.registry is")
    print("              one line; we get native toolset names that match")
    print("              CONTRACTS.md §5 verbatim (gov_discovery, gov_documents,")
    print("              gov_compliance, gov_risks, gov_proposals, human_review).")
    print()
    print("Q4 Hermes execution backend on VX1:")
    print("    Hermes runs in-process (Python). No separate daemon. So `api`")
    print("    container imports Hermes; no sidecar needed.")
    print("    DECISION: Hermes runs IN the api container as a library, not a")
    print("              sidecar. docker-compose has only api/postgres/redis.")
    print()
    print("Q5 Hermes memory + our Postgres:")
    print("    Hermes memory = MEMORY.md/USER.md in HERMES_HOME, plus session DBs.")
    print("    Postgres = domain entities (CompanyProfile, Opportunity, ...).")
    print("    Zero overlap by design. We disable cross-session memory in")
    print("    .hermes/config.yaml (`memory.cross_session: false`).")
    print("    DECISION: per-run only; no double-storage; clear between eval runs.")
    print()
    print("Q6 Cost tracking:")
    print("    Hermes does not surface per-call cost as a first-class field on")
    print("    callbacks. It tracks token usage internally via iteration_budget.")
    print("    Each of OUR domain skills (extract_requirements, score_fit, ...)")
    print("    will compute cost_usd from the LLM client's usage data and return")
    print("    it in the tool_result envelope. The bridge sums these.")
    print("    DECISION: cost_usd lives in OUR tool wrapper, not Hermes. Pricing")
    print("              table at /api/agent/llm.py.")
    print()
    print("Q7 Per-subagent model override:")
    print("    `delegate_task` accepts no model kwarg directly, but config.yaml")
    print("    `delegation.model` / `delegation.provider` lets us pin a global")
    print("    delegation-level override. Per-call override is not exposed via")
    print("    the public delegate_task signature — implication: all child agents")
    print("    inherit the parent's model unless config sets a delegation override.")
    print("    DECISION: keep all agents on Sonnet for v1 (cost still ≤ $0.30/run")
    print("              per AGENT_ARCHITECTURE.md estimates). Revisit only if")
    print("              we hit the $0.50 cap.")
    print()
    print("═" * 72)
    print("Spike complete. Write findings to tasks/HERMES_SPIKE.md.")
    print("═" * 72)


def main() -> int:
    verify_toolset_registration()
    events = run_in_process_spike()
    session = run_subprocess_spike()
    print_findings_summary(events, session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
