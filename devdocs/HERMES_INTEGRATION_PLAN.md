# Hermes Integration & Launch-Ready Plan

> Dated **2026-05-09**. Owns the path from "seeded simulation today" to
> "real Hermes-driven Michaela bench in production" — plus the supporting
> work (UI, eval, deploy) needed for an actual launch. Reads top-to-bottom;
> phases sequence by dependency.

---

## TL;DR

Today the system stores rows correctly, auths users, and produces a
deterministic seeded Michaela run that emits the right SSE shape — but
**Hermes is not actually invoked**, no LLM is called during a run, and our
project's `.hermes/` config has the wrong schema and isn't loaded by Hermes
anyway. Closing that gap and getting to a launch-ready product takes
~14–25 days of solo work across 9 phases. Phases 0–1 are non-blocking
truth-in-advertising fixes that can ship today; Phases 2–5 are the real
Hermes wiring; Phases 6–9 are the supporting work for an actual launch.

---

## Decisions you need to confirm before Phase 2 starts

These are technical defaults baked into the plan below. Each has a
recommendation; tell me to switch and I'll re-thread.

| # | Decision | Recommendation | Why |
|---|----------|----------------|-----|
| **D1** | Hermes provider route | **Anthropic direct** (`provider: anthropic`, `default: claude-sonnet-4-6`, `api_key_env: ANTHROPIC_API_KEY`) | Direct route gives fewer moving parts, clearer 401 debugging, and lets FastAPI skills and Hermes workers share one credential source. OpenRouter remains a future routing option, not the project architecture. |
| **D2** | Hermes home strategy | **`HERMES_HOME=$(pwd)/.hermes` per-project (isolated)** | Does not clobber or depend on an existing personal/global `~/.hermes/` setup. Each project gets deterministic config, skills, memory, and credentials. Trivial to set in Makefile/systemd. |
| **D3** | Bench rollout order | **All 7 agents at once** with the toolset-restriction architecture as designed | Half-rolled-out delegation chains are buggier than fully-rolled-out ones (unclear "did Roy get called?" failures). The §11.1 enforcement chain wants all 5 layers in place. |
| **D4** | Seeded path retention | **Keep under `DEMO_REPLAY_TRACE=true` flag for offline demos** | Cheap insurance for stage demos with shaky wifi or expired API keys. Default off in dev; flippable for live presentations. |
| **D5** | Scope of "everything" | **Full** — Hermes wiring + UI + eval harness + VX1 deploy | "Launch-ready" means a real human can sign up via /web, hit start, and get a real action package. Anything less is a private build. |

If any of these need to change, the phase sequence may shift but the total
runway stays similar.

---

## Phase 0 — Truth in advertising (1–2 hours, ships today)

### Goal

Stop overclaiming in docs and fix the schema-broken `.hermes/config.yaml`
so any human (or future AI session) reading the repo knows what's
actually wired vs. planned.

### Files touched

- `/.hermes/config.yaml` — drop invented keys (`models:`, `providers:`,
  `telemetry:`, `memory.cross_session`); replace with valid Hermes schema:
  `model:` block, real `memory:` keys.
- `tasks/AGENT_ARCHITECTURE.md` — replace "Hermes is wired" with "seeded
  bridge ships today; live Hermes integration is the next milestone (see
  HERMES_INTEGRATION_PLAN.md)."
- `HERMES.md` (root) — same truth correction.
- `devdocs/CURRENT_STATE.md` — update §2 ("The seven agents") to
  distinguish wired-as-data-shape from wired-as-LLM-runtime.
- `PRD.md` — small clarification line in v1.2.4 changelog footnote.

### Deliverable

A repo where every doc accurately describes what's running. Future
sessions don't get misled.

### Verify

- `grep -r "Hermes is wired" docs/` → 0 hits (replaced with accurate phrasing).
- `cat .hermes/config.yaml` validates against Hermes' config schema (no
  unrecognized top-level keys).

### Risk

None. Doc-only + one small config edit.

---

## Phase 1 — Make our project's `.hermes/` actually loadable (1–2 hours)

### Goal

Get Hermes to read OUR project's config + skills + SOUL, without
clobbering the user's existing `~/.hermes/` setup. Decision D2 says
HERMES_HOME isolation.

### Files touched

- `Makefile` — add a `hermes` target that runs Hermes with
  `HERMES_HOME=$(pwd)/.hermes`:
  ```make
  hermes: ## Run Hermes against this project's config (HERMES_HOME isolated)
  	@HERMES_HOME=$$(pwd)/.hermes hermes
  ```
- `infra/systemd/govcapture-api.service` — add `Environment=HERMES_HOME=/opt/govcapture/.hermes` so prod Hermes uses the project config too.
- `.hermes/config.yaml` (already fixed in Phase 0).
- New file: `.hermes/.env.example` — template for the `ANTHROPIC_API_KEY`
  variable used by the project-isolated Hermes home.
- `.gitignore` — add `.hermes/.env` (gitignored), keep
  `.hermes/.env.example` (committed).
- `README.md` (or top of `HERMES.md`) — quickstart paragraph: how to copy
  `.hermes/.env.example` to `.hermes/.env` and fill in the key.

### Deliverable

`make hermes` opens a Hermes REPL that loads our project's config, our
SOUL.md, and discovers our SKILL.md files (still 0 toolsets registered at
this point — that's Phase 2 — so the skills are visible but their tools
aren't callable).

### Verify

- `make hermes` then `/skills` lists `operate_bid_desk`, `discover_opportunities`,
  `score_fit_with_eligibility_check`, etc.
- `hermes config show` (with `HERMES_HOME` exported) shows our `model:` and
  `delegation:` config, not the user's default.
- `~/.hermes/config.yaml` is **untouched**.

### Risk

Low. If HERMES_HOME isolation has rough edges (Hermes assumes some files
relative to its install), we fall back to symlinking just the files we
need.

---

## Phase 2 — Build the Hermes plugin: register the 6 toolsets (2–3 days)

### Goal

Make Hermes able to actually call our domain skills. This is the biggest
single piece of new code.

### Files created

```
hermes_plugin_govcapture/                    ← NEW top-level Python package
├── __init__.py                              ← exports register()
├── pyproject.toml                           ← entry_point: hermes.plugins
├── plugin.py                                ← register(ctx) — wires all 6 toolsets
├── adapters/                                ← thin wrappers that adapt
│   ├── __init__.py                          ←   our api/skills/*.py funcs
│   ├── gov_discovery.py                     ←   to Hermes' tool-handler
│   ├── gov_documents.py                     ←   contract:
│   ├── gov_compliance.py                    ←     handler(args, **kw) -> JSON str
│   ├── gov_intel.py                         ←   each adapter:
│   │                                            1. parse args dict → skill input
│   ├── gov_proposals.py                     ←     2. call skill func (async)
│   └── human_review.py                      ←     3. JSON-stringify output
└── tests/
    └── test_register.py                     ← smoke: all 11 tools registered
```

### Toolset → tool map (matches AGENT_ARCHITECTURE.md exactly)

| Toolset | Tools | Granted to (per agent) | Backed by |
|---------|-------|------------------------|-----------|
| `gov_discovery_meta` | `parse_goal`, `summarize_run`, `request_human_review` | Michaela | api/skills/parse_goal/, inline LLM, api/skills/request_human_review/ |
| `gov_discovery` | `search_sam`, `load_seeded_opportunities` | Scot | api/skills/search_sam/, api/skills/load_seeded_opportunities/ |
| `gov_fit` | `rank_opportunities`, `score_fit` | Lenny | api/skills/rank_opportunities/, api/skills/score_fit/ |
| `gov_compliance` | `extract_requirements`, `score_fit`, `detect_risks` | Gabby | api/skills/extract_requirements/, score_fit/, detect_risks/ |
| `gov_intel` | `query_usaspending` (NEW skill, planned) | Lance | NEW api/skills/query_usaspending/skill.py |
| `gov_documents` | `parse_pdf`, `fetch_attachment`, `verify_source_page` | Happer | api/skills/parse_pdf/, fetch_attachment/, NEW verify_source_page/ |
| `gov_proposals` | `generate_action_package` | Roy | api/skills/generate_action_package/ |

### New skills we need to write

- `api/skills/query_usaspending/skill.py` — Lance's competitive intel.
  Hits USASpending API, returns incumbent + prior awards + win difficulty.
- `api/skills/verify_source_page/skill.py` — Happer's source-citation
  verifier. Confirms a quoted snippet appears on the cited page.
- `api/skills/request_human_review/skill.py` — escalation gate. Returns a
  question + context payload; doesn't actually pause the run (the real
  pause happens at the bridge layer).
- `api/skills/summarize_run/skill.py` — Michaela's final synthesis.
  Sonnet call with all bench outputs as context.

### Adapter pattern (sample for `extract_requirements`)

```python
# hermes_plugin_govcapture/adapters/gov_compliance.py
import json
from api.skills.extract_requirements import (
    ExtractInput, extract_requirements,
)

EXTRACT_REQUIREMENTS_SCHEMA = {
    "name": "extract_requirements",
    "description": "Read parsed solicitation chunks and produce structured §10.1 requirements.",
    "parameters": {
        "type": "object",
        "properties": {
            "doc_id":               {"type": "string"},
            "parsed":               {"type": "object"},
            "opportunity_metadata": {"type": "object"},
        },
        "required": ["parsed"],
    },
}

async def _handle_extract(args, **kw):
    payload = ExtractInput.model_validate(args)
    result, metrics = await extract_requirements(payload)
    return json.dumps({
        "success": True,
        "data": result.model_dump(),
        "metrics": metrics.model_dump(),
    })

def register_gov_compliance(ctx):
    ctx.register_tool(
        name="extract_requirements",
        toolset="gov_compliance",
        schema=EXTRACT_REQUIREMENTS_SCHEMA,
        handler=lambda args, **kw: _handle_extract(args, **kw),
        is_async=True,
        description="Extract §10.1 requirements with evidence binding.",
        emoji="📋",
        check_fn=lambda: bool(os.getenv("ANTHROPIC_API_KEY")),
        requires_env=["ANTHROPIC_API_KEY"],
    )
    # ... score_fit and detect_risks similarly
```

### Install / discovery

Two install modes; we'll support both:

1. **Local dev** — `pip install -e ./hermes_plugin_govcapture` from the repo
   root. Hermes auto-discovers it via `entry_points` (see Hermes plugin docs:
   `[project.entry-points."hermes.plugins"]`).
2. **VX1 prod** — same `uv pip install -e` invocation in the deploy script.

### Deliverable

`make hermes` REPL → `/skills` shows all 11 tools across the 6 toolsets.
Calling any tool from the REPL (e.g. `parse_goal({"goal": "cyber TX"})`)
exercises the real api/skills/ Python.

### Verify

- `pytest hermes_plugin_govcapture/tests/test_register.py` — confirms
  `register(ctx)` produces 11 tool registrations across 6 toolsets.
- Manual: `make hermes`, then in REPL: `/tools` shows the inventory.
- All 4 fixtures' parse_pdf+extract_requirements smoke runs through the
  registered handlers (not direct Python imports).

### Risk

**Medium-high.** Bridging async Python skills to Hermes' tool-handler
contract has surface area: error propagation, JSON shape, large-payload
handling (parse_pdf returns chunks of text), tool timeout behavior. Plan
3 days; budget 2 extra for surprises.

---

## Phase 3 — Real Hermes invocation in `hermes_runner.py` (1–2 days)

### Goal

Replace the seeded bridge's deterministic Python with actual Hermes
invocation. `POST /agent-runs` should produce a real Michaela run.

### Approach

Hermes is OpenAI-SDK-based and exposes a CLI + chat protocol. Two
realistic invocation modes:

#### Mode A: subprocess + JSON trace (recommended for v1)

```python
# api/agent/hermes_runner.py — rewritten
import asyncio, json, uuid

async def run_michaela(*, redis, client, run_id):
    if settings.demo_replay_trace:                  # safety-net path
        from api.agent.hermes_bridge import run_seeded_michaela_capture
        await run_seeded_michaela_capture(redis=redis, client=client, run_id=run_id)
        return

    # Real Hermes path
    run = await AgentRunRepository(client).get(run_id)
    proc = await asyncio.create_subprocess_exec(
        "hermes", "chat",
        "--skill", "operate_bid_desk",
        "--input", json.dumps({
            "goal": run["goal"],
            "company_profile_id": run["company_profile_id"],
            "run_id": str(run_id),
            "internal_api_key": settings.internal_api_key,
        }),
        "--json-trace",                              # one JSON event per stdout line
        env={**os.environ, "HERMES_HOME": settings.hermes_home},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async for line in proc.stdout:                   # real-time event stream
        event = json.loads(line)
        translated = translate_hermes_event(event)
        await redis.publish(f"agent-run:{run_id}",
                            json.dumps(translated))

    rc = await proc.wait()
    # handle exit code, mark_completed, etc.
```

#### Mode B: Python SDK (if Hermes exposes one stable enough)

We need to verify via Context7 / hermes README whether `hermes-agent` ships
a programmatic Python API. If yes, this is cleaner (no subprocess pipe
parsing). If no, Mode A is what ships.

### Files touched

- `api/agent/hermes_runner.py` — full rewrite (per above)
- `api/agent/hermes_bridge.py` — kept as the seeded fallback (renamed
  `seeded_bridge.py` to make intent clear; current `hermes_bridge.py`
  becomes `trace_translator.py` for Mode A's `translate_hermes_event`).
- `api/routes/agent_runs.py` — `_kick_off_run` now always calls the new
  `run_michaela`; the `demo_replay_trace` decision moves into runner.

### Deliverable

`POST /agent-runs` against a real Supabase + with `ANTHROPIC_API_KEY` set
produces a run that calls actual Claude (visible as latency + cost in
SSE events) and writes real (not seeded) requirements/scores/risks/packages.

### Verify

- `curl -X POST /agent-runs` with `DEMO_REPLAY_TRACE=false`, watch
  `/agent-runs/{id}/stream` — events show non-zero `cost_usd` and
  `latency_ms` from real Claude calls.
- Database has `extracted_requirements` rows with real evidence_snippets
  pulled from the fixture PDFs.
- Toggling `DEMO_REPLAY_TRACE=true` falls back to seeded path with no
  Claude calls — for offline demos.

### Risk

**Medium.** Subprocess lifecycle (timeout, kill on cancel, stderr
capture), trace event format may differ from docs, cold-start latency on
Hermes invocation might be noticeable. Plan 1.5 days; budget 0.5 buffer.

---

## Phase 4 — Real trace bridge: Hermes events → CONTRACTS.md §3 SSE (1 day)

### Goal

Hermes emits its own trace events; the frontend timeline (B5) expects
CONTRACTS.md §3 shapes. Translate in real time.

### Files touched

- `api/agent/trace_translator.py` (NEW, ~200 LOC) —
  `translate_hermes_event(raw: dict) -> dict | None` returns a
  CONTRACTS.md §3 event or None to drop.

### Mapping table (drafted; refine when we see real Hermes output)

| Hermes event | Our SSE event | Notes |
|--------------|---------------|-------|
| `run_started` (root) | `run_started` | Pass through with `run_id`, `goal` |
| `subagent_spawn` | `subagent_spawned` | Add `parent_id`, `agent_name` (from delegate_task goal text) |
| `subagent_complete` | `subagent_completed` | Pass through |
| `tool_call_start` | `tool_called` | Map `tool_name`, `parameters` → `tool`, `input` |
| `tool_call_end` | `tool_returned` | Map `result`, `latency_ms`, `cost_usd` |
| `planner_thought` | (drop or surface as `step_started`) | Decide based on demo readability |
| `budget_exceeded` | `run_completed` (status=failed) | Cap reached; emit final summary |
| `run_complete` | `run_completed` | Pass through |
| (Hermes-internal noise) | None | Filter out to keep timeline readable |

### Deliverable

The frontend's timeline UI sees the same event contract whether the run
came from the seeded bridge or real Hermes. No frontend changes needed.

### Verify

- Run a real Hermes run; `tee` the SSE stream to a file; verify every
  event validates against `schemas/trace-event.schema.json`.
- Run a seeded run; verify identical event shape.
- Frontend timeline renders both runs identically modulo content.

### Risk

Low–medium. Once we know Hermes' event format, this is mechanical.

---

## Phase 5 — End-to-end smoke against the 4 fixtures (4–8 hours)

### Goal

Prove the full chain works against every fixture. **This is the §11.1
enforcement test.**

### Files touched

- `eval/runner/run_fixture.py` (NEW) — seeds a profile + opportunity
  from a fixture, posts /agent-runs, waits for SSE `run_completed`, asserts.
- `eval/goldens/<slug>.json` (NEW, 4 files) — expected decision band,
  expected blockers, expected approval-gate items.

### Fixture-by-fixture assertions

| Fixture | Assertion |
|---------|-----------|
| `strong-pursue` | `decision == "strong_pursue"`, `total_score >= 80`, action_package has full mode (timeline, checklist, outreach_draft) |
| `maybe` | `decision == "maybe"`, partner_suggestions present, missing_information non-empty |
| `reject` | **`decision == "reject"`** AND **`fit_score.breakdown.capability >= 15`** (proves the §11.1 deterministic short-circuit fires regardless of capability strength) |
| `adversarial-image-pdf` | run completes (no crash), at least one `extracted_requirements` row has `confidence == "low"` (no fabricated evidence from image-only PDF) |

### Deliverable

`make eval` runs all 4 fixtures end-to-end against a real Supabase + real
Claude, asserts goldens, exits 0 if all pass.

### Verify

- All 4 assertions pass on first run against `main`.
- Each run cost recorded; budget checks <= $0.50/run, <= $2.00 total.
- §11.1 assertion reproducibly passes — re-run 3× to confirm
  determinism (the reject path's deterministic short-circuit must be
  100% reliable).

### Risk

Medium. Real Claude responses have variance; the goldens may need
tolerances rather than exact match. The reject assertion is the only
hard gate (deterministic).

---

## Phase 6 — Doc rewrite, accurate this time (2–4 hours)

### Goal

Bring every doc into alignment with what's actually shipping post-
Phase 5.

### Files touched

- `tasks/AGENT_ARCHITECTURE.md` — rewrite "How a run flows" with the
  real Hermes invocation path. Keep toolset map.
- `HERMES.md` (root) — accurate runtime wiring section.
- `devdocs/CURRENT_STATE.md` — bump architecture diagram, status table.
- `tasks/CONTRACTS.md §3` — finalize trace-event taxonomy with the
  agreed Hermes mappings.
- `infra/RUNBOOK.md` — add the `HERMES_HOME` env line and the
  `pip install -e ./hermes_plugin_govcapture` deploy step.
- `PRD.md` — v1.2.5 changelog entry: "Hermes wired live; seeded path
  retained behind DEMO_REPLAY_TRACE flag."
- DELETE: `devdocs/HERMES_INTEGRATION_PLAN.md` (this file) — its job is
  done at this point. Or keep as historical record under
  `devdocs/_history/`.

### Deliverable

Anyone reading the repo understands the architecture matches the code.
No more aspirational claims.

### Verify

- `grep -r "is wired" docs/ tasks/` — every hit is true post-Phase 5.
- Architecture diagram in CURRENT_STATE.md matches `api/agent/` files.

### Risk

None.

---

## Phase 7 — Eval harness as a real harness (1–2 days)

### Goal

Phase 5 wrote one-shot fixtures; Phase 7 makes it CI-grade.

### Files touched

- `eval/runner/` — full structure with config, parallel runs, golden
  diffs, regression detection.
- `eval/goldens/` — expanded with sub-assertions per skill.
- `Makefile` — `make eval` target, `make eval-fast` for haiku-only mode.
- `.github/workflows/eval.yml` (NEW, optional) — runs eval on PR.
- `eval/README.md` — how to add a fixture, how to update goldens.

### Deliverable

`make eval` is part of pre-merge gates. New PRs that break a fixture get
flagged before merge.

### Verify

- `make eval` exits 0 on `main`.
- Intentionally break a skill prompt → eval flags the regression.
- Cost report at end shows total spend per run.

### Risk

Low. Mechanical extension of Phase 5.

---

## Phase 8 — `/web` product UI (3–5 days)

### Goal

A real human can sign up, create a profile, start a run, watch the
timeline, and read the action package — without curl.

### Files touched / created

- `web/src/app/(auth)/login/page.tsx` — Supabase Auth login
- `web/src/app/(auth)/signup/page.tsx` — sign up
- `web/src/app/(app)/profile/page.tsx` — company profile form
- `web/src/app/(app)/runs/page.tsx` — list of runs
- `web/src/app/(app)/runs/[id]/page.tsx` — run detail with live SSE
  timeline
- `web/src/app/(app)/runs/[id]/package/page.tsx` — action package viewer
- `web/src/components/RunTimeline.tsx` — consumes SSE
- `web/src/lib/api.ts` — typed API client (uses zod from
  `web/lib/schemas/`)
- `web/src/lib/supabase/client.ts` — Supabase JS client
- `web/middleware.ts` — JWT-protect (app) routes (parallel track has
  this in flight)

### Deliverable

A single-user-friendly path from signup → profile → run → action package.

### Verify

- Manual end-to-end: sign up → profile → run → see timeline render →
  read package → approve.
- All 4 fixtures runnable from the UI.
- Loom recording of a complete run for the demo backup.

### Risk

Medium. The parallel track has been adding pieces (`web/src/middleware.ts`,
`web/src/lib/`, `web/src/app/{login,auth,app}/`); merging that work
cleanly + filling the rest is the bulk.

---

## Phase 9 — VX1 deploy (4–8 hours)

### Goal

Production URL works. The demo can be shown from a public IP, not localhost.

### Files touched

- `infra/bootstrap.sh` — verify still works after Hermes plugin add
- `infra/deploy.sh` — add `pip install -e ./hermes_plugin_govcapture`
- `infra/systemd/govcapture-api.service` — `Environment=HERMES_HOME=/opt/govcapture/.hermes`
- `infra/RUNBOOK.md` — final deploy steps with all the new env vars
- DNS + TLS — point domain at VX1, certbot cert
- Supabase `cors_allowed_origins` — add prod domain

### Deliverable

`https://api.govcapture.example/healthz` → 200.
`https://app.govcapture.example/` → product loads.
Real run from prod URL works.

### Verify

- `curl https://api.govcapture.example/healthz` → 200
- Run a fixture from the production frontend, see real Claude response
- Loom backup recorded for demo

### Risk

Low. We did most of the work in `infra/bootstrap.sh` already.

---

## Total runway

| Path | Days |
|------|------|
| Solo, sequential | 14–25 days |
| Solo, parallelized (Phase 8 in parallel with Phases 5–7) | 11–17 days |
| Critical path to "live demo" (skip 7 + 9, demo from localhost) | 8–12 days |
| **Bare minimum to "Hermes really runs Michaela"** (Phases 0–5) | **5–8 days** |

---

## Verification gates (objective checkpoints between phases)

| After Phase | Gabby |
|-------------|------|
| 0 | `grep -r "Hermes is wired" docs/ tasks/` returns 0 hits |
| 1 | `make hermes` opens REPL with `/skills` showing our SKILL.md files |
| 2 | `pytest hermes_plugin_govcapture/tests/` passes; `/tools` lists 11 tools |
| 3 | `POST /agent-runs` triggers a real Claude call (visible in cost in SSE) |
| 4 | Frontend timeline renders identical shape from seeded vs. real run |
| 5 | `make eval` passes all 4 fixtures, including §11.1 reject assertion |
| 6 | Docs match code |
| 7 | `make eval` is in CI/gates new PRs |
| 8 | Manual signup → run → package flow works |
| 9 | `curl https://<prod>/healthz` returns 200 |

---

## Risk register

1. **Hermes plugin contract is harder than docs suggest.** Plan: timebox
   Phase 2 to 4 days max; if blocked, fall back to Mode B (Python SDK)
   or extend the seeded bridge with selective live skill calls (hybrid).
2. **`hermes chat --json-trace` flag may not exist as imagined.** Plan:
   verify in Phase 0 by reading Hermes CLI help + Context7 docs; fall
   back to alternative invocation if absent.
3. **§11.1 deterministic short-circuit might not survive real LLM
   variability.** Plan: the short-circuit lives in PYTHON inside
   `score_fit`, fires before the LLM call. As long as we hit
   `score_fit` (not let Hermes free-form), it's deterministic. If
   Hermes' planner ever bypasses score_fit, that's an architecture
   bug — fix immediately.
4. **Cost overrun on first eval run.** Plan: cap runs to Haiku via
   `LLM_DEV_MODEL` for initial eval; only use Sonnet on tagged demo
   runs. Add `RUN_BUDGET_USD=0.50` enforcement at the bridge level.
5. **The parallel track keeps editing files Phase 2/3 will rewrite.**
   Plan: announce the wiring work; for the duration of Phases 2–5,
   freeze concurrent edits in `api/agent/`, `api/skills/`, and the new
   `hermes_plugin_govcapture/` directory.

---

## Recommended execution order (assuming all decisions confirmed as defaults)

```
Day 1     : Phase 0 + Phase 1                        ← safe, ships truth
Days 2–4  : Phase 2 — plugin + adapters              ← biggest risk
Days 5–6  : Phase 3 — real Hermes invocation
Day 7     : Phase 4 — trace bridge
Day 8     : Phase 5 — fixture eval (the §11.1 gate)
Day 9     : Phase 6 — final doc rewrite
Days 10–11: Phase 7 — eval harness for CI
Days 11–14: Phase 8 — /web UI (parallelizable from Day 9)
Day 15    : Phase 9 — VX1 deploy
```

If Phases 2 or 3 hit a wall, the seeded bridge keeps the demo flow
working — we can ship a "limited but real" version for hackathon judging
while Hermes integration matures.
