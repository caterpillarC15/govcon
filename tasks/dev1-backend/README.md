# Dev 1 — Track A — Backend / Agent / Infra

You own the FastAPI proxy, the Hermes integration, the domain skills, deterministic tooling, the eval harness, and the Vultr VX1 deployment. Track B (Dev 2) owns the frontend, fixture content, and demo choreography. Read this whole file before opening a task.

---

## Read order before any code

Joint docs live at the parent (`../`); your dev-specific files live here. Read in this order:

1. `README.md` (this file) — your map.
2. `../HERMES.md` — agent runtime spec (NEW; read before A9).
3. `../CONTRACTS.md` — schemas, event shapes, env vars, skill registry. **You are the implementor of this contract.**
4. `../INTERFERENCE_MAP.md` — file ownership and shared-file protocols.
5. `../PHASE_0.md` — joint setup; you and Dev 2 do P0.1–P0.7 together before splitting.
6. `../FIXTURES.md` — what Dev 2 hands you. Your skills must consume these shapes correctly.
7. `../DEMO.md` — the §13.1 stage script (you assist; B drives).
8. `RUNBOOK.md` — your dev-specific commands and debugging guide.
9. Start with `tasks/A1.md`.

`STANDUP.md` here is your append-only log; check `../dev2-frontend/STANDUP.md` for B's updates.

---

## Your surface

| Path | Owner | Notes |
|------|-------|-------|
| `/api/**` | You | Except `/api/schemas/` (codegen'd) |
| `/api/skills/**` | You | Domain skills run inside Hermes |
| `/infra/**` | You | Bootstrap, nginx, certbot, backups |
| `/eval/runner/**` | You | The harness; B owns `/eval/goldens/` |
| `Makefile` (root) | You | B can request additions via standup |
| `/schemas/*.json` | Shared | Schema PRs need both devs to ack |
| `/api/schemas/`, `/web/lib/schemas/` | Generated | Never hand-edit |

---

## Your task list (suggested order)

| # | Task | Type | File | Done |
|---|------|------|------|------|
| A1 | FastAPI skeleton + native Postgres/Redis (no Docker) + Hermes install per-host | Plumbing | `tasks/archive/A1.md` | [x] 2026-05-09 |
| A2 | DB schema + Alembic migrations | Plumbing | `tasks/archive/A2.md` | [x] 2026-05-09 |
| A3 | Real CRUD endpoints + SSE proxy (S2 trigger) | Plumbing | `tasks/archive/A3.md` | [x] 2026-05-09 |
| A4 | `parse_pdf` skill | Skill | `tasks/archive/A4.md` | [x] 2026-05-09 |
| A5 | `extract_requirements` skill | Skill (LLM) | `tasks/archive/A5.md` | [x] 2026-05-09 |
| A6 | `score_fit` skill (with §11.1 short-circuit) | Skill | `tasks/A6.md` | [ ] |
| A7 | `detect_risks` skill | Skill (LLM) | `tasks/A7.md` | [ ] |
| A8 | `generate_action_package` skill | Skill (LLM) | `tasks/A8.md` | [ ] |
| A9 | **Hermes integration**: skill manifest, planner instructions, runner, trace bridge (S3 trigger) | Agent integration | `tasks/A9.md` | [ ] |
| ~~A10~~ | ~~OpenClaw bridge~~ — **dropped per PRD v1.2.2; Hermes covers browser-bound tools** | — | — | n/a |
| A11 | `search_sam_opportunities` + `load_seeded_opportunities` skills | Skill | `tasks/A11.md` | [ ] |
| A12 | Eval harness (`make eval`) | Tooling | `tasks/A12.md` | [ ] |
| A13 | VX1 deploy: bootstrap, nginx, TLS, backups, Hermes prod config (S4 trigger) | Ops | `tasks/A13.md` | [ ] |

**Critical path:** A1 → A2 → A3 → A4 → A5 → A6 || A7 → A8 → A9 → A12.
**Parallel-safe** (slot during LLM waits): A11, A13.

> **PRD v1.2.2 changed A9:** the bespoke planner/registry/recovery code is replaced by `hermes-agent`. A9 is now an integration task. Read `HERMES.md` first.

---

## Status (2026-05-09)

**Done:** A1 (skeleton + Hermes v0.13.0 installed) → P0.2 (10 JSON Schemas + `make schemas` codegen wired) → A2 (7 tables, migration `0001_initial`) → A3 (11 endpoints + SSE replay stub from `/schemas/trace-event.example.jsonl`) → A4 (`parse_pdf`, hermetic reportlab tests) → A5 (`extract_requirements`, structured outputs, evidence-binding post-validation) → **PRD v1.2.3 (Supabase pivot)**: Postgres and Storage now hosted on Supabase, infra/* shrinks ~40%, Redis stays local on VX1.

**S2 trigger ready** — Dev 2 can switch `NEXT_PUBLIC_API_BASE` off the mock server.

**Tests:** `uv run pytest api/tests` → 71 passed, 2 skipped (Dev 2's seed-PDF fixtures not authored yet). SSL config in `api/db/__init__.py` is hostname-conditional, so local PG dev keeps working.

**Architecture decisions made (don't relitigate):**

- **Skills layout:** `/api/skills/<name>/{__init__.py, skill.py, prompt.txt}` as plain async Python. Hermes toolset wrapper happens in A9. (A4.md / A5.md skeletons used `/api/agent/tools/`; we moved them so the user-facing skill module path is stable across A9.)
- **Shared LLM client:** `api/llm.py` — `AsyncAnthropic`, structured output via `output_config.format` (no parse-and-retry loop), top-level `cache_control` on the system prompt, per-model cost estimation, surfaces `cache_read_input_tokens`. Skills receive `LLMMetrics`; the trace bridge (A9) wraps into `tool_returned`.
- **Pre-A9 SSE:** `api/agent/replay.py` rewrites `run_id` in the example JSONL and publishes to Redis pub/sub `agent-run:{id}` with a 250 ms initial delay so the SSE subscriber can connect after `POST /agent-runs` returns. Replaced by Hermes bridge in A9.
- **Postgres now Supabase (v1.2.3).** Use the **Direct Connection URL** (port 5432), NOT the pooler at 6543 — asyncpg's prepared statements break transaction-mode pooling. The engine adds `connect_args={"ssl": "require"}` automatically for any non-localhost hostname (`api/db/__init__.py`). Alembic migrations run against Supabase identically; `make migrate` is unchanged. Local PG on `localhost` still works as a dev fallback.
- **Storage now Supabase (v1.2.3).** Bucket `govcapture-attachments`. `api/storage.py` wraps the REST API via httpx (no extra SDK). `parse_pdf` deliberately stays local-path-only; callers (eval harness, Hermes bridge) download from Storage to `/tmp` before invoking the skill.
- **Redis stays native on VX1** for the SSE pub/sub bridge (PRD §7.5). Switching to Supabase Realtime is rework, not speed, since the bridge is already built and the on-the-wire SSE shape is what Dev 2's frontend consumes.
- **Auth (§17 Q5) and Realtime stay deferred.** Service-role key on the FastAPI side mediates all DB/Storage access for v1.2.3. The web client never sees the service role.
- **Migration revision id:** `0001` (overrode autogen hash for clean ordering — there's no prior history).
- **Codegen module suffix stripped** post-generation so `from api.schemas.agent_run import AgentRun` matches A3's spec rather than `agent_run_schema.py`.
- **`LLMMetrics.attempts` allows `0`** for the unparseable-input short-circuit path (no LLM call).

---

## Your prompt drafts

In `prompts/` you have starting drafts. Iterate against `make eval`.

| File | Used by |
|------|---------|
| `prompts/planner.md` | A9 |
| `prompts/extract_requirements.md` | A5 |
| `prompts/score_fit_rationale.md` | A6 |
| `prompts/detect_risks.md` | A7 |
| `prompts/generate_action_package.md` | A8 |

These are not final. The eval harness is the test bench — change a prompt, rerun `make eval`, look at the diff against goldens.

---

## Critical rules

- **§11.1 is enforced twice.** A6 has the deterministic short-circuit. A12 has the eval assertion that capability strengths cannot override the reject fixture's eligibility blocker. Both must pass before you ship.
- **Dev mode uses Haiku** (`LLM_DEV_MODEL`). **Sonnet** (`LLM_SYNTH_MODEL`) is for prod and eval. Default to Haiku in code; switch via env at deploy.
- **Never read env outside `/api/config.py`.** One file owns the truth.
- **Schemas: regenerate via `make schemas`. Both devs ack. Never hand-edit generated files.**
- **Mock server (P0.6) stays alive until A3 lands.** B is fetching from it. Replace it incrementally per endpoint, not in a big-bang switch.
- **Every LLM tool validates its output against the §10 schema before returning.** Invalid JSON → one retry with stricter prompt → on second failure, return degraded output and flag the step.
- **Every tool reports `latency_ms` and `cost_usd`.** The planner uses these for budget tracking. Non-LLM tools report `cost_usd: 0.0`.

---

## When Dev 2 needs you

| Trigger | What B needs from you | Time |
|---------|----------------------|------|
| End of P0 | Mock API responding on every endpoint; SSE replays the example JSONL | ~5 min ack |
| S2 — A3 lands | Real CRUD live; B switches `NEXT_PUBLIC_API_BASE` | ~10 min joint smoke test |
| S3 — A9 lands | First end-to-end localhost dry-run; sit together | ~30 min |
| Schema PR | One-line ack; verify B's `tsc --noEmit` still passes | ~2 min |
| Fixture PR review | Confirm `parse_pdf` accepts the new PDF; `expected.json` shape OK | ~5 min per fixture |
| Demo rehearsal (S5) | At the laptop, ready to restart any container | ~30 min |

---

## When you're stuck

1. Re-read the PRD section linked in the task file (`../../PRD.md`).
2. Check `../STANDUP.md` for prior decisions.
3. If schema-related: stop, ping Dev 2, change together.
4. If LLM output is wrong: check prompt vs. PRD §11; check schema validator; check evidence-binding rule.
5. If recovery is failing: look at `/api/agent/recovery.py` table; confirm the failure mode is mapped to a branch.
6. If runtime is mysterious: tail the agent run trace from Redis pub/sub; the planner's rationale is logged with every tool call.

Don't relitigate frozen decisions. Add a note to STANDUP.md and move on.
