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
| `uv run pytest api/tests/` | **206 passed** (186 + 20 from §5.14 weekly opportunity email + the v1.2.6 deterministic-skill suite) |
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

**Still placeholder in `.env`** (won't block /healthz or DB calls):

- `SAM_API_KEY=` — optional; empty falls back to `load_seeded_opportunities`.

> **PRD v1.2.6 note:** This pack no longer reads `ANTHROPIC_API_KEY`.
> The model-provider boundary moved entirely to `/root/michealaai`;
> skills here are deterministic-only.

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
| D2 | Hermes home for dev testing: **`HERMES_HOME=$(pwd)/.hermes` (project-isolated)**. Does not touch user's `~/.hermes/`. | Confirmed |
| D3 | Data layer: **Supabase via `supabase-py` AsyncClient (PostgREST)**. SQLAlchemy / asyncpg / Alembic dropped (PRD v1.2.4). Schema = `supabase/migrations/*.sql` applied via `supabase db push`. | Done |
| D4 | Auth: **Supabase JWT (`AuthenticatedUser`) for users + X-Internal-API-Key (`InternalActor`) for sub-agent writebacks**. RLS on every table. `owner_profile_id` on user-facing tables; `get_owned()` repo methods. | Done |
| D5 | Hosting: **Vultr VX1 + nginx + systemd** (no Docker). Vercel for `/web` + `/landing`. Supabase manages DB/Auth/Storage. The Michaela orchestrator runs separately (its own deployment target). | Pending VX1 deploy |
| D6 | Tooling: `uv` for Python deps; `bun` for michealaai TS; `make` targets canonical for common workflows. | Done |
| D7 | Worker names: **Gate (eligibility), Ledger (competitive intel)**. Scot/Lenny/Happer/Roy/Michaela unchanged. NOTE: Michaela's runtime introduces these as Gabby and Lance respectively — bench-naming reconciliation is open work; see active plan Phase 2.1. | Locked PRD v1.2.5 |
| D8 | Fixtures: 4 sets — `strong-pursue`, `maybe-needs-partner`, `reject`, `adversarial-image-pdf`. PDFs + manifests committed. | Done |
| D9 | This repo's identity: **GovCon Bid Desk capability pack**, NOT the orchestrator. Orchestrator lives in /root/michealaai. | PRD v1.2.5 |
| D10 | In-repo orchestration removed: `api/agent/` is gone. `POST /agent-runs` only persists a row; the external orchestrator picks it up out of band. | PRD v1.2.5 |
| D11 | Demo-routing env vars (`DEMO_USE_SEEDED_ONLY`, `DEMO_REPLAY_TRACE`) are **not read by this repo** anymore. Seeded/demo routing belongs to the external orchestrator. | PRD v1.2.5 |

---

## 5. Provider / key conventions for THIS repo

> **PRD v1.2.6:** This pack carries no LLM credential. The
> model-provider boundary moved entirely to `/root/michealaai`. The
> env vars below are the ONLY credentials the FastAPI service reads.

```
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
CORS_ALLOWED_ORIGINS  → http://localhost:3000,http://localhost:3001,
                         http://localhost:5173 in dev; prod origins in prod
```

**Removed env vars** (don't add back without a logged decision):
`DATABASE_URL`, `OPENAI_*`, `NEXT_PUBLIC_APP_NAME`, `DEMO_REPLAY_TRACE`,
`DEMO_USE_SEEDED_ONLY`, `ANTHROPIC_API_KEY`, `HERMES_MODEL`,
`LLM_DEV_MODEL`, `LLM_SYNTH_MODEL`, `RUN_BUDGET_USD/STEPS/SECONDS`. The
first three were dropped at PRD v1.2.4 (Postgres tooling rip-out +
Supabase pivot). The `DEMO_*` pair was dropped at PRD v1.2.5
(orchestration moved out of this repo). The LLM credentials and budget
knobs were dropped at PRD v1.2.6 (deterministic-only skills; provider
boundary lives in `/root/michealaai`).

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
    ├── README.md                              ← active vs archived index
    ├── 2026-05-10-everything-to-v1.0.0.md     ← drift cleanup + launch finish
    └── _archive/                              ← finish-it-all, frontend-cleanup, skills-deterministic
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

## 8 · Active work

The active plan is `docs/superpowers/plans/2026-05-10-everything-to-v1.0.0.md`.
Sprint-specific menus that previously lived in §§8–14 of this file
are archived in commit history; their outcomes shipped in commits
listed under `devdocs/CURRENT_STATE.md` §10.

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

Per-sprint gates (formerly listed here for Sprints A–G) are
superseded; current phase-by-phase gates live in
`docs/superpowers/plans/2026-05-10-everything-to-v1.0.0.md`.

---

## 17. "Ask first" triggers

Stop and surface to the user before doing any of these:

1. **Renaming or moving files outside the explicit list in the chosen
   sprint section.**
2. **Schema changes** — anything touching `schemas/*.json`,
   `supabase/migrations/`, or breaking field renames in
   `api/schemas/`. These need joint-edit ack.
3. **Modifying `api/repositories/`** beyond adding methods needed by
   the sprint. Repo refactors are their own sprint.
4. **Touching `web/` or `landing/`** unless the chosen sprint is C or
   the change is a single bug fix you can name.
5. **Pushing to a git remote** — never without explicit "push".
6. **Adding a Python or JS dependency** — `uv add <pkg>` or
   `npm install <pkg>`. Confirm before, including a one-line reason.
7. **Running anything that costs money** (paid SAM tier, etc.) —
   confirm budget. (LLM credentials no longer live in this repo per
   PRD v1.2.6.)
8. **Encountering a concurrent edit or hook intervention that
   contradicts this handoff** — re-read, then surface the conflict
   (the previous session had this when a hook reverted legacy labels
   to Gate/Ledger; surfacing fixed it cleanly).
9. **Cross-repo work in `/root/michealaai`** — this handoff covers
    only `/Volumes/CS_Stuff/govcon`. Any work in the orchestrator
    repo is a separate session.

---

## 18. Risk register

| # | Risk | Mitigation |
|---|------|------------|
| R1 | Concurrent edits (user or linter) cause merge thrash. | Re-read each file just before writing. The previous session got 5+ edit-collision errors; recover by re-reading and trying again. Don't fight the linter. |
| R3 | `/web` UI rendered against a contract Michaela doesn't meet (web ships before orchestrator wires up). | Run `make sse-stub` to publish seeded run events into Redis; iterate on UI without orchestrator dependency. Wire to the real orchestrator only after `/root/michealaai` confirms the pickup contract. |
| R4 | VX1 deploy late in the day → DNS propagation drags. | Start before noon local; have a rollback plan (`systemctl stop govcapture-api`; restore previous `/opt/govcapture` worktree). |
| R5 | New env var added in code but not `.env.example`. | Append-only protocol per `tasks/CONTRACTS.md §4`. Always update both files in the same commit. |
| R6 | `INTERNAL_API_KEY` leaks. | Never print it in logs. `.env*` gitignored. If leaked, rotate immediately and update both this repo and `/root/michealaai`. |
| R7 | Schema PR in this repo lands before michealaai consumes the new field. | Use additive migrations (new columns nullable; new tables empty). Never ALTER COLUMN DROP NOT NULL or DROP TABLE without coordinating. |
| R8 | A sub-agent writes through a user JWT instead of `InternalActor`. | Tests on the internal `/tools/<name>` routes must include the 401-without-key case. Run on every PR. |
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
