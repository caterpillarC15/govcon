# Contracts

This document is the single source of truth for everything that both tracks must agree on: repo layout, schemas, event shapes, env vars, tool registry, and codegen rules. Schema drift is the #1 risk for parallel work — read this carefully and treat it as canonical.

---

## 1. Repo layout

```
/api          — FastAPI proxy + Hermes integration + domain skills              [Track A]
/api/skills   — Hermes skills: parse_pdf, extract_requirements, score_fit, ...  [Track A]
/infra        — docker-compose, bootstrap.sh, nginx.conf, certbot setup         [Track A]
/eval         — eval harness runner                                             [Track A owns runner]
              └─ goldens/ — expected.json per fixture                           [Track B owns goldens]
/web          — Next.js frontend, Tailwind, shadcn/ui                           [Track B]
/fixtures     — seeded opportunities + PDFs                                     [Track B owns content]
              └─ <slug>/opportunity.json                                        [B authors]
              └─ <slug>/attachments/*.pdf                                       [B authors]
              └─ <slug>/expected.json                                           [B authors]
/schemas      — JSON Schema source of truth for ALL data structures             [Shared, locked in P0]
PRD.md        — product spec, frozen at v1.2.1                                  [Joint edit only]
Makefile      — top-level targets (schemas, eval, dev, deploy)                  [Shared]
docker-compose.yaml  — local dev stack                                          [Track A]
.env.example  — env var contract                                                [Joint, append-only]
tasks/        — this folder; build plan + standups                              [Joint]
```

---

## 2. Schemas — single source of truth

**Source files:** `/schemas/*.json` (JSON Schema draft 2020-12).

**Codegen targets:**
- Python (Pydantic v2): `/api/schemas/*.py` via `datamodel-code-generator`
- TypeScript (zod + types): `/web/lib/schemas/*.ts` via `json-schema-to-zod`

**Build target:** `make schemas` runs both generators. Both devs run this after pulling any schema change.

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

The agent emits these events via SSE on `GET /agent-runs/:id/stream`. B's timeline (B5) renders them. The taxonomy is a discriminated union on `type`.

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
  "tool": "search_sam_opportunities | load_seeded_opportunities | fetch_attachment | verify_source_page | parse_pdf | extract_requirements | score_fit | detect_risks | generate_action_package | request_human_review",
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

**Examples for B's local dev:** `/schemas/trace-event.example.jsonl` — committed in P0.3, contains a recorded successful run with one of each event type at human-readable cadence (~500ms–2s gaps). B can replay this in dev when A's agent isn't running.

**SSE framing:** each event is one SSE message: `event: <type>\ndata: <json-line>\n\n`. The mock server (P0.6) and the real server emit the same framing.

---

## 4. Env var contract

`/.env.example` (committed; secrets in `/.env` are gitignored):

```bash
# LLM
ANTHROPIC_API_KEY=
LLM_DEV_MODEL=claude-haiku-4-5-20251001
LLM_SYNTH_MODEL=claude-sonnet-4-6

# External APIs
SAM_API_KEY=

# Storage
DATABASE_URL=postgresql://govcon:govcon@localhost:5432/govcon
REDIS_URL=redis://localhost:6379/0

# Hermes runtime (configured via `hermes model` CLI; HOME holds skills + memory)
HERMES_HOME=/var/lib/hermes
HERMES_MODEL=claude-sonnet-4-6

# Agent budgets (PRD §4.5, §17 Q1)
RUN_BUDGET_USD=0.50
RUN_BUDGET_STEPS=40
RUN_BUDGET_SECONDS=360

# Frontend → backend (B)
NEXT_PUBLIC_API_BASE=http://localhost:8000

# Demo mode flags
DEMO_USE_SEEDED_ONLY=false   # true forces planner to skip live SAM and Hermes browser tools
```

**Rules:**
- `.env.example` is append-only. New vars get added here AND in this contract section.
- Never read `os.environ` outside `/api/config.py` or `/web/lib/env.ts`. Centralized so one file owns the truth.

---

## 5. Skill registry (under Hermes)

Mirrors PRD §4.5 (v1.2.2). All skills run inside the Hermes runtime. Each skill's input/output is a Pydantic model on the API side and a zod schema on the web side. All inputs validated before the call; all outputs validated after. See `HERMES.md` for runtime details.

| Skill | Owner | Input schema | Output schema |
|-------|-------|--------------|---------------|
| `search_sam_opportunities` | Domain skill (A11) | `SearchSamInput` | `Opportunity[]` |
| `load_seeded_opportunities` | Domain skill (A11) | `LoadSeededInput` (filters) | `Opportunity[]` |
| `fetch_attachment` | Hermes built-in (A9) | `{url}` | `{local_path, content_type, bytes}` |
| `verify_source_page` | Hermes built-in (A9) | `{url, fields_to_verify}` | `{verified: bool, fields: {...}}` |
| `parse_pdf` | Domain skill (A4) | `ParsePdfInput` (path) | `{chunks: [{page_number, text, doc_id}], unparseable: bool}` |
| `extract_requirements` | Domain skill (A5) | `ExtractInput` (chunks, opportunity_id) | §10.1 RequirementExtractionOutput |
| `score_fit` | Domain skill (A6) | `ScoreFitInput` (profile, requirements) | §10.2 FitScoreOutput |
| `detect_risks` | Domain skill (A7) | `DetectRisksInput` (profile, requirements) | `RiskFlag[]` |
| `generate_action_package` | Domain skill (A8) | `GenerateActionPackageInput` | §10.3 ActionPackageOutput |
| `request_human_review` | Hermes built-in (A9) | `{question, context}` | event emission (no return) |

Each tool also reports `latency_ms` and `cost_usd` (0 for non-LLM tools). The planner uses these for budget tracking.

---

## 6. API endpoints

PRD §9 is canonical. Locked surface for v1:

```
POST   /company-profiles                  → CompanyProfile
GET    /company-profiles/:id              → CompanyProfile
POST   /agent-runs                        → AgentRun (accepts inline profile or profile_id)
GET    /agent-runs/:id                    → AgentRun
GET    /agent-runs/:id/stream             → SSE stream of TraceEvent
GET    /agent-runs/:id/opportunities      → Opportunity[]
GET    /opportunities/:id                 → Opportunity
GET    /opportunities/:id/requirements    → ExtractedRequirement[]
GET    /opportunities/:id/fit-score       → FitScore
GET    /opportunities/:id/risks           → RiskFlag[]
GET    /action-packages/:id               → ActionPackage
GET    /healthz                           → { status: "ok" }
```

The mock server (P0.6) implements all of the above against canned fixtures so B is unblocked.

---

## 7. Versioning & change control

- PRD bumps a minor version on any joint edit, logged in the PRD changelog header.
- Schemas are not versioned independently for v1; breaking schema changes require a joint decision (logged in `tasks/README.md`).
- Tool registry is locked at v1; adding a new tool requires updating §5 above and the planner prompt simultaneously.

If you find yourself wanting to break a contract: stop, log the question in `STANDUP.md`, get the other dev's ack, then change.
