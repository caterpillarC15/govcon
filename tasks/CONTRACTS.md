# Contracts

This document is the single source of truth for repo layout, schemas,
event shapes, env vars, tool registry, and codegen rules. Schema drift
is the highest-impact risk for parallel work — treat this as canonical.

---

## 1. Repo layout

> The Track A / Track B labels from the original two-track build plan
> are retired (PRD v1.2.5). Active development happens on `main` with
> per-feature branches. Layout below is the current capability-pack
> shape.

```
/api          — FastAPI capability-pack API (CRUD + tool-call HTTP)
/api/skills   — GovCon tools: parse_pdf, extract_requirements, score_fit, ...
/infra        — bootstrap.sh, systemd units, nginx.conf, certbot setup
/web          — Next.js product UI (authenticated shell + console)
/landing      — Next.js marketing site
/fixtures     — seeded opportunity manifests + PDFs
              └─ <slug>/manifest.json
              └─ <slug>/attachments/*.pdf
/schemas      — JSON Schema source of truth for ALL data structures
/supabase/migrations — versioned SQL applied via `supabase db push`
PRD.md        — product spec, current v1.2.5
Makefile      — top-level targets (schemas, eval, dev, services-up, deploy)
.env.example  — env var contract (append-only)
tasks/        — reference docs (contracts, fixtures, demo, landing brief)
devdocs/      — system-model + capability-pack-integration + canvas docs
```

---

## 2. Schemas — single source of truth

**Source files:** `/schemas/*.json` (JSON Schema draft 2020-12).

**Codegen targets:**
- Python (Pydantic v2): `/api/schemas/*.py` via `datamodel-code-generator`
- TypeScript (zod + types): planned for `/web`, but not currently wired or
  consumed by the scaffolded product shell.

**Build target:** `make schemas` currently regenerates Python models only and
prints a warning for the unwired TypeScript side. Both devs run it after
pulling any schema change that touches Python API contracts.

**Files to author in P0.2:**

| File | PRD source | Used by |
|------|------------|---------|
| `/schemas/company-profile.schema.json` | §8.1 | A2, A3, A6, A8 / B3 |
| `/schemas/opportunity.schema.json` | §8.2 | A3, A11, A12 / B6, B7, B9–B12 |
| `/schemas/extracted-requirement.schema.json` | §8.3 + §10.1 | A5, A6, A7 / B7 |
| `/schemas/fit-score.schema.json` | §8.4 + §10.2 | A6 / B6, B7, B8 |
| `/schemas/risk-flag.schema.json` | §8.5 | A7, A8 / B7, B8 |
| `/schemas/action-package.schema.json` | §8.6 + §10.3 | A8 / B8 |
| `/schemas/agent-run.schema.json` | §8.7 | A1, A3, A9 / B5 |
| `/schemas/trace-event.schema.json` | §3 below | A9 / B5 |

**Change protocol:**
1. Schema PRs touch BOTH the source `.json` and regenerated outputs in the same PR.
2. Both devs ack any schema PR (one-line emoji ack on the PR is fine).
3. If a schema change breaks the other track's build, the schema author is on the hook to fix or revert.
4. No hand-edits to generated files. Ever. Run `make schemas`.

---

## 3. Trace event taxonomy

The external Michaela orchestrator emits these events. This API forwards
them via SSE on `GET /agent-runs/:id/stream` when another process publishes
to Redis channel `agent-run:{id}`. `/web` can also render the persisted
`agent_runs.steps` array after a refresh. The taxonomy is a discriminated
union on `type`.

**Event types:**

```jsonc
// run lifecycle
{ "type": "run_started", "run_id": "uuid", "goal": "string", "profile_id": "uuid", "ts": "ISO-8601" }
{ "type": "run_completed", "run_id": "uuid", "status": "complete | partial | failed", "summary": "string", "ts": "..." }

// step lifecycle (a step is one planner-decided unit of work)
{ "type": "step_started", "run_id": "uuid", "step_id": "uuid", "label": "string", "ts": "..." }
{ "type": "step_completed", "run_id": "uuid", "step_id": "uuid",
  "status": "complete | degraded | failed | needs_review", "ts": "..." }

// tool calls within a step
{ "type": "tool_called", "run_id": "uuid", "step_id": "uuid",
  "tool": "parse_goal | search_sam_opportunities | load_seeded_opportunities | rank_opportunities | fetch_attachment | verify_source_page | parse_pdf | extract_requirements | score_fit | detect_risks | generate_action_package | request_human_review",
  "input": { /* tool-specific */ },
  "rationale": "string (planner one-sentence)",
  "ts": "..." }
{ "type": "tool_returned", "run_id": "uuid", "step_id": "uuid", "tool": "...",
  "output": { /* tool-specific, present on success */ } | null,
  "error": "string | null",
  "latency_ms": 1234,
  "cost_usd": 0.0123,
  "ts": "..." }

// agent decisions surfaced as events for the UI
{ "type": "opportunity_ranked", "run_id": "uuid", "opportunity_id": "uuid",
  "score": 88, "decision": "strong_pursue | pursue | maybe | reject", "ts": "..." }
{ "type": "needs_human", "run_id": "uuid", "question": "string", "context": { /* free-form */ }, "ts": "..." }
```

**Examples for local dev:** `/schemas/trace-event.example.jsonl` is a shape
reference only if present. This repo no longer ships an in-repo replay
runner; demo/pre-cached playback belongs to the Michaela runtime or a
separate fixture harness.

**SSE framing:** each event is one SSE message:
`event: <type>\ndata: <json-line>\n\n`. The FastAPI endpoint preserves this
framing for events it receives from Redis.

---

## 4. Env var contract

`/.env.example` (committed; secrets in `/.env` are gitignored):

```bash
# Supabase (browser-safe vs server-only)
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_ANON_KEY=
SUPABASE_STORAGE_BUCKET=govcapture-attachments
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE=http://localhost:8000

# PRD v1.2.6: skills are deterministic — pack carries no LLM credential.
# ANTHROPIC_API_KEY, LLM_DEV_MODEL, LLM_SYNTH_MODEL, and the
# RUN_BUDGET_USD/STEPS/SECONDS env vars were dropped at v1.2.6. Michaela's
# bench in /root/michealaai owns LLM calls + budget tracking.

# External APIs
SAM_API_KEY=

# SSE pub/sub bridge — native Redis on VX1 in prod, Homebrew/apt local in dev.
REDIS_URL=redis://localhost:6379/0

# API security / CORS
INTERNAL_API_KEY=
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173

# Resend (weekly opportunity email — PRD §5.14, v1.2.6)
RESEND_API_KEY=
RESEND_FROM_EMAIL=GovCapture <onboarding@resend.dev>
RESEND_REPLY_TO=
EMAIL_PUBLIC_BASE_URL=http://localhost:8000
EMAIL_UNSUBSCRIBE_SECRET=
EMAIL_LEGAL_FOOTER_ADDRESS=
EMAIL_REQUIRE_DOUBLE_OPT_IN=false
EMAIL_DRY_RUN=true
EMAIL_AUTO_PICK_ENABLED=true
EMAIL_AUTO_PICK_MIN_SCORE=60
EMAIL_AUTO_PICK_MAX_CANDIDATES=20
EMAIL_NAICS_ALLOWLIST=
EMAIL_USE_FIXTURES_FOR_AUTO_PICK=false
```

**Rules:**
- `.env.example` is append-only. New vars get added here AND in this contract section.
- Never read `os.environ` outside `/api/config.py`,
  `/web/src/lib/supabase/env.ts`, or the middleware path that imports that
  helper. Centralized so one file owns the truth.
- `SUPABASE_SERVICE_ROLE_KEY` is server-only. It MUST NOT be inlined into
  Vercel env or any Next.js client bundle. Frontend uses
  `NEXT_PUBLIC_SUPABASE_ANON_KEY`; FastAPI uses the service role for server
  persistence and verifies browser JWTs before protected reads/writes.
- `INTERNAL_API_KEY` is only for Hermes/tool-write paths AND for the
  weekly-opportunity-email cron route (`POST /internal/cron/weekly-opportunity-email`,
  PRD §5.14). Public users cannot POST analysis artifacts directly, and
  the cron route is also nginx-blocked at the edge for `/internal/*` paths.
- `EMAIL_UNSUBSCRIBE_SECRET` is the HMAC key for unsubscribe-link signing.
  MUST differ between dev and prod. Generate with `openssl rand -hex 32`.
- `EMAIL_LEGAL_FOOTER_ADDRESS` is required in production (`api/config.py`
  refuses to start when `EMAIL_DRY_RUN=false` and this is empty).
- `RESEND_API_KEY` is server-only; never prefix with `NEXT_PUBLIC_`. The
  weekly-email job calls Resend's HTTP API from FastAPI; the Next.js
  bundle never imports `resend`.

---

## 5. Tool registry

Mirrors PRD §4.5 (v1.2.5). The mechanics live in this repo under
`api/skills/`; Michaela's workers decide when to call them. Each tool's
input/output is validated on the API side. TypeScript/zod codegen is still
planned, not wired. See `HERMES.md` and
`devdocs/CAPABILITY_PACK_INTEGRATION.md` for the runtime boundary.

This repo owns the **domain skills** (11) — all deterministic
(PRD v1.2.6). LLM judgment lives in the calling worker's agent
context (in `/root/michealaai`); these skills hold mechanics +
validators only. Hermes built-ins (`verify_source_page`,
`request_human_review`) are runtime-layer concerns and live with the
orchestrator, not here.

| Skill | Caller worker | Input schema | Output |
|-------|---------------|--------------|--------|
| `parse_goal` | Michaela | `ParseGoalInput` | `{raw_goal, company_profile}` (pass-through) |
| `search_sam` | Scot | `SearchSamInput` | `Opportunity[]` |
| `load_seeded_opportunities` | Scot | `LoadSeededInput` (filters) | `Opportunity[]` |
| `rank_opportunities` | Lenny | `RankOpportunitiesInput` | sorted `Opportunity[]` |
| `fetch_attachment` | Happer | `FetchAttachmentInput` (url, opportunity_id) | `{storage_path, content_type, bytes}` |
| `parse_pdf` | Happer | `ParsePdfInput` (storage_path) | `{chunks: [{page_number, text, doc_id}], unparseable: bool}` |
| `extract_requirements` | Gate | `ExtractInput` (parsed, optional requirements) | `{chunks, requirements (validated), missing_fields, conflicts}` |
| `score_fit` | Lenny + Gate | `ScoreFitInput` (profile, requirements, optional total_score) | §11.1 short-circuit + decision-band normalizer |
| `detect_risks` | Gate | `DetectRisksInput` (profile, requirements, risks) | §5.8 taxonomy-validated risks |
| `generate_action_package` | Roy | `GenerateActionPackageInput` (mode, content) | §10.3 ActionPackage (full or reject_summary) |
| `query_usaspending` | Ledger | `QueryUsaspendingInput` (opportunity_id, naics, agency) | `CompetitorHistory[]` (writeback) |

HTTP `POST /tools/<name>` wrappers return a uniform `{"data": ...}`
envelope. PRD v1.2.6 dropped the `metrics` field — every skill is
deterministic, so cost + token tracking belongs with the caller, not
this repo.

Michaela bench ownership:

| Agent | Owns |
|-------|------|
| Michaela | Orchestration, final user-facing answer, `parse_goal`, `summarize_run`, delegation |
| Scot | SAM.gov discovery and seeded fallback |
| Lenny | Fit ranking / pursue-monitor-skip support |
| Gate | Eligibility blocker checks and §11.1 reject gate |
| Ledger | USASpending / incumbent / award-history intelligence |
| Happer | Repeatable execution, attachment fetches, PDF parsing, file/status work |
| Roy | Bid memo, capability statement, contracting-officer email, action package |

---

## 6. API endpoints

PRD §9 is canonical. Locked surface for v1 (53 routes total — the
pack-side breakdown also lives in `devdocs/CURRENT_STATE.md` §7):

```
# unauth
GET    /healthz                           → { status: "ok" }
POST   /waitlist                          → { status: "ok", already_registered: boolean }
GET    /.well-known/agent.json            → MCP-style agent manifest
GET    /.well-known/llms.txt              → plain-text agent description for LLM crawlers
GET    /email-subscriptions/unsubscribe   → 200 HTML success page (HMAC token in ?token=)  (PRD §5.14)
POST   /email-subscriptions/unsubscribe   → 204 No Content (RFC 8058 List-Unsubscribe-Post one-click)  (PRD §5.14)

# user JWT (Supabase)
POST   /company-profiles                  → CompanyProfile
GET    /company-profiles                  → CompanyProfile[]
GET    /company-profiles/:id              → CompanyProfile
GET    /profiles/me                       → Profile
POST   /profiles/me                       → Profile
POST   /agent-runs                        → AgentRun request row (accepts inline profile or profile_id; does not start a runner)
GET    /agent-runs/:id                    → AgentRun
GET    /agent-runs/:id/opportunities      → Opportunity[]
GET    /agent-runs/:id/stream             → SSE stream of TraceEvent
GET    /opportunities/:id                 → Opportunity
GET    /opportunities/:id/requirements    → ExtractedRequirement[]
GET    /opportunities/:id/fit-score       → FitScore
GET    /opportunities/:id/risks           → RiskFlag[]
GET    /opportunities/:id/competitors     → CompetitorHistory[]
GET    /action-packages/:id               → ActionPackage
GET    /api/keys                          → ApiKey[]            (caller's keys)
POST   /api/keys                          → ApiKeyMint          (mint gck_… key — plaintext returned once)
DELETE /api/keys/:id                      → 204 No Content      (revoke)

# internal only — X-Internal-API-Key (writebacks from the orchestrator)
POST   /opportunities/:id/requirements    → ExtractedRequirement
POST   /opportunities/:id/fit-score       → FitScore
POST   /opportunities/:id/risks           → RiskFlag
POST   /opportunities/:id/competitors     → CompetitorHistory
POST   /action-packages                   → ActionPackage
POST   /tools/<name>                      → see §6 sub-table below (×11)

# per-agent bearer (gck_…) — same surface mirrored under /api/v1
POST   /api/v1/tools/<name>               → see §6 sub-table below (×11)

# internal cron — Authorization: Bearer ${INTERNAL_API_KEY} (loopback only; nginx 404s /internal/*)
POST   /internal/cron/auto-pick-weekly-opportunity      → { week_key, opportunity_id|null, reason }   (PRD §5.14)
POST   /internal/cron/weekly-opportunity-email          → { week_key, opportunity_id, total_eligible, sent, skipped_already_sent, failed, dry_run }   (PRD §5.14)
```

Public: `GET /healthz`, `POST /waitlist`, the two `/.well-known/*` paths.
Authenticated user (Supabase JWT): profile creation/read, agent-run
creation/read, opportunity reads, action-package reads, API-key
management.
Internal only (X-Internal-API-Key): per-opportunity analysis writebacks,
action-package creation, and the `/tools/<name>` skill surface.
Per-agent bearer (gck_…): the public `/api/v1/tools/<name>` mirror,
with rate limiting (60 rpm refilled at 1/s, fail-open on Redis loss).

### `POST /tools/<name>` — internal-only skill surface (Sprint B)

All routes require `X-Internal-API-Key`. Response envelope:
`{"data": ...}` (PRD v1.2.6 — deterministic-only, no `metrics` field).

| Route | Skill module | LLM | Notes |
|---|---|---|---|
| POST `/tools/parse-goal` | `api.skills.parse_goal` | yes | Goal → search criteria |
| POST `/tools/parse-pdf` | `api.skills.parse_pdf` | no | Server-local filesystem path |
| POST `/tools/extract-requirements` | `api.skills.extract_requirements` | yes | §10.1 contract; evidence-binding post-validation |
| POST `/tools/score-fit` | `api.skills.score_fit` | conditional | §11.1 short-circuit skips LLM on eligibility blockers |
| POST `/tools/detect-risks` | `api.skills.detect_risks` | yes | §5.8 taxonomy; silent-drops unknown categories |
| POST `/tools/generate-action-package` | `api.skills.generate_action_package` | conditional | `mode: "reject_summary"` skips LLM |
| POST `/tools/search-sam` | `api.skills.search_sam` | no | Reads `SAM_API_KEY`; sends required `award_type_codes`; degraded fallback on rate-limit/5xx |
| POST `/tools/fetch-attachment` | `api.skills.fetch_attachment` | no | Writes to Supabase Storage `raw/<run_id>/<filename>` |
| POST `/tools/rank-opportunities` | `api.skills.rank_opportunities` | no | Pure deterministic sort |
| POST `/tools/load-seeded-opportunities` | `api.skills.load_seeded_opportunities` | no | Idempotent on slug |
| POST `/tools/query-usaspending` | `api.skills.query_usaspending` | no | USASpending.gov prior-awards lookup (Ledger); persists `competitor_history` rows |

Request schemas: `api/schemas/tool_requests.py`. Routes hold no business logic; each is a thin dispatch into the underlying skill function.

---

## 7. Versioning & change control

- PRD bumps a minor version on any joint edit, logged in the PRD changelog header.
- Schemas are not versioned independently for v1; breaking schema changes require a joint decision (logged in `tasks/README.md`).
- Tool registry is locked at v1; adding a new tool requires updating §5 above and the planner prompt simultaneously.

If you find yourself wanting to break a contract: stop, log the question in
`tasks/README.md` decision log, get the other dev's ack, then change.
