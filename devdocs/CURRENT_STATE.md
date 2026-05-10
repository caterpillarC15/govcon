# GovCon — Current State of the Repo

> Canonical synthesis dated **2026-05-09**. This doc supersedes any older
> PRD or task markdown that contradicts it. When this doc disagrees with
> `PRD.md` or `tasks/*.md`, **this doc wins** until those files are
> rewritten to match.

This is the single page a new contributor (or a future agent session) reads
to know where the product stands. It captures (1) what the system is, (2) what
ships today, (3) the seven named agents, (4) the data + auth model, (5) the
recent architecture decisions and the artifacts they left behind.

---

## 1. The product

**GovCon Bid Desk Operator** — a hired AI worker that finds federal contracts
worth bidding, decides pursue / monitor / skip, and turns every opportunity
into a bid memo and action plan with a human-approval gate before anything
goes out the door.

Public-facing language: bid desk operator, contract scout, pursuit plan,
bid/no-bid decision. Internal language: capture, pipeline, compliance matrix.

Strategic horizon (`devdocs/CAPABILITY_PACKS_CANVAS.md`): GovCon is the
first **capability pack** — a callable specialist that other agents (or a
human's personal agent) can rent. Document-processor, FBA, and ads packs
follow. The MVP stays scoped to the GovCon pack.

---

## 2. The seven agents (the bench)

Michaela is the product/workloop. Hermes is the runtime shell around it.
Anthropic/OpenRouter are model transport choices only. The tracked FastAPI
runtime currently executes the seeded Michaela bridge; live Hermes
CLI/sub-agent execution is still a pending integration.

The system runs as a CEO + 6 specialists. Roles, ownership, and one-line
outputs:

| # | Agent | Role | Owns | Sample output |
|---|-------|------|------|---------------|
| 1 | **Michaela** | CEO / orchestrator | The whole board, priorities, the user-facing answer | "1 worth pursuing • 12 days left • 2 gaps • Bid memo ready" |
| 2 | **Scot** | Discovery / SAM.gov bulk scan | Top-of-funnel opportunity discovery | "Found 81,031 → next 90 days 14,000 → matched 42" |
| 3 | **Lenny** | Fit ranking | Pursue / monitor / skip decision support | "Pursue 2 • Monitor 6 • Skip 39 • Best fit: VA Cybersecurity Support" |
| 4 | **Gabby** | Eligibility blocker check | The hard-no compliance gate (§11.1) | "Eligible? no - Blocker: missing clearance - Do not bid" |
| 5 | **Lance** | Competitive intelligence | Past awards, incumbents, market history | "Incumbent: Tetra Tech - won 3x - difficulty: hard - prob 22%" |
| 6 | **Happer** | Execution runner | Repeatable boring jobs, retries, file moves | "Job done • rows processed • files written • errors found" |
| 7 | **Roy** | Packaging / handoff | User-ready delivery (memo, email, capability statement) | "Bid memo ready • capability statement drafted • email ready" |

**Michaela is the only agent that talks to the user-facing API.** Every run
starts with Michaela. The other six are sub-agents she delegates to. The
delegation chain is enforced through Hermes' `delegate_task(toolsets=[…])`
restriction — Michaela cannot call `parse_pdf`, Gabby cannot call
`search_sam`, etc. Architecture is enforced at the toolset boundary, not by
a prompt rule.

This 7-agent bench replaces the older "Capture Lead + Analyst + 3
specialists" five-agent design (preserved in
`tasks/AGENT_ARCHITECTURE.md`'s history section). The §11.1 eligibility
short-circuit, source-binding rule, no-fabrication rule, and approval gate
all carry over unchanged.

---

## 3. Architecture

```
┌─────────────────────────┐      HTTP       ┌────────────────────────────────────┐
│ /web (Next 15)          │ ───────────────▶│ FastAPI proxy                       │
│ React 19, Tailwind 4    │   Bearer JWT    │  routes/                            │
│ EventSource (SSE)       │ ◀─── SSE  ──────│   - healthz, waitlist, profiles,    │
└─────────────────────────┘                 │     company-profiles, agent-runs,   │
                                            │     opportunities, action-packages   │
                                            │  auth: AuthenticatedUser (JWT)      │
                                            │        InternalActor (X-Internal-…) │
                                            │  llm.py (Anthropic SDK)             │
                                            │  storage.py (Supabase Storage REST) │
                                            │  agent/hermes_runner.py             │
                                            │  agent/hermes_bridge.py             │
                                            │  agent/replay.py (explicit demo)    │
                                            │  skills/  (the bench's tool surface) │
                                            └─────┬───────────────────┬────────────┘
                                                  │                    │
                                                  ▼                    ▼
                                       ┌─────────────────────┐  ┌──────────────┐
                                       │ Supabase project    │  │ Redis (local │
                                       │  - Postgres (DB)    │  │  or VX1)     │
                                       │  - Auth (GoTrue)    │  │  pub/sub for │
                                       │  - Storage bucket   │  │  SSE bridge  │
                                       │    govcapture-…     │  └──────────────┘
                                       └─────────────────────┘
```

The data layer is Supabase **PostgREST** (via `supabase-py`'s `AsyncClient`).
SQLAlchemy / asyncpg / Alembic are gone (PRD v1.2.4). Schemas live as
versioned SQL under `supabase/migrations/` and are applied with
`supabase db push`.

---

## 4. Tech stack as it actually is

| Layer       | Today                                                                |
|-------------|----------------------------------------------------------------------|
| Backend     | Python 3.12, FastAPI, `uv` for deps                                  |
| **DB**      | Supabase Postgres via **`supabase-py` AsyncClient (PostgREST)**      |
| **Auth**    | Supabase Auth bearer JWT (`AuthenticatedUser`) + internal API key (`InternalActor`) |
| **Schema mgmt** | `supabase/migrations/*.sql` applied with the Supabase CLI       |
| Storage     | Supabase Storage REST API via httpx (`api/storage.py`)               |
| Pub/sub     | Redis (`redis.asyncio`) for SSE event fan-out                        |
| LLM         | Anthropic SDK (Sonnet 4.6 synth, Haiku 4.5 dev)                      |
| PDFs        | pypdf for parse, reportlab+Pillow for fixture PDFs                   |
| Frontend    | Next 15 App Router, React 19, Tailwind 4, zod, `landing/`            |
|             | (marketing) + `/web` (product, skeleton)                             |
| Agent core  | Michaela workloop; seeded FastAPI bridge today, live Hermes runtime pending |
| Deploy      | Vultr VX1 (Ubuntu 24.04), gunicorn + systemd, nginx, certbot         |
|             | Vercel for `/landing` + `/web`                                       |

Dropped from earlier states: SQLAlchemy 2.0, asyncpg, alembic, Docker,
on-box Postgres, the dev1-backend / dev2-frontend two-track folder layout,
the `/var/lib/govcapture` filesystem layout for solicitation files.

---

## 5. Data model — current tables

Eight core tables (govbase-style normalized) plus five Michaela-layer tables
plus ownership columns added 2026-05-09. SQL lives in
`supabase/migrations/`.

**Core (`20260509132830_create_govcon_core.sql`):**

| Table | Purpose |
|-------|---------|
| `psc_codes`, `naics_codes`, `agencies`, `agency_subsidiaries`, `locations`, `contacts` | Reference / dimension tables |
| `company_profiles` | The buyer's company profile (one row per ICP entity) |
| `opportunities` | A federal opportunity (denormalized list fields + FKs) |
| `opportunity_contacts` | Junction: opportunity ↔ contact |
| `extracted_requirements` | Per-opportunity requirements (Gabby writes) |
| `fit_scores` | Per-opportunity per-profile fit (Lenny + Gabby write) |
| `risk_flags` | Per-opportunity per-profile risks (Gabby writes) |
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
(`get_owned`) only return rows the calling user owns. Row-Level Security
is enabled on every table; service-role bypasses RLS for internal writes.

**Provenance (`20260509132444_remote_schema.sql`):**
the original Supabase remote-schema dump (kept for completeness; will
collapse into the others on the next squash).

---

## 6. API surface (what's live on `main`)

| Verb + path                                  | Auth          | Purpose                                                  |
|----------------------------------------------|---------------|----------------------------------------------------------|
| `GET  /healthz`                              | none          | Supabase ping + Redis ping                               |
| `POST /waitlist`                             | none          | Marketing capture                                        |
| `*    /profiles…`                            | JWT           | The signed-in Supabase user's profile                    |
| `GET  /company-profiles`                     | JWT (owner)   | List company profiles owned by the caller                |
| `POST /company-profiles`                     | JWT           | Create a company profile (owner = caller)                |
| `GET  /company-profiles/{id}`                | JWT (owner)   | Read a company profile (RLS-scoped)                      |
| `POST /agent-runs`                           | JWT           | Start a Michaela run                                     |
| `GET  /agent-runs/{id}`                      | JWT (owner)   | Read a run                                               |
| `GET  /agent-runs/{id}/opportunities`        | JWT (owner)   | The run's matched opportunities                          |
| `GET  /agent-runs/{id}/stream`               | JWT (owner)   | Server-Sent Events (Redis pub/sub bridge)                |
| `GET  /opportunities/{id}`                   | JWT           | Read an opportunity                                      |
| `GET  /opportunities/{id}/{requirements,fit-score,risks}` | JWT (owner-aware) | Per-opportunity analysis read paths       |
| `POST /opportunities/{id}/{requirements,fit-score,risks}` | **InternalActor** (X-Internal-API-Key) | Sub-agent writebacks |
| `GET  /action-packages/{id}`                 | JWT (owner)   | Read a Roy-produced package                              |
| `POST /action-packages`                      | **InternalActor** | Roy writeback                                        |

User-facing routes use Supabase JWT; sub-agent writebacks use a separate
internal API key so no human bearer token can reach the write path.

---

## 7. Skills (the bench's tool surface)

Concrete Python tools under `api/skills/<name>/`. Each is a thin async
function with declared input/output. Hermes' subagents call them through
toolset bundles (`gov_discovery`, `gov_compliance`, etc.).

| Skill | Owner agent | Status |
|-------|-------------|--------|
| `parse_goal` | Michaela | done |
| `parse_pdf` | Happer (per-attachment) | done |
| `extract_requirements` | Gabby | done |
| `score_fit` | Lenny + Gabby (§11.1 short-circuit) | done |
| `detect_risks` | Gabby | done |
| `generate_action_package` | Roy | done |
| `search_sam` | Scot | done |
| `fetch_attachment` | Happer | done |
| `rank_opportunities` | Lenny | done |
| `load_seeded_opportunities` | Scot (fixtures fallback) | done |

Not yet wired: a dedicated `query_usaspending` skill for Lance
(competitive intel). Currently Lance's outputs ride on the same
`risk_flags` table with a `category="competitor_history"` convention.

---

## 8. Recent architecture decisions (commit-grounded timeline)

| Date       | Decision                                                                                | Source                         |
|------------|-----------------------------------------------------------------------------------------|--------------------------------|
| 2026-05-09 | PRD v1.1 → v1.2 — §4.5 Agent Architecture, §11.1 eligibility, §13.1 demo               | `5498b81`, `b007d38`           |
| 2026-05-09 | Hermes Agent runtime adopted (PRD v1.2.2)                                               | `7079c81`, `tasks/AGENT_ARCHITECTURE.md` |
| 2026-05-09 | No Docker — apt + systemd both ends                                                     | `tasks/README.md` decision log |
| 2026-05-09 | Vultr VX1 deployment infra landed                                                       | `4afaea4`                      |
| 2026-05-09 | Supabase pivot (PRD v1.2.3) — Postgres off VX1 onto Supabase                            | `a07e534`, `f982286`           |
| 2026-05-09 | Phase 0 (POST writes, /web skel, fixture template) merged                               | `dc9d1d8`                      |
| 2026-05-09 | **Postgres tooling rip-out (PRD v1.2.4)** — SQLAlchemy + asyncpg + Alembic dropped; data layer is `supabase-py` PostgREST | this session     |
| 2026-05-09 | **Auth + ownership added** — Supabase JWT + InternalActor; `owner_profile_id` on user-facing tables | concurrent work    |
| 2026-05-09 | **Michaela 7-agent bench named** — Michaela CEO + Scot, Lenny, Gabby, Lance, Happer, Roy | this session                  |

---

## 9. What ships today vs. what's next

**Done (committed on `main` as of `dc9d1d8` plus the 2026-05-09 in-flight branch):**

- Schemas + Pydantic codegen (`make schemas`)
- Supabase migrations 0001 (remote dump) + 0002 (govcon core) + 0003 (Michaela layer) + 0004 (ownership)
- Auth: `AuthenticatedUser` (JWT-via-Supabase-`/auth/v1/user`) + `InternalActor` (X-Internal-API-Key)
- 4 user-facing repositories (opportunity, agent_run, company_profile, action_package) +
  2 user resources (profile, waitlist)
- 11+ FastAPI routes across 8 router files
- 10 skills (parse_goal, parse_pdf, extract_requirements, score_fit, detect_risks,
  generate_action_package, search_sam, fetch_attachment, rank_opportunities, load_seeded)
- Seeded Michaela SSE bridge (`api/agent/hermes_bridge.py`) plus explicit replay fallback
- Supabase Storage wrapper (`api/storage.py`)
- 4 fixture sets (strong-pursue, maybe, reject, adversarial-image-pdf) with `manifest.json` + PDFs + `build_pdf.py`
- VX1 bootstrap + deploy + nginx + systemd
- Landing site (Next 15 glassmorphism), product `/web` Supabase Auth seeded console
- `.hermes/{config.yaml, SOUL.md, skills/govcapture/}` skill manifests

**Next:**

- Lance's `query_usaspending` skill (separate writeback table)
- Live Hermes CLI/sub-agent mode behind `api/agent/hermes_runner.py`
- Eval harness (`eval/runner/`, `eval/goldens/`)
- `/web` product UI beyond the authenticated shell
- Email-out path for Roy's drafted contracting-officer messages

---

## 10. Env-var contract (current)

`api/config.py` is the single source of truth. Variables read by code:

| Variable                           | Required | Purpose                                          |
|------------------------------------|----------|--------------------------------------------------|
| `ANTHROPIC_API_KEY`                | yes      | Anthropic SDK + Hermes model                     |
| `SAM_API_KEY`                      | optional | Live SAM.gov; empty = seeded fixtures only       |
| `SUPABASE_URL`                     | yes      | Supabase project URL                             |
| `SUPABASE_SERVICE_ROLE_KEY`        | yes      | Server-only, bypasses RLS for internal writes    |
| `SUPABASE_ANON_KEY`                | yes      | Used by `require_user` JWT verification          |
| `SUPABASE_STORAGE_BUCKET`          | yes      | Default `govcapture-attachments`                 |
| `INTERNAL_API_KEY`                 | yes      | Header value for sub-agent writeback routes      |
| `REDIS_URL`                        | yes      | Redis pub/sub                                    |
| `HERMES_HOME`                      | yes      | Project-isolated Hermes state directory          |
| `HERMES_MODEL`                     | yes      | Default Hermes model (claude-sonnet-4-6)         |
| `LLM_DEV_MODEL` / `LLM_SYNTH_MODEL`| yes      | Haiku / Sonnet split                             |
| `RUN_BUDGET_USD/STEPS/SECONDS`     | yes      | PRD §4.5 budgets                                 |
| `DEMO_USE_SEEDED_ONLY`             | optional | true = no live SAM (PRD §13.1)                   |
| `CORS_ALLOWED_ORIGINS`             | optional | Comma-separated list (default localhost:3000/3001/5173) |
| `NEXT_PUBLIC_SUPABASE_URL`         | yes (/web) | Browser-safe Supabase URL                      |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`    | yes (/web) | Browser-safe Supabase anon key                 |
| `NEXT_PUBLIC_API_BASE`             | yes (/web + landing) | FastAPI base URL                        |

Dropped vs. earlier states: `DATABASE_URL`, `OPENAI_*`,
`NEXT_PUBLIC_APP_NAME`.

---

## 11. Where to look

| Topic | File |
|-------|------|
| Agent design | `tasks/AGENT_ARCHITECTURE.md` |
| Michaela/Hermes/provider boundary | `devdocs/MICHAELA_SYSTEM_MODEL.md` |
| Hermes runtime context | `HERMES.md` (root — auto-loaded by Hermes) |
| Hermes integration spec | `HERMES.md` (root) + `tasks/AGENT_ARCHITECTURE.md` |
| Per-agent persona | `.hermes/SOUL.md`, `.hermes/skills/govcapture/<skill>/SKILL.md` |
| API contracts | `tasks/CONTRACTS.md` |
| Schemas | `schemas/*.json`, generated `api/schemas/*.py` |
| Demo script | `tasks/DEMO.md` |
| Fixtures | `tasks/FIXTURES.md`, `fixtures/` |
| Deploy | `infra/RUNBOOK.md`, `infra/{bootstrap,deploy}.sh` |
| Strategy / why | `devdocs/CAPABILITY_PACKS_CANVAS.md`, `devdocs/V1_PRODUCT_ALIGNMENT.md` |
