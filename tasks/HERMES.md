# Hermes Integration

We are using **[hermes-agent](https://github.com/nousresearch/hermes-agent)** from Nous Research as the agent runtime. This document is the integration spec — read it before working on Track A.

---

## What Hermes provides (so we don't build it)

| Capability | Hermes ✓ | Notes |
|------------|----------|-------|
| Agent planner loop | ✓ | Native; we register skills, Hermes plans tool sequencing |
| Tool / skill registry | ✓ | Skills are Python modules with declared input/output |
| Skill creation & self-improvement | ✓ | Hermes can author new skills mid-run |
| Long-term memory + cross-session recall | ✓ | Built-in; we don't need a separate memory layer |
| Cron / scheduling | ✓ | Useful for nightly opportunity refresh (post-MVP) |
| Multi-channel gateway (Slack, Discord, Telegram, etc.) | ✓ | Not used for hackathon demo, but free |
| Model agnosticism (Claude, OpenRouter, OpenAI, local) | ✓ | Switch via `hermes model` command — no code changes |
| Multiple execution backends (local, Docker, SSH, Modal, Vercel Sandbox) | ✓ | We default to local on VX1 |

## What we still build

| Layer | Owner | Notes |
|-------|-------|-------|
| Domain skills (the 9 from CONTRACTS.md §5) | Track A | Implemented as Hermes skills |
| FastAPI proxy: `/agent-runs`, `/healthz`, `/agent-runs/:id/stream` | Track A | Frontend can't talk to Hermes CLI directly |
| Postgres for domain data | Track A | Opportunities, requirements, scores, packages — separate from Hermes memory |
| Trace-event bridge (Hermes trace → our SSE events per CONTRACTS.md §3) | Track A | The translation layer that keeps the frontend contract stable |
| Frontend, fixtures, demo | Track B | **Unchanged** |
| Eval harness | Track A | Calls skills directly OR drives Hermes runs |

---

## Architecture

```
┌──────────────┐    HTTP        ┌──────────────────┐
│  Next.js     │ ─────────────▶ │  FastAPI proxy   │
│  /web        │                │  /api            │
└──────────────┘ ◀───── SSE ────└──────────────────┘
                                         │
                                         │ subprocess / RPC
                                         ▼
                                ┌──────────────────┐
                                │  Hermes Agent    │
                                │  - planner       │
                                │  - skills (ours) │
                                │  - memory        │
                                └──────────────────┘
                                         │
                       ┌─────────────────┼─────────────────┐
                       ▼                 ▼                 ▼
                ┌────────────┐    ┌────────────┐    ┌────────────┐
                │ LLM (Claude)│    │ Postgres   │    │ Local FS   │
                │ via Hermes  │    │ (domain)   │    │ /fixtures  │
                └────────────┘    └────────────┘    └────────────┘
```

Hermes is the agent core. FastAPI is the public web-facing surface. Postgres holds domain data (opportunities, profiles, scores, packages). The frontend never talks to Hermes directly.

---

## Installation (P0.1 addendum)

Add to the bootstrap / Phase 0 setup:

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes model    # configure model — set to claude-sonnet-4-6 by default
```

Hermes requires Python 3.11+ and `uv`. Both are available on Ubuntu 24.04 LTS.

For Docker-compose dev, run Hermes inside the `api` container or as a sidecar. Either way, Hermes is invoked from FastAPI as a subprocess or via Hermes' RPC interface (depending on what's stable in the version we ship).

---

## Skills we register

Each domain skill is a Python module under `/api/skills/<skill_name>/` with:

```
/api/skills/extract_requirements/
├── skill.md              # Hermes skill definition (description, inputs, outputs)
├── implementation.py     # the actual Python function
└── examples/             # optional: example invocations for Hermes' planner
```

Skill registration manifest:

| Skill | Replaces task | Notes |
|-------|---------------|-------|
| `parse_pdf` | A4 | pure-Python pypdf |
| `extract_requirements` | A5 | LLM call inside the skill |
| `score_fit` | A6 | deterministic math + LLM rationale; §11.1 enforced inside skill |
| `detect_risks` | A7 | LLM call |
| `generate_action_package` | A8 | LLM call (Sonnet) |
| `search_sam` | A11 | live API + cache |
| `load_seeded_opportunities` | A11 | reads `/fixtures/` |
| `fetch_attachment` | A10 (OpenClaw replacement) | Hermes has built-in HTTP/browser tools — leverage those rather than re-implementing |
| `verify_source_page` | A10 (OpenClaw replacement) | Use Hermes' browser tool |

**OpenClaw is dropped from the stack.** Hermes covers the same surface. PRD §7.3 needs a v1.2.2 update reflecting this.

---

## Trace event bridge

The frontend's Timeline (B5) consumes our SSE event types from CONTRACTS.md §3. Hermes has its own trace format. We need a **bridge**:

```python
# /api/agent/hermes_bridge.py

async def run_with_trace(run_id: UUID, profile: CompanyProfile, goal: str) -> None:
    """Kick off a Hermes run and translate its trace to our SSE events."""
    await emit_event("run_started", run_id, goal=goal, profile_id=profile.id)

    async for hermes_event in hermes_client.run(
        instructions=build_planner_instructions(profile, goal),
        skills=ALLOWED_SKILLS,
        budget=Budget.from_settings(),
    ):
        ours = translate(hermes_event)
        if ours is not None:
            await emit_event(ours.type, run_id, **ours.payload)

    await emit_event("run_completed", run_id, status="complete", summary=build_summary(...))


def translate(hermes_event) -> OurEvent | None:
    """Map Hermes' trace primitives to CONTRACTS.md §3 events."""
    match hermes_event.kind:
        case "step_start": return OurEvent("step_started", {...})
        case "tool_call":  return OurEvent("tool_called", {...})
        case "tool_result": return OurEvent("tool_returned", {...})
        case "step_end":   return OurEvent("step_completed", {...})
        case _:            return None  # filter Hermes-internal events
```

The translation layer is THE critical piece. Without it, the frontend doesn't render. With it, the frontend never knows Hermes exists.

---

## §11.1 enforcement under Hermes

Hermes' planner is general-purpose; it doesn't know about our eligibility rule. Enforcement remains:

1. **Inside the `score_fit` skill** — the deterministic short-circuit (A6) runs before the rubric math. Hermes calling `score_fit` gets back `decision=reject` for hard blockers regardless of capability.
2. **Inside the `generate_action_package` skill** — the slimmed reject package is returned deterministically (A8 split).
3. **In the planner instructions** — we tell Hermes' planner: "if `score_fit` returns `decision=reject`, do NOT call `generate_action_package` for an action plan; call it for the reject summary."
4. **In the eval harness (A12)** — the assertion that capability strengths cannot override the reject fixture's eligibility blocker.

Belt + suspenders + parachute.

---

## Budget control

Hermes has its own concept of execution budgets. Map our PRD §4.5 budgets:

| Ours | Hermes |
|------|--------|
| `RUN_BUDGET_STEPS=40` | `--max-steps` or equivalent |
| `RUN_BUDGET_SECONDS=360` | `--timeout-seconds` |
| `RUN_BUDGET_USD=0.50` | tracked by us in the bridge — sum `cost_usd` from skill returns; abort the run if exceeded |

Cost tracking is ours because Hermes is model-agnostic; the per-token rates live in `/api/agent/llm.py`'s pricing table.

---

## Updated tasks (Dev 1)

The Dev 1 task list shifts. Update `dev1-backend/README.md` with this revised order:

| # | Task | Status | Notes |
|---|------|--------|-------|
| A1 | FastAPI skeleton + docker-compose + Hermes install | Same | Add Hermes to the `api` container or sidecar |
| A2 | DB schema + migrations | Same | Domain tables only; Hermes manages its own memory |
| A3 | CRUD endpoints + SSE proxy | Same | SSE proxies the Hermes trace bridge |
| A4 | `parse_pdf` skill | Slight rename: skill not tool |
| A5 | `extract_requirements` skill | Same logic, packaged as Hermes skill |
| A6 | `score_fit` skill (with §11.1 enforcement) | Same |
| A7 | `detect_risks` skill | Same |
| A8 | `generate_action_package` skill | Same |
| ~~A9~~ | ~~Bespoke planner loop~~ | **Replaced** | Use Hermes |
| **A9'** | **Hermes integration: planner instructions, skill registration, trace bridge** | New | Critical path |
| ~~A10~~ | ~~OpenClaw bridge~~ | **Dropped** | Hermes covers it |
| A11 | `search_sam` + `load_seeded` skills | Same |
| A12 | Eval harness | Same |
| A13 | VX1 deploy | Same | Plus Hermes runtime install in bootstrap.sh |

Net change: **A10 is dropped** (saves us a substantial integration), **A9 is reframed** as a Hermes integration task instead of a bespoke planner. Track A surface area shrinks.

---

## What to do right now

1. Both devs read this file before next sync.
2. Track A: pause A9 / A10 work; revise tasks per above.
3. Update the PRD with a v1.2.2 changelog entry (next section in this doc covers what to write).
4. Update `dev1-backend/tasks/A9.md` and remove `A10.md`.
5. Add `dev1-backend/tasks/A9-hermes.md` for the integration spec.
6. Bridge translation table (`translate()` above) — pin this once we read Hermes' actual trace format. Add to `CONTRACTS.md §3.1`.

---

## PRD changelog entry to add (v1.2.1 → v1.2.2)

```
> **Changelog v1.2.1 → v1.2.2**
> - Adopted hermes-agent (Nous Research) as the agent runtime. Hermes provides planner loop, tool registry, memory, and multi-backend execution. We register domain skills (parse_pdf, extract_requirements, score_fit, detect_risks, generate_action_package, search_sam, load_seeded) within Hermes; FastAPI becomes a thin proxy with a trace-event bridge to preserve CONTRACTS.md §3 SSE shape for the frontend.
> - §7.3 updated: OpenClaw is dropped. Hermes covers browser-bound tools and skill execution.
> - §4.5 updated: planner architecture now references Hermes' built-in loop; our additions are domain skills, the §11.1 enforcement inside score_fit, and the trace bridge.
> - Models remain configurable; default Claude Sonnet 4.6 (synthesis) + Haiku 4.5 (cheap passes) via Hermes' model-agnostic config (`hermes model`).
> - See `tasks/HERMES.md` for full integration spec.
```

---

## Open questions

These need resolution during P0 update or first Hermes-integration spike:

1. **Hermes API surface for programmatic invocation.** Is there a stable Python SDK or RPC, or do we shell out to the `hermes` CLI? This affects the FastAPI bridge implementation.
2. **Hermes trace format.** What event types does Hermes emit during a run? We need to map every kind we care about.
3. **Hermes skill schemas.** Does Hermes enforce skill input/output schemas, or does each skill do its own Pydantic validation? Affects A4–A8 implementation.
4. **Hermes execution backend on VX1.** Local subprocess is simplest. Docker backend is cleanest. Pick one for A13.
5. **Hermes memory + our Postgres.** Hermes has its own memory layer. Our Postgres holds domain data. Confirm there's no double-storage of, e.g., extracted requirements.
6. **Cost tracking.** Hermes is model-agnostic — does it surface per-call token counts so our budget tracker works? If not, we wrap LLM calls inside skills and track ourselves.

These are P0 follow-ups, logged in `STANDUP.md` after the update. Don't block other work on them.
