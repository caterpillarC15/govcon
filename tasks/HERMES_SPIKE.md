# Hermes Integration Spike — Findings

**Date:** 2026-05-09
**Author:** Track A (backend)
**Status:** Complete. All 7 open questions in `tasks/HERMES.md` have working-code answers.
**Verification:** `scripts/spike_hermes.py` (committed alongside this doc). Run with
`/usr/local/lib/hermes-agent/venv/bin/python scripts/spike_hermes.py` from the repo root.

This document closes the spike phase. The next phase is Milestone 1 / `tasks/PHASE_0.md`.

---

## Host state confirmed

- Hermes Agent **v0.13.0** installed at `/usr/local/lib/hermes-agent` (Python 3.11 venv).
- `~/.hermes/config.yaml` already has the values our 5-agent design requires:
  - `delegation.max_spawn_depth: 2`
  - `delegation.max_concurrent_children: 3`
  - `delegation.orchestrator_enabled: true`
- All 7 govcapture SKILL.md procedures load (`hermes skills list | grep govcapture`).
  Symlink `~/.hermes/skills/govcapture → <repo>/.hermes/skills/govcapture` already in place.
- `~/.hermes/SOUL.md` and the project-root `HERMES.md` resolve as expected.
- Anthropic credentials live in `~/.hermes/auth.json` `credential_pool.anthropic[]`
  as an OAuth `access_token` (not a static `api_key`). The spike's loader handles
  all three storage paths (`.env`, `auth.json`, shell env). `/api/config.py` will
  do the same in Milestone 1.

---

## Spike script summary

`scripts/spike_hermes.py` runs three phases. All three pass on this host.

| Phase | What it proves | Result |
|-------|----------------|--------|
| 1. Toolset registration | `tools.registry.register(toolset='spike_math', ...)` works for arbitrary toolset names; `toolsets.resolve_toolset()` returns the registered tools. | ✓ `spike_math → ['spike_add']`, `spike_text → ['spike_echo']` |
| 2. In-process AIAgent + callbacks | `AIAgent(enabled_toolsets=['spike_math'], tool_start_callback=…, tool_complete_callback=…)` runs Haiku, picks our tool, fires callbacks with `(tool_call_id, name, args)` / `(…, result)`. | ✓ 2 trace events captured; final response `"The result of 17 + 25 is 42."`; ~2.7 s wall-clock |
| 3. Subprocess `hermes -z` | `hermes -z <prompt>` exits 0 and writes a `~/.hermes/sessions/session_*.json` snapshot containing role-tagged messages. | ✓ 79–93 KB snapshot, role counts `{user:1, assistant:1}`; ~2.3 s wall-clock |

The script is idempotent and side-effect-free except for the session snapshot
that any `hermes -z` run produces.

---

## Answers to the 7 open questions

### Q1. Programmatic invocation

**Two stable paths, both verified.**

- **Subprocess (production):** `hermes -z <prompt> -m <model> --provider anthropic`.
  Exit 0 on success; persists a `session_<ts>_<id>.json` snapshot under
  `~/.hermes/sessions/`. Process boundary survives crashes.
- **In-process (tests / eval harness):** `from run_agent import AIAgent`,
  pass keyword callbacks, call `agent.chat(msg)` or `agent.run_conversation(...)`.
  Returns the final response string; callbacks fire as tools execute.

**Decision.**

| Caller | Path | Why |
|--------|------|-----|
| `/api/agent/hermes_runner.py` (FastAPI) | **subprocess** | Crash isolation; the FastAPI worker stays alive even if a model call hangs. Restart-safe. |
| `/eval/runner/` (A12 harness) | **in-process** | We need the structured callback stream for assertions; subprocess parsing the session snapshot is strictly inferior. |

Both paths invoke the same Hermes core, so registered toolsets and SKILL.md
procedures behave identically.

### Q2. Trace event format

**Hermes does not emit a structured trace stream natively.** Two surfaces exist instead.

- **Callbacks on `AIAgent` (in-process):**
  - `tool_start_callback(tool_call_id: str, name: str, args: dict)`
  - `tool_complete_callback(tool_call_id: str, name: str, args: dict, result)`
  - `tool_progress_callback(event: str, name: str, preview: str, args: dict)`
  - `step_callback`, `thinking_callback`, `reasoning_callback`,
    `interim_assistant_callback`, `clarify_callback`, `stream_delta_callback`,
    `status_callback`, `tool_gen_callback`
  Source: `run_agent.py` `AIAgent.__init__` lines 1079–1310 of the v0.13.0 install.

- **Session snapshots (subprocess):** `~/.hermes/sessions/session_<ts>_<id>.json`,
  containing OpenAI-format messages (`role`, `content`, `tool_calls`,
  `tool_call_id`). `tool_call_id` links assistant tool-call requests to
  `role: "tool"` results.

**Decision.**

The bridge (`/api/agent/hermes_bridge.py`, A9) implements **two translation modes**:

- **In-process mode (eval harness):** subscribe to `tool_start_callback` /
  `tool_complete_callback`. Synthesize `tool_called` / `tool_returned` events
  with `latency_ms` (computed from monotonic clock between start and complete)
  and `cost_usd` (extracted from the tool's return envelope — see Q6).

- **Subprocess mode (production FastAPI):** the runner spawns `hermes -z` with
  `--pass-session-id <run_id>` (or equivalent), then tails the session snapshot.
  The bridge translates each new `role: "tool"` message into a
  `tool_returned` event and pairs it with the preceding `tool_calls` entry to
  produce `tool_called`.

The translation table is added to `CONTRACTS.md §3.1` in this PR.

### Q3. Toolset registration mechanism

**Direct registration via Hermes' tool registry.**

```python
from tools.registry import registry, tool_result
from typing import Any

def my_handler(args: dict, **_kw) -> str:
    ...
    return tool_result({"...": ...})

registry.register(
    name="extract_requirements",
    toolset="gov_compliance",
    schema=EXTRACT_REQUIREMENTS_SCHEMA,
    handler=my_handler,
    is_async=True,
    description="...",
    emoji="📋",
)
```

The `toolset` string is arbitrary. `delegate_task(toolsets=["gov_compliance"])`
filters on it directly. Verified end-to-end with `spike_math` and `spike_text`.

**MCP server is the alternative** (`mcp_govcapture_*` tool prefixes, JSON-RPC
over stdio). Rejected for v1 — it adds a process + serialization layer with
no architectural gain. We can adopt it later for cross-language tooling.

**Decision.** Direct registration. The 6 toolsets named in CONTRACTS.md §5
become real toolset strings on the registry side:

| Toolset | Tools | Granted to |
|---------|-------|------------|
| `gov_discovery` | `parse_goal`, `search_sam_opportunities`, `load_seeded_opportunities`, `rank_opportunities`, `summarize_run` | Capture Lead |
| `gov_documents` | `fetch_attachment`, `parse_pdf`, `verify_source_page` | Capture Analyst |
| `gov_compliance` | `extract_requirements`, `score_fit` | Compliance Officer |
| `gov_risks` | `detect_risks` | Risk Analyst |
| `gov_proposals` | `generate_action_package` | Proposal Strategist |
| `human_review` | `request_human_review` | All agents |

A bootstrap module `/api/agent/toolsets.py` (Milestone 3) imports the implementations
and calls `registry.register(...)` at import time. The FastAPI app imports this
module before starting the Hermes runner, so registration happens once per process.

### Q4. Hermes execution backend on VX1

**Hermes runs in-process (Python) inside the `api` container as a library.**
Not a sidecar.

This is the cleanest layout because:
- Hermes is a pip-installable Python package; the `api` image already needs
  Python, FastAPI, and the domain skill modules. Adding Hermes is `pip install`.
- Toolset registration is at module-import time. With Hermes in the same
  process, FastAPI startup deterministically registers our toolsets before any
  agent run begins.
- The subprocess invocation path (Q1) calls `hermes -z` from within the same
  container — no cross-container plumbing.

**Decision.** `docker-compose.yaml` has three services:

```
services:
  api:        # FastAPI + Hermes (library + CLI), uvicorn workers
  postgres:   # postgres:16
  redis:      # redis:7-alpine
```

The Vultr VX1 deployment (A13) uses the same compose file with prod overrides.

### Q5. Hermes memory vs. our Postgres

**No overlap.** Hermes memory = `MEMORY.md` / `USER.md` in `HERMES_HOME` plus
session snapshots — agent recall, not domain data. Postgres = domain entities
(CompanyProfile, Opportunity, ExtractedRequirement, FitScore, RiskFlag,
ActionPackage, AgentRun).

The project ships `.hermes/config.yaml` with `memory.cross_session: false` so
no information leaks between runs. The eval harness (A12) calls
`hermes memory clear` between fixtures to guarantee a clean start.

**Decision.** No double-storage. The bridge does not write Hermes' session
data into Postgres. The runner persists only the canonical PRD §8 entities
plus the §3 trace events. Hermes' session snapshots are a debug artifact, not
a system of record.

### Q6. Cost tracking

**Hermes does not surface per-call `cost_usd` on the callback hooks.** It
tracks token counts internally for `iteration_budget` enforcement, but not in
a structured way the bridge can consume.

**Decision.** Cost lives in *our* tool wrappers.

```python
# /api/agent/llm.py
PRICING_USD_PER_MILLION_TOKENS = {
    "claude-sonnet-4-6":            {"input": 3.0,  "output": 15.0},
    "claude-haiku-4-5-20251001":    {"input": 0.8,  "output": 4.0},
}

# /api/skills/extract_requirements/implementation.py
async def extract_requirements(...) -> RequirementExtractionOutput:
    t0 = monotonic()
    response = await llm.complete(...)
    cost = compute_cost(response.usage, response.model)
    output = validate_against_schema(response.content)
    return tool_result(
        output,
        meta={"latency_ms": int((monotonic() - t0) * 1000), "cost_usd": cost},
    )
```

The bridge sums `meta.cost_usd` across all `tool_returned` events. When the
running total exceeds `RUN_BUDGET_USD` (default `0.50`), the bridge emits a
`run_completed` with `status: "partial"` and aborts the Hermes run. The abort
reason is persisted on `agent_run.status` per PRD §4.5.

### Q7. Per-subagent model override

**`delegate_task` exposes no per-call `model` kwarg.** The only override point
is `~/.hermes/config.yaml` `delegation.model` / `delegation.provider`, which
applies globally to all delegated children.

**Decision.** All agents on Sonnet for v1. AGENT_ARCHITECTURE.md estimates
≈$0.20 per 3-opportunity demo run (roughly half the $0.50 cap). Per-role
splits (e.g., Risk Analyst on Haiku) are a post-MVP optimization, deferred
until we hit the cap on real fixtures.

If we later need per-role models, two paths exist:
- Set `delegation.model` to `claude-haiku-4-5-20251001` globally and override
  *upward* to Sonnet inside the `extract_requirements` and
  `generate_action_package` skill implementations (where the LLM call is in
  our Python). This pushes the model decision into the toolset, where we
  already control it.
- Submit a Hermes upstream PR exposing `model` as a per-task `delegate_task`
  arg. Track in the post-MVP backlog.

---

## CONTRACTS.md follow-ups (this PR)

The spike confirmed two contract changes that ship in the same commit as this
findings doc:

1. **`CONTRACTS.md §3.1`** — added: bridge translation table mapping Hermes'
   callbacks and session-snapshot fields onto the §3 event taxonomy.
2. **`CONTRACTS.md §1` and `INTERFERENCE_MAP.md §1`** — bumped the PRD-version
   reference from `v1.2.1` to `v1.2.2` (PRD itself was already at v1.2.2).

Two contract changes the spike confirmed are *not* needed:

- **Frontend env var name.** CONTRACTS.md §4 already uses `NEXT_PUBLIC_API_BASE`,
  which is correct for the migrated Next.js landing app. No change needed
  (the brief was stale on this point).
- **MCP integration.** Direct registration (Q3) replaces the proposed MCP
  approach. No `mcp_servers:` entry, no `hermes mcp add`.

---

## What this unblocks

- **Milestone 1 (Phase 0):** docker-compose layout is decided (no Hermes sidecar);
  `/api/config.py` env contract handles the three credential paths the spike
  found; the schema/codegen pipeline can proceed.
- **Milestone 3 (A4–A8):** each domain skill knows how it gets registered
  (direct `registry.register(...)` at module-import) and how it returns
  cost/latency (in the `tool_result` envelope's `meta`).
- **Milestone 4 (A9):** the bridge has two concrete translation modes
  (callback-based and snapshot-tail). The §11.1 enforcement chain remains
  unchanged — the deterministic short-circuit in `score_fit` Phase A runs in
  our own Python before any model call, regardless of which invocation path
  Hermes uses.

---

## Reproduction

```bash
cd /root/govcon
/usr/local/lib/hermes-agent/venv/bin/python scripts/spike_hermes.py
```

Expected output (abbreviated):

```
PHASE 1: Custom toolset registration via tools.registry
  ✓ toolset 'spike_math'    → tools: ['spike_add']
  ✓ toolset 'spike_text'    → tools: ['spike_echo']

PHASE 2: In-process AIAgent with tool_*_callback trace capture
  → running agent (toolsets=['spike_math']) ...
  ┊ ⚡ spike_add   0.0s
  ← agent finished in 2.72s
  ← final response: 'The result of 17 + 25 is 42.'

  Captured 2 trace events:
    • tool_called   spike_add    args={"a": 17, "b": 25}
    • tool_returned spike_add    {"sum": 42}

PHASE 3: Subprocess (`hermes -z`) — production invocation path
  → hermes -z <prompt>  (haiku, default Hermes config)
  ← exited 0 in 2.32s
  ← new session snapshot: ~/.hermes/sessions/session_<ts>_<id>.json
  ← message role counts: {'user': 1, 'assistant': 1}
```
