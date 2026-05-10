# GovCapture Agent PRD

## Product Requirements Document

**Product name:** GovCapture Agent
**Document status:** MVP PRD v1.2.6
**Primary track:** Agents Track
**Primary objective:** Build an autonomous AI capture agent that turns a small business profile and government contracting goal into a useful federal opportunity analysis package by searching opportunities, parsing solicitation documents, extracting requirements, scoring fit, detecting blockers, and producing actionable next steps with human approval gates.

> **Changelog v1.2.5 → v1.2.6** (2026-05-10)
> - **Added §5.14 Weekly Opportunity Email.** A standalone outbound channel: one curated federal opportunity per week to opted-in waitlist signups, sent via Resend. The pick is chosen by an LLM auto-picker against a clearly-labeled synthetic SMB profile, gated by deterministic safety filters (no narrow set-asides, deadline ≥ 14 days, no clearance/CUI keywords, US performance). PRD §11.1 spirit is preserved across the audience: when in doubt, refuse to pick. The email job is idempotent per `(email, week_key)`, dry-run by default, and refuses to send in production unless `EMAIL_LEGAL_FOOTER_ADDRESS` is set.
> - **§6 wording corrected.** "Real email sending" was always meant to forbid auto-submission of proposals via email, not all outbound mail. Replaced with "Real proposal submission via email" so weekly opportunity emails are unambiguously in scope.
> - **§17 Q10 added** — Resend domain verification status (default: dev uses sandbox sender; prod requires verified domain DNS).
> - **Two systemd timers added** on the VX1: `govcapture-cron-auto-pick.timer` (Sun 22:00 UTC, runs the picker) and `govcapture-cron-weekly.timer` (Mon 14:00 UTC, runs the send). Decoupled so a failed pick never breaks the send job. Both gated by `INTERNAL_API_KEY`.
> - **Reuses existing `INTERNAL_API_KEY`** for cron auth — no new `CRON_SECRET` env var.
> - **Reuses the existing `waitlist_signups` table** by adding `weekly_opportunity_enabled`, `unsubscribed_at`, `unsubscribed_reason`, `bounced_at`, `complained_at`, `confirmed_at`, `last_emailed_at` columns. Two new tables `weekly_opportunity_picks` and `weekly_opportunity_email_log` carry per-week curation and per-recipient idempotency. New Supabase migration under `supabase/migrations/`.
> - **Skills are now deterministic-only.** Per the operating rule (mechanics in tools, judgment in agents), `parse_goal`, `extract_requirements`, `score_fit`, `detect_risks`, and `generate_action_package` no longer call any LLM provider. Michaela's bench in `/root/michealaai` owns all LLM judgment; this repo carries only mechanics, schemas, and contracts. Skills accept agent-emitted content and validate against PRD §11.1, §11, §5.8, §5.13.
> - **Removed surface:** `api/llm.py` (LLM wrapper, LLMMetrics, LLMError), `api/tests/fakes.py` (FakeLLM), `api.deps.get_llm`. The `anthropic` SDK dropped from `pyproject.toml`. Worker prompts under `api/skills/<name>/prompt.txt` deleted (5 files).
> - **Removed env vars:** `ANTHROPIC_API_KEY`, `LLM_DEV_MODEL`, `LLM_SYNTH_MODEL`, `RUN_BUDGET_USD`, `RUN_BUDGET_STEPS`, `RUN_BUDGET_SECONDS`. Budgets move to Michaela's environment in `/root/michealaai`.
> - **Response envelope change:** `/tools/<name>` and `/api/v1/tools/<name>` now return `{"data": ...}` only — no `metrics` field. Cross-repo callers in `/root/michealaai` must stop reading `response.metrics`. Documented in `devdocs/CAPABILITY_PACK_INTEGRATION.md`.
> - **Eval harness simplified** to byte-exact deterministic diff. `make eval` no longer requires Anthropic credits; goldens bootstrapped at 18 (4 fixtures × {parse_goal, score_fit, detect_risks, generate_action_package, extract_requirements} minus skipped combos).
> - 2026-05-10 — Bench naming aligned with Michaela's runtime: Gate → Gabby
>   (eligibility), Ledger → Lance (competitive intel). The other four
>   workers (Scot, Lenny, Happer, Roy) and Michaela the orchestrator
>   unchanged. Old names retained only in this changelog.
>
> **Changelog v1.2.4 → v1.2.5** (2026-05-09)
> - **Repo boundary corrected.** This repo is now the GovCon Bid Desk
>   capability pack: tools, schemas, Supabase data layer, FastAPI routes,
>   landing, and `/web`. Michaela's workloop, worker bench, task queue, and
>   orchestration recipes live in `/root/michealaai`.
> - **In-repo orchestration removed.** `api/agent/` seeded bridge/replay code
>   was deleted. `POST /agent-runs` creates a run-request row; it does not
>   start a local Hermes subprocess. The external Michaela orchestrator writes
>   trace events and generated artifacts back through this pack's contracts.
> - **Bench names corrected to the latest system language.** Michaela owns the
>   board; workers are Scot, Lenny, Ledger, Gate, Happer, and Roy. Legacy
>   `Lance`/`Gabby` labels are deprecated in active docs.
> - **Env contract narrowed.** `DEMO_USE_SEEDED_ONLY` and
>   `DEMO_REPLAY_TRACE` are not read by this repo. Seeded/demo routing belongs
>   to Michaela's runtime or a fixture harness outside this repo.
> - **New docs:** `devdocs/MICHAELA_SYSTEM_MODEL.md` and
>   `devdocs/CAPABILITY_PACK_INTEGRATION.md` define the layer boundary.
>
> **Changelog v1.2.3 → v1.2.4** (2026-05-09)
> - **Postgres tooling removed.** SQLAlchemy 2.0, asyncpg, and Alembic are gone from `pyproject.toml` and from the codebase. The data layer is now `supabase-py`'s `AsyncClient` talking to Supabase **PostgREST**. Schemas live as versioned SQL under `supabase/migrations/` and are applied with `supabase db push`. `DATABASE_URL` is no longer an env var.
> - **Auth + ownership added.** Two auth roles: `AuthenticatedUser` (Supabase JWT verified through `/auth/v1/user`) for user-facing routes; `InternalActor` (X-Internal-API-Key header) for sub-agent writebacks. New `INTERNAL_API_KEY` env var. New `owner_profile_id` column on user-facing tables; `get_owned()` repository methods scope reads by JWT identity. RLS enabled on every table.
> - **New resources:** `/profiles` (one row per Supabase Auth user; FK into `auth.users`), `/waitlist` (marketing capture), and the Michaela-layer tables (`opportunity_matches`, `documents`, `document_chunks`, `run_events`).
> - **Michaela 7-agent bench named.** The Michaela system uses a CEO + 6 worker agents: Michaela (orchestrator), Scot (discovery), Lenny (fit ranking), Gate (eligibility), Ledger (competitive intel), Happer (execution runner), Roy (packaging). Hermes is the runtime shell around this bench, not the product architecture. Replaces the prior 5-agent design (Capture Lead / Analyst / Compliance Officer / Risk Analyst / Proposal Strategist). The §11.1 chain, source-binding, no-fabrication, and approval-gate rules carry over unchanged. See `devdocs/MICHAELA_SYSTEM_MODEL.md`.
> - §7.5 simplified: "Supabase project provisioned via the Supabase CLI; SQL migrations in `supabase/migrations/`." No mention of asyncpg or Direct Connection URL — irrelevant now.
> - §9 endpoints: writeback POSTs (`/opportunities/{id}/{requirements,fit-score,risks}`, `/action-packages`) require `InternalActor`; everything else requires `AuthenticatedUser`. Healthz, waitlist signup are public.
> - Deferred items still deferred: Supabase Realtime (Redis stays for SSE pub/sub), cross-run agent memory.
>
> **Changelog v1.2.2 → v1.2.3**
> - **Adopted Supabase for managed Postgres + object storage.** §7.5 promotes Supabase from "recommended" to chosen. Postgres moves off the VX1 box and onto a Supabase project (asyncpg connects over SSL); raw and parsed solicitation files move from `/var/lib/govcapture/{raw,parsed}` into a Supabase Storage bucket. **Redis stays native on VX1** (powers the SSE pub/sub bridge — switching to Supabase Realtime mid-build is rework, not speed).
> - §7.6 updated: VX1 service-allocation table no longer lists Postgres or pg_dump backups (Supabase handles both). VX1 still hosts FastAPI + Hermes + Redis + nginx natively. Bootstrap script shrinks ~40%.
> - §17 Q5 (auth) and the Supabase Realtime pivot are explicitly **deferred**. Supabase's Auth and Realtime features are available but not used in v1.2.3 — keeps the surface change scoped.
> - §17 Q6 (raw retention) supersedes the on-box 30-day purge: retention is now a Supabase Storage bucket policy, not a `find -mtime` cron.
> - No change to §4.5 agent architecture, §5 features, §8 data model, §9 API endpoints, §10 structured outputs, §11.1 eligibility rule, §13.1 demo script, §19 eval harness. Tests, schemas, codegen, skills (parse_pdf, extract_requirements, A6+) all infra-agnostic.
>
> **Product-positioning note for V1**
> - Internal docs may continue to use "capture" because it is precise govcon operating language.
> - Publicly, the product should be framed as a **GovCon Bid Desk Operator**: a hired AI worker that finds contracts worth bidding, tells the team whether to pursue, and creates the action plan.
> - Compliance and requirement extraction are internal mechanisms, not the sales headline.
> - Michaela is the product/workloop and owns orchestration. Hermes is the runtime shell/tool harness. Anthropic/OpenRouter are model transport choices only. OpenClaw may be used as a channel/tool substrate, but customers experience one agent.
>
> **Changelog v1.2.1 → v1.2.2**
> - Adopted **hermes-agent** (Nous Research, https://github.com/nousresearch/hermes-agent) as the agent runtime. Hermes provides the planner loop, tool/skill registry, long-term memory, multi-backend execution (local / Docker / SSH / Modal / Vercel Sandbox), and is model-agnostic. We register domain skills (`parse_pdf`, `extract_requirements`, `score_fit`, `detect_risks`, `generate_action_package`, `search_sam`, `load_seeded_opportunities`) inside Hermes; FastAPI becomes a thin proxy with a trace-event bridge that preserves the CONTRACTS.md §3 SSE shape so the frontend never has to know Hermes exists.
> - §4.5 updated: planner loop, tool registry, and budgeting now reference Hermes' built-ins. Our additions are the domain skills, the §11.1 enforcement (which lives inside `score_fit` and `generate_action_package`), and the trace bridge. The decision-policy and error-recovery semantics are unchanged contractually.
> - §7.3 updated: OpenClaw is no longer a peer agent brain. Michaela owns the product workloop; Hermes provides runtime memory, skills/tools, provider config, and delegation support. OpenClaw may still serve as a bounded channel/tool substrate for browser-bound work, web chat, WhatsApp, or Slack when that accelerates the V1 bid-desk worker.
> - Model defaults remain Claude Sonnet 4.6 (synthesis) and Haiku 4.5 (cheap passes), configured via `hermes model`. Hermes' model-agnosticism means we can swap providers later without code changes.
> - See `HERMES.md` (repo root), `devdocs/MICHAELA_SYSTEM_MODEL.md`, and `devdocs/CAPABILITY_PACK_INTEGRATION.md` for the integration spec, agent bench, toolset map, and §11.1 enforcement chain.
>
> **Changelog v1.2 → v1.2.1**
> - Added §7.6 Deployment Target — locks in Vultr VX1 (16 vCPU / 64 GB RAM / 960 GB NVMe / Ubuntu 24.04 LTS) as the single-box MVP host with a concrete service allocation table, sizing notes, and operational hygiene checklist.
>
> **Changelog v1.1 → v1.2**
> - Added §4.5 Agent Architecture (planner, tool registry, decision policy, error recovery, observability) — makes the agent loop explicit instead of an implicit pipeline. This is what the Agents Track judges look for.
> - Tightened §5.4 with named demo fixtures (strong-pursue / maybe / reject) so the rubric is visibly exercised in demos.
> - Sharpened §7.3 to make explicit which tools OpenClaw owns (browser-bound) vs. which FastAPI owns (deterministic local).
> - Added §11.1 Eligibility conservatism rule — eligibility mismatch is always a critical blocker, never a soft penalty.
> - Added §13.1 Demo Script — 3-minute live narrative for hackathon judging.
> - Added §17 Q9 — hackathon track selection: Agents Track primary, optional Texas Open Data layer (TX place-of-performance + Austin/SA/Houston/Dallas open data adapter).
> - Added §19 Evaluation Harness — fixture-based assertions to prevent prompt/tool regressions and serve as a pre-demo smoke test.
>
> **Changelog v1.0 → v1.1**
> - Fixed corrupted text in §2 ("compliance requihe valuable" → "compliance requirements").
> - Fixed typos: "caanalysis", "complet", "le" (risk Title field).
> - Restored missing scoring weight in §5.7 ("Certification/compliance readiness: 10"). Verified weights sum to 100.
> - Added §17 Open Questions & Risks and §18 Data Handling & Privacy.
> - Tightened §5.4 to specify the MVP fallback hierarchy (live → cached → seeded).
> - Clarified that the SAM.gov API requires an API key and has rate limits; seeded fixtures are required for demo reliability.

---

# 1. Executive Summary

GovCapture Agent is an autonomous capture workflow for small businesses pursuing federal contracts. The system starts with a company profile and a contracting goal, searches or loads relevant government opportunities, retrieves and parses solicitation documents, extracts structured requirements, compares those requirements against the company profile, identifies blockers and risks, recommends pursue/maybe/reject decisions, and generates a practical action package.

The MVP is designed around one useful workflow:

> Company profile + contracting goal → relevant opportunities → parsed solicitation requirements → fit score → blocker detection → action package.

The product is not a generic chatbot. It is an agentic operations workflow that uses tools, reads documents, reasons over requirements, produces structured outputs, and keeps humans in the loop before sensitive actions.

The MVP should be good enough to show real companies immediately after build completion. It should produce outputs that a small business owner, operator, or proposal consultant can understand, verify, and act on.

---

# 2. Product Thesis

Small businesses do not only need help finding government contracts. They need help deciding which opportunities are worth pursuing and what to do next.

Government contracting opportunities are often buried inside portals, dense PDFs, amendments, eligibility rules, deadlines, certifications, set-asides, submission instructions, and compliance requirements. The valuable workflow is turning that chaos into a clear pursuit decision and action package.

GovCapture Agent acts as an autonomous capture analyst that performs the first-pass work a business owner or junior capture analyst would otherwise do manually.

---

# 3. Target Users

## 3.1 Primary User: Small Business Owner / Operator

Profile:

* 1–50 person company
* Has real capabilities but limited government contracting experience
* Wants federal, state, or local government work
* May not have a dedicated capture or proposal team
* Needs clear guidance on eligibility, requirements, blockers, and next actions

Desired outcome:

> "Tell me which contracts we should pursue, which ones we should avoid, and what we need to do next."

## 3.2 Secondary User: Proposal Consultant / Capture Consultant

Profile:

* Helps companies identify and pursue government opportunities
* Understands GovCon but is bottlenecked by manual research and document review
* Works with multiple clients
* Needs faster first-pass capture analysis

Desired outcome:

> "Help me quickly qualify opportunities and produce a first-pass pursuit package for my client."

## 3.3 Tertiary User: Subcontractor Seeking Teaming Opportunities

Profile:

* Has a niche capability
* May not be ready to bid as prime
* Wants to identify contracts where they can support a prime contractor

Desired outcome:

> "Find opportunities where we could be valuable as a subcontractor and help us understand the teaming angle."

---

# 4. Core MVP Workflow

The MVP supports one complete capture run.

## User flow

1. User enters or reviews a company profile.
2. User enters a contracting goal.
3. Agent starts a capture run.
4. Agent searches or loads relevant opportunities.
5. Agent retrieves or loads solicitation documents.
6. Agent parses solicitation PDFs or attachments.
7. Agent extracts structured requirements with evidence.
8. Agent scores company fit.
9. Agent detects blockers and risks.
10. Agent ranks opportunities.
11. Agent generates an action package for relevant opportunity.
12. Agent shows human approval gates for sensitive actions.

---

## 4.5 Agent Architecture

GovCapture Agent is an *agent*, not a hardcoded pipeline. The §4 user flow is what the agent typically does on a clean run; the architecture below is how it actually decides, recovers, and stays bounded. This section is what makes the project an Agents Track submission rather than a workflow with LLM calls in it.

### Planner loop

A planner LLM receives, on every step:

* The company profile
* The contracting goal
* The tool registry (with input/output schemas, cost hint, latency hint)
* The current run state (steps completed, outputs so far, errors encountered, remaining budget)

The planner emits one of: a tool call, `done`, or `needs_human`. After each tool call returns, the planner re-evaluates state and chooses the next action. The loop is bounded by:

* Max steps per run (default 40)
* Max wall-clock per run (default 6 minutes)
* Max LLM cost per run (default $0.50, see §17 Q1)

The planner's one-sentence rationale for each decision is logged to the agent run trace.

### Tool registry

Each tool has a JSON-schema input and output, validated before invocation and after return. Invalid I/O triggers the recovery path below.

| Tool | Owner | Purpose |
|------|-------|---------|
| `parse_goal` | Michaela / FastAPI toolset | NL goal → structured search criteria |
| `search_sam_opportunities` | Scot / FastAPI toolset | Query SAM.gov v2 search API by keywords/NAICS/set-aside/place-of-performance |
| `load_seeded_opportunities` | Scot / FastAPI toolset | Load hand-curated fixture set (demo-stable fallback, see §5.4) |
| `rank_opportunities` | Lenny / FastAPI toolset | Deterministically sort candidates by fit signals |
| `fetch_attachment` | Happer / FastAPI or Hermes HTTP toolset | Download solicitation attachments |
| `verify_source_page` | Happer / Hermes browser or HTTP toolset | Confirm source metadata when API data is partial |
| `parse_pdf` | Happer / FastAPI toolset | Extract page-level text + metadata from a PDF |
| `extract_requirements` | Gabby / AI + FastAPI toolset | Run requirement extraction over parsed chunks; returns structured requirements with evidence |
| `score_fit` | Lenny + Gabby / AI + FastAPI toolset | Apply §5.7 rubric and §11.1 hard eligibility short-circuit |
| `detect_risks` | Gabby / AI + FastAPI toolset | Apply §5.8 categories; returns risk flags with severity |
| `query_usaspending` | Lance / planned toolset | Find incumbents, prior awards, recompete history |
| `generate_action_package` | Roy / AI + FastAPI toolset | Synthesize §5.11 package from extracted requirements + score + risks |
| `request_human_review` | Michaela / FastAPI | Halt and surface a question to the user when confidence is below threshold |

Michaela owns the product workloop and board-level orchestration. Hermes
provides runtime memory, skill/tool discovery, provider configuration, and
delegation support. FastAPI owns deterministic domain tools, schema validation,
persistence, and the API surface. OpenClaw is optional channel/browser
substrate only; it is not a peer agent brain.

### Decision policy

* **Tool selection.** Planner picks the cheapest tool that advances the goal. For opportunity loading, prefer cached → seeded → live (§5.4 fallback hierarchy is a planner preference, not a hardcoded order).
* **Confidence gating.** If `extract_requirements` returns more than 30% `low`/`unknown` confidence on a document, the planner re-runs with smaller chunks before continuing to scoring.
* **Eligibility short-circuit.** If any extracted requirement flags a hard eligibility mismatch (set-aside, clearance, citizenship), the planner skips deep scoring and emits `reject` with the blocker as the reason. See §11.1.
* **Budget awareness.** Planner tracks remaining step/time/cost budget and degrades gracefully — e.g., score the top-3 ranked opportunities deeply, summarize the remainder.
* **Human-in-the-loop.** When confidence is low across the board or a sensitive action is required, the planner emits `needs_human` and pauses the run rather than guessing.

### Error recovery

| Failure | Recovery |
|---------|----------|
| SAM.gov 429 / 5xx | Fall back to cached → seeded; mark step `degraded` in timeline |
| PDF unparseable (image-only, encrypted) | Mark document `unparseable`; surface to user; continue with available text |
| Attachment fetch fails | Retry once with backoff via Happer; then mark missing and continue |
| LLM returns invalid JSON | Retry with stricter prompt + schema reminder; on second failure, mark step `failed` and continue with degraded output |
| Extraction confidence collapse (all `low`/`unknown`) | Re-chunk smaller; if still bad, escalate to `request_human_review` |
| Planner exceeds step / time / cost budget | Summarize progress, emit partial action package, flag incompleteness in the timeline |

### Observability

Every tool call is logged to the agent run with: tool name, input, output (or error), latency, token cost, and the planner's one-sentence rationale. The §5.3 timeline UI is a projection of this trace. Users can expand any timeline step to see the underlying tool I/O — this is required for trust and is part of what makes the agent's behavior verifiable rather than magical.

---

# 5. MVP Feature Scope

## 5.1 Company Profile Input

The system must support a company profile with enough detail to compare against solicitation requirements.

Required fields:

* Company name
* Company website
* Company description
* Capabilities
* Industry keywords
* Location
* Service area
* NAICS codes, optional
* Certifications
* Small business status
* SAM registration status
* Clearance status
* Past performance
* Insurance/bonding status if known
* Preferred contract size
* Preferred role: prime, subcontractor, or either

The profile can be created through structured fields or pasted as messy text that the system normalizes.

### Output

The system creates a normalized company profile object used for search, scoring, blocker detection, and package generation.

---

## 5.2 Contracting Goal Input

The system must support a plain-language goal.

Example goal types:

```txt
Find cybersecurity opportunities we can pursue in the next 30 days.
Find facilities maintenance contracts near Texas.
Find software development opportunities where we can subcontract.
Find small business set-aside contracts that match our capabilities.
```

The system converts the goal into internal search criteria:

* Keywords
* Capability tags
* Due date window
* Target geography
* Target agencies if specified
* Opportunity type
* Set-aside preference
* Relevant NAICS hints if available

---

## 5.3 Agent Run Timeline

The UI must show the agent's progress through the workflow.

Timeline steps:

```txt
1. Read company profile
2. Parsed contracting goal
3. Searched opportunities or loaded cached opportunities
4. Found relevant opportunities
5. Retrieved solicitation documents
6. Parsed solicitation documents
7. Extracted structured requirements
8. Scored company fit
9. Detected blockers and risks
10. Ranked opportunities
11. Generated action package
12. Awaiting human approval
```

Each step should have a status:

* pending
* running
* complete
* failed
* needs review

The timeline is a product feature, not only a visual flourish. It lets users understand what the agent did and where outputs came from.

---

## 5.4 Opportunity Search / Opportunity Loader

The system must retrieve or load a set of relevant opportunities.

The MVP uses a fallback hierarchy for reliability during demos:

1. **Live SAM.gov API search** (preferred when API key is available and rate limits allow)
2. **Cached SAM.gov opportunities** (recent results stored locally)
3. **Seeded realistic opportunities** (hand-curated fixtures that always work)
4. **User-uploaded solicitation documents** (founder-led onboarding override)

> Note: SAM.gov's `opportunities/v2/search` API requires a registered API key and enforces per-key rate limits. Seeded fixtures are mandatory for demo reliability and offline development.

### Seeded fixture set (MVP demo)

Three hand-curated fixtures cover the decision spectrum so demos visibly exercise the §5.7 rubric and §5.8 risk detection:

1. **Strong-pursue fixture.** Small-business set-aside, NAICS aligned with the demo company, deadline 30+ days out, clear technical scope, no clearance required. Should land in the 85–100 band.
2. **Maybe / needs-partner fixture.** Relevant scope, but past-performance threshold or specialized capability the demo company can't meet alone — should surface a partner suggestion via §5.12. Should land in the 55–69 band.
3. **Reject fixture.** Hard blocker (e.g., requires Secret clearance, or 8(a) set-aside the demo company doesn't qualify for) — should short-circuit per §11.1 with a critical blocker before deep scoring. Should land in the 0–54 band with `reject`.

A fourth **adversarial fixture** (image-only PDF) exercises the recovery path in §4.5 and is used by the §19 eval harness.

Each fixture is a real or realistic SAM.gov-style record with at least one attached PDF solicitation. Fixtures are checked into the repo and versioned alongside the prompts that consume them.

Each opportunity should include:

* Title
* Agency
* Solicitation number
* Source URL
* Due date
* NAICS
* Set-aside status
* Location/place of performance if available
* Short description
* Attachment/document references

### Output

The system displays ranked opportunity cards with:

* Fit score
* Decision: pursue / maybe / reject
* Main reason
* Main risk
* Link to detail view

---

## 5.5 Solicitation Document Parsing

The system must parse solicitation documents and preserve source context.

Supported MVP document types:

* PDF
* text extracted from PDF
* DOCX if easy
* manually uploaded solicitation files

The parser should extract text from documents and preserve page-level references where possible.

The parser must support:

* PDF text extraction
* Page-level text
* Basic chunking
* Source document metadata
* Extraction confidence

### Required extracted categories

The MVP should extract as many of the following as available:

* Opportunity title
* Solicitation number
* Agency
* Due date
* Questions deadline
* NAICS
* Set-aside status
* Submission instructions
* Required documents
* Evaluation criteria
* Technical requirements
* Past performance requirements
* Clearance/security requirements
* Insurance or bonding requirements
* Place of performance
* Period of performance
* Contract type if available
* Pricing instructions if available

---

## 5.6 Requirement Extraction

The system must turn raw solicitation text into structured requirements.

Each extracted requirement must include:

* Requirement type
* Title
* Extracted value
* Description
* Confidence level
* Evidence snippet
* Source document
* Page number if available
* Blocker flag if relevant

### Requirement types

Supported MVP types:

* eligibility
* technical
* past_performance
* certification
* insurance
* bonding
* security
* submission
* evaluation
* deadline
* location
* pricing
* document_required

### Confidence levels

* high: explicit source text found
* medium: likely supported by source text
* low: ambiguous extraction
* unknown: not found or not enough evidence

### Evidence requirement

The system should show source-backed evidence snippets for important requirements. This is required for credibility and user trust.

---

## 5.7 Fit Scoring

The system must compare the company profile against each opportunity's requirements and generate a score.

Total score: 100 points.

Scoring dimensions (weights sum to 100):

```txt
Capability match:                    20
Eligibility/set-aside match:         15
NAICS/industry match:                10
Past performance fit:                15
Certification/compliance readiness:  10
Insurance/bonding readiness:         10
Deadline feasibility:                10
Proposal complexity:                  5
Geography/place of performance fit:   5
-----------------------------------
Total:                              100
```

### Decision bands

```txt
85–100: Strong pursue
70–84:  Pursue
55–69:  Maybe / needs partner
 0–54:  Reject / weak fit
```

### Output

Each fit score must include:

* Total score
* Decision
* Confidence
* Score breakdown
* Strengths
* Weaknesses
* Blockers
* Missing information
* Recommended next action

---

## 5.8 Risk and Blocker Detection

The system must flag issues that affect whether the company should pursue the opportunity.

Risk categories:

* Clearance required but unavailable
* Set-aside mismatch
* Certification gap
* Past performance weakness
* Deadline too close
* Missing or unclear attachments
* Submission ambiguity
* Insurance or bonding gap
* Scope mismatch
* Legal/compliance review required
* Pricing complexity
* Required document not found

Risk severities:

* critical blocker
* major risk
* moderate risk
* minor concern

### Output

Each risk must include:

* Title
* Severity
* Explanation
* Evidence if available
* Recommended mitigation
* Whether human review is required

---

## 5.9 Opportunity Ranking

The system must display ranked opportunity cards.

Each card should show:

* Opportunity title
* Agency
* Due date
* NAICS
* Set-aside
* Fit score
* Decision
* Top reason
* Main risk

The ranking should prioritize opportunities that are both relevant and realistically pursuable.

---

## 5.10 Opportunity Detail View

The system must provide a detail view for analyzed opportunities.

Detail view sections:

* Summary
* Extracted requirements
* Evidence snippets
* Fit score breakdown
* Risk flags
* Missing information
* Recommended next action
* Source documents

This screen should make the decision explainable and verifiable.

---

## 5.11 Action Package Generator

The system must generate a final action package for a selected opportunity.

Required sections:

1. Executive pursuit brief
2. Pursue/no-pursue decision
3. Fit score rationale
4. Compliance matrix
5. Risk register
6. Proposal checklist
7. Timeline to submission
8. Partner or teaming suggestion if relevant
9. Outreach draft if relevant
10. Human approval checklist

### Compliance matrix fields

Each compliance row should include:

* Requirement
* Status: met / missing / unclear / not applicable
* Evidence
* Next action
* Owner

### Risk register fields

Each risk should include:

* Risk
* Severity
* Explanation
* Mitigation

### Proposal checklist

Checklist should include concrete next actions such as:

* Verify SAM registration
* Confirm eligibility
* Review required documents
* Draft technical response
* Prepare past performance references
* Confirm submission deadline
* Review pricing requirements
* Confirm insurance/bonding requirements
* Get authorized approval before submission

---

## 5.12 Partner / Teaming Suggestion

The MVP should include a lightweight partner suggestion section when the company has a gap that a partner could solve.

Examples:

* Need a cleared prime
* Need a past performance partner
* Need a local delivery partner
* Need a specialized compliance partner
* Need a subcontractor with a missing technical capability

The system should not invent contact information.

Each suggestion should include:

* Partner type needed
* Gap being solved
* Why the partner matters
* Suggested outreach angle
* Confidence level

A full partner marketplace is not part of the MVP.

---

## 5.13 Human Approval Gates

The system must clearly require human approval before sensitive actions.

Human approval required before:

* Contacting a contracting officer
* Contacting a partner company
* Sending outreach email
* Submitting proposal materials
* Claiming compliance
* Claiming certifications
* Sending pricing
* Uploading signed documents
* Making legal representations

MVP implementation:

The product should show an approval block in the action package.

Example:

```txt
Human approval required before using this output externally.
Do not send emails, submit materials, claim certifications, or mark compliance complete without authorized review.
```

Buttons may include:

* Copy outreach draft
* Mark reviewed
* Export package

No real email sending is required for MVP. (Inside the agent run, that is. Outbound marketing email — the §5.14 weekly opportunity drop — is a separate, opt-in channel.)

---

## 5.14 Weekly Opportunity Email

A standalone outbound channel: one curated federal opportunity per week, sent to opted-in subscribers as a low-commitment preview of what the bid-desk produces in-product. **One email per recipient per week, ever.** Unsubscribe is one-click and works without login.

### Audience

Reuses `waitlist_signups` (the existing landing form). New columns on that table track preferences:

* `weekly_opportunity_enabled` (default `true` — the form copy says "we'll send you one curated federal opportunity each week")
* `unsubscribed_at` / `unsubscribed_reason`
* `bounced_at` / `complained_at` (driven by future Resend webhook; harmless until then)
* `confirmed_at` (only consulted if `EMAIL_REQUIRE_DOUBLE_OPT_IN=true`; default `false`)
* `last_emailed_at` (denormalized convenience; authoritative log is `weekly_opportunity_email_log`)

Eligibility = `weekly_opportunity_enabled AND unsubscribed_at IS NULL AND bounced_at IS NULL AND complained_at IS NULL AND no row in weekly_opportunity_email_log for (email, week_key, 'weekly_opportunity', 'sent')`.

### Cadence and idempotency

* `week_key = "YYYY-Www"` (ISO 8601, UTC).
* `weekly_opportunity_email_log` carries `UNIQUE (email, week_key, email_type)`. Job uses two-phase `INSERT … ON CONFLICT DO NOTHING RETURNING id` to claim a slot atomically before calling Resend, then `UPDATE` with `status='sent', resend_message_id, sent_at`.
* On Resend 4xx/5xx, the row is left as `failed`. The next weekly run will skip it (slot taken). Re-attempt requires manual `DELETE` — intentional, prevents runaway retries that look spammy.

### Pick selection

Two paths into `weekly_opportunity_picks (week_key UNIQUE, opportunity_id, source, picker_audit, …)`:

1. **Curator override** — `scripts/pick_weekly_opportunity.py --week 2026-W19 --opportunity-id <uuid>`. `source='manual'`. Refuses fixture-sourced opportunities unless `--allow-fixture` is passed.
2. **LLM auto-picker** — `api/jobs/auto_pick_weekly_opportunity.py`, fired by `govcapture-cron-auto-pick.timer` Sunday 22:00 UTC. Pulls a candidate set from the last 7 days of cached opportunities (or live SAM if `SAM_API_KEY` set), applies hard safety filters, ranks survivors against a clearly-labeled synthetic SMB profile via the existing `score_fit` skill, picks the top candidate above `EMAIL_AUTO_PICK_MIN_SCORE` (default 60) with `confidence ∈ {high, medium}`. `source='llm_auto'`. If no candidate passes, no row is written and the Monday send job exits clean. The `picker_audit` JSONB column logs which candidates were considered and why each was rejected.

Manual override wins via `INSERT … ON CONFLICT (week_key) DO NOTHING` — if the curator pinned a pick before Sunday 22:00, the auto-picker silently skips.

### Hard safety filters (auto-picker, deterministic, no LLM input)

Honor the spirit of §11.1 across an audience the agent does not have CompanyProfile data for:

* `set_aside IS NULL OR set_aside = 'Total Small Business'`. Anything narrower (8(a), HUBZone, WOSB, EDWOSB, SDVOSB, VOSB) requires per-subscriber eligibility we don't have.
* `due_date >= today + 14 days`. Recipient needs time to act.
* `place_of_performance` is US (NULL or US states).
* Description does not contain (case-insensitive whole-word): `secret`, `top secret`, `clearance`, `cleared personnel`, `CUI`, `controlled unclassified`, `ITAR`, `classified`.
* NAICS in `EMAIL_NAICS_ALLOWLIST` if set.
* `attachments` non-empty.

Only survivors are scored.

### Email content

Subject: `"This week's federal opportunity: {opportunity.title[:60]}"`. Plain-text alternative always sent alongside HTML.

Body, in order:

1. Header — "GovCapture · Week NN, YYYY".
2. Honest framing — "One contract worth a look. We picked it from this week's SAM.gov listings." Not "you should pursue this."
3. Opportunity card — title, agency, solicitation number, due date, NAICS, set-aside, place of performance, short description.
4. Single CTA button — "View on SAM.gov" linking to `opportunity.source_url`. No secondary CTAs.
5. Honest framing 2 — "This isn't a fit analysis — it's one opportunity to read. Run a real fit check at govcapture.app."
6. Footer — sender name, `EMAIL_LEGAL_FOOTER_ADDRESS`, signed unsubscribe link, "you're getting this because…" line.

No fake personalization (no `Hi {first_name}` — we don't have first names).

### Headers

* `List-Unsubscribe: <https://api.govcapture.example/email-subscriptions/unsubscribe?token=…>, <mailto:unsubscribe@govcapture.app>`
* `List-Unsubscribe-Post: List-Unsubscribe=One-Click` (RFC 8058)
* `X-Entity-Ref-ID: <log_row_id>` for trace correlation

### Unsubscribe

Token = `base64url(HMAC-SHA256(EMAIL_UNSUBSCRIBE_SECRET, subscription_id + ':' + email))`. Stable across weeks. URL `GET /email-subscriptions/unsubscribe?token=…` validates, sets `unsubscribed_at = now()`, returns a small inline HTML page from FastAPI (no Next.js round-trip). `POST` of the same URL serves List-Unsubscribe-Post one-click and returns 204. Raw subscription IDs and emails never appear in URLs — the HMAC binds them.

### Cron + protection

* `POST /internal/cron/weekly-opportunity-email` requires `Authorization: Bearer ${INTERNAL_API_KEY}` (constant-time compare). Returns structured JSON: `{week_key, opportunity_id, total_eligible, sent, skipped_already_sent, failed, dry_run}`.
* nginx returns 404 for `/internal/*` paths at the edge — the route is reachable only over loopback from the systemd timer.
* `EMAIL_DRY_RUN=true` (default) writes `weekly_opportunity_email_log` rows with `status='dry_run'` and never calls Resend. Production deploy must explicitly flip to `false` after a verified domain test.

### Production gating

`api/config.py` refuses to start when `EMAIL_DRY_RUN=false` AND any of `RESEND_API_KEY`, `EMAIL_UNSUBSCRIBE_SECRET`, `EMAIL_LEGAL_FOOTER_ADDRESS` is empty.

### Observability

Per-attempt structured JSON to `journalctl -u govcapture-cron-weekly`. Logs hash recipient emails (SHA-256). Resend message ID retained — not a secret. No raw email addresses, no API keys, no token values in logs.

---

# 6. Non-Goals for MVP

The MVP will not include:

* Official proposal submission
* SAM.gov account registration
* Automated legal review
* Insurance procurement
* Bonding procurement
* Full CRM
* Full partner marketplace
* Payment system
* Team workspaces
* Real proposal submission via email (weekly opportunity emails ARE in scope — see §5.14)
* Google Docs export
* Full proposal drafting from scratch
* Self-hosted models
* GPU infrastructure
* Classified or controlled document workflows

---

# 7. Technical Stack

## 7.1 Frontend

Recommended:

```txt
Next.js
TypeScript
Tailwind CSS
shadcn/ui
Vercel
```

Frontend responsibilities:

* Profile and goal screen
* Agent run timeline
* Opportunity ranking cards
* Opportunity detail page
* Action package page
* Approval gate UI

---

## 7.2 Backend

Chosen (v1.2.3):

```txt
Python FastAPI on Vultr VX1 (native systemd, no Docker)
Redis on VX1 (SSE pub/sub bridge)
Supabase Postgres (managed; replaces native PG)
Supabase Storage (managed; replaces /var/lib/govcapture/{raw,parsed})
```

Backend responsibilities:

* Agent run request persistence and result reads
* Opportunity loading/search
* Document parsing
* Requirement extraction
* Fit scoring
* Risk detection
* Action package generation
* API endpoints

Michaela orchestration is no longer owned by this repo. The external
`/root/michealaai` runtime picks up run requests and writes trace/results
back through this pack's contracts.

---

## 7.3 Agent / Automation Layer

Chosen:

```txt
Michaela system on Hermes runtime in /root/michealaai
This repo's .hermes directory is pack-local tool context only
Optional browser/channel substrate when needed
```

Michaela owns the board and product workloop. Hermes is the runtime shell that
loads project-local context, skills, memory, provider config, and worker
delegation. Michaela's repo defines the seven named agents and orchestration
recipes. This repo's `.hermes/` folder only carries tool-procedure context for
isolated testing of the GovCon pack. FastAPI owns deterministic domain tools,
schema validation, persistence, and the public API surface.

Bench responsibilities:

* Michaela: orchestration, priority setting, final user-facing answer
* Scot: SAM.gov discovery / seeded fallback
* Lenny: fit ranking and pursue/monitor/skip decision support
* Gabby: eligibility blocker checks and §11.1 hard reject gate
* Lance: USASpending / incumbent / award-history intelligence
* Happer: repeatable execution, attachment fetches, PDF parsing
* Roy: bid memo, capability statement, CO email, action package

OpenClaw may still be used as a bounded channel/browser substrate for portal
work, web chat, WhatsApp, or Slack, but it is not a second agent brain.

---

## 7.4 AI Layer

Recommended:

```txt
Hosted LLM API
Structured JSON outputs
Schema validation
```

Use LLMs for:

* Goal parsing
* Requirement extraction
* Fit scoring explanation
* Risk analysis
* Action package generation
* Outreach draft generation

All structured model outputs must be validated before display.

---

## 7.5 Data Storage

Chosen (v1.2.4):

```txt
Supabase Postgres        — structured data (PRD §8 tables)
Supabase Storage         — raw and parsed solicitation files
Redis on VX1             — SSE pub/sub bridge for the agent run trace
Supabase Auth            — email auth / JWT identity for user routes
```

The FastAPI app uses `supabase-py`'s async client against Supabase PostgREST
with the server-only service role key. SQLAlchemy, asyncpg, Alembic, and
`DATABASE_URL` are not part of v1.2.4 runtime or migrations.

Storage layout:

| Bucket / prefix | Contents | Retention |
|---|---|---|
| `govcapture-attachments/raw/<run_id>/<filename>` | Original PDFs (live SAM fetch + uploads) | Per §17 Q6 (30-day raw policy via bucket-level retention rule) |
| `govcapture-attachments/parsed/<run_id>/<doc_id>.json` | Output of `parse_pdf` (chunks + metadata) | Indefinite — small, useful for re-scoring |
| `govcapture-attachments/fixtures/<slug>/...` | Seeded fixture PDFs (committed shape, mirrored to bucket for prod) | Indefinite |

For MVP speed, a seeded JSON dataset is acceptable for opportunity and package data as long as the product still performs a real analysis workflow.

---

## 7.6 Deployment Target

The MVP runs on a single Vultr **VX1** general-purpose VPS:

```txt
Vultr VX1 — General Purpose
16 vCPU / 64 GB RAM
960 GB NVMe
Ubuntu 24.04 LTS
```

VX1 hosts the application stack natively; **Postgres and object storage are externalized to Supabase** (v1.2.3 — see §7.5). Allocation:

| Service | Role | Notes |
|---------|------|-------|
| Next.js (built, served by Node or behind nginx) | Frontend | Could also be deployed to Vercel; keep both options open |
| FastAPI (uvicorn + gunicorn workers, under systemd) | Capability-pack API | 4–8 workers; scale with vCPU |
| Redis (apt-installed, native systemd unit) | SSE pub/sub bridge for the agent run trace | Single instance, persistence on |
| nginx | TLS termination + reverse proxy | Let's Encrypt via certbot |
| systemd | Service supervision | One unit per long-running process (`govcapture-api`, `redis-server`, `nginx`); no Docker, no compose |
| **Supabase Postgres** (external) | Structured data (§8) | Connected over SSL; managed backups; no on-box pg install |
| **Supabase Storage** (external) | Raw + parsed solicitation files | Bucket-level retention policy implements §17 Q6 |
| Michaela / Hermes runtime (separate) | Orchestration and worker bench | Lives in `/root/michealaai`; calls this pack |

### Sizing notes

* 16 vCPU comfortably handles parallel PDF parsing and concurrent agent runs; planner concurrency budget can run multiple opportunities in parallel rather than strictly sequentially.
* 64 GB RAM leaves room for Redis, headless Chromium instances, and FastAPI workers without swap. Postgres shared buffers no longer competing for RAM since PG is off-box.
* 960 GB NVMe is dramatically over-provisioned now that PDFs live in Supabase Storage; the box only needs working space for Hermes' filesystem tools, Redis persistence, and journal logs.

### Operational hygiene

* Provision via a one-shot bootstrap script (`infra/bootstrap.sh`) so the box is reproducible. Bootstrap installs Redis, Python, Hermes, and nginx via `apt`; the FastAPI app runs under a `govcapture-api.service` systemd unit.
* Firewall: ufw allow 22/tcp, 80/tcp, 443/tcp; deny everything else.
* Unattended security upgrades enabled; FastAPI and Hermes run as a non-root `govcapture` user.
* **Supabase handles Postgres backups** (point-in-time restore on Pro tier; 7-day rolling on Free tier — fine for MVP). The on-box pg_dump cron is dropped.
* Health check endpoint (`/healthz`) for the agent run service so the demo is monitorable. Supabase's own status page covers DB / Storage health.

This deployment target supersedes the generic "Vultr VPS" reference in §7.2.

---

# 8. Minimal Data Model

## 8.1 CompanyProfile

```txt
id
name
website
description
capabilities
industry_keywords
location
service_area
naics_codes
certifications
small_business_status
sam_status
clearance_status
past_performance
insurance_bonding_status
preferred_contract_size
preferred_role
created_at
updated_at
```

## 8.2 Opportunity

```txt
id
title
agency
solicitation_number
source_url
due_date
naics
set_aside
place_of_performance
description
attachments
raw_payload
created_at
updated_at
```

## 8.3 ExtractedRequirement

```txt
id
opportunity_id
type
title
value
description
confidence
evidence_snippet
source_document
page_number
is_blocker
created_at
```

## 8.4 FitScore

```txt
id
opportunity_id
company_profile_id
total_score
decision
confidence
breakdown
strengths
weaknesses
blockers
missing_info
recommended_next_action
created_at
```

## 8.5 RiskFlag

```txt
id
opportunity_id
company_profile_id
category
severity
title
description
evidence
mitigation
requires_human_review
created_at
```

## 8.6 ActionPackage

```txt
id
opportunity_id
company_profile_id
executive_summary
decision
fit_score
fit_rationale
compliance_matrix
risk_register
proposal_checklist
timeline
partner_suggestions
outreach_draft
approval_required
created_at
```

## 8.7 AgentRun

```txt
id
profile_id
goal
company_profile_id
status
steps
opportunities
selected_opportunity_id
action_package_id
created_at
completed_at
```

---

# 9. Minimal API Requirements

## Required endpoints

```txt
POST /company-profiles
GET  /company-profiles/:id
GET  /profiles/me
POST /profiles/me
POST /agent-runs
GET  /agent-runs/:id
GET  /agent-runs/:id/opportunities
GET  /opportunities/:id
GET  /opportunities/:id/requirements
GET  /opportunities/:id/fit-score
GET  /opportunities/:id/risks
GET  /action-packages/:id
POST /waitlist
```

For MVP speed, the company profile may also be included directly when creating an agent run.

Public endpoints: `GET /healthz`, `POST /waitlist`, landing page.
Authenticated endpoints require a Supabase bearer JWT. Internal writeback
POSTs for requirements, fit scores, risks, and action packages require
`X-Internal-API-Key` so public users cannot forge analysis artifacts.

---

# 10. Structured Output Schemas

## 10.1 Requirement Extraction Output

```json
{
  "requirements": [
    {
      "type": "eligibility | technical | past_performance | certification | insurance | bonding | security | submission | evaluation | deadline | location | pricing | document_required",
      "title": "string",
      "value": "string",
      "description": "string",
      "confidence": "high | medium | low | unknown",
      "evidence_snippet": "string",
      "source_document": "string",
      "page_number": 1,
      "is_blocker": false
    }
  ],
  "missing_fields": ["string"],
  "conflicts": [
    {
      "field": "string",
      "candidates": ["string"],
      "requires_human_review": true
    }
  ]
}
```

## 10.2 Fit Score Output

```json
{
  "total_score": 82,
  "decision": "strong_pursue | pursue | maybe | reject",
  "confidence": "high | medium | low",
  "score_breakdown": {
    "capability": 18,
    "eligibility": 14,
    "naics": 9,
    "past_performance": 10,
    "certification": 8,
    "insurance_bonding": 7,
    "deadline": 9,
    "complexity": 4,
    "geography": 3
  },
  "strengths": ["string"],
  "weaknesses": ["string"],
  "blockers": ["string"],
  "missing_information": ["string"],
  "recommended_next_action": "string"
}
```

## 10.3 Action Package Output

```json
{
  "executive_summary": "string",
  "decision": "string",
  "fit_score": 82,
  "fit_rationale": "string",
  "compliance_matrix": [
    {
      "requirement": "string",
      "status": "met | missing | unclear | not_applicable",
      "evidence": "string",
      "next_action": "string",
      "owner": "string"
    }
  ],
  "risk_register": [
    {
      "risk": "string",
      "severity": "critical | major | moderate | minor",
      "explanation": "string",
      "mitigation": "string"
    }
  ],
  "proposal_checklist": ["string"],
  "timeline": [
    {
      "date": "string",
      "task": "string",
      "owner": "string"
    }
  ],
  "partner_suggestions": [
    {
      "partner_type": "string",
      "gap_solved": "string",
      "why_needed": "string",
      "outreach_angle": "string",
      "confidence": "high | medium | low"
    }
  ],
  "outreach_draft": {
    "subject": "string",
    "body": "string"
  },
  "human_approval_required": ["string"]
}
```

---

# 11. Prompting Requirements

Every agent prompt must include:

* Role
* Objective
* Inputs
* Output schema
* Guardrails
* Uncertainty behavior
* Requirement to distinguish extracted facts from inferences
* Requirement to include source evidence when available
* Requirement to avoid legal/compliance overclaims

## Requirement extraction prompt behavior

The model must:

* Extract only supported requirements
* Preserve exact dates and deadlines
* Include source snippets
* Include confidence levels
* Mark missing information
* Identify conflicts
* Avoid inventing requirements

## Fit scoring prompt behavior

The model must:

* Compare solicitation requirements against the company profile
* Apply the scoring rubric
* Identify blockers
* Be conservative on eligibility
* Explain the decision
* Recommend a next action

## Action package prompt behavior

The model must:

* Generate practical business artifacts
* Include uncertainty where needed
* Preserve human approval requirements
* Avoid claiming legal compliance unless verified
* Produce concise, useful next steps

---

## 11.1 Eligibility Conservatism Rule

Eligibility hallucination is the highest user-harm failure mode (telling a non-eligible company to pursue a set-aside they cannot win). The fit-scoring prompt and the planner's eligibility short-circuit (§4.5) MUST follow these rules:

* If eligibility is uncertain, score the eligibility dimension **0** (not partial credit) and emit a critical blocker.
* Set-aside mismatches (8(a), HUBZone, WOSB, EDWOSB, SDVOSB, VOSB, etc.) where the company has not declared the matching certification → **always** critical blocker, never soft penalty.
* Clearance requirements not held by the company → **always** critical blocker.
* Foreign-ownership or citizenship requirements → critical blocker if unclear.
* Any critical eligibility blocker forces `decision = reject`, regardless of capability/NAICS strengths. The planner MUST NOT weigh strengths against hard eligibility blockers.

Example (correct):

> Solicitation requires 8(a) certification. Company profile lists no 8(a). → eligibility score 0, critical blocker, decision = reject.

Example (forbidden, MUST NOT produce):

> Solicitation requires 8(a). Capability match strong → score 72, decision = pursue with note about 8(a).

This rule is enforced by the §19 eval harness against the reject fixture.

---

# 12. Build Plan

## Phase 1: Foundation

Deliverables:

* Frontend shell
* Backend shell
* Company profile creation
* Contracting goal input
* Agent run object
* Agent run timeline
* Seeded opportunity loading

Success criteria:

* User can create a profile, enter a goal, start a run, and see workflow progress.

---

## Phase 2: Opportunity Workflow

Deliverables:

* Opportunity loader or SAM.gov connector
* Opportunity normalization
* Ranked opportunity cards
* Opportunity detail page
* Source URL and metadata preservation

Success criteria:

* System displays relevant opportunities with enough metadata for analysis.

---

## Phase 3: Document Parsing

Deliverables:

* PDF upload or retrieval
* PDF text extraction
* Page-level snippets
* Chunking
* Requirement extraction schema
* Requirement display UI

Success criteria:

* System extracts structured requirements from at least one solicitation document.

---

## Phase 4: Fit Scoring and Risk Detection

Deliverables:

* Scoring rubric
* Fit score output
* Blocker detection
* Risk flags
* Missing information detection

Success criteria:

* System recommends pursue/maybe/reject with explanations and evidence.

---

## Phase 5: Action Package

Deliverables:

* Executive brief
* Compliance matrix
* Risk register
* Proposal checklist
* Timeline
* Partner/team suggestion
* Outreach draft
* Approval gate

Success criteria:

* System generates one complete action package that a real business could review.

---

## Phase 6: Outreach Readiness

Deliverables:

* Stable deployed URL
* Reliable seeded sample run
* Ability to create or edit company profiles
* Ability to analyze at least one opportunity end-to-end
* Clean product explanation
* Clear output that can be shown to small businesses or consultants

Success criteria:

* Team can reach out to companies and show a working product flow, not only slides or mockups.

---

# 13. Acceptance Criteria

The MVP is acceptable if:

* User can enter or create a company profile
* User can enter a contracting goal
* Agent run timeline shows workflow steps
* System displays relevant opportunities
* System parses at least one solicitation document
* System extracts structured requirements with evidence
* System scores fit against the company profile
* System recommends pursue/maybe/reject
* System flags clear blockers and risks
* System generates an action package
* System shows human approval gates
* Product can be shown to real target users for feedback

The MVP is not acceptable if:

* It only summarizes pasted text
* It only lists opportunities without decisions
* It cannot explain why an opportunity was accepted or rejected
* It has no source evidence
* It invents requirements or contact information
* It claims to submit official proposals
* It lacks human approval gates

---

## 13.1 Demo Script

A 3-minute live demo for hackathon judging. The demo runs against the §5.4 seeded fixtures so SAM.gov rate limits or network issues cannot break the pitch.

In the v1.2.5 split, the live run must be driven by the external Michaela
runtime. `/web` may queue the run request and display/refresh outputs, but it
does not execute agents inside this repo.

**0:00 – 0:30 — Problem framing.** "Small businesses leave billions in federal contracts on the table because qualifying an opportunity takes hours of PDF reading, eligibility-checking, and compliance-matrix building. We built an autonomous capture analyst that does the first-pass work in minutes."

**0:30 – 1:00 — Setup.** Show a real small-business profile (e.g., a Texas-based cybersecurity firm, 12 employees, no 8(a), CMMC Level 2, SAM-registered). Enter the goal: *"Find cybersecurity opportunities we can pursue in the next 60 days."*

**1:00 – 2:00 — Live agent run.** The §5.3 timeline updates in real time, projected from the §4.5 agent trace. Highlight on stage:

* Tool calls visible as they happen (`search_sam_opportunities` → `fetch_attachment` → `parse_pdf` → `extract_requirements` → `score_fit` → `detect_risks` → `generate_action_package`).
* Evidence snippets linked to specific PDF pages — click one, the source PDF opens at the cited page.
* Three opportunities returned:
  * **Strong-pursue** (fixture 1) — 88/100 with rationale and concrete next actions.
  * **Maybe — needs partner** (fixture 2) — 64/100 with a partner-type suggestion (§5.12) explaining the gap.
  * **Reject** (fixture 3) — short-circuited at eligibility (§11.1) with the blocker evidence-cited from page X of the solicitation.

**2:00 – 2:30 — Output.** Open the action package (§5.11) on the strong-pursue opportunity. Show executive brief, compliance matrix, risk register, proposal checklist with deadlines, draft outreach message, and the human-approval block.

**2:30 – 3:00 — Close.** "Every claim has source evidence. Every sensitive action requires human approval. The agent picks tools, recovers from failures, stays within a $0.50 cost budget per run, and produces output a small business owner can verify and act on. This is the first-pass capture analyst small businesses can't afford to hire."

### Backup demo paths

* If a tool call fails live, the timeline shows the §4.5 recovery (degraded → seeded fallback). This is a feature, not an embarrassment — call it out.
* If wall-clock budget runs short, switch directly to a pre-cached completed run on the same fixtures and walk the action package.

---

# 14. Product Success Metrics

## Early user validation metrics

* Number of companies or consultants shown the product
* Number of users willing to share their company profile or opportunity target
* Number of users who say the output would save them time
* Number of users who request a follow-up analysis
* Number of users willing to pay or pilot
* Number of useful corrections users make to the agent output

## Product utility metrics

* Opportunities analyzed per run
* Requirements extracted per opportunity
* Percentage of requirements with evidence snippets
* Fit score completion rate
* Action package generation rate
* Number of blocker/risk flags surfaced
* User-rated usefulness of action package

## Reliability metrics

* Agent run completion rate
* Document parse success rate
* Structured extraction success rate
* Invalid JSON/error rate
* Average run time
* Number of manual fallbacks required

---

# 15. Outreach Positioning

For early company outreach, position the product as:

> GovCapture Agent helps small businesses quickly understand which government contracts are worth pursuing. It reads solicitation documents, extracts requirements, scores fit, flags blockers, and generates a first-pass action package.

Avoid claiming:

* guaranteed eligibility
* guaranteed compliance
* automatic proposal submission
* legal review
* guaranteed contract wins

Use language like:

* first-pass capture analysis
* opportunity qualification
* pursuit readiness
* requirements extraction
* blocker detection
* action package
* human-reviewed workflow

---

# 16. Final Product Positioning

GovCapture Agent turns a small business profile into a government contract action package. It searches opportunities, reads solicitation documents, extracts requirements, scores fit, identifies blockers, and generates next actions so businesses know what to pursue and what to avoid.

The product should be described as:

> An autonomous capture analyst for small businesses pursuing government contracts.

The product should make early users think:

> This helps me avoid wasting time on bad-fit opportunities and gives me a concrete starting point for the ones worth pursuing.

---

# 17. Open Questions & Risks

These are unresolved decisions to track during build. None block Phase 1, but each should be resolved before its corresponding phase ships.

| # | Question | Phase | Default if undecided |
|---|----------|-------|----------------------|
| 1 | Which hosted LLM provider, and what is the per-run cost ceiling? | Phase 3 | Use cheapest model that produces valid JSON; cap at $0.50/run. |
| 2 | OCR fallback for image-only PDFs (e.g., scanned solicitations)? | Phase 3 | Skip OCR in MVP; mark document as "unparseable" and surface to user. |
| 3 | How are SAM.gov API keys provisioned per environment, and what is the rate-limit budget? | Phase 2 | Single shared key with seeded-fixture fallback on 429. |
| 4 | Is multi-tenancy (multiple companies per account) in scope? | Phase 1 | No — single profile per session for MVP. |
| 5 | Authentication model for the deployed app? | Phase 6 | Magic-link email auth or none (anonymous run + share link). |
| 6 | How long is parsed document text retained? | Phase 3 | 30 days, then purge raw text; keep extracted requirements. |
| 7 | What happens when fit score is borderline (e.g., 54 vs. 55)? | Phase 4 | Display score with confidence band; do not treat boundary as binary. |
| 8 | Do we need amendment-detection (solicitation modifications)? | Phase 3 | Out of scope for MVP; document as known limitation. |
| 9 | Hackathon track selection — Agents Track only, or also layer Texas Open Data? | Phase 6 | **Agents Track is primary.** Optional stretch: ship a TX place-of-performance filter and an adapter for `data.austintexas.gov` / `data.sanantonio.gov` / `data.houstontx.gov` / `dallasopendata.com` to surface state and local procurement alongside federal SAM opportunities. Adds a Texas relevance signal for AITX judges without diluting the Agents Track submission. |
| 10 | §5.14 weekly opportunity email — sender domain status? | Outbound email | **Default to the Resend sandbox sender** (`onboarding@resend.dev`) which only delivers to the Resend account-owner inbox — fine for dev. Production requires a verified domain at resend.com/domains (SPF + DKIM + optional DMARC DNS records); flip `RESEND_FROM_EMAIL` to a `noreply@<verified-domain>` address before flipping `EMAIL_DRY_RUN=false`. |

## Top product risks

* **Hallucinated requirements.** Extraction without strict evidence-binding will produce confident-sounding wrong answers. Mitigation: every non-`unknown`-confidence requirement must include an `evidence_snippet`; UI must visibly link to source page.
* **Demo fragility.** Live SAM.gov calls fail or rate-limit during demos. Mitigation: seeded fixtures are first-class, not a fallback hack.
* **Eligibility overclaim.** Telling a non-set-aside-eligible company they can pursue a set-aside contract is a serious user harm. Mitigation: scoring prompt must be conservative on eligibility; eligibility mismatch is always a critical blocker, never a soft penalty.
* **PDF parsing variance.** Solicitations vary wildly in structure. Mitigation: page-level chunking + per-requirement-type extraction prompts, not a single mega-prompt.

---

# 18. Data Handling & Privacy

The MVP processes company profile data and government solicitation documents. Solicitations on SAM.gov are public, but company profiles may contain non-public information (past performance, certifications, internal capabilities).

MVP commitments:

* Company profile data is stored only as needed to run analyses; no third-party sharing.
* LLM calls send profile + solicitation text to the chosen hosted provider — users must be told this in the profile-creation UI.
* No CUI (Controlled Unclassified Information) or classified material should be uploaded; the upload UI must display this restriction.
* Raw uploaded documents are retained per §17 question 6; users can request deletion.
* No PII beyond user email and company-volunteered profile data is collected.
* **Weekly opportunity email subscribers (§5.14):** address is shared with Resend (email-delivery processor) at send time and stored in Supabase Postgres. No third-party sharing beyond delivery. Unsubscribe is one-click and removes the recipient from all future sends; the `weekly_opportunity_email_log` row is retained for audit but the subscription row is marked `unsubscribed_at` and skipped by all future eligibility queries.

Out of scope for MVP: SOC 2, FedRAMP, ITAR handling, encrypted-at-rest guarantees beyond cloud provider defaults, GDPR/CCPA data-subject-request endpoints beyond unsubscribe, Resend bounce/complaint webhook ingestion (planned post-MVP — `bounced_at`/`complained_at` columns are present and unused).

---

# 19. Evaluation Harness

A minimal eval suite ensures changes to prompts, tool implementations, or model versions do not regress demo quality. It is also the pre-demo smoke test.

## Fixtures

The three §5.4 demo fixtures (strong-pursue / maybe / reject) plus the adversarial image-only-PDF fixture form the eval set. Fixtures live in the repo and are versioned. Each fixture includes:

* The opportunity record (SAM.gov-style JSON)
* The attached solicitation PDF(s)
* Expected requirement extractions (golden output for ≥80% of titles, exact match on `due_date`, `naics`, `set_aside`)
* Expected fit-score decision band
* Expected critical blockers
* Expected partner-suggestion presence (for the maybe fixture)

## Assertions per fixture

* Requirement extraction recovers expected `due_date`, `naics`, `set_aside` exactly, and ≥80% of expected requirement titles.
* Every requirement with confidence ≥ `medium` has a non-empty `evidence_snippet` and a valid `page_number`.
* Fit-score decision lands in the expected band (strong_pursue / maybe / reject).
* Critical blockers expected by the fixture are present in the risk register; **§11.1 reject-fixture short-circuit is asserted explicitly** (eligibility score = 0, decision = reject, regardless of capability strengths).
* Action package contains every §5.11 section (no missing sections, no empty required fields).
* Total run cost ≤ §17 Q1 ceiling; total wall-clock ≤ §4.5 budget.

## Run

* Current repo validation: `make fixtures-validate` plus the seeded-skill tests
  (`test_load_seeded`, `test_score_fit`, `test_detect_risks`,
  `test_generate_action_package`) run locally against seeded fixtures with no
  live SAM.gov calls.
* Planned full eval harness: pass/fail summary plus JSON diff of any drift from
  golden outputs.
* Run the current validation before any prompt or tool change ships. Treat the
  full golden diff harness as a launch-hardening task, not something already
  present in the repo.

## Adversarial cases (stretch)

* Solicitation with **conflicting set-aside language** across attachments → conflict surfaced in the §10.1 `conflicts` array, `requires_human_review = true`.
* Solicitation with **deadline already passed** → decision = reject, blocker = "deadline passed."
* Profile **missing SAM registration** → critical blocker on every opportunity until registration is recorded.
* **Image-only PDF** (the adversarial fixture) → document marked `unparseable`, run continues with available metadata, planner emits `needs_human` if no other documents are usable.
