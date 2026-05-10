# GovCon Bid Desk capability pack — current state

> Canonical synthesis dated **2026-05-10** (PRD v1.2.6). This doc
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
│ Supabase project `vvyxjdoenjujkxwbnzyl` (PostgREST + Auth + Storage)│
│ Bucket: govcapture-attachments (private).                           │
│ Tables: company_profiles, opportunities, extracted_requirements,    │
│   fit_scores, risk_flags, action_packages, agent_runs, profiles,    │
│   waitlist_signups, opportunity_matches, documents, document_chunks,│
│   run_events, dimension tables, plus §5.14 weekly-opportunity tables│
│   and (cohabitating) persona_* tables for the public-presence       │
│   project — see §6.5 below.                                         │
│ R2 (planned): raw files. Today using Supabase Storage end-to-end.   │
│ Redis: SSE pub/sub bridge (native; Supabase Realtime is deferred).  │
└─────────────────────────────────────────────────────────────────────┘
```

### Three Supabase projects on Michaela's host — disambiguation

Discovered 2026-05-10: there are three Supabase instances in use across
this product family. Don't conflate them.

| Project ref | Purpose | Who reads/writes | Schema source |
|---|---|---|---|
| `vvyxjdoenjujkxwbnzyl` | **This pack + persona/public-presence (shared project).** All our migrations live here. Bucket `govcapture-attachments` private; bucket `persona-assets` public (different namespace). | This repo's FastAPI; Michaela's orchestrator pickup loop. | `supabase/migrations/*.sql` here is canonical for the govcon-pack tables. Persona tables (`personas`, `persona_profiles`, `persona_assets`, …) come from a separate skill in `/root/michealaai`. |
| `ktygrvbpugqhfyibzirr` | **Michaela's competitive-intel warehouse.** Tables: `agencies`, `contractors`, `contracts`, `psc_win_patterns`, `customer_profiles`. | Lance (competitive-intel worker) reads. Not used by this pack. | Owned by `/root/michealaai`. |
| `pooler.supabase.com` (project ref unknown) | GBrain / knowledge-base. | `/root/gbrain`. | Wholly separate; documented for context only. |

**Cohabitation risk to watch:** `vvyxjdoenjujkxwbnzyl` carries both this
pack's private data (action packages, fit scores, run rows) AND the
persona project's public-bucket assets (`persona-assets/michaela/profile/`).
Confirm `govcapture-attachments` is bucket-public=`false` in Studio
before any production send. The persona schema and our schema do not
share a table that we own — table names like `agent_runs` are ours;
`persona_*` are theirs.

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

PRD v1.2.6 (2026-05-10) further dropped: `api/llm.py`, the `anthropic`
SDK, `ANTHROPIC_API_KEY`, `LLM_DEV_MODEL`, `LLM_SYNTH_MODEL`, and the
`RUN_BUDGET_USD/STEPS/SECONDS` env vars. Skills are deterministic; LLM
calls live in `/root/michealaai` with Michaela's bench.

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
| `GET  /opportunities/{id}/competitors`       | JWT (owner)   | Ledger competitive-intel list                            |
| `POST /opportunities/{id}/competitors`       | **InternalActor** | Ledger writeback                                      |
| `GET  /action-packages/{id}`                 | JWT (owner)   | Read a Roy-produced package                              |
| `POST /action-packages`                      | **InternalActor** | Roy writeback                                        |
| `POST /tools/<name>` (×11)                   | **InternalActor** | Direct skill dispatch for non-Hermes callers      |
| `POST /api/keys`                             | JWT           | Mint per-agent gck_… API key                             |
| `GET  /api/keys`                             | JWT           | List caller's API keys                                   |
| `DELETE /api/keys/{id}`                      | JWT           | Revoke a key                                             |
| `POST /api/v1/tools/<name>` (×11)            | gck_ or InternalActor | Public skill dispatch (per-agent bearer) |
| `GET  /.well-known/agent.json`               | none          | Agent discovery manifest                                  |
| `GET  /.well-known/llms.txt`                 | none          | LLM agent description                                     |

The Next.js `/landing` site additionally serves `GET /agents` (with JSON-LD `SoftwareApplication`) and `GET /robots.txt`; those are not FastAPI routes.

User-facing routes use Supabase JWT; sub-agent writebacks use a
separate internal API key (X-Internal-API-Key header) or per-agent
bearer token (gck_…) so no human bearer token can reach the write path.

**Route count:** **53** total — 11 `/api/v1/tools/<name>` (public, gck_) + 11 `/tools/<name>` (internal) + 3 `/api/keys` + 4 `/agent-runs` + 3 `/company-profiles` + 2 `/profiles/me` + 1 `/opportunities/{id}` + 8 `/opportunities/{id}/{requirements,fit-score,risks,competitors}` (4 GET + 4 POST) + 2 `/action-packages` + 2 `/.well-known/*` + 1 `/healthz` + 1 `/waitlist` + 4 FastAPI auto (`/docs`, `/docs/oauth2-redirect`, `/redoc`, `/openapi.json`).

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
| `query_usaspending` | Ledger | done |

Ledger's competitive-intel outputs persist to the dedicated
`competitor_history` table (migration `20260510120100`) — the prior
workaround of riding on `risk_flags` with `category="competitor_history"`
was retired when the skill landed.

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

**Done (committed on `main` as of 2026-05-10, launch-runway sprint):**

- Schemas + Pydantic codegen (`make schemas`)
- Supabase migrations (remote dump + govcon core + Michaela layer + ownership + api_keys + competitor_history)
- Auth: `AuthenticatedUser` + `InternalActor` + per-agent gck_… bearer tokens
- Per-agent API key minting + rate limiting (Redis-backed; fail-open)
- 4 user-facing repositories (opportunity, agent_run, company_profile, action_package) + 2 user resources (profile, waitlist)
- 53 FastAPI path operations across 10 router modules, including 11 public `/api/v1/tools/<name>` + 11 internal `/tools/<name>` + 3 /api/keys + 2 /opportunities/{id}/competitors + 2 /.well-known/*
- 11 skills (parse_goal, parse_pdf, extract_requirements, score_fit, detect_risks, generate_action_package, search_sam, fetch_attachment, rank_opportunities, load_seeded_opportunities, query_usaspending)
- Supabase Storage wrapper (`api/storage.py`)
- 4 fixture sets (strong-pursue, maybe, reject, adversarial-image-pdf) with `manifest.json` + PDFs + `build_pdf.py`
- VX1 bootstrap + deploy + nginx + systemd (runbook in `infra/RUNBOOK.md`)
- Landing site (Next 15 glassmorphism) with SEO (robots.txt, JSON-LD SoftwareApplication)
- Product `/web` with authenticated shell + loading skeletons + error boundaries + SSE stream upgrade
- MCP server package (`mcp-server-govcapture` wrapping `/api/v1/tools`)
- Eval harness — byte-exact regression gate (PRD v1.2.6, deterministic-only). Goldens committed under `fixtures/<slug>/goldens/`; `make eval` PASSes today.
- ApprovalGate server-side persistence: `POST /action-packages/{id}/approve` + `approved_at`/`approved_by` columns + frontend wire-up (commit `93e396b`)
- SSE polish: RunTimeline memoize + dedupe + partial badge (commit `0f03693`)
- Auth hardening: `getSession`→`getUser` via `requireUser` helper across 9 web routes + middleware (commit `6827594`)
- `make schemas` idempotent + scoped to generated-only files; 6 hand-written modules preserved (commit `c74a9ce`)
- **PRD §5.14 weekly opportunity email — shipped end-to-end, behind `EMAIL_DRY_RUN=true`** (commits `685a8b5`, `1910631`, `3a916a4`):
  schema (`waitlist_signups` columns + `weekly_opportunity_picks` + `weekly_opportunity_email_log`), 14 new env vars + production refuse-to-start guard, HMAC unsubscribe token service, Resend HTTP client, deterministic safety filters (set-aside, deadline, US PoP, clearance keywords, NAICS allowlist, attachments), LLM auto-picker against synthetic SMB profile, Monday send job with two-phase claim, public `/email-subscriptions/unsubscribe` (GET HTML + RFC 8058 POST one-click), two internal `/internal/cron/*` routes (Bearer `INTERNAL_API_KEY`), `scripts/pick_weekly_opportunity.py` curator override, two systemd timers (`govcapture-cron-auto-pick.timer` Sun 22:00 UTC + `govcapture-cron-weekly.timer` Mon 14:00 UTC).
- 199 passing tests (186 prior + 13 §5.14: safety×4, unsubscribe HMAC×2, render×1, cron auth×3, production guard×2, week-key format×1)

**Next (this repo's queue) — all gated on external action:**

- Phase 5: Resend account + DNS + Supabase Studio SMTP (Channel A magic-link); also unblocks `RESEND_API_KEY` for Channel B (§5.14 weekly opportunity email).
- Phase 6: Vultr VX1 production deploy (Vultr account + DNS + Vercel env). Once deployed, enable §5.14 cron timers via `systemctl enable --now govcapture-cron-auto-pick.timer govcapture-cron-weekly.timer`.
- Phase 7: Sprint G cross-repo e2e (coordination with `/root/michealaai`).
- §5.14 production-flip: see `devdocs/LAUNCH_CHECKLIST.md` §9. Sequence is dry-run smoke test → flip `EMAIL_DRY_RUN=false` → self-test send → enable timers.
- Phase 9: v1.0.0 git tag (gated on 5/6/7 above).

**Schema state (verified 2026-05-10 via `supabase migration list` — all applied):**

| Local timestamp | Remote timestamp | Status |
|---|---|---|
| 20260509132444 | 20260509132444 | applied (remote_schema baseline) |
| 20260509132830 | 20260509132830 | applied (govcon core) |
| 20260509140333 | 20260509140333 | applied (Michaela MVP layer) |
| 20260509140838 | 20260509140838 | applied (ownership + provenance) |
| 20260509203000 | 20260509203000 | applied (waitlist) |
| 20260510021500 | 20260510021500 | applied (remote-drift placeholder; see below) |
| 20260510024000 | 20260510024000 | applied (remote-drift placeholder; see below) |
| 20260510092040 | 20260510092040 | applied (action_package approval columns) |
| 20260510120000 | 20260510120000 | applied (api_keys table) |
| 20260510120100 | 20260510120100 | applied (competitor_history table) |

Two timestamps (`20260510021500`, `20260510024000`) were applied to the
linked Supabase project outside this repo (likely Studio edits). They
exist locally as **empty placeholder files** so the Supabase CLI sees
local + remote histories as synchronized. A fresh project provisioned
from `supabase/migrations/` would NOT have whatever those two
migrations did; resolve in a post-v1 schema squash by inspecting via
Studio and authoring equivalent migrations.

**Owned by `/root/michealaai`, not us:**

- Michaela orchestrator + worker bench
- Per-opportunity orchestration recipe
- Trace event emission (we ship the schema; they emit against it)
- LLM cost + budget tracking (PRD v1.2.6 — pack is deterministic; Michaela owns provider auth)

---

## 11. Env-var contract (current)

`api/config.py` is the single source of truth. Variables read by code:

| Variable                           | Required | Purpose                                          |
|------------------------------------|----------|--------------------------------------------------|
| `SAM_API_KEY`                      | optional | Live SAM.gov; empty = seeded fixtures only       |
| `SUPABASE_URL`                     | yes      | Supabase project URL (`vvyxjdoenjujkxwbnzyl`)    |
| `SUPABASE_SERVICE_ROLE_KEY`        | yes      | Server-only, bypasses RLS for internal writes    |
| `SUPABASE_ANON_KEY`                | yes      | Used by `require_user` JWT verification          |
| `SUPABASE_STORAGE_BUCKET`          | yes      | Default `govcapture-attachments`                 |
| `INTERNAL_API_KEY`                 | yes      | Header value for sub-agent writeback routes; also Bearer for `/internal/cron/*` |
| `REDIS_URL`                        | yes      | Redis pub/sub                                    |
| `CORS_ALLOWED_ORIGINS`             | optional | Comma-separated list                             |
| `RESEND_API_KEY` + `EMAIL_*` (×13) | yes (prod) | §5.14 weekly opportunity email; production guard refuses start unless required keys are set when `EMAIL_DRY_RUN=false` |
| `NEXT_PUBLIC_SUPABASE_URL`         | yes (/web) | Browser-safe Supabase URL                      |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`    | yes (/web) | Browser-safe Supabase anon key                 |
| `NEXT_PUBLIC_API_BASE`             | yes (/web + landing) | FastAPI base URL                       |
| `NEXT_PUBLIC_SITE_URL` / `NEXT_PUBLIC_APP_URL` | yes (/web + landing) | Canonical landing + app URLs |

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
| Fixtures | `tasks/FIXTURES.md`, `fixtures/` |
| Landing copy | `tasks/LANDING_BRIEF.md` |
| Deploy | `infra/RUNBOOK.md`, `infra/{bootstrap,deploy}.sh` |
| Continuation prompt | `devdocs/HANDOFF_PROMPT.md` |
| Active plans | `docs/superpowers/plans/2026-05-10-finish-it-all.md`, `docs/superpowers/plans/2026-05-10-frontend-cleanup-fixes.md` |
