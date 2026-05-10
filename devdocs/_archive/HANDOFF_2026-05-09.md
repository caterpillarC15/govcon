# GovCon Bid Desk capability pack — comprehensive handoff prompt

> **Read top to bottom before doing anything.** This single file is
> designed to be pasted into a fresh Claude Code, Codex, or comparable
> agent session running against `/Volumes/CS_Stuff/govcon`. It contains
> the corrected architecture, the current state, decisions already made,
> the doc-rewrite plan, conventions, verification gates, and the explicit
> task. After reading, the receiving agent should be able to execute
> without re-asking the human dozens of clarifying questions.

---

## 0. Who you are and what you're being asked to do

You are an engineer continuing the **GovCon Bid Desk Operator capability
pack**. The previous session (where this handoff was written) confirmed
the architecture below, identified what's misaligned in the repo, and
left an actionable doc-rewrite + light code-surgery plan.

Your job in this session:

1. **Read the entire handoff before touching anything.**
2. **Confirm the architecture is still correct** by spot-checking a few
   files from the "current state" section — don't trust this doc blindly,
   the repo is the source of truth.
3. **Execute the doc-rewrite plan** (Section 8) phase by phase.
4. **Surgically remove the orchestration code that doesn't belong** in
   this repo (Section 9).
5. **Verify every gate** in Section 11 before declaring a phase done.
6. **Stop and ask the human** when you hit any of the "ask first"
   triggers in Section 12.

Estimated effort: **1–2 days** for a competent solo session. The
prerequisites are already in place (Supabase linked, schema applied,
auth wired, env file gitignored).

---

## 1. The layered architecture (do not get this wrong)

There are **four layers** in this product. Conflating them was the source
of nearly every misunderstanding in the previous session.

```
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER — Michaela (TypeScript / Bun)                     │
│ Repo:    /root/michealaai                                            │
│ Stack:   Bun + TypeScript                                            │
│ Tests:   bun test tests/*.test.ts                                    │
│ Core:    src/workloop/{types, agentPool, defaultAgents, taskQueue,  │
│                          openLoopStore, surfacing, workLoop}.ts     │
│ Docs:    docs/WORKLOOP.md, agent-bootstrap/{README,DIRECTIVES,      │
│                                              TOOLS}.md              │
│                                                                       │
│ What it does:                                                         │
│   - Captures open loops from conversation                             │
│   - Queues microtasks                                                 │
│   - Assigns to named workers by capability                            │
│   - Stores results, decides resurfacing                               │
│   - In-memory MVP today; Supabase tables planned                      │
│                                                                       │
│ Workers (judgment, not management — depth-1 leaves):                  │
│   Scot   — SAM discovery / top-of-funnel                              │
│   Lenny  — fit ranking / profile matching                             │
│   Lance  — incumbents / awards / competitive intel                    │
│   Gabby  — eligibility / compliance blockers (§11.1 owner)            │
│   Happer — execution runner (browser, files, overflow work)           │
│   Roy    — packaging / handoff (memo, email, capability statement)    │
│                                                                       │
│ Michaela is the orchestrator, not a worker. The 6 workers are the     │
│ bench. "7 named entities" = Michaela + 6 workers.                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │ workers run inside
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ RUNTIME LAYER — Hermes Agent (Nous Research)                        │
│ Install: ~/.hermes/    (per-user)                                    │
│ Version: v0.13.0 confirmed installed                                 │
│ Provides: CLI/chat runtime, tool calling, skills (SKILL.md           │
│   progressive disclosure), memory, provider config (anthropic /      │
│   openrouter / others), gateway support, cron jobs, subagents        │
│   (delegate_task), profiles / isolated homes (HERMES_HOME).          │
│                                                                       │
│ Hermes is NOT the product. Michaela uses Hermes as infrastructure.    │
└────────────────────────────┬────────────────────────────────────────┘
                             │ tool-calls (Hermes plugin) into
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CAPABILITY-PACK LAYER — THIS REPO                                    │
│ Repo:    /Volumes/CS_Stuff/govcon  (also referred to as "govcon")    │
│ Stack:   Python 3.12 + FastAPI + uv  (backend)                       │
│           Next 15 + React 19 + Tailwind 4  (web/, landing/)          │
│ Identity: GovCon Bid Desk capability pack                            │
│                                                                       │
│ What it owns:                                                         │
│   - Shared tools (judgment-free mechanics): api/skills/<name>/       │
│     • parse_pdf, extract_requirements, score_fit, detect_risks,      │
│       generate_action_package, search_sam, fetch_attachment,         │
│       parse_goal, rank_opportunities, load_seeded_opportunities      │
│   - HTTP API for CRUD: api/routes/<resource>.py                      │
│   - Auth: api/auth.py — Supabase JWT (users) + InternalActor         │
│     (X-Internal-API-Key for sub-agent writebacks)                    │
│   - Data layer: api/repositories/ via supabase-py PostgREST          │
│     (no SQLAlchemy/asyncpg/Alembic — PRD v1.2.4)                     │
│   - Storage wrapper: api/storage.py — Supabase Storage REST          │
│   - /web — direct-user product surface (Bid Desk UI)                  │
│   - /landing — marketing site                                         │
│   - PLANNED: hermes_plugin_govcapture/ — Hermes plugin that          │
│     registers this pack's tools for native worker calls              │
│                                                                       │
│ What it does NOT own:                                                 │
│   ❌ Michaela the orchestrator                                        │
│   ❌ Work loop, agent pool, task queue, open-loop store               │
│   ❌ The worker bench (those agents live in /root/michealaai)         │
│   ❌ Orchestration recipes (operate_bid_desk, analyze_opportunity_e2e)│
│   ❌ Trace replay / fake "Michaela run" simulation                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │ data
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ DATA + TRANSPORT                                                     │
│ Supabase project: vvyxjdoenjujkxwbnzyl (linked, all 5 migrations    │
│   applied). Bucket govcapture-attachments (private, created).        │
│   Tables: company_profiles, opportunities, extracted_requirements,   │
│   fit_scores, risk_flags, action_packages, agent_runs, profiles,     │
│   waitlist_signups, opportunity_matches, documents, document_chunks, │
│   run_events + dimension tables.                                     │
│                                                                       │
│ R2 (planned): raw files (PDFs, attachments, CSV snapshots).          │
│   Currently using Supabase Storage for raw + parsed.                 │
│                                                                       │
│ Anthropic / OpenRouter: model transport. Just the pipe.              │
│   Direct Anthropic recommended for this pack (D1 below).             │
└─────────────────────────────────────────────────────────────────────┘
```

### Operating rule (memorize this)

> **Mechanics in shared tools. Judgment in agents. Contracts in schemas.
> Michaela owns the board.**

If you find yourself building "judgment" inside this pack (e.g., a Python
function that decides whether to bid), stop. That belongs to a worker
(Gabby, Lenny, etc.) running in Michaela's Hermes. This pack only
provides mechanics: parse this PDF, search SAM with these criteria, score
these requirements against this profile. The decision belongs to the
agent calling our tools.

---

## 2. What's confirmed working RIGHT NOW (verified facts)

These are not aspirational — they were directly tested in the previous
session.

| Component | Status | How verified |
|-----------|--------|--------------|
| Supabase project | Linked | `supabase migration list` shows local==remote |
| All 5 SQL migrations | Applied | `supabase db push` ran clean |
| Storage bucket `govcapture-attachments` | Created (private) | POST `/storage/v1/bucket` returned 200; GET listed it |
| `.env` real keys (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `INTERNAL_API_KEY`, `NEXT_PUBLIC_*`) | Filled | `git check-ignore .env` confirms gitignore; `.env.example` is the template |
| Live `select` against `company_profiles`, `waitlist_signups`, `profiles` | Returns `[]` | `acreate_client` + `.table().select()` round-trip |
| Redis | Running locally (`PONG`) | `redis-cli ping` |
| **`/healthz` end-to-end** against live Supabase + Redis | **200 OK** | `app.router.lifespan_context` + ASGITransport, `{"status":"ok"}` |
| FastAPI app boots | Clean | `from api.main import app` → 23 routes |
| `pytest api/tests/` | **111/111 pass** | Full suite green |
| `ruff check api` | Clean | 0 warnings |
| `mypy api` | Clean | 0 errors (with `pydantic.mypy` plugin enabled) |

**Still placeholder in `.env`** (won't block `/healthz` or DB calls — needed
when LLM skills run):
- `ANTHROPIC_API_KEY=sk-ant-test-placeholder` — replace with a real key
  from console.anthropic.com when you want LLM skills to work
- `SAM_API_KEY=` — optional; empty falls back to seeded fixtures

---

## 3. What's broken / misplaced (the doc-rewrite scope)

The previous session inherited docs that overclaimed an integration
status. The architecture corrections (this repo = pack, NOT orchestrator)
make several files structurally wrong, not just textually wrong. Here's
the inventory.

### 3a. Misplaced orchestration code (belongs in /root/michealaai)

| Path | Why misplaced | Action |
|------|---------------|--------|
| `api/agent/hermes_runner.py` | Pretends to invoke Hermes; really calls a deterministic seeded bridge. Orchestration is michealaai's job. | **Delete** in this repo. (Optionally relocate to /root/michealaai if useful as a starting point there.) |
| `api/agent/hermes_bridge.py` | 500 lines of fake "Michaela run" pretending to be a trace bridge. None of it actually invokes Hermes or LLMs. | **Delete**. The eval harness (Phase 4 below) replaces its useful pieces. |
| `api/agent/replay.py` | SSE replay of `trace-event.example.jsonl`. This is "what a run would look like" — orchestration territory. | **Delete**. michealaai will emit real run events. |
| `api/agent/__init__.py` | Empty package | **Delete the directory** entirely after the above 3 are gone. |
| `api/routes/agent_runs.py::create_agent_run` _kick_off_run trigger | Currently calls `replay.py` to fake events. The CRUD parts are fine for michealaai to write into. | **Keep CRUD**; **remove orchestration trigger**. |

### 3b. Misplaced docs (describe Michaela's bench, not this pack)

| Path | Why misplaced | Action |
|------|---------------|--------|
| `tasks/AGENT_ARCHITECTURE.md` | Describes Michaela's worker bench, toolset map for delegation, §11.1 chain — all the orchestrator's design. | **Delete**. Move to /root/michealaai if not already there. |
| `.hermes/SOUL.md` | Persona/voice file for Michaela & her bench — agent territory. | **Delete**. Belongs in /root/michealaai's HERMES_HOME. |
| `.hermes/skills/govcapture/operate_bid_desk/` | Cross-tool orchestration recipe (parse_goal → delegate to Scot → ...). Orchestration. | **Delete**. michealaai's territory. |
| `.hermes/skills/govcapture/analyze_opportunity_e2e/` | Per-opp orchestration recipe. Same. | **Delete**. michealaai's. |
| `.hermes/skills/govcapture/discover_opportunities/` | Scot's worker recipe. | **Delete**. michealaai's. |

### 3c. Tool-procedure SKILL.mds (KEEP — these are the pack's procedures)

These describe how to USE this pack's tools. They're appropriate
progressive-disclosure procedures for any agent (Michaela's workers or a
human dev) calling our tools. **Keep them, no edits unless content is
wrong.**

- `.hermes/skills/govcapture/extract_requirements_with_evidence/SKILL.md`
- `.hermes/skills/govcapture/score_fit_with_eligibility_check/SKILL.md`
- `.hermes/skills/govcapture/detect_risks_calibrated/SKILL.md`
- `.hermes/skills/govcapture/generate_full_action_package/SKILL.md`
- `.hermes/skills/govcapture/generate_reject_summary/SKILL.md`

### 3d. Hermes config

`.hermes/config.yaml` was written assuming this repo runs the orchestrator.
It encodes delegation depth, bench design, etc. — none of which is this
pack's concern.

| Action | Why |
|--------|-----|
| **Slim drastically** to a project-isolated dev config: `model.provider: anthropic`, `model.default: claude-sonnet-4-6`, basic `memory:` defaults | Devs may want to run Hermes against this pack's tools for testing. That's the only reason this file exists in this repo. |
| Drop `delegation:` block | Delegation is michealaai's concern. |
| Drop `models:` (plural) — invented key | Real key is singular `model:`. |
| Drop `providers:` block — invented | Provider goes inside `model:`. |
| Drop `telemetry:` block — invented | Not a real Hermes config key. |
| Drop `memory.cross_session: true` — invented | Real keys: `memory_enabled`, `user_profile_enabled`, `memory_char_limit`, `user_char_limit`. |

### 3e. Doc claims to fix (overstating integration)

| File | Specific lines / claims | Replace with |
|------|------------------------|--------------|
| `HERMES.md` (root) | "Michaela and her bench running in this repo"; "7-agent bench" framing | "Hermes project context for the GovCon capability pack — describes the tools available when an agent runs `hermes` against this repo's `HERMES_HOME=$(pwd)/.hermes`. The agent persona and bench live in /root/michealaai, not here." |
| `devdocs/CURRENT_STATE.md` | §1 "the system runs as a CEO + 6 specialists" — implies the orchestrator lives here | "This repo is the GovCon Bid Desk capability pack: tools + data + product surface. The orchestrator (Michaela) and worker bench (Scot, Lenny, Lance, Gabby, Happer, Roy) live in /root/michealaai." |
| `devdocs/CURRENT_STATE.md` | §2 "The seven agents (the bench)" with table of all 7 | Slim to a one-paragraph pointer to /root/michealaai's docs; remove the full table. |
| `devdocs/CURRENT_STATE.md` | §3 architecture diagram showing Hermes runner inside this repo | Replace with the 4-layer diagram from Section 1 of THIS handoff. |
| `devdocs/V1_PRODUCT_ALIGNMENT.md` | Already mostly updated; verify worker names use Gabby/Lance | Spot-check, light edits only. |
| `devdocs/CAPABILITY_PACKS_CANVAS.md` | Strategic horizon doc — should be untouched. | Leave alone. |
| `tasks/README.md` | "frozen decisions" table mentions agent identities + delegation; bench design — that's orchestrator's | Slim "Agent identities" row to "(maintained in /root/michealaai)". Keep the data-layer / auth / hosting / fixture-set rows. |
| `tasks/CONTRACTS.md §3` (trace event taxonomy) | OK to keep — schema source of truth that michealaai will emit against | No change. |
| `tasks/CONTRACTS.md §4` (env contract) | Already correct after PRD v1.2.4 | No change. |
| `tasks/DEMO.md` | Demo script likely names agents | Update to use Gabby (was Gate) and Lance (was Ledger). |
| `tasks/INTERFERENCE_MAP.md` | Describes file ownership; Track A/B language already deprecated | Light edit: add note that orchestration code (api/agent/) is being removed; ownership boundary now centers on api/skills/, api/routes/, supabase/, web/. |
| `tasks/FIXTURES.md` | Fixture authoring guide | Spot-check; likely fine. |
| `infra/RUNBOOK.md` | Already correct (Supabase CLI flow, no Alembic) after PRD v1.2.4 | Light additions only: HERMES_HOME for dev testing; pack vs. orchestrator note. |
| `PRD.md` | v1.2.4 changelog OK; need v1.2.5 entry for the pack repositioning | Add v1.2.5 changelog entry (text in Section 8 of this handoff). |
| `.hermes/SOUL.md` | Just edited by user with Michaela + 6 in a unified table; structurally still wrong (this repo doesn't host the bench) | **Delete** the file from this repo (already covered in 3b). The version that lives in /root/michealaai's HERMES_HOME is the canonical one. |

### 3f. Files to CREATE

| Path | Purpose |
|------|---------|
| `devdocs/MICHAELA_SYSTEM_MODEL.md` | Referenced by V1_PRODUCT_ALIGNMENT.md but doesn't exist. Should describe the Michaela-as-orchestrator architecture, the work-loop pattern, and how this pack fits in. ~200–300 lines. |
| `devdocs/CAPABILITY_PACK_INTEGRATION.md` | Replaces the misnamed HERMES_INTEGRATION_PLAN.md. Documents how this pack exposes its tools to Michaela TS workers (via Hermes plugin + HTTP API). ~150–250 lines. |
| `hermes_plugin_govcapture/` (Phase 5+) | The Python plugin that registers our tools for Hermes. Defer to a future session unless this session has time. |

### 3g. Files to DELETE

Everything in 3a + 3b plus:

- `devdocs/HERMES_INTEGRATION_PLAN.md` — the older plan that assumed this repo is the orchestrator. Replace with `CAPABILITY_PACK_INTEGRATION.md` from 3f.
- `tasks/_archive/` — already deleted in a prior session; verify it's gone.
- `docs/superpowers/plans/2026-05-09-*.md` — already deleted.

---

## 4. The bench (lives in /root/michealaai, not here)

Document for context only — no edits to this in this repo:

| # | Name | Role | Sample output |
|---|------|------|---------------|
| 0 | **Michaela** | CEO / orchestrator | "1 worth pursuing • 12 days left • 2 gaps • Bid memo ready" |
| 1 | Scot | Discovery / SAM bulk scan | "Found 81,031 → next 90 days 14,000 → matched 42" |
| 2 | Lenny | Fit ranking | "Pursue 2 • Monitor 6 • Skip 39 • Best fit: VA Cybersecurity Support" |
| 3 | Gabby | Eligibility blocker check (§11.1 owner) | "Eligible? no • Blocker: missing clearance • Do not bid" |
| 4 | Lance | Competitive intel | "Incumbent: Tetra Tech • won 3× • difficulty: hard • prob 22%" |
| 5 | Happer | Execution runner | "Job done • rows processed • files written • errors found" |
| 6 | Roy | Packaging / handoff | "Bid memo ready • capability statement drafted • email ready" |

**Naming note:** Recent renames in michealaai — `Gate → Gabby`,
`Ledger → Lance`. Other names unchanged. Scope of these renames in this
repo: doc text only (no code references the old names because the bench
doesn't live here).

---

## 5. Decisions already made (don't re-litigate)

| ID | Decision | Status |
|----|----------|--------|
| D1 | Provider route for this pack: **direct Anthropic** (not via OpenRouter). `model.provider: anthropic`, `default: claude-sonnet-4-6`, reads `ANTHROPIC_API_KEY` env var. | Confirmed |
| D2 | Hermes home for dev testing: **`HERMES_HOME=$(pwd)/.hermes` (project-isolated)**. Does not touch user's `~/.hermes/`. | Confirmed |
| D3 | Data layer: **Supabase via `supabase-py` AsyncClient (PostgREST)**. SQLAlchemy / asyncpg / Alembic dropped (PRD v1.2.4). Schema = `supabase/migrations/*.sql` applied via `supabase db push`. | Done |
| D4 | Auth: **Supabase JWT (`AuthenticatedUser`) for users + X-Internal-API-Key (`InternalActor`) for sub-agent writebacks**. RLS on every table. `owner_profile_id` on user-facing tables; `get_owned()` repo methods. | Done |
| D5 | Hosting: **Vultr VX1 + nginx + systemd** (no Docker). Vercel for `/web` + `/landing`. Supabase manages DB/Auth/Storage. | Pending VX1 deploy |
| D6 | Tooling: `uv` for Python deps; `bun` for michealaai TS; `make` targets canonical for common workflows. | Done |
| D7 | Worker names in this repo's docs: **Gabby (was Gate), Lance (was Ledger)**. Other names unchanged. | Pending propagation |
| D8 | Fixtures: 4 sets — `strong-pursue`, `maybe`, `reject`, `adversarial-image-pdf`. PDFs + manifests committed. | Done |
| D9 | This repo's identity: **GovCon Bid Desk capability pack**, NOT the orchestrator. Orchestrator lives in /root/michealaai. | Confirmed |

---

## 6. Provider/key conventions for THIS repo

```
ANTHROPIC_API_KEY     → server-side, used by api/llm.py for skill-internal
                         LLM calls. Set in .env (gitignored). Required for
                         LLM-backed skills to work.
SAM_API_KEY           → optional; empty falls back to seeded fixtures.
SUPABASE_URL          → real (vvyxjdoenjujkxwbnzyl.supabase.co)
SUPABASE_SERVICE_ROLE_KEY → real (sb_secret_…). Server-only. Bypasses RLS.
SUPABASE_ANON_KEY     → real (sb_publishable_…). Used by api/auth.py to
                         verify Supabase JWTs via /auth/v1/user.
SUPABASE_STORAGE_BUCKET → "govcapture-attachments" (created, private)
INTERNAL_API_KEY      → real random (lG-4NSCt…). Required header
                         (X-Internal-API-Key) for sub-agent writeback
                         routes. Never expose to browser.
NEXT_PUBLIC_SUPABASE_URL, _ANON_KEY → real, for /web
NEXT_PUBLIC_API_BASE  → http://localhost:8000 in dev; prod URL in prod
REDIS_URL             → redis://localhost:6379/0 in dev
HERMES_HOME           → "$(pwd)/.hermes" for dev testing only; not loaded
                         by this repo's runtime
HERMES_MODEL          → claude-sonnet-4-6 (default)
LLM_DEV_MODEL         → claude-haiku-4-5-20251001
LLM_SYNTH_MODEL       → claude-sonnet-4-6
RUN_BUDGET_USD/STEPS/SECONDS → 0.50 / 40 / 360 (PRD §4.5 budgets)
DEMO_USE_SEEDED_ONLY  → false (true = no live SAM, /fixtures only)
DEMO_REPLAY_TRACE     → false (legacy; the seeded bridge is being deleted)
CORS_ALLOWED_ORIGINS  → http://localhost:3000,http://localhost:3001,
                         http://localhost:5173 (dev); prod origins in prod
```

`.env.example` is the committed template; `.env` is gitignored. Both
match `api/config.py` keys exactly.

---

## 7. Repository layout (post-rewrite target state)

```
/Volumes/CS_Stuff/govcon/
├── PRD.md                           ← v1.2.5 (post-rewrite)
├── README.md                        ← pack overview + quickstart
├── HERMES.md                        ← short: dev guide for running
│                                       hermes against this pack's tools
├── Makefile                         ← dev, services-up, schemas,
│                                       fixtures-validate, hermes
│                                       (project-isolated), test, etc.
├── pyproject.toml                   ← supabase, fastapi, anthropic, etc.
├── package.json                     ← npm workspace root
├── .env / .env.example / .env.production.example
├── .gitignore
├── .hermes/
│   ├── config.yaml                  ← slim, schema-correct dev config
│   ├── .env.example                 ← template for HERMES_HOME-isolated
│   │                                   ANTHROPIC_API_KEY
│   └── skills/govcapture/           ← tool-usage SKILL.mds only
│       ├── extract_requirements_with_evidence/
│       ├── score_fit_with_eligibility_check/
│       ├── detect_risks_calibrated/
│       ├── generate_full_action_package/
│       └── generate_reject_summary/
├── api/
│   ├── __init__.py
│   ├── auth.py                      ← AuthenticatedUser + InternalActor
│   ├── config.py                    ← pydantic-settings, single source
│   ├── deps.py                      ← repo dependency providers
│   ├── llm.py                       ← Anthropic SDK wrapper (LLMMetrics)
│   ├── main.py                      ← FastAPI app, lifespan, routers
│   ├── redis.py                     ← redis.asyncio client
│   ├── storage.py                   ← Supabase Storage REST (httpx)
│   ├── db/
│   │   └── __init__.py              ← supabase-py AsyncClient factory
│   ├── repositories/
│   │   ├── action_package.py
│   │   ├── agent_run.py
│   │   ├── company_profile.py
│   │   ├── opportunity.py
│   │   ├── profile.py
│   │   └── waitlist.py
│   ├── routes/
│   │   ├── action_packages.py       ← CRUD only (no orchestration)
│   │   ├── agent_runs.py            ← CRUD only (drop _kick_off_run)
│   │   ├── company_profiles.py
│   │   ├── healthz.py
│   │   ├── opportunities.py
│   │   ├── profiles.py
│   │   └── waitlist.py
│   ├── schemas/                     ← generated by `make schemas`
│   ├── skills/                      ← shared GovCon tools
│   │   ├── parse_pdf/
│   │   ├── extract_requirements/
│   │   ├── score_fit/
│   │   ├── detect_risks/
│   │   ├── generate_action_package/
│   │   ├── search_sam/
│   │   ├── fetch_attachment/
│   │   ├── parse_goal/
│   │   ├── rank_opportunities/
│   │   └── load_seeded_opportunities/
│   └── tests/
│       ├── conftest.py              ← FakeSupabase + auth overrides
│       ├── fakes.py                 ← FakeLLM
│       └── test_*.py
│   # NOTE: api/agent/ removed entirely (Phase 1 deletion)
├── supabase/
│   └── migrations/
│       ├── 20260509132444_remote_schema.sql
│       ├── 20260509132830_create_govcon_core.sql
│       ├── 20260509140333_michaela_mvp_layer.sql
│       ├── 20260509140838_add_ownership_and_provenance.sql
│       └── 20260509203000_add_waitlist_signups.sql
├── schemas/                         ← JSON Schema sources
├── fixtures/                        ← strong-pursue, maybe, reject,
│                                       adversarial-image-pdf
├── eval/                            ← Phase 4 target
│   ├── runner/
│   └── goldens/
├── infra/
│   ├── RUNBOOK.md
│   ├── bootstrap.sh
│   ├── deploy.sh
│   ├── nginx/
│   └── systemd/
├── web/                             ← Next 15 product UI
├── landing/                         ← Next 15 marketing
├── tasks/                           ← reference docs
│   ├── README.md                    ← frozen decisions, layout
│   ├── CONTRACTS.md                 ← schemas, SSE, env
│   ├── INTERFERENCE_MAP.md          ← file ownership
│   ├── FIXTURES.md                  ← fixture authoring
│   └── DEMO.md                      ← demo script (worker names updated)
└── devdocs/
    ├── CURRENT_STATE.md             ← rewritten as "pack" identity
    ├── CAPABILITY_PACKS_CANVAS.md   ← unchanged (strategic horizon)
    ├── V1_PRODUCT_ALIGNMENT.md      ← already updated (verify Gabby/Lance)
    ├── MICHAELA_SYSTEM_MODEL.md     ← NEW: orchestrator + pack
    │                                       relationship
    ├── CAPABILITY_PACK_INTEGRATION.md ← NEW: Hermes plugin + HTTP API
    │                                       integration spec
    ├── HANDOFF_PROMPT.md            ← THIS FILE
    └── prompt.md                    ← (legacy; leave unless conflicts)
```

Files NO LONGER present after the rewrite:

```
api/agent/                                   ← entire dir removed
.hermes/SOUL.md                              ← removed
.hermes/skills/govcapture/operate_bid_desk/  ← removed
.hermes/skills/govcapture/analyze_opportunity_e2e/  ← removed
.hermes/skills/govcapture/discover_opportunities/   ← removed
tasks/AGENT_ARCHITECTURE.md                  ← removed
devdocs/HERMES_INTEGRATION_PLAN.md           ← removed (replaced by
                                                 CAPABILITY_PACK_INTEGRATION.md)
```

---

## 8. The doc-rewrite plan (file by file)

Execute these in order. Each phase is self-contained and verifiable.

### Phase 0 — Surgical removal of orchestration code (1–2h)

**Goal:** physically remove what doesn't belong in this repo.

**Steps:**
1. `rm api/agent/hermes_runner.py api/agent/hermes_bridge.py api/agent/replay.py`
2. `rmdir api/agent` (after `__init__.py` is also removed)
3. Edit `api/routes/agent_runs.py`:
   - Remove `from api.agent.replay import replay_example_run`
   - Remove `_kick_off_run` function
   - In `create_agent_run`, remove the `asyncio.create_task(_kick_off_run(...))` call
   - Remove the `from api.config import settings` import if no longer used
   - Remove the `if settings.demo_replay_trace:` gate (the variable can be deprecated)
4. Edit `api/config.py` — leave `demo_replay_trace` for now (other code may still reference it; clean up in a later pass).
5. Run tests: `uv run pytest api/tests/`. If `test_routes.py::test_sse_replays_first_event` fails (it would, since replay is gone), DELETE that test.
6. Run tests again. Should be green.
7. Run `uv run mypy api` and `uv run ruff check api`. Should be clean.

**Verify:**
- `find api/agent -type f` returns nothing.
- `grep -rn "from api.agent" api/` returns nothing.
- `pytest api/tests/` exits 0.

### Phase 1 — Slim `.hermes/config.yaml` to schema-correct dev-only (30m)

**Goal:** the config file becomes useful for `HERMES_HOME=$(pwd)/.hermes hermes`
testing and nothing else. No bench/delegation directives.

**New content for `.hermes/config.yaml`:**

```yaml
# Hermes config for dev testing this pack's tools.
#
# This file is consumed when a developer runs:
#   HERMES_HOME=$(pwd)/.hermes hermes
#
# It is NOT loaded by FastAPI or by any production process — those read
# api/config.py and .env directly. The orchestrator (Michaela) and worker
# bench live in /root/michealaai with their own ~/.hermes/.
#
# Dropping invented keys (models:, providers:, telemetry:,
# memory.cross_session) that this repo previously hand-rolled.

model:
  provider: "anthropic"
  default: "claude-sonnet-4-6"
  # api_key: read from .env's ANTHROPIC_API_KEY (do not put a literal
  # value here; commit-safety).

memory:
  memory_enabled: true
  user_profile_enabled: false  # this is a tool-testing home, not a personal profile
  memory_char_limit: 2200
  user_char_limit: 1375
```

**Verify:**
- `HERMES_HOME=$(pwd)/.hermes hermes config show` reports:
  - Model provider: anthropic, default: claude-sonnet-4-6
  - Memory enabled: true
  - No "unknown key" warnings.

### Phase 2 — Delete misplaced docs + SOUL.md (30m)

**Steps:**
1. `rm tasks/AGENT_ARCHITECTURE.md`
2. `rm .hermes/SOUL.md`
3. `rm -rf .hermes/skills/govcapture/operate_bid_desk`
4. `rm -rf .hermes/skills/govcapture/analyze_opportunity_e2e`
5. `rm -rf .hermes/skills/govcapture/discover_opportunities`
6. `rm devdocs/HERMES_INTEGRATION_PLAN.md`

**Verify:**
- `ls .hermes/skills/govcapture/` shows only the 5 tool-procedure dirs.
- `ls tasks/` does not include AGENT_ARCHITECTURE.md.
- `ls devdocs/` does not include HERMES_INTEGRATION_PLAN.md.

### Phase 3 — Rewrite the rest of the docs (1–2h)

**Files to rewrite (full):**

#### `HERMES.md` (root) — slim to ~80 lines

```markdown
# Hermes context for the GovCon Bid Desk capability pack

This file gives a Hermes runtime project-context when a developer points
their `HERMES_HOME` at this repo's `.hermes/` to test the pack's tools in
isolation. It is **NOT** loaded by FastAPI or by any production process.

The orchestrator (Michaela) and her worker bench (Scot, Lenny, Lance,
Gabby, Happer, Roy) live in **/root/michealaai**. This repo is the
**GovCon Bid Desk capability pack**: shared tools, data layer, HTTP API,
and the direct-user product surface (`/web`).

## What you can do here

When a developer runs:

```bash
HERMES_HOME=$(pwd)/.hermes hermes
```

…they get a Hermes REPL that loads:

- `model.provider: anthropic, default: claude-sonnet-4-6` (per `.hermes/config.yaml`)
- The 5 tool-usage SKILL.md procedures under `.hermes/skills/govcapture/`
- Memory storage isolated to `.hermes/memories/`

This is for testing tool calls in isolation. It is not a production
runtime.

## Hard rules (apply when an agent runs against this pack's tools)

1. **§11.1 — Eligibility conservatism.** Hard eligibility blockers
   (clearance, set-aside, citizenship, certification) deterministically
   produce `decision = reject` regardless of capability strength. The
   short-circuit lives in Python inside `score_fit`. Don't let an agent
   talk its way around it.

2. **Source-binding.** Every claim with confidence ≥ medium must carry a
   verbatim quote + page_number from the source. If you can't quote it,
   set confidence to low/unknown and leave evidence empty.

3. **No fabrication.** Don't invent CO names, dollar values, or
   certifications the profile didn't declare. Generic salutations only.

4. **Approval gate.** Action packages always emit `human_approval_required`
   covering: external contact, certification claims, submission,
   compliance attestation.

5. **Budget.** 40 steps / 6 minutes / $0.50 per agent run.

## What's NOT here

- Michaela's persona/SOUL — `/root/michealaai`'s HERMES_HOME
- Worker definitions, agent-bootstrap, work-loop logic — `/root/michealaai`
- Orchestration recipes (`operate_bid_desk`, etc.) — `/root/michealaai`

## Where to look

- `tasks/CONTRACTS.md` — schemas, SSE event taxonomy
- `devdocs/CURRENT_STATE.md` — single-page state of this pack
- `devdocs/MICHAELA_SYSTEM_MODEL.md` — orchestrator + pack relationship
- `devdocs/CAPABILITY_PACK_INTEGRATION.md` — how Michaela TS calls
- `PRD.md` — product spec (current v1.2.5)
```

#### `devdocs/CURRENT_STATE.md` — full rewrite

Sections to write:
1. **The product** — pack identity (Bid Desk), capability-packs canvas
2. **The architecture (4 layers)** — copy the diagram from Section 1 of
   this handoff
3. **What this repo IS** — list (tools, data, API, UI)
4. **What this repo IS NOT** — list (orchestrator, bench, runtime)
5. **Tech stack** — same table as before
6. **Data model** — same tables list
7. **API surface** — same endpoint table (drop orchestration trigger row)
8. **Skills (the pack's tool surface)** — list of 10 skills, owner
   tagged with the worker that calls it (e.g., "called by Gabby in
   michealaai")
9. **Recent decisions** — same timeline + add v1.2.5 row for pack
   repositioning
10. **What ships today vs. next** — slim list (no orchestration items)
11. **Env-var contract** — same
12. **Where to look** — same

#### `devdocs/MICHAELA_SYSTEM_MODEL.md` — NEW

Sections:
1. **Why this doc exists** — V1_PRODUCT_ALIGNMENT references it
2. **The work-loop pattern** — capture observation → queue microtask
   → assign by capability → store result → decide whether to resurface
3. **Michaela the orchestrator** — owns the board, captures open loops,
   keeps user-facing output simple
4. **The 6 workers** — Scot, Lenny, Lance, Gabby, Happer, Roy with
   roles and outputs (use the table from Section 4 of this handoff)
5. **How Michaela uses this pack** — calls Hermes plugin tools or HTTP
   endpoints; reads/writes Supabase tables; consumes pack's procedures
6. **What lives in /root/michealaai vs. here** — clear boundary table
7. **Operating rule** — mechanics in tools, judgment in agents,
   contracts in schemas, Michaela owns the board
8. **Pointers to michealaai** — repo path, key files, docs

#### `devdocs/CAPABILITY_PACK_INTEGRATION.md` — NEW

Sections:
1. **Two transport surfaces** — Hermes plugin (native worker calls) +
   HTTP REST (any-language calls)
2. **Hermes plugin design** — `hermes_plugin_govcapture/` package,
   `register(ctx)` entrypoint, adapter modules per toolset
3. **HTTP API design** — POST `/tools/<name>` endpoints, InternalActor auth,
   same Python adapters
4. **Phased rollout** — Phase 5 plugin; Phase 6 HTTP-API parity
5. **Verification** — `hermes /skills` shows our tools; `curl /tools/parse-pdf`
   returns structured output
6. **Why both surfaces** — Hermes for in-runtime workers; HTTP for TS,
   Codex, Cursor agents that don't run in Hermes

#### `tasks/README.md` — light edits

- Drop "Agent identities" row from frozen decisions table (now
  michealaai's territory).
- Add row: "This repo's identity: GovCon Bid Desk capability pack
  (tools + data + UI). Orchestrator lives in /root/michealaai."
- Update Layout block: drop AGENT_ARCHITECTURE.md from the listed files.

#### `tasks/DEMO.md` — propagate worker name renames

- Replace `Gate` → `Gabby`, `Ledger` → `Lance` everywhere.
- Demo script narrative may say "Gabby just returned eligibility = reject"
  instead of "the Compliance Officer just returned…".

#### `tasks/INTERFERENCE_MAP.md` — light edits

- Add note in §1: "api/agent/ removed — orchestration moved to
  /root/michealaai. File ownership in this repo centers on api/skills/,
  api/routes/, supabase/migrations/, web/, fixtures/."

#### `PRD.md` — add v1.2.5 changelog entry

Insert at top of changelog section (above v1.2.4):

```markdown
> **Changelog v1.2.4 → v1.2.5** (2026-05-09)
> - **This repo repositioned as a capability pack.** The orchestrator
>   (Michaela) and worker bench (Scot, Lenny, Lance, Gabby, Happer, Roy)
>   live in `/root/michealaai` (TypeScript/Bun work-loop project), not
>   here. This repo is now scoped as the **GovCon Bid Desk capability
>   pack**: shared tools, data layer, HTTP API, direct-user `/web`
>   product surface, and (planned) `hermes_plugin_govcapture` Python
>   plugin so Michaela's Hermes-hosted workers can native-call our
>   tools.
> - **Misplaced orchestration code removed:** `api/agent/hermes_runner.py`,
>   `api/agent/hermes_bridge.py`, `api/agent/replay.py`,
>   `tasks/AGENT_ARCHITECTURE.md`, `.hermes/SOUL.md`,
>   `.hermes/skills/govcapture/{operate_bid_desk,analyze_opportunity_e2e,
>   discover_opportunities}/SKILL.md`, `devdocs/HERMES_INTEGRATION_PLAN.md`.
> - **Worker naming aligned with michealaai:** Gate → Gabby, Ledger → Lance.
> - `.hermes/config.yaml` slimmed to a schema-correct dev-only file. No
>   delegation/bench directives — those belong in michealaai's HERMES_HOME.
> - New docs: `devdocs/MICHAELA_SYSTEM_MODEL.md` (orchestrator + pack
>   relationship), `devdocs/CAPABILITY_PACK_INTEGRATION.md` (Hermes
>   plugin + HTTP-API integration spec).
```

### Phase 4 — Rename remaining "Gate"/"Ledger" mentions (15m)

```bash
grep -rln "Gate\|Ledger" --include="*.md" devdocs/ tasks/ infra/ HERMES.md README.md PRD.md 2>/dev/null \
  | xargs grep -l "Gate.*eligibility\|Ledger.*intel\|Ledger.*incumbent\|Gate.*compliance\|Gate.*blocker"
```

Manually review each hit and replace with Gabby / Lance where context
matches the new bench naming.

### Phase 5 — Create new docs (1h)

Write `devdocs/MICHAELA_SYSTEM_MODEL.md` and
`devdocs/CAPABILITY_PACK_INTEGRATION.md` per Phase 3 specs above.

### Phase 6 — Final verification (15m)

Run all gates in Section 11.

---

## 9. The Hermes plugin + HTTP API (post-doc-rewrite milestone)

This is documented in the new `CAPABILITY_PACK_INTEGRATION.md` (Phase 5
above). Implementation is a separate sprint after the doc rewrite —
roughly 3–5 days of work. Brief outline so this handoff is self-contained:

**Hermes plugin (`hermes_plugin_govcapture/`):**

```
hermes_plugin_govcapture/
├── __init__.py
├── pyproject.toml              # entry_points: hermes.plugins
├── plugin.py                   # register(ctx) — wires all toolsets
├── adapters/
│   ├── __init__.py
│   ├── gov_discovery.py        # search_sam, load_seeded_opportunities
│   ├── gov_documents.py        # parse_pdf, fetch_attachment
│   ├── gov_compliance.py       # extract_requirements, score_fit, detect_risks
│   ├── gov_proposals.py        # generate_action_package
│   ├── gov_intel.py            # query_usaspending (NEW skill needed)
│   └── meta.py                 # parse_goal, summarize_run, request_human_review
└── tests/
    └── test_register.py
```

Each adapter wraps a `api/skills/<name>/skill.py` async function in a
synchronous-or-async Hermes tool handler returning JSON-stringified output.

**HTTP REST tools (in `api/routes/tools.py` — NEW):**

`POST /tools/parse-pdf`, `POST /tools/extract-requirements`, etc.,
authed via `InternalActor`. Same Python adapters under the hood.

---

## 10. Conventions to follow during the rewrite

### Edits

- **Use `Edit` for surgical changes** (add/remove single sections).
- **Use `Write` only for full-file rewrites** — and only after `Read`-ing
  the current contents first (the harness enforces this).
- **Never silently revert concurrent edits.** If a file you're about to
  edit was modified while you were reading, re-read first.
- **Don't add features beyond the spec.** This is a doc rewrite + small
  code surgery, not a refactor.

### Commits

- Commit per phase, not per file. Suggested messages:
  - `chore(api): remove misplaced orchestration code (api/agent/, agent_runs._kick_off_run)`
  - `docs(.hermes): slim config.yaml to schema-correct dev-only`
  - `docs: delete misplaced orchestration docs (AGENT_ARCHITECTURE, SOUL, plan)`
  - `docs: rewrite HERMES.md, CURRENT_STATE.md, tasks/* for capability-pack identity`
  - `docs(devdocs): add MICHAELA_SYSTEM_MODEL + CAPABILITY_PACK_INTEGRATION`
  - `docs(prd): v1.2.5 — repository repositioned as capability pack`
  - `chore: rename Gate→Gabby, Ledger→Lance across docs`
- Use `git status` and `git diff --stat` before each commit to verify
  scope.
- Don't push to remote unless the human asks.

### Tests

- After Phase 0: `uv run pytest api/tests/`. Must be green.
- After Phase 1: `HERMES_HOME=$(pwd)/.hermes hermes config show`. Must
  not warn about unknown keys.
- Final: `uv run pytest api/tests/`, `uv run ruff check api`, `uv run mypy api`.
  All clean.

### Style

- Markdown lines max ~78 chars where possible (some tables/code blocks
  exempt).
- File frontmatter only where Hermes spec requires it (SKILL.md files).
- Don't use emoji unless the human asks.

---

## 11. Verification gates (must be green before declaring done)

| Gate | Verify with | Required outcome |
|------|------------|------------------|
| G0 | `find api/agent -type f` | (empty — directory gone) |
| G1 | `grep -rn "from api.agent\|api.agent" api/` | (empty) |
| G2 | `uv run pytest api/tests/` | All tests pass; suite size ≥ 105 (down from 111 if we deleted SSE replay test) |
| G3 | `HERMES_HOME=$(pwd)/.hermes hermes config show` | No "unknown key" warnings; provider=anthropic, default=claude-sonnet-4-6 |
| G4 | `ls .hermes/skills/govcapture/` | Exactly 5 dirs: extract_requirements_with_evidence, score_fit_with_eligibility_check, detect_risks_calibrated, generate_full_action_package, generate_reject_summary |
| G5 | `ls tasks/ devdocs/` | No AGENT_ARCHITECTURE.md, no HERMES_INTEGRATION_PLAN.md, no SOUL.md |
| G6 | `ls devdocs/MICHAELA_SYSTEM_MODEL.md devdocs/CAPABILITY_PACK_INTEGRATION.md` | Both exist |
| G7 | `grep -rn "Hermes is wired\|the bench lives here" devdocs/ tasks/ HERMES.md README.md PRD.md` | (empty) |
| G8 | `grep -rcn "Gate\b\|Ledger\b" devdocs/ tasks/ HERMES.md README.md PRD.md` | Hits, if any, are not naming agents (e.g., "gate-keeping" is fine; "Gate is the eligibility owner" is not) |
| G9 | `uv run python -c "from api.main import app; print(len([r for r in app.routes if hasattr(r,'path')]))"` | ≥ 22 (one less than before due to dropping orchestration trigger; exact number depends on resource count) |
| G10 | `uv run python -c "import asyncio; from api.config import get_settings; from supabase import acreate_client; get_settings.cache_clear(); s = get_settings(); asyncio.run((lambda: acreate_client(s.supabase_url, s.supabase_service_role_key))())"` then `/healthz` smoke | 200 OK against live Supabase |
| G11 | `uv run ruff check api` | All checks passed |
| G12 | `uv run mypy api` | 0 errors |

---

## 12. "Ask first" triggers (stop and surface to human)

Stop and ask before doing any of these:

1. **Renaming or moving files outside the explicit list in this handoff.**
2. **Deleting tests** beyond the SSE-replay test mentioned in Phase 0.
3. **Modifying `api/skills/<name>/skill.py`** beyond imports — the
   skills themselves are not in scope.
4. **Modifying `api/repositories/`, `api/routes/` (other than agent_runs.py)**
   for any reason other than the explicit Phase 0 surgery.
5. **Touching `supabase/migrations/`, `schemas/*.json`, `fixtures/`** —
   not in scope.
6. **Touching `web/` or `landing/`** — separate phase.
7. **Pushing to a git remote** — never without explicit "push" instruction.
8. **Running `npm install` or `uv sync`** unless dependency changes are
   in scope (none are in this rewrite).
9. **Encountering a concurrent edit that contradicts this handoff** —
   re-read, then surface the conflict before reconciling.
10. **Running anything that costs money** (Anthropic API calls,
    OpenRouter calls) — not needed for the doc rewrite.

---

## 13. Risk register

| # | Risk | Mitigation |
|---|------|-----------|
| R1 | Concurrent edits to docs (parallel tool / human) cause merge thrash. | Re-read each file just before writing. Commit per phase to keep diffs small. |
| R2 | Removing `api/agent/` breaks something that imports it indirectly. | `grep -rn "api.agent\|from api.agent"` before deletion. Run full pytest after. |
| R3 | `tests/test_routes.py::test_sse_replays_first_event` (or similar SSE-replay test) fails after Phase 0. | Delete the test (it tests orchestration we're removing). Don't try to "fix" it. |
| R4 | `.hermes/config.yaml` rewrite breaks existing dev workflows. | Anyone who was running `hermes` against this repo's `.hermes/` was likely seeing stale/invalid config anyway (per audit). Document the new dev-only purpose in the rewritten file's header. |
| R5 | The `MICHAELA_SYSTEM_MODEL.md` and `CAPABILITY_PACK_INTEGRATION.md` files require knowledge of /root/michealaai which this session doesn't have direct access to. | Write what we know with confidence (architecture, work-loop pattern, worker bench from this handoff). Mark anything specific to michealaai code as "see /root/michealaai/<path> for canonical". Don't guess. |
| R6 | The human renames more workers between sessions (e.g., "actually Gabby is now Cara"). | Worker names appear in maybe 30 places in this repo's docs. The renames are mechanical. If a future rename happens, do another pass. |
| R7 | A worker's tool dependency in our skills doesn't match what michealaai expects. | Out of scope for this rewrite. Surface to human if discovered. |

---

## 14. Success criteria (when you're done)

You're done when **all of the following** are true:

1. **All 12 verification gates (G0–G12) pass.**
2. **The repo's docs accurately describe a capability pack**, not an
   orchestrator or a self-contained agent system.
3. **`api/agent/` is gone**; `agent_runs.py` is CRUD-only; no test or
   route imports `api.agent.*`.
4. **`MICHAELA_SYSTEM_MODEL.md` and `CAPABILITY_PACK_INTEGRATION.md`
   exist** and reference each other + V1_PRODUCT_ALIGNMENT correctly.
5. **`PRD.md` has a v1.2.5 changelog** entry covering the
   repositioning + the deletions.
6. **Worker names are consistent** (Gabby, Lance) across docs.
7. **`pytest`, `ruff`, `mypy` all green.**
8. **`/healthz` still 200** against live Supabase + Redis.
9. **A grep for misleading claims** (`grep -rn "Hermes is wired\|the bench lives here"`)
   returns nothing.
10. **The human has been notified** of any "ask first" trigger you hit
    and given direction.

When 1–10 are all true, summarize the changes (one short paragraph),
list the commits made, and stop. Don't proceed to the next sprint
(plugin + HTTP API) without explicit approval.

---

## 15. After the doc rewrite — preview of next sprints

The doc rewrite is preparation for two follow-up sprints:

### Sprint A: Hermes plugin (`hermes_plugin_govcapture/`) — 3–5 days

Build the Python plugin that registers our pack's tools so Michaela's
Hermes-hosted workers can native-call them. See
`devdocs/CAPABILITY_PACK_INTEGRATION.md` (which you'll write in Phase 5).

### Sprint B: HTTP-API parity for non-Hermes callers — 1–2 days

Add `POST /tools/<name>` endpoints so any TypeScript / Codex / Cursor
agent that doesn't run in Hermes can still call our tools. Same Python
adapters under the hood; just a different transport.

These two sprints, plus the `/web` product UI build-out (3–5 days) and
VX1 deploy (4–8h), bring the pack from "doc-correct, infrastructure-only"
to "real human can sign up, run a bid analysis, get a memo from a
production URL." Estimated full path: ~10–14 additional days after this
handoff's doc rewrite is done.

---

## 16. Quick-reference: what to copy when handing off again

If you need to spin up another fresh agent later, paste this entire file
plus a short prefix:

```
You are continuing work on /Volumes/CS_Stuff/govcon — the GovCon Bid Desk
capability pack — picking up after the [Phase X] sprint completed in the
prior session.

The complete onboarding context is in devdocs/HANDOFF_PROMPT.md (this
file). Read it top to bottom before doing anything. Use it as your single
source of truth for architecture, decisions, and conventions. The
specific task for this session is: [INSERT TASK].

When in doubt, follow Section 12 ("Ask first" triggers) and stop to ask
the human rather than guessing.
```

---

**End of handoff. Now read it again before starting.**
