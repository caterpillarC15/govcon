# GovCon Bid Desk capability pack — current state

> Canonical synthesis dated **2026-05-09** (PRD v1.2.5). This doc
> supersedes any older PRD section or task markdown that contradicts
> it. When this doc disagrees with `PRD.md` or `tasks/*.md`, **this doc
> wins** until those files are rewritten to match.

This is the single page a new contributor (or a future agent session)
reads to know what this repo is, what's wired today, and what lives
elsewhere. It captures (1) the product, (2) the four-layer
architecture, (3) what this repo owns and doesn't, (4) tech stack,
(5) data + auth model, (6) API surface, (7) skills, (8) recent
decisions, (9) what ships today vs. what's next, (10) env contract,
(11) where to look.

---

## 1. The product

**GovCon Bid Desk Operator** — a hired AI worker that finds federal
contracts worth bidding, decides pursue / monitor / skip, and turns
every opportunity into a bid memo and action plan with a human-approval
gate before anything goes out the door.

Public-facing language: bid desk operator, contract scout, pursuit
plan, bid/no-bid decision. Internal language: capture, pipeline,
compliance matrix.

Strategic horizon (`devdocs/CAPABILITY_PACKS_CANVAS.md`): GovCon is
the first **capability pack** — a callable specialist that other
agents (or a human's personal agent) can rent. Document-processor,
FBA, and ads packs follow.

---

## 2. The four-layer architecture

There are four layers in this product. Conflating them was the source
of nearly every misunderstanding before PRD v1.2.5.

```
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER — Michaela (TypeScript / Bun)                     │
│ Repo:    /root/michealaai (separate)                                │
│ Stack:   Bun + TypeScript                                           │
│ Tests:   bun test tests/*.test.ts                                   │
│ Core:    src/workloop/{types,agentPool,defaultAgents,taskQueue,     │
│                          openLoopStore,surfacing,workLoop}.ts       │
│                                                                     │
│ - Captures open loops; queues microtasks; assigns by capability;    │
│   stores results; decides resurfacing.                              │
│ - In-memory MVP today; Supabase tables planned.                     │
│ - Workers (judgment, depth-1 leaves):                               │
│     Scot   — SAM discovery / top-of-funnel                          │
│     Lenny  — fit ranking / profile matching                         │
│     Ledger  — incumbents / awards / competitive intel                │
│     Gate  — eligibility / compliance blockers (§11.1 owner)        │
│     Happer — execution runner (browser, files, overflow work)       │
│     Roy    — packaging / handoff (memo, email, capability statement)│
│                                                                     │
│ Michaela is the orchestrator, not a worker. The 6 workers are the   │
│ bench. "7 named entities" = Michaela + 6 workers.                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │ tool-calls (Hermes plugin) into
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ RUNTIME LAYER — hermes-agent (Nous Research)                        │
│ Install: ~/.hermes/    (per-user)                                   │
│ Provides: CLI/chat runtime, tool calling, skills                    │
│   (SKILL.md progressive disclosure), memory, provider config,       │
│   gateway, cron, subagents (delegate_task), profile/HERMES_HOME.    │
│                                                                     │
│ Hermes is NOT the product. Michaela uses Hermes as infrastructure.  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Hermes plugin (planned) +
                             │ HTTP REST today
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CAPABILITY-PACK LAYER — this repo (govcon)                          │
│ Stack: Python 3.12 + FastAPI + uv (backend)                         │
│        Next 15 + React 19 + Tailwind 4 (web/, landing/)             │
│                                                                     │
│ What it owns:                                                       │
│   - Shared tools (judgment-free mechanics) under api/skills/        │
│   - HTTP CRUD API under api/routes/                                 │
│   - Auth (api/auth.py): Supabase JWT + InternalActor                │
│   - Data layer: api/repositories/ via supabase-py PostgREST         │
│   - Storage wrapper: api/storage.py — Supabase Storage REST         │
│   - /web — direct-user product surface (Bid Desk UI)                │
│   - /landing — marketing site                                       │
│   - PLANNED: hermes_plugin_govcapture/ — Python plugin so           │
│     Michaela's Hermes-hosted workers can native-call our tools.     │
│                                                                     │
│ What it does NOT own:                                               │
│   - Michaela the orchestrator                                       │
│   - Work loop, agent pool, task queue, open-loop store              │
│   - The worker bench (those agents live in /root/michealaai)        │
│   - Orchestration recipes                                           │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ DATA + TRANSPORT                                                    │
│ Supabase project (PostgREST + Auth + Storage).                      │
│ Bucket: govcapture-attachments (private).                           │
│ Tables: company_profiles, opportunities, extracted_requirements,    │
│   fit_scores, risk_flags, action_packages, agent_runs, profiles,    │
│   waitlist_signups, opportunity_matches, documents, document_chunks,│
│   run_events, dimension tables.                                     │
│ R2 (planned): raw files. Today using Supabase Storage end-to-end.   │
│ Redis: SSE pub/sub bridge (native; Supabase Realtime is deferred).  │
└─────────────────────────────────────────────────────────────────────┘
```

**Operating rule.** Mechanics belong in shared tools. Judgment belongs
in agents. Contracts belong in schemas. Michaela owns the board. If
this pack starts to grow "decide whether to bid" logic, that's a
worker's job (Gate, Lenny) running in Michaela's Hermes — not ours.

---

## 3. What this repo IS

- A **capability pack**: tools + data + product UI.
- A FastAPI service exposing CRUD + tool-call HTTP endpoints (latter
  planned per `devdocs/CAPABILITY_PACK_INTEGRATION.md`).
- The owner of the GovCon-domain Python skills and the SQL migration
  set.
- The owner of the direct-user product surface (`/web`) and marketing
  surface (`/landing`).

## 4. What this repo IS NOT

- Not the orchestrator. Michaela lives in `/root/michealaai`.
- Not the worker bench. Scot, Lenny, Ledger, Gate, Happer, Roy live
  in `/root/michealaai`.
- Not a runtime. We do not host an LLM-loop. `POST /agent-runs`
  persists a row; Michaela picks it up out of band.
- Not a Hermes home. The `.hermes/` here is for developer testing of
  this pack's tools in isolation, never loaded by FastAPI.

---

## 5. Tech stack as it actually is

| Layer       | Today                                                                |
|-------------|----------------------------------------------------------------------|
| Backend     | Python 3.12, FastAPI, `uv` for deps                                  |
| **DB**      | Supabase Postgres via **`supabase-py` AsyncClient (PostgREST)**      |
| **Auth**    | Supabase JWT (`AuthenticatedUser`) + internal API key (`InternalActor`) |
| **Schema mgmt** | `supabase/migrations/*.sql` applied with the Supabase CLI       |
| Storage     | Supabase Storage REST API via httpx (`api/storage.py`)               |
| Pub/sub     | Redis (`redis.asyncio`) — SSE event fan-out                          |
| LLM         | Anthropic SDK (Sonnet 4.6 synth, Haiku 4.5 dev)                      |
| PDFs        | pypdf for parse, reportlab+Pillow for fixture PDFs                   |
| Frontend    | Next 15 App Router, React 19, Tailwind 4, zod                        |
|             | `landing/` (marketing) + `/web` (product, authenticated shell)       |
| Deploy      | Vultr VX1 (Ubuntu 24.04), gunicorn + systemd, nginx, certbot         |
|             | Vercel for `/landing` + `/web`                                       |

Dropped from earlier states: SQLAlchemy 2.0, asyncpg, alembic, Docker,
on-box Postgres, the dev1-backend / dev2-frontend two-track folder
layout, the `/var/lib/govcapture` filesystem layout, and the in-repo
Hermes runner / seeded bridge / replay path. Orchestration now belongs
to `/root/michealaai`; this repo only exposes the contracts it calls.

---

## 6. Data model — current tables

SQL lives in `supabase/migrations/`.

**Core (`20260509132830_create_govcon_core.sql`):**

| Table | Purpose |
|-------|---------|
| `psc_codes`, `naics_codes`, `agencies`, `agency_subsidiaries`, `locations`, `contacts` | Reference / dimension tables |
| `company_profiles` | The buyer's company profile (one row per ICP entity) |
| `opportunities` | A federal opportunity (denormalized list fields + FKs) |
| `opportunity_contacts` | Junction: opportunity ↔ contact |
| `extracted_requirements` | Per-opportunity requirements (Gate writes) |
| `fit_scores` | Per-opportunity per-profile fit (Lenny + Gate write) |
| `risk_flags` | Per-opportunity per-profile risks (Gate writes) |
| `action_packages` | The §10.3 deliverable (Roy writes) |
| `agent_runs` | One row per Michaela run; trace + ids |

**Michaela layer (`20260509140333_michaela_mvp_layer.sql`):**

| Table | Purpose |
|-------|---------|
| `profiles` | One row per Supabase Auth user; FK into `auth.users` |
| `opportunity_matches` | Per-customer scoring (Lenny writes; `agent_name` records who) |
| `documents` | Pointer to a PDF in Supabase Storage / R2 |
| `document_chunks` | Page-level parsed text for evidence + citations |
| `run_events` | Append-only trace per `agent_run_id` (mirrors SSE) |

**Ownership (`20260509140838_add_ownership_and_provenance.sql`):**
adds `owner_profile_id` to user-facing tables so the JWT-scoped routes
(`get_owned`) only return rows the calling user owns. RLS is enabled
on every table; service-role bypasses RLS for internal writes.

**Provenance (`20260509132444_remote_schema.sql`):** original
Supabase remote-schema dump. Will collapse into the others on the
next squash.

---

## 7. API surface (what's live on `main`)

| Verb + path                                  | Auth          | Purpose                                                  |
|----------------------------------------------|---------------|----------------------------------------------------------|
| `GET  /healthz`                              | none          | Supabase ping + Redis ping                               |
| `POST /waitlist`                             | none          | Marketing capture                                        |
| `*    /profiles…`                            | JWT           | The signed-in Supabase user's profile                    |
| `GET  /company-profiles`                     | JWT (owner)   | List company profiles owned by the caller                |
| `POST /company-profiles`                     | JWT           | Create a company profile (owner = caller)                |
| `GET  /company-profiles/{id}`                | JWT (owner)   | Read a company profile (RLS-scoped)                      |
| `POST /agent-runs`                           | JWT           | Persist a run row. Michaela picks it up out of band.     |
| `GET  /agent-runs/{id}`                      | JWT (owner)   | Read a run                                               |
| `GET  /agent-runs/{id}/opportunities`        | JWT (owner)   | The run's matched opportunities                          |
| `GET  /agent-runs/{id}/stream`               | JWT (owner)   | Server-Sent Events (Redis pub/sub bridge)                |
| `GET  /opportunities/{id}`                   | JWT           | Read an opportunity                                      |
| `GET  /opportunities/{id}/{requirements,fit-score,risks}` | JWT (owner-aware) | Per-opportunity analysis read paths       |
| `POST /opportunities/{id}/{requirements,fit-score,risks}` | **InternalActor** (X-Internal-API-Key) | Sub-agent writebacks |
| `GET  /action-packages/{id}`                 | JWT (owner)   | Read a Roy-produced package                              |
| `POST /action-packages`                      | **InternalActor** | Roy writeback                                        |
| `POST /tools/<name>` (×10)                   | **InternalActor** | Direct skill dispatch for non-Hermes callers (Sprint B) |

User-facing routes use Supabase JWT; sub-agent writebacks use a
separate internal API key so no human bearer token can reach the
write path.

---

## 8. Skills (the pack's tool surface)

Concrete Python tools under `api/skills/<name>/`. Each is a thin
async function with declared input/output. Michaela's workers in
`/root/michealaai` call them through the planned Hermes plugin or
through HTTP. Owner column names which Michaela worker is the typical
caller.

| Skill | Typical caller | Status |
|-------|----------------|--------|
| `parse_goal` | Michaela | done |
| `parse_pdf` | Happer | done |
| `extract_requirements` | Gate | done |
| `score_fit` (with §11.1 short-circuit) | Lenny + Gate | done |
| `detect_risks` | Gate | done |
| `generate_action_package` | Roy | done |
| `search_sam` | Scot | done |
| `fetch_attachment` | Happer | done |
| `rank_opportunities` | Lenny | done |
| `load_seeded_opportunities` | Scot (fixtures fallback) | done |

Not yet wired: a dedicated `query_usaspending` skill for Ledger
(competitive intel). Currently Ledger's outputs ride on the same
`risk_flags` table with a `category="competitor_history"` convention.

The `.hermes/skills/govcapture/` directory holds five
**tool-procedure** SKILL.mds (extract_requirements_with_evidence,
score_fit_with_eligibility_check, detect_risks_calibrated,
generate_full_action_package, generate_reject_summary). These describe
how an agent should USE this pack's tools. They are not orchestration
recipes — those live in `/root/michealaai`.

---

## 9. Recent architecture decisions (commit-grounded timeline)

| Date       | Decision                                                                                              | Source                       |
|------------|-------------------------------------------------------------------------------------------------------|------------------------------|
| 2026-05-09 | PRD v1.1 → v1.2 — §4.5 Agent Architecture, §11.1 eligibility, §13.1 demo                              | `5498b81`, `b007d38`         |
| 2026-05-09 | Hermes Agent runtime adopted (PRD v1.2.2)                                                             | `7079c81`                    |
| 2026-05-09 | No Docker — apt + systemd both ends                                                                   | `tasks/README.md` decision log |
| 2026-05-09 | Vultr VX1 deployment infra landed                                                                     | `4afaea4`                    |
| 2026-05-09 | Supabase pivot (PRD v1.2.3) — Postgres off VX1 onto Supabase                                          | `a07e534`, `f982286`         |
| 2026-05-09 | Phase 0 (POST writes, /web skeleton, fixture template) merged                                         | `dc9d1d8`                    |
| 2026-05-09 | **Postgres tooling rip-out (PRD v1.2.4)** — SQLAlchemy / asyncpg / Alembic dropped                    | this session                 |
| 2026-05-09 | **Auth + ownership added** — Supabase JWT + InternalActor; `owner_profile_id` on user-facing tables   | concurrent work              |
| 2026-05-09 | **Michaela 7-agent bench named** — Michaela CEO + Scot, Lenny, Gate, Ledger, Happer, Roy              | this session                 |
| 2026-05-09 | **PRD v1.2.5 — repo repositioned as capability pack.** Orchestration code removed; bench moved to `/root/michealaai`. New docs: MICHAELA_SYSTEM_MODEL, CAPABILITY_PACK_INTEGRATION. | this session |

---

## 10. What ships today vs. what's next

**Done (committed on `main` as of `dc9d1d8` plus the 2026-05-09 in-flight branch):**

- Schemas + Pydantic codegen (`make schemas`)
- Supabase migrations (remote dump + govcon core + Michaela layer + ownership)
- Auth: `AuthenticatedUser` + `InternalActor`
- 4 user-facing repositories (opportunity, agent_run, company_profile,
  action_package) + 2 user resources (profile, waitlist)
- 29 FastAPI path operations across 8 router modules, including 10
  internal `/tools/<name>` skill dispatches added 2026-05-09
- 10 skills (parse_goal, parse_pdf, extract_requirements, score_fit,
  detect_risks, generate_action_package, search_sam, fetch_attachment,
  rank_opportunities, load_seeded)
- Supabase Storage wrapper (`api/storage.py`)
- 4 fixture sets (strong-pursue, maybe, reject, adversarial-image-pdf)
  with `manifest.json` + PDFs + `build_pdf.py`
- VX1 bootstrap + deploy + nginx + systemd
- Landing site (Next 15 glassmorphism), product `/web` Supabase Auth
  authenticated shell

**Next (this repo's queue):**

- Ledger's `query_usaspending` skill (separate writeback table)
- `hermes_plugin_govcapture/` — register tool adapters with Hermes for
  Michaela's workers (per `devdocs/CAPABILITY_PACK_INTEGRATION.md`)
- Eval harness (`eval/runner/`, `eval/goldens/`)
- `/web` product UI beyond the authenticated shell

**Owned by `/root/michealaai`, not us:**

- Michaela orchestrator + worker bench
- Per-opportunity orchestration recipe
- Trace event emission (we ship the schema; they emit against it)

---

## 11. Env-var contract (current)

`api/config.py` is the single source of truth. Variables read by code:

| Variable                           | Required | Purpose                                          |
|------------------------------------|----------|--------------------------------------------------|
| `ANTHROPIC_API_KEY`                | yes      | Anthropic SDK for skill-internal LLM calls       |
| `SAM_API_KEY`                      | optional | Live SAM.gov; empty = seeded fixtures only       |
| `SUPABASE_URL`                     | yes      | Supabase project URL                             |
| `SUPABASE_SERVICE_ROLE_KEY`        | yes      | Server-only, bypasses RLS for internal writes    |
| `SUPABASE_ANON_KEY`                | yes      | Used by `require_user` JWT verification          |
| `SUPABASE_STORAGE_BUCKET`          | yes      | Default `govcapture-attachments`                 |
| `INTERNAL_API_KEY`                 | yes      | Header value for sub-agent writeback routes      |
| `REDIS_URL`                        | yes      | Redis pub/sub                                    |
| `LLM_DEV_MODEL` / `LLM_SYNTH_MODEL`| yes      | Haiku / Sonnet split                             |
| `RUN_BUDGET_USD/STEPS/SECONDS`     | yes      | PRD §4.5 budgets                                 |
| `CORS_ALLOWED_ORIGINS`             | optional | Comma-separated list                              |
| `NEXT_PUBLIC_SUPABASE_URL`         | yes (/web) | Browser-safe Supabase URL                      |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`    | yes (/web) | Browser-safe Supabase anon key                 |
| `NEXT_PUBLIC_API_BASE`             | yes (/web + landing) | FastAPI base URL                       |

Dropped vs. earlier states: `DATABASE_URL`, `OPENAI_*`,
`NEXT_PUBLIC_APP_NAME`, `HERMES_HOME`, `HERMES_MODEL`,
`DEMO_USE_SEEDED_ONLY`, `DEMO_REPLAY_TRACE`.

---

## 12. Where to look

| Topic | File |
|-------|------|
| Layer model (orchestrator + pack) | `devdocs/MICHAELA_SYSTEM_MODEL.md` |
| Hermes plugin + HTTP API integration | `devdocs/CAPABILITY_PACK_INTEGRATION.md` |
| Public framing filter | `devdocs/V1_PRODUCT_ALIGNMENT.md` |
| Strategy / capability packs | `devdocs/CAPABILITY_PACKS_CANVAS.md` |
| Hermes runtime context (dev only) | `HERMES.md` (root) |
| API contracts | `tasks/CONTRACTS.md` |
| Schemas | `schemas/*.json`, generated `api/schemas/*.py` |
| Demo script | `tasks/DEMO.md` |
| Fixtures | `tasks/FIXTURES.md`, `fixtures/` |
| Landing copy | `tasks/LANDING_BRIEF.md` |
| Deploy | `infra/RUNBOOK.md`, `infra/{bootstrap,deploy}.sh` |
| Historical handoff | `devdocs/_archive/HANDOFF_2026-05-09.md` |
