# GovCon Bid Desk capability pack — continuation handoff

> **Read top to bottom before doing anything.** This single file is
> designed to be pasted into a fresh Claude Code, Codex, or comparable
> agent session running against `/Volumes/CS_Stuff/govcon`. It picks up
> where the **2026-05-10 launch-runway and frontend-cleanup sprints**
> left off, on top of PRD v1.2.5. The pre-v1.2.5 handoff (capability-pack
> repositioning) was deleted as part of the doc-redundancy sweep.

---

## 0. Who you are and what you're being asked to do

You are an engineer continuing the **GovCon Bid Desk capability pack**.
The previous session (where this handoff was written) finished the
v1.2.4 → v1.2.5 repositioning: it removed in-repo orchestration code,
slimmed the Hermes config to schema-correct dev-only, deleted misplaced
orchestrator docs, archived the prior handoff, rewrote every live doc,
and locked the canonical worker names as **Gate** (eligibility) and
**Ledger** (competitive intel).

Your job in this session:

1. **Read the entire handoff before touching anything.** The earlier
   session burned cycles on rework when sub-agents skipped this step.
2. **Confirm Section 1 ("Verified state") still holds** by spot-checking
   `git log -8`, `git status`, and `uv run pytest api/tests/`. Don't
   trust this doc blindly; the repo is the source of truth.
3. **Pick a sprint from Section 7** with the user. Don't start before
   the user has confirmed which sprint and (where ambiguous) what flavor.
4. **Execute the chosen sprint phase by phase** per its dedicated
   section (8–14).
5. **Verify the gates in Section 16** before declaring any phase done.
6. **Stop and ask** when you hit any "ask first" trigger in Section 17.

Estimated runway from this handoff to a public launch:
**~10–14 days** of competent solo work, broken across 5–7 sprints. The
prerequisites are already in place: Supabase linked, schema applied,
auth wired, env files gitignored, full test suite green.

---

## 1. Verified state at handoff (what's true RIGHT NOW)

Verified 2026-05-10 after the launch-runway sprint, the post-runway
frontend/agent fix patch (`5ff99cb`, `310bb`, `a03591f`, `f5a2e48`), and
the finish-it-all execution session (`93e396b`, `0f03693`, `6827594`,
`c74a9ce`, `47ba676`, `435acac`).

| Check | Result |
|-------|--------|
| Branch | `main`, working tree clean, up-to-date with `origin/main` |
| `uv run pytest api/tests/` | **186 passed** (183 baseline + 3 from action_package approve route) |
| `uv run ruff check api` | All checks passed |
| `uv run mypy api` | Success: no issues found in **76 source files** |
| `uv run python -c "from api.main import app; print(sum(1 for r in app.routes if hasattr(r,'path')))"` | **53** routes — 11 `/api/v1/tools/<name>` + 11 `/tools/<name>` + 3 `/api/keys` + 4 `/agent-runs` + 3 `/company-profiles` + 2 `/profiles/me` + 9 `/opportunities*` + 2 `/action-packages` + 2 `/.well-known/*` + 1 `/healthz` + 1 `/waitlist` + 4 FastAPI auto |
| `npm -w landing run build && npm -w web run build` | Both Next 15 builds clean (clear `.next/` if you see a stale `_not-found` collect-page-data error — the `transpilePackages: ['lucide-react']` fix is in `landing/next.config.mjs`) |
| `npm -w landing run lint && npm -w web run lint && npm -w web run typecheck` | All clean |
| `make fixtures-validate` | OK for all 4 fixtures (strong-pursue, maybe, reject, adversarial-image-pdf) |
| `HERMES_HOME=$(pwd)/.hermes hermes config show` | Reads model.provider=anthropic, default=claude-sonnet-4-6; no unknown-key warnings |
| `find api/agent -type f` | (empty — directory gone) |
| `grep -rn 'from api\.agent' api/` | (empty) |
| `ls .hermes/skills/govcapture/` | exactly 5 dirs: `extract_requirements_with_evidence`, `score_fit_with_eligibility_check`, `detect_risks_calibrated`, `generate_full_action_package`, `generate_reject_summary` |
| `ls tasks/` | `CONTRACTS.md FIXTURES.md LANDING_BRIEF.md README.md` (DEMO/INTERFERENCE_MAP retired in the 2026-05-10 doc sweep) |
| `ls devdocs/` | `CAPABILITY_PACK_INTEGRATION.md CAPABILITY_PACKS_CANVAS.md CURRENT_STATE.md HANDOFF_PROMPT.md MICHAELA_SYSTEM_MODEL.md V1_PRODUCT_ALIGNMENT.md` (no `_archive/`) |
| `git check-ignore .env` | matches `.env` (real keys safely uncommitted) |
| Bucket `govcapture-attachments` | created (private) |
| Supabase project ref | `vvyxjdoenjujkxwbnzyl` — **shared with persona/public-presence**; Michaela's intel warehouse `ktygrvbpugqhfyibzirr` is a DIFFERENT project Lance reads. See `devdocs/CAPABILITY_PACK_INTEGRATION.md` "Three Supabase projects". |

### Schema state (Supabase) — all migrations applied

`supabase migration list` (2026-05-10) shows local + remote synchronized:

| Local | Remote | Status |
|---|---|---|
| 20260509132444 | 20260509132444 | applied (remote_schema baseline) |
| 20260509132830 | 20260509132830 | applied (govcon core) |
| 20260509140333 | 20260509140333 | applied (Michaela MVP layer) |
| 20260509140838 | 20260509140838 | applied (ownership + provenance) |
| 20260509203000 | 20260509203000 | applied (waitlist) |
| 20260510021500 | 20260510021500 | applied (remote-drift placeholder, empty SQL locally — actual change lives in remote DB) |
| 20260510024000 | 20260510024000 | applied (remote-drift placeholder, empty SQL locally — actual change lives in remote DB) |
| 20260510092040 | 20260510092040 | applied (action_package approval columns) |
| 20260510120000 | 20260510120000 | applied (api_keys table) |
| 20260510120100 | 20260510120100 | applied (competitor_history table) |

Two timestamps (`20260510021500`, `20260510024000`) were applied to the
linked Supabase project outside this repo (likely Studio edits). They
exist locally as empty placeholder files so the Supabase CLI sees local
+ remote histories as synchronized. **A fresh project provisioned from
`supabase/migrations/` would NOT have whatever those two migrations did**
— resolve in a post-v1 schema squash by inspecting via Studio and
authoring equivalent migrations.

Verified live (2026-05-10) via `api/db.get_client`:
- `api_keys` table queryable
- `competitor_history` table queryable
- `action_packages.approved_at` + `approved_by` columns accessible

**Still placeholder in `.env`** (won't block /healthz or DB calls — needed only when LLM-backed skills are exercised end-to-end):

- `ANTHROPIC_API_KEY=sk-ant-test-placeholder` — replace with a real key from console.anthropic.com to exercise LLM skills.
- `SAM_API_KEY=` — optional; empty falls back to `load_seeded_opportunities`.

---

## 2. The four-layer architecture (do not get this wrong)

Conflating these layers was the source of nearly every misunderstanding
before PRD v1.2.5. Memorize this diagram.

```
┌─────────────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER — Michaela (TypeScript / Bun)                     │
│ Repo:    /root/michealaai (separate)                                │
│ Stack:   Bun + TypeScript                                           │
│ Tests:   bun test tests/*.test.ts                                   │
│                                                                     │
│ - Captures open loops; queues microtasks; assigns by capability;    │
│   stores results; decides resurfacing.                              │
│ - Workers (judgment, depth-1 leaves):                               │
│     Scot   — SAM discovery / top-of-funnel                          │
│     Lenny  — fit ranking / profile matching                         │
│     Ledger — incumbents / awards / competitive intel                │
│     Gate   — eligibility / compliance blockers (§11.1 owner)        │
│     Happer — execution runner (browser, files, overflow work)       │
│     Roy    — packaging / handoff (memo, email, capability statement)│
│                                                                     │
│ Michaela is the orchestrator, not a worker. Six workers = bench.    │
│ "7 named entities" = Michaela + 6 workers.                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ tool-calls (Hermes plugin) into
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ RUNTIME LAYER — hermes-agent (Nous Research)                        │
│ Install: ~/.hermes/    (per-user)                                   │
│ Provides: CLI/chat runtime, tool calling, skills (SKILL.md          │
│   progressive disclosure), memory, provider config, gateway, cron,  │
│   subagents (delegate_task), profile/HERMES_HOME isolation.         │
│                                                                     │
│ Hermes is NOT the product. Michaela uses Hermes as infrastructure.  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Hermes plugin (planned, Sprint A) +
                             │ HTTP REST (planned, Sprint B)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CAPABILITY-PACK LAYER — this repo (govcon)                          │
│ Stack: Python 3.12 + FastAPI + uv (backend)                         │
│        Next 15 + React 19 + Tailwind 4 (web/, landing/)             │
│                                                                     │
│ Owns: shared tools (api/skills/), HTTP CRUD API (api/routes/),      │
│       Supabase data layer (api/repositories/), auth (api/auth.py),  │
│       Storage wrapper (api/storage.py), /web product surface,       │
│       /landing marketing surface.                                   │
│                                                                     │
│ Does NOT own: Michaela, the worker bench, work-loop logic,          │
│       per-opportunity orchestration recipes, agent-loop runtime.    │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ DATA + TRANSPORT                                                    │
│ Supabase project (PostgREST + Auth + Storage). Bucket private.      │
│ Tables: company_profiles, opportunities, extracted_requirements,    │
│   fit_scores, risk_flags, action_packages, agent_runs, profiles,    │
│   waitlist_signups, opportunity_matches, documents, document_chunks,│
│   run_events, dimension tables (psc_codes, naics_codes, agencies…). │
│ Redis (native; SSE pub/sub bridge). Supabase Realtime is deferred.  │
└─────────────────────────────────────────────────────────────────────┘
```

### Operating rule (memorize)

> **Mechanics in shared tools. Judgment in agents. Contracts in
> schemas. Michaela owns the board.**

If you find yourself building "judgment" inside this pack (e.g., a
Python function that decides whether to bid), stop. That belongs to a
worker (Gate, Lenny, etc.) running in Michaela's Hermes. This pack
provides mechanics: parse this PDF, search SAM with these criteria,
score these requirements against this profile. The decision belongs to
the agent calling our tools.

---

## 3. The bench (lives in `/root/michealaai`, not here)

Document for context only — no edits to bench definitions land in this
repo. If you find yourself naming agents in this repo's docs, use these
exact names.

| # | Name | Role | Sample output |
|---|------|------|---------------|
| 0 | **Michaela** | CEO / orchestrator | "1 worth pursuing • 12 days left • 2 gaps • Bid memo ready" |
| 1 | Scot   | Discovery / SAM bulk scan | "Found 81,031 → next 90 days 14,000 → matched 42" |
| 2 | Lenny  | Fit ranking | "Pursue 2 • Monitor 6 • Skip 39 • Best fit: VA Cybersecurity Support" |
| 3 | Gate   | Eligibility blocker check (§11.1 owner) | "Eligible? no • Blocker: missing clearance • Do not bid" |
| 4 | Ledger | Competitive intel | "Incumbent: Tetra Tech • won 3× • difficulty: hard • prob 22%" |
| 5 | Happer | Execution runner | "Job done • rows processed • files written • errors found" |
| 6 | Roy    | Packaging / handoff | "Bid memo ready • capability statement drafted • email ready" |

**Naming history (do not relitigate):** the previous handoff suggested
renaming Gate and Ledger to legacy alternate labels. That direction is
**wrong** — it was reverted mid-session. The canonical names are
**Gate** and **Ledger**. The PRD v1.2.5 changelog explicitly deprecates
the legacy labels.

---

## 4. Decisions already made (don't re-litigate)

| ID | Decision | Status |
|----|----------|--------|
| D1 | Provider route for this pack: **direct Anthropic** (`provider: anthropic`, `default: claude-sonnet-4-6`, reads `ANTHROPIC_API_KEY`). OpenRouter is a future routing option only. | Confirmed |
| D2 | Hermes home for dev testing: **`HERMES_HOME=$(pwd)/.hermes` (project-isolated)**. Does not touch user's `~/.hermes/`. | Confirmed |
| D3 | Data layer: **Supabase via `supabase-py` AsyncClient (PostgREST)**. SQLAlchemy / asyncpg / Alembic dropped (PRD v1.2.4). Schema = `supabase/migrations/*.sql` applied via `supabase db push`. | Done |
| D4 | Auth: **Supabase JWT (`AuthenticatedUser`) for users + X-Internal-API-Key (`InternalActor`) for sub-agent writebacks**. RLS on every table. `owner_profile_id` on user-facing tables; `get_owned()` repo methods. | Done |
| D5 | Hosting: **Vultr VX1 + nginx + systemd** (no Docker). Vercel for `/web` + `/landing`. Supabase manages DB/Auth/Storage. The Michaela orchestrator runs separately (its own deployment target). | Pending VX1 deploy |
| D6 | Tooling: `uv` for Python deps; `bun` for michealaai TS; `make` targets canonical for common workflows. | Done |
| D7 | Worker names: **Gate (eligibility), Ledger (competitive intel)**. Scot/Lenny/Happer/Roy/Michaela unchanged. | Locked PRD v1.2.5 |
| D8 | Fixtures: 4 sets — `strong-pursue`, `maybe-needs-partner`, `reject`, `adversarial-image-pdf`. PDFs + manifests committed. | Done |
| D9 | This repo's identity: **GovCon Bid Desk capability pack**, NOT the orchestrator. Orchestrator lives in /root/michealaai. | PRD v1.2.5 |
| D10 | In-repo orchestration removed: `api/agent/` is gone. `POST /agent-runs` only persists a row; the external orchestrator picks it up out of band. | PRD v1.2.5 |
| D11 | Demo-routing env vars (`DEMO_USE_SEEDED_ONLY`, `DEMO_REPLAY_TRACE`) are **not read by this repo** anymore. Seeded/demo routing belongs to the external orchestrator. | PRD v1.2.5 |

---

## 5. Provider / key conventions for THIS repo

```
ANTHROPIC_API_KEY     → server-side, used by api/llm.py for skill-internal
                         LLM calls. Set in .env (gitignored). Required for
                         LLM-backed skills (extract_requirements, score_fit,
                         detect_risks, generate_action_package) to work.
SAM_API_KEY           → optional; empty falls back to load_seeded_opportunities.
SUPABASE_URL          → real (vvyxjdoenjujkxwbnzyl.supabase.co)
SUPABASE_SERVICE_ROLE_KEY → real (sb_secret_…). Server-only. Bypasses RLS.
SUPABASE_ANON_KEY     → real (sb_publishable_…). Used by api/auth.py to
                         verify Supabase JWTs via /auth/v1/user.
SUPABASE_STORAGE_BUCKET → "govcapture-attachments" (created, private).
INTERNAL_API_KEY      → long random. Required header (X-Internal-API-Key)
                         for sub-agent writeback routes. Never expose to
                         browser. Mirror to Michaela's environment in
                         /root/michealaai so writebacks succeed.
NEXT_PUBLIC_SUPABASE_URL, _ANON_KEY → real, for /web
NEXT_PUBLIC_API_BASE  → http://localhost:8000 in dev; prod URL in prod
REDIS_URL             → redis://localhost:6379/0 in dev
HERMES_HOME           → "$(pwd)/.hermes" for dev testing only; not loaded
                         by this repo's runtime
HERMES_MODEL          → claude-sonnet-4-6 (default)
LLM_DEV_MODEL         → claude-haiku-4-5-20251001
LLM_SYNTH_MODEL       → claude-sonnet-4-6
RUN_BUDGET_USD/STEPS/SECONDS → 0.50 / 40 / 360 (PRD §4.5 budgets)
CORS_ALLOWED_ORIGINS  → http://localhost:3000,http://localhost:3001,
                         http://localhost:5173 in dev; prod origins in prod
```

**Removed env vars** (don't add back without a logged decision):
`DATABASE_URL`, `OPENAI_*`, `NEXT_PUBLIC_APP_NAME`, `DEMO_REPLAY_TRACE`,
`DEMO_USE_SEEDED_ONLY`. The first three were dropped at PRD v1.2.4
(Postgres tooling rip-out + Supabase pivot). The `DEMO_*` pair was
dropped at PRD v1.2.5 (orchestration moved out of this repo).

`.env.example` is the committed template; `.env` is gitignored. Both
match `api/config.py` keys exactly.

---

## 6. Repository layout (current state)

```
/Volumes/CS_Stuff/govcon/
├── PRD.md                           ← v1.2.5
├── README.md                        ← capability-pack identity + setup
├── HERMES.md                        ← short dev guide for running hermes
│                                       against this pack's tools
├── Makefile                         ← dev, services-up, schemas,
│                                       fixtures-validate, test, etc.
├── pyproject.toml
├── package.json                     ← npm workspace root
├── .env / .env.example / .env.production.example
├── .gitignore                       ← excludes .hermes runtime artifacts
├── .hermes/
│   ├── config.yaml                  ← slim, schema-correct dev config
│   └── skills/govcapture/           ← 5 tool-usage SKILL.mds
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
│   ├── llm.py                       ← Anthropic SDK wrapper
│   ├── main.py                      ← FastAPI app, lifespan, routers
│   ├── redis.py                     ← redis.asyncio client
│   ├── storage.py                   ← Supabase Storage REST (httpx)
│   ├── db/
│   ├── repositories/                ← supabase-py PostgREST repos
│   ├── routes/                      ← CRUD only (orchestration removed)
│   │   ├── action_packages.py
│   │   ├── agent_runs.py            ← persists row only; no kick-off
│   │   ├── company_profiles.py
│   │   ├── healthz.py
│   │   ├── opportunities.py
│   │   ├── profiles.py
│   │   └── waitlist.py
│   ├── schemas/                     ← generated by `make schemas`
│   ├── skills/                      ← shared GovCon tools (11)
│   │   ├── parse_pdf/
│   │   ├── extract_requirements/
│   │   ├── score_fit/               ← §11.1 short-circuit lives here
│   │   ├── detect_risks/
│   │   ├── generate_action_package/
│   │   ├── search_sam/
│   │   ├── fetch_attachment/
│   │   ├── parse_goal/
│   │   ├── rank_opportunities/
│   │   ├── load_seeded_opportunities/
│   │   └── query_usaspending/       ← Ledger competitive intel
│   └── tests/
├── eval/                            ← fixture-driven LLM regression harness
├── mcp_server_govcapture/           ← MCP wrapper around /api/v1/tools/<name>
├── supabase/migrations/             ← 7 SQL files (5 applied + 2 local-only); canonical schema
├── schemas/                         ← JSON Schema sources
├── fixtures/                        ← strong-pursue, maybe, reject,
│                                       adversarial-image-pdf
├── infra/
│   ├── RUNBOOK.md                   ← v1.2.5
│   ├── bootstrap.sh
│   ├── deploy.sh
│   ├── nginx/
│   └── systemd/
├── web/                             ← Next 15 product UI
├── landing/                         ← Next 15 marketing
├── tasks/                           ← reference docs
│   ├── README.md                    ← frozen decisions, decision log
│   ├── CONTRACTS.md                 ← schemas, SSE, env, skill registry, API surface
│   ├── FIXTURES.md
│   └── LANDING_BRIEF.md             ← landing-page copy brief
├── devdocs/
│   ├── CURRENT_STATE.md             ← single page state of the repo
│   ├── CAPABILITY_PACKS_CANVAS.md   ← strategic horizon
│   ├── V1_PRODUCT_ALIGNMENT.md      ← public framing filter
│   ├── MICHAELA_SYSTEM_MODEL.md     ← orchestrator + pack relationship
│   ├── CAPABILITY_PACK_INTEGRATION.md ← Hermes plugin + HTTP API spec
│   └── HANDOFF_PROMPT.md            ← THIS FILE
└── docs/superpowers/plans/          ← active execution plans
    ├── 2026-05-10-finish-it-all.md       ← consolidated runway → v1.0.0
    └── 2026-05-10-frontend-cleanup-fixes.md  ← in-flight FE hyperanalysis fixes
```

**Files NO LONGER present** (deleted in the v1.2.5 repositioning + the
2026-05-10 doc-redundancy sweep):

```
# v1.2.5 repositioning
api/agent/                                    ← entire dir removed
api/tests/test_hermes_bridge.py               ← tested removed code
.hermes/SOUL.md                               ← runtime artifact, gitignored
.hermes/skills/govcapture/operate_bid_desk/   ← orchestration recipe
.hermes/skills/govcapture/analyze_opportunity_e2e/ ← orchestration recipe
.hermes/skills/govcapture/discover_opportunities/  ← worker recipe
tasks/AGENT_ARCHITECTURE.md                   ← Michaela's bench design
tasks/HERMES.md                               ← duplicated root HERMES.md
devdocs/HERMES_INTEGRATION_PLAN.md            ← stale plan
devdocs/prompt.md                             ← misnamed; → tasks/LANDING_BRIEF.md

# 2026-05-10 doc sweep (redundant/superseded)
tasks/INTERFERENCE_MAP.md                     ← retired Track A/B layout
tasks/DEMO.md                                 ← hackathon §13.1 stage script
devdocs/_archive/HANDOFF_2026-05-09.md        ← pre-v1.2.5 handoff
docs/superpowers/plans/2026-05-09-sprint-b-http-tools-parity.md  ← Sprint B done
docs/superpowers/plans/2026-05-10-launch-runway.md               ← superseded by finish-it-all
docs/superpowers/plans/2026-05-10-sprint-c-web-ui-and-auth.md    ← superseded by finish-it-all
```

---

## 7. The next-sprint menu

Pick one with the user before coding. The "recommended path" stitches
A → B → C → D for a real public launch in ~10–14 days. E and F are
nice-to-haves; G is cross-repo coordination work that may bottleneck
A and C.

| ID | Sprint | Effort | Unblocks | Depends on |
|----|--------|--------|----------|------------|
| ~~**A**~~ | ~~`hermes_plugin_govcapture/` Python plugin so Michaela's Hermes-hosted workers native-call our tools~~ — **SPEC + MCP PACKAGE DONE 2026-05-09** (966fa96; `mcp-server-govcapture` wraps `/api/v1/tools`; native Hermes plugin skipped in favor of MCP bridge). | 3–5 days | Native delegation from /root/michealaai workers; better latency than HTTP | None |
| ~~**B**~~ | ~~HTTP `POST /tools/<name>` parity for non-Hermes callers (TS, Codex, Cursor)~~ — **DONE 2026-05-09** (3c9a7de + 1b239c6 + Phase 4.x query_usaspending; 11 internal routes + 11 public `/api/v1/tools/<name>` mirror; 53 routes total; 183 tests). | 1–2 days | Any orchestrator that doesn't run Hermes | None |
| ~~**C**~~ | ~~`/web` product UI build-out (profile create → goal entry → run timeline → opportunity detail → action-package review)~~ — **PHASES 0–6, 7.1, 7.2, 7.4, 8 DONE** (5628129 loading skeletons + error boundaries; 94120fd SSE upgrade + same-origin proxy; e8e2500 SEO + robots.txt; a63bf30 rate-limit fail-open). **Phases 1.3 mobile sweep, 1.4 a11y, 1.5 copy pass owed** (user-driven). | 3–5 days | Public demo; first-customer trial | A or B (something must produce real artifacts) |
| **D** | Vultr VX1 production deploy | 4–8 hours | Public URL; hosted /healthz | A or B working locally |
| ~~**E**~~ | ~~`query_usaspending` skill for Ledger (separate writeback table)~~ — **DONE 2026-05-10** (3b19e39; Ledger's competitive-intel skill + competitor_history schema + migrations b334c20 ec7eb5f). | 1–2 days | Real competitive-intel content (today rides on `risk_flags` w/ category convention) | Schema PR ack |
| ~~**F**~~ | ~~`eval/` harness — fixture-driven regression on LLM skills~~ — **SCAFFOLDING DONE** (b420fd5; runner + differs + golden structure). **Goldens bootstrap owed** (`make eval-bootstrap`; costs Anthropic tokens; user-driven). | 2–3 days | Confidence in cross-version model upgrades | None |
| ~~G~~ | ~~Cross-repo coordination with `/root/michealaai` — emit-spec, run-row pickup contract, trace event format~~ — **SPEC DONE 2026-05-10** in `devdocs/CAPABILITY_PACK_INTEGRATION.md` (pickup contract, claim SQL, status state machine, INTERNAL_API_KEY provisioning, known-unknowns table). **End-to-end verification owed by `/root/michealaai`** (cross-repo). | 1–2 days | All of A/B/C in real end-to-end | michealaai's own status |

**Recommended next order:** D (deploy) → Sprint G e2e (cross-repo) → Phase 1.3/1.4/1.5 (user-driven UI polish) → eval goldens bootstrap (token cost) → v1.0.0 tag

Why B before A: HTTP `/tools/` is a faster unblock for any external
caller (including a thin TypeScript shim from /root/michealaai), buys
time to learn the Hermes plugin API in parallel. A is strictly better
once built (lower latency, native types) but takes more research up
front.

---

## 8. Sprint A — `hermes_plugin_govcapture/` (3–5 days)

### Goal

A pip-installable Python package that, when present in a Hermes
runtime's environment, exposes this repo's `api.skills.<name>` async
functions as native Hermes tools — bundled into toolsets that match
the bench's delegation envelope (`gov_discovery`, `gov_compliance`,
`gov_proposals`, `gov_intel`, `gov_documents`, `meta`).

### Files to create

```
hermes_plugin_govcapture/
├── __init__.py
├── pyproject.toml              ← entry_points: hermes.plugins
├── plugin.py                   ← register(ctx) entrypoint
├── adapters/
│   ├── __init__.py
│   ├── gov_discovery.py        ← search_sam, load_seeded_opportunities
│   ├── gov_documents.py        ← parse_pdf, fetch_attachment
│   ├── gov_compliance.py       ← extract_requirements, score_fit, detect_risks
│   ├── gov_proposals.py        ← generate_action_package
│   ├── gov_intel.py            ← (placeholder) query_usaspending — see Sprint E
│   └── meta.py                 ← parse_goal, summarize_run, request_human_review
└── tests/
    ├── __init__.py
    └── test_register.py
```

### Concrete steps

1. **Research Hermes plugin spec (30–60 min).** Read `~/.hermes/`
   docs or run `hermes plugins --help` to confirm the plugin
   discovery mechanism. The two most likely shapes are (a)
   `entry_points = {"hermes.plugins": ["govcapture = hermes_plugin_govcapture.plugin:register"]}` and (b) drop a `plugin.py` into a
   well-known dir. **Don't guess** — ask the user to confirm or
   provide a Hermes plugin example before coding.
2. **Scaffold the package** (`pyproject.toml` with the plugin entry
   point; `__init__.py` exposing `register`).
3. **Adapter pattern.** Each adapter module exports a function
   `register(ctx)` that calls `ctx.register_tool(name, callable, ...)`.
   The callable is a thin wrapper:
   ```python
   async def parse_pdf_tool(input_json: str) -> str:
       payload = ParsePdfInput.model_validate_json(input_json)
       result = await api_skills.parse_pdf.skill.run(payload)
       return result.model_dump_json()
   ```
   String-in / string-out matches Hermes' tool-call envelope; the
   adapter handles serialization so the underlying skill keeps its
   typed Pydantic interface.
4. **Test in isolation:** `cd hermes_plugin_govcapture && uv run pytest`.
5. **Test in Hermes:** `HERMES_HOME=$(pwd)/.hermes hermes /skills`
   should list the new tools under their toolset bundles.
6. **Don't change `api/skills/<name>/skill.py`.** Adapters stay in
   the plugin; skills stay provider-agnostic.

### Verification gates

- `uv run pytest hermes_plugin_govcapture/tests/` — green.
- `uv run pytest api/tests/` — still 112 (no regression).
- `HERMES_HOME=$(pwd)/.hermes hermes /skills` — lists ≥10 tools.
- `HERMES_HOME=$(pwd)/.hermes hermes` REPL — `parse_goal` callable
  end-to-end against a sample goal.

### Ask first

- Hermes plugin discovery mechanism (entry_points vs. file drop).
- Whether `gov_intel.query_usaspending` should be stubbed or skipped
  until Sprint E lands.
- Where to install the plugin into `/root/michealaai`'s Hermes (path
  may matter for the entry_point pickup).

### Estimated effort

3–5 days. Day 1: research + scaffold. Day 2: adapters + register. Day
3: tests + Hermes REPL exercise. Day 4–5: integration with
michealaai's Hermes home; iterate on toolset boundaries.

---

## 9. Sprint B — HTTP `POST /tools/<name>` parity (1–2 days)

### Goal

Each `api.skills.<name>` is callable through a thin HTTP endpoint
guarded by `InternalActor`. Lets any non-Hermes caller (TypeScript
shim from /root/michealaai, Codex, Cursor, curl) drive the tools
without learning the Hermes plugin spec.

### Files to create / modify

```
api/routes/tools.py              ← NEW
api/main.py                      ← include the router
api/tests/test_tools_routes.py   ← NEW
```

### Routes

All POST, all `InternalActor`-protected (X-Internal-API-Key required).
JSON in / JSON out.

```
POST /tools/parse-goal
POST /tools/parse-pdf
POST /tools/extract-requirements
POST /tools/score-fit                ← §11.1 short-circuit applies
POST /tools/detect-risks
POST /tools/generate-action-package
POST /tools/search-sam
POST /tools/fetch-attachment
POST /tools/rank-opportunities
POST /tools/load-seeded-opportunities
```

### Concrete steps

1. **Pattern per route:**
   ```python
   @router.post("/parse-pdf")
   async def parse_pdf_route(
       payload: ParsePdfInput,
       _actor: InternalActor = Depends(require_internal),
   ) -> ParsePdfOutput:
       return await api.skills.parse_pdf.skill.run(payload)
   ```
   Reuse the existing Pydantic input/output schemas. No business
   logic in the route — just dispatch.
2. **Tests cover** (a) happy-path with valid X-Internal-API-Key and
   minimal payload, (b) 401 without the header, (c) 422 with a
   malformed payload, (d) one skill that internally raises (e.g.,
   `parse_pdf` on a corrupt PDF) returns a structured error.
3. **Update `tasks/CONTRACTS.md` §6** to list the new endpoints under
   "Internal only".
4. **Update `devdocs/CURRENT_STATE.md` §7 (API surface)** to add the
   new rows.
5. **Update `devdocs/CAPABILITY_PACK_INTEGRATION.md`** to mark the
   HTTP surface as "live" (currently described as planned).

### Verification gates

- `uv run pytest api/tests/test_tools_routes.py` — all green.
- `uv run pytest api/tests/` — 112 + new count, no regressions.
- `uv run ruff check api && uv run mypy api` — clean.
- `curl -X POST http://localhost:8000/tools/parse-goal -H 'X-Internal-API-Key: <key>' -H 'Content-Type: application/json' -d '{"goal":"find SOC contracts"}'` — returns structured JSON.
- App route count goes from 24 → ~34.

### Ask first

- Whether to use one router file (`api/routes/tools.py`) or one per
  toolset bundle (mirrors Sprint A's adapter layout).
- Whether to add a trailing rate-limit guard (probably no for
  internal-only).

### Estimated effort

1–2 days. Day 1: routes + tests + docs. Day 2 (optional): observability
(latency_ms, cost_usd surfaced on each response) + load test.

---

## 10. Sprint C — `/web` product UI build-out (3–5 days)

### Goal

Take `/web` from "authenticated shell + seeded console" to a real
end-to-end product surface a small contractor can use: enter their
profile, set a goal, watch a run, review an opportunity, approve a
bid memo.

### Surfaces to build

| Route | Purpose |
|-------|---------|
| `/app/profile/new` | Company profile form (writes `company_profiles`) |
| `/app/profile` | View / edit current profile |
| `/app/goal` | Goal entry; `POST /agent-runs`; redirect to run page |
| `/app/runs/[id]` | Run timeline (SSE) + matched opportunities list |
| `/app/opportunities/[id]` | Per-opportunity: requirements, fit, risks |
| `/app/action-packages/[id]` | Action package + approval gate UI |

### Concrete steps

1. **Audit existing `/web/` console** — most of these surfaces have a
   seeded prototype in `web/src/app/app/AppConsole.tsx`. Decompose
   into route-segment-driven pages.
2. **API client** — `web/src/lib/api.ts` already exists; extend with
   typed fetchers per endpoint.
3. **SSE client** — `EventSource` against
   `/agent-runs/{id}/stream`. Render trace events as a timeline; auto-
   close on `run_completed`.
4. **Approval gate** — render `human_approval_required[]` as required
   checkboxes; "Submit" disabled until all are checked. Note: this
   pack does not enforce approval server-side; it ships the gate
   metadata. The UI is the enforcement point until/unless an external
   submission tool is added.
5. **Loading and error states** for every fetch; never render a
   blank "Loading..." for >2s without a skeleton.
6. **Type safety** — keep `npm run typecheck:web` green.
7. **No business logic in the UI.** If the UI starts deciding pursue
   vs. skip, you're rebuilding Lenny in the browser. Stop.

### Verification gates

- `npm run typecheck:web` — clean.
- `npm run build:web` — clean.
- `npm -w web run lint` — clean.
- Manual: log in (Supabase magic-link); create profile; start run;
  see SSE events; view opportunity; see action package.
- The system-prompt rule: **"For UI or frontend changes, start the
  dev server and use the feature in a browser before reporting the
  task as complete."** Honor it. Type checks ≠ feature correctness.

### Ask first

- Whether to introduce a component library (shadcn/ui is mentioned in
  CONTRACTS.md but not installed). If yes, which one.
- Whether mobile breakpoints matter for the first launch.
- Whether to render the UI even when the external orchestrator isn't
  emitting events (graceful "waiting for runner…" state).

### Dependency on Sprint G

Without an orchestrator emitting SSE events into Redis channel
`agent-run:{run_id}`, the timeline page renders an empty stream. Either
build a thin local stub for development (a Python script that
publishes seeded events on a 500ms cadence) or coordinate with
michealaai to land at least a hello-world emitter.

### Estimated effort

3–5 days. Day 1: profile + goal pages. Day 2: run timeline + SSE.
Day 3: opportunity detail + action package view. Day 4: approval gate
+ polish. Day 5: edge cases + integration with real runner.

---

## 11. Sprint D — Vultr VX1 production deploy (4–8 hours)

### Goal

A reachable production URL serving `/healthz` 200 and ready to receive
real traffic, with TLS and a systemd-managed FastAPI process.

### Concrete steps (per `infra/RUNBOOK.md`)

1. **Provision** Vultr VX1, Ubuntu 24.04, root SSH.
2. **Run `infra/bootstrap.sh`** — installs apt deps, ufw, redis,
   `govcapture` user, systemd unit. Idempotent.
3. **Clone repo** to `/opt/govcapture` (deploy key if private).
4. **Drop `.env`** with prod values:
   ```
   ANTHROPIC_API_KEY        — sk-ant-…
   SUPABASE_URL             — https://<ref>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY
   SUPABASE_ANON_KEY
   SUPABASE_STORAGE_BUCKET  — govcapture-attachments
   INTERNAL_API_KEY         — long random; mirror to /root/michealaai
   CORS_ALLOWED_ORIGINS     — https://app.govcapture.example,…
   REDIS_URL                — redis://localhost:6379/0
   HERMES_HOME              — /opt/govcapture/.hermes (if Hermes runs here)
   HERMES_MODEL             — claude-sonnet-4-6
   LLM_DEV_MODEL            — claude-haiku-4-5-20251001
   LLM_SYNTH_MODEL          — claude-sonnet-4-6
   RUN_BUDGET_USD/STEPS/SECONDS
   ```
5. **`uv sync`** as the `govcapture` user.
6. **`systemctl enable --now govcapture-api.service`** and check
   `systemctl status`.
7. **`curl 127.0.0.1:8000/healthz`** — must return `{"status":"ok"}`.
8. **nginx + certbot** — TLS for `api.<your-domain>`, reverse proxy
   to `127.0.0.1:8000`.
9. **DNS A record** at `api.<your-domain>`. Wait for propagation.
10. **`curl https://api.<your-domain>/healthz`** — 200 OK.
11. **Set `NEXT_PUBLIC_API_BASE`** on Vercel to the prod URL. Redeploy.

### Verification gates

- `systemctl is-active govcapture-api.service` — `active`.
- `curl https://api.<your-domain>/healthz` from outside the box — 200.
- `journalctl -u govcapture-api -n 50` — no tracebacks.
- `nginx -t` — syntax OK.
- `certbot certificates` — cert valid > 30 days.

### Ask first

- Domain to use (`api.govcapture.example` is a placeholder).
- Whether the Michaela orchestrator deploys to the **same** VX1 box
  (separate systemd unit, shared `INTERNAL_API_KEY`) or to its own
  host. If same box, allocate ports + memory carefully.
- Whether to set up Vultr snapshots / nightly Supabase backups.

### Estimated effort

4–8 hours, contiguous. Don't start late in the day; DNS propagation
adds non-deterministic wait.

---

## 12. Sprint E — `query_usaspending` skill for Ledger (1–2 days)

### Goal

Today, Ledger's competitive-intel outputs ride on `risk_flags` with
`category="competitor_history"`. That's a workaround. Give Ledger a
proper skill + writeback table.

### Files

```
api/skills/query_usaspending/
├── __init__.py
├── prompt.txt             ← optional, if any LLM synthesis happens
└── skill.py
api/repositories/competitor_history.py   ← NEW
api/routes/opportunities.py              ← extend with /competitors POST/GET
api/schemas/competitor_history.py        ← generated from new schema
schemas/competitor-history.schema.json   ← NEW
supabase/migrations/<timestamp>_add_competitor_history.sql  ← NEW
```

### Concrete steps

1. **Schema first** — add `competitor-history.schema.json` with fields
   like `opportunity_id`, `incumbent_name`, `awards[]`, `total_obligated_usd`,
   `win_difficulty`, `evidence_url`. Run `make schemas`.
2. **Migration** — `supabase/migrations/<ts>_add_competitor_history.sql`
   with columns matching the schema; RLS; `owner_profile_id`. Apply
   with `supabase db push`.
3. **Skill** — `api/skills/query_usaspending/skill.py` — async fetch
   from USASpending API (no LLM needed for the basic shape; consider
   one for narrative summary). Returns `CompetitorHistory[]`.
4. **Repository + routes** — mirror the pattern in
   `api/repositories/risk_flag.py` and the per-opportunity routes.
5. **Adapter additions** — extend `gov_intel.py` (Sprint A) and
   `tools.py` (Sprint B) if they're already shipped.
6. **Backfill or migrate** existing `risk_flags` rows with
   `category="competitor_history"` to the new table (or leave them
   and document the cutover date in `CURRENT_STATE.md`).

### Verification gates

- `uv run pytest api/tests/test_query_usaspending.py` — green.
- `make schemas` — no diff after re-run (idempotent).
- `supabase db push` — applies cleanly to a fresh project.
- `mypy + ruff` — clean.

### Ask first

- USASpending API key (if any) — most endpoints are unauth, but rate
  limits matter; confirm before scaling.
- Whether to backfill from `risk_flags`.

### Estimated effort

1–2 days. Half a day on schema + migration + repo. Half on skill +
tests + docs.

---

## 13. Sprint F — `eval/` harness (2–3 days)

### Goal

Fixture-driven regression tests for the LLM-backed skills
(extract_requirements, score_fit, detect_risks,
generate_action_package). Catches model-version drift and prompt
regressions before they reach a customer.

### Files

```
eval/
├── runner/
│   ├── __init__.py
│   ├── runner.py              ← run a fixture through a skill, diff vs golden
│   └── differs.py             ← structured comparison (allow score drift ±X)
├── goldens/
│   ├── strong-pursue/
│   │   ├── extract_requirements.golden.json
│   │   ├── score_fit.golden.json
│   │   └── …
│   ├── maybe-needs-partner/
│   ├── reject/
│   └── adversarial-image-pdf/
└── README.md
```

### Concrete steps

1. **Define the diff tolerance.** LLM outputs aren't bit-stable.
   Specify per-field tolerance: `decision` must match exactly;
   `total_score` ±5; `evidence_snippet` substring match; etc.
2. **Bootstrap goldens** by running each skill on each fixture once
   under the canonical model versions and committing the output.
3. **`make eval`** target that runs the harness; exits non-zero on
   any out-of-tolerance diff.
4. **CI integration** — run on PRs that touch `api/skills/`,
   `api/llm.py`, fixtures, or migrations.

### Verification gates

- `make eval` — passes against committed goldens.
- Deliberately break a skill (mutate a constant), re-run — fails.
- Re-bootstrap a single golden — `make eval` passes again.

### Ask first

- How strict the tolerance should be. Strict catches drift but
  flickers; loose hides regressions.
- Whether to run on every PR or only nightly.

### Estimated effort

2–3 days. Day 1: runner + differ. Day 2: bootstrap goldens. Day 3:
CI wiring + tolerance tuning.

---

## 14. Sprint G — Cross-repo coordination with `/root/michealaai` (1–2 days)

### Goal

This pack and the orchestrator project must agree on the contract for
how Michaela picks up `agent_runs` rows, calls our tools, and emits
trace events. Otherwise Sprint A/B/C produce a working pack that
nobody talks to.

### Concrete deliverables (in this repo)

1. **Document the run-row pickup contract** in
   `devdocs/CAPABILITY_PACK_INTEGRATION.md`:
   - When the orchestrator polls / subscribes for new `agent_runs`.
   - How it claims a row (Postgres advisory lock? `started_at` set?
     a `worker_id` column?).
   - How it marks completion / failure.
2. **Document the trace event format** in `tasks/CONTRACTS.md §3`
   (already partly there; verify it matches what the orchestrator
   actually emits).
3. **Lock the `INTERNAL_API_KEY` provisioning** — exact env var name,
   how michealaai obtains it (shared secrets manager? mirrored .env?).

### What's NOT in this repo's scope

- The orchestrator's pickup loop implementation.
- Michaela's prompts, persona, work-loop logic.
- Worker bench definitions.

### Verification gates

- A real `agent_runs` row created via `POST /agent-runs` from `/web`
  is picked up by `/root/michealaai`'s orchestrator within N seconds.
- Trace events flow back through Redis and render in `/web`.
- An action package row appears with `owner_profile_id` matching the
  caller.

### Ask first (always)

- Whether `/root/michealaai` has a checked-out branch / commit that
  matches the contract you're documenting. Stale orchestrator =
  stale contract.
- Who owns the schema changes if the contract requires a new column
  on `agent_runs` (e.g., `worker_id`, `claimed_at`).

### Estimated effort

1–2 days. Most is spec-writing + a single integration test.

---

## 15. Conventions for execution (apply to every sprint)

### Branching + commits

- The previous session worked on `main` directly with explicit user
  consent. Default for this session: **ask before doing the same**.
  Feature branches are safer for sprints that touch >5 files. The
  user said for the v1.2.5 doc work: "Stay on main." That doesn't
  carry forward automatically.
- **Commit per phase**, not per file. Commit messages: short subject
  ≤ 70 chars; body explains the why; trailer
  `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
  if you're using that model.
- Don't push to remote unless the user says "push".
- Never `--no-verify` a commit hook. Fix the underlying issue.

### Edits

- **Use `Edit` for surgical changes**; `Write` only for full-file
  rewrites and only after `Read`-ing the current contents first (the
  harness enforces this).
- **Re-read before edit** when a file you read earlier in the session
  has been modified by user/linter intervention. The previous session
  had the user editing in parallel; expect it.
- **Don't expand scope** without flagging. If you find tangential
  cleanup, surface it in chat ("noticed X is also stale; want me to
  include?") rather than silently bundling.

### Tests

- After every functional change, run `uv run pytest api/tests/ -q`.
- After Hermes-related work, run
  `HERMES_HOME=$(pwd)/.hermes hermes config show` and verify clean.
- After UI work, run the browser flow per the system-prompt
  requirement.

### Style

- Markdown lines ≤ ~78 chars where possible (tables/code exempt).
- File frontmatter only where Hermes spec requires it (SKILL.md
  files).
- No emoji unless the user asks.

### Memory and TrueMemory

- TrueMemory MCP may or may not be loaded in your session. If it's
  available, search at session start for "user preferences and
  context" before answering questions about the user.
- Don't write user facts to Claude Code's auto-memory
  (`~/.claude/projects/*/memory/`); those go to TrueMemory.

---

## 16. Verification gates (must be green per sprint AND globally)

### Global (must hold at end of every sprint)

| Gate | Command | Required outcome |
|------|---------|------------------|
| GL1 | `uv run pytest api/tests/` | All pass; suite size ≥ baseline (112 today) |
| GL2 | `uv run ruff check api` | All checks passed |
| GL3 | `uv run mypy api` | 0 errors |
| GL4 | `git status` | clean (no unintended changes) |
| GL5 | `find api/agent -type f` | empty (orchestration must stay out) |
| GL6 | `grep -rn 'from api\.agent' api/` | empty |
| GL7 | old-name scan over live docs/code (exclude archive; allow PRD changelog deprecation note only) | no live legacy-label usage |
| GL8 | `HERMES_HOME=$(pwd)/.hermes hermes config show` | no unknown-key warnings |

### Sprint A (Hermes plugin)

- Plugin tests pass; `hermes /skills` lists ≥10 tools; main repo
  pytest unchanged.

### Sprint B (HTTP /tools/)

- Route count goes 24 → ~34; new tests pass; happy + auth-fail + bad-payload
  paths covered.

### Sprint C (Web UI)

- `typecheck:web` + `build:web` clean; manual browser flow completes
  without a console error.

### Sprint D (Deploy)

- `https://<prod>/healthz` returns 200 from outside the box; cert
  valid > 30 days; `journalctl -u govcapture-api -n 50` has no
  tracebacks since unit start.

### Sprint E (USASpending)

- New skill tests pass; `make schemas` idempotent;
  `supabase db push` clean against fresh project.

### Sprint F (Eval harness)

- `make eval` passes against committed goldens; deliberate breakage
  fails it; rebootstrap restores green.

### Sprint G (Cross-repo)

- End-to-end `agent_runs` round-trip from `/web` through Michaela
  back to `/web` (action-package render).

---

## 17. "Ask first" triggers

Stop and surface to the user before doing any of these:

1. **Renaming or moving files outside the explicit list in the chosen
   sprint section.**
2. **Branching strategy** — main vs. feature branch — at sprint start
   if not already settled.
3. **Schema changes** — anything touching `schemas/*.json`,
   `supabase/migrations/`, or breaking field renames in
   `api/schemas/`. These need joint-edit ack.
4. **Modifying `api/repositories/`** beyond adding methods needed by
   the sprint. Repo refactors are their own sprint.
5. **Touching `web/` or `landing/`** unless the chosen sprint is C or
   the change is a single bug fix you can name.
6. **Pushing to a git remote** — never without explicit "push".
7. **Adding a Python or JS dependency** — `uv add <pkg>` or
   `npm install <pkg>`. Confirm before, including a one-line reason.
8. **Running anything that costs money** (Anthropic API beyond a few
   test calls, OpenRouter, paid SAM tier) — confirm budget.
9. **Encountering a concurrent edit or hook intervention that
   contradicts this handoff** — re-read, then surface the conflict
   (the previous session had this when a hook reverted legacy labels
   to Gate/Ledger; surfacing fixed it cleanly).
10. **Cross-repo work in `/root/michealaai`** — this handoff covers
    only `/Volumes/CS_Stuff/govcon`. Any work in the orchestrator
    repo is a separate session.
11. **Removing `DEMO_*` from anywhere they still appear** — those env
    vars are dropped from this repo's runtime but the PRD changelog
    references them historically. Don't strip the references.

---

## 18. Risk register

| # | Risk | Mitigation |
|---|------|------------|
| R1 | Concurrent edits (user or linter) cause merge thrash. | Re-read each file just before writing. The previous session got 5+ edit-collision errors; recover by re-reading and trying again. Don't fight the linter. |
| R2 | Hermes plugin spec turns out to differ from what's assumed in Sprint A. | Don't write adapters before confirming with `hermes plugins --help` or a working plugin example. 30 min of research saves 2 days of rework. |
| R3 | `/web` UI built against a contract Michaela doesn't meet (Sprint C without G). | Build a local stub publisher (a 30-line Python script) for SSE events; iterate on UI without orchestrator dependency. Wire to real orchestrator only after Sprint G. |
| R4 | VX1 deploy late in the day → DNS propagation drags. | Start before noon local; have a rollback plan (`systemctl stop govcapture-api`; restore previous `/opt/govcapture` worktree). |
| R5 | New env var added in code but not `.env.example`. | Append-only protocol per `tasks/CONTRACTS.md §4`. Always update both files in the same commit. |
| R6 | `INTERNAL_API_KEY` leaks. | Never print it in logs. `.env*` gitignored. If leaked, rotate immediately and update both this repo and `/root/michealaai`. |
| R7 | Schema PR in this repo lands before michealaai consumes the new field. | Use additive migrations (new columns nullable; new tables empty). Never ALTER COLUMN DROP NOT NULL or DROP TABLE without coordinating. |
| R8 | A sub-agent writes through a user JWT instead of `InternalActor`. | Tests on `tools.py` routes (Sprint B) must include the 401-without-key case. Run on every PR. |
| R9 | LLM call cost runaway during dev (running real Sonnet on every test). | `LLM_DEV_MODEL=claude-haiku-4-5-20251001` is the default; Sonnet only on tagged tests. Budget ceiling per run is `$0.50` (PRD §17 Q1). |
| R10 | The user expects you to update `/root/michealaai`. | You can't (different repo). Surface immediately: "this work is in this pack; the orchestrator side needs a separate session in `/root/michealaai`."|

---

## 19. Quick-reference: handing off again

If you need to spin up another fresh agent later, paste this entire
file plus a short prefix:

```
You are continuing work on /Volumes/CS_Stuff/govcon — the GovCon Bid
Desk capability pack — picking up after the [Sprint X] commit
[hash] from the prior session.

The complete onboarding context is in devdocs/HANDOFF_PROMPT.md (this
file). Read it top to bottom before doing anything. Use it as your
single source of truth for architecture, decisions, conventions, and
the menu of next sprints. The specific task for this session is:
[INSERT TASK].

When in doubt, follow Section 17 ("Ask first") and stop to ask the
human rather than guessing.
```

After completing a sprint, **update Section 1 ("Verified state")**
with the new commit hash and any change in test count, route count,
or doc inventory. Update Section 7 to mark the sprint as `done` with
a one-line outcome. Update the predecessor pointer in the header.

If a sprint reveals that this handoff is materially wrong (e.g.,
Hermes plugin spec is different, michealaai doesn't match the
described shape), edit the affected sections. Don't leave a future
agent with stale claims; trust in this file is what makes it useful.

---

**End of handoff. Now read it again before starting.**
