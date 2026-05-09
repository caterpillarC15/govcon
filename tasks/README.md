# Build Plan — Two-Track Layout

GovCapture Agent build, parallelized across two devs. Per the v1.2.2 reorganization:

- **Joint docs (everything both devs need)** live here at `/tasks/` — one canonical copy, no duplication.
- **Dev-specific work (tasks, runbooks, prompts, fixture drafts, design notes)** lives in `dev1-backend/` or `dev2-frontend/`.
- **Per-dev standups** live inside each dev folder (`dev{1,2}-*/STANDUP.md`) — append-only, each dev reads the other's daily.

---

## Layout

```
tasks/
├── README.md                  ← you are here
├── CONTRACTS.md               ← joint: schemas, SSE shapes, env, skill registry
├── HERMES.md                  ← joint: hermes-agent integration spec
├── INTERFERENCE_MAP.md        ← joint: file ownership, shared-file protocols
├── PHASE_0.md                 ← joint: setup checklist (do this together first)
├── FIXTURES.md                ← joint: fixture content spec
├── DEMO.md                    ← joint: §13.1 stage script + backup paths
│
├── dev1-backend/              ← Dev 1 (Track A — backend, Hermes, infra)
│   ├── README.md              ← entry point: read this first
│   ├── RUNBOOK.md             ← commands, debugging, pitfalls
│   ├── STANDUP.md             ← Dev 1's append-only daily log
│   ├── tasks/                 ← A1–A13 task files with code skeletons
│   ├── prompts/               ← LLM prompt drafts (planner, extract, score, risks, package)
│   └── skeletons/             ← bootstrap.sh, systemd units, nginx.conf snippets, etc.
│
└── dev2-frontend/             ← Dev 2 (Track B — frontend, fixtures, demo)
    ├── README.md              ← entry point: read this first
    ├── RUNBOOK.md             ← commands, debugging, pitfalls
    ├── DESIGN.md              ← UI tokens, layout patterns
    ├── STANDUP.md             ← Dev 2's append-only daily log
    ├── tasks/                 ← B1–B14 task files with component skeletons
    └── fixture-content/       ← solicitation PDF text drafts + demo company profile
```

---

## Pick your folder

| Dev | Track | Folder | Surface |
|-----|-------|--------|---------|
| Dev 1 | A — Backend / Agent / Infra | [`dev1-backend/`](dev1-backend/README.md) | FastAPI proxy, Hermes integration, domain skills, Postgres, eval harness, Vultr VX1 deploy |
| Dev 2 | B — Frontend / Fixtures / Demo | [`dev2-frontend/`](dev2-frontend/README.md) | Next.js app on Vercel, agent-run timeline, fixture content, demo choreography |

---

## Cross-folder workflow

1. Both devs do `PHASE_0.md` together (joint setup, ~3 hours).
2. Each dev opens their folder's `README.md` and works `tasks/` top-to-bottom.
3. Sync at the checkpoints in `INTERFERENCE_MAP.md §3` (S1–S5).
4. Daily: append to your folder's `STANDUP.md`; read the other folder's `STANDUP.md`.
5. Schema PRs touch `/schemas/` and require both devs to ack. See `INTERFERENCE_MAP.md §2`.

---

## Frozen decisions

These are settled. Do not relitigate without a joint decision logged in this file's "Decision log" section below.

| Area | Decision | Source |
|------|----------|--------|
| Hackathon track | Agents Track primary; optional Texas Open Data layer | PRD §17 Q9 |
| Deployment target | Vultr VX1 (16 vCPU / 64 GB / 960 GB / Ubuntu 24.04) | PRD §7.6 |
| Agent runtime | **hermes-agent** (Nous Research) | `HERMES.md`, PRD §4.5/§7.3 v1.2.2 |
| LLM provider | Anthropic Claude (Sonnet 4.6 + Haiku 4.5) via `hermes model` | `CONTRACTS.md §4` |
| Schema source | `/schemas/*.json` JSON Schema; codegen Pydantic + zod via `make schemas` | `CONTRACTS.md §2` |
| Frontend hosting | Vercel for `/web`; VX1 hosts API/agent/DB | PRD §7.1, §7.6 |
| Fixture set | strong-pursue, maybe-needs-partner, reject, adversarial-image-pdf | PRD §5.4, `FIXTURES.md` |
| Eligibility rule | §11.1 — uncertainty = score 0 + critical blocker, never soft penalty | PRD §11.1, A6, A12 |
| Cost ceiling | $0.50 per agent run | PRD §17 Q1 |
| Step/time budget | 40 steps / 6 minutes per run | PRD §4.5 |

---

## Decision log (append-only)

- **2026-05-09** — PRD v1.2.1 frozen; Vultr VX1 locked as deployment target.
- **2026-05-09** — Two-track parallelization plan adopted; folder `/tasks` is canonical build plan.
- **2026-05-09** — Anthropic Claude chosen as LLM provider per PRD §17 Q1.
- **2026-05-09** — Adopted `hermes-agent` (Nous Research) as agent runtime. OpenClaw dropped. Track A surface area shrinks. PRD bumped to v1.2.2. See `HERMES.md`.
- **2026-05-09** — Reorganized `/tasks/`: joint docs at root (one canonical copy), dev-specific work in `dev1-backend/` and `dev2-frontend/`. No file duplication. Per-dev standups inside each dev folder.
- **2026-05-09** — **No Docker, anywhere.** Both local dev and the VX1 prod box run Postgres, Redis, FastAPI, and Hermes as native services (Homebrew on macOS, apt + systemd on Ubuntu 24.04). No `docker-compose.yaml`, no `Dockerfile`, no `docker-compose.prod.yaml`. Hermes' multi-backend execution feature is configured to use the local subprocess backend on the VX1. Reasons: simpler dev/prod parity (apt + systemd works the same on both ends after a one-time install step), no Docker daemon to maintain, faster boot, fewer moving parts. A1 and A13 rewritten accordingly.
- **2026-05-09** — **Track A Checkpoint 1 landed (commit `11421b4`).** A1 (FastAPI skeleton + native PG/Redis + Hermes v0.13.0) → P0.2 (10 JSON Schemas in `/schemas/` + `make schemas` codegen via `datamodel-code-generator`) → A2 (Alembic migration `0001_initial`, 7 PRD §8 tables) → A3 (11 endpoints from CONTRACTS.md §6 + SSE replay of `/schemas/trace-event.example.jsonl`). **S2 sync trigger is ready** — Dev 2 can swap `NEXT_PUBLIC_API_BASE` off the mock server.
- **2026-05-09** — **A4 + A5 landed.** `parse_pdf` (pure pypdf, no OCR per PRD §17 Q2) and `extract_requirements` (Anthropic structured outputs via `output_config.format`, prompt-cached system prompt, post-validation: page-bounds + evidence binding + fuzzy-match downgrade per PRD §11). Skills live at `/api/skills/<name>/` as plain async Python — the Hermes toolset wrapper layers on in A9. Shared LLM client at `api/llm.py`. Tests: 71 passed / 2 fixture-dependent skipped.
- **2026-05-09** — **Adopted Supabase for Postgres + Storage.** PRD bumped to v1.2.3. Postgres moves off VX1 onto a Supabase project (asyncpg connects over SSL via Direct Connection on port 5432); raw + parsed solicitation files move from `/var/lib/govcapture/{raw,parsed}` into the Supabase `govcapture-attachments` bucket. **Redis stays native on VX1** (the SSE pub/sub bridge was already built; Realtime would be rework). **Auth stays deferred** per §17 Q5. VX1 still hosts FastAPI + Hermes + Redis + nginx; bootstrap script shrinks ~40% (no postgresql install, no role setup, no pg_dump cron, no `/var/lib/govcapture` data dirs, no `govcapture-backup.{service,timer}`). New `api/storage.py` thin wrapper around the Supabase Storage REST API via httpx. New env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_STORAGE_BUCKET`. SSL config in `api/db/__init__.py` is hostname-conditional so local Postgres dev still works (71 tests stay green).
