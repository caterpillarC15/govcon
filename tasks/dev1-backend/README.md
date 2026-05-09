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
| `docker-compose.yaml` | You | Top-level local-dev compose |
| `Makefile` (root) | You | B can request additions via standup |
| `/schemas/*.json` | Shared | Schema PRs need both devs to ack |
| `/api/schemas/`, `/web/lib/schemas/` | Generated | Never hand-edit |

---

## Your task list (suggested order)

| # | Task | Type | File | Done |
|---|------|------|------|------|
| A1 | FastAPI skeleton + Postgres+Redis docker-compose + Hermes install in `api` image | Plumbing | `tasks/A1.md` | [ ] |
| A2 | DB schema + Alembic migrations | Plumbing | `tasks/A2.md` | [ ] |
| A3 | Real CRUD endpoints + SSE proxy (S2 trigger) | Plumbing | `tasks/A3.md` | [ ] |
| A4 | `parse_pdf` skill | Skill | `tasks/A4.md` | [ ] |
| A5 | `extract_requirements` skill | Skill (LLM) | `tasks/A5.md` | [ ] |
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
