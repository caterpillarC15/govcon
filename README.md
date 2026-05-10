# GovCon Bid Desk capability pack

GovCon Bid Desk is a capability pack: shared tools, a data layer, an
HTTP API, and a direct-user product surface (`/web`) for AI agents
operating government-contracting workflows. Michaela — the orchestrator
that drives bid analyses end-to-end — and her worker bench (Scot, Lenny,
Ledger, Gate, Happer, Roy) live in **/root/michealaai**, a separate
TypeScript / Bun project. They consume this pack's tools either through
HTTP or (planned) through a Hermes plugin.

The product truth is `PRD.md` v1.2.5. The layer model is
`devdocs/MICHAELA_SYSTEM_MODEL.md`. The pack-integration spec is
`devdocs/CAPABILITY_PACK_INTEGRATION.md`.

## What this repo owns

- **Shared tools** under `api/skills/<name>/` — `parse_pdf`,
  `extract_requirements`, `score_fit` (with the §11.1 deterministic
  reject short-circuit), `detect_risks`, `generate_action_package`,
  `search_sam`, `fetch_attachment`, `parse_goal`,
  `rank_opportunities`, `load_seeded_opportunities`.
- **HTTP CRUD API** under `api/routes/` — health, profiles, company
  profiles, agent runs, opportunities, internal analysis writebacks,
  action packages, waitlist.
- **Data layer** — Supabase via `supabase-py` AsyncClient (PostgREST).
  Schema lives as versioned SQL under `supabase/migrations/`.
- **Auth** — `AuthenticatedUser` (Supabase JWT) for user routes;
  `InternalActor` (X-Internal-API-Key) for sub-agent writebacks.
- **`/web`** — Next 15 product UI behind Supabase Auth.
- **`/landing`** — public marketing site.
- **Tool-procedure SKILL.mds** under `.hermes/skills/govcapture/` — the
  five procedures an agent should consult when it calls our tools.

## What this repo does NOT own

- The orchestrator (Michaela) and the worker bench — those live in
  `/root/michealaai`.
- The work-loop, agent pool, task queue, open-loop store — also
  `/root/michealaai`.
- The per-opportunity orchestration recipe — `/root/michealaai`.
- A runtime that boots an LLM agent from `POST /agent-runs`. The HTTP
  route now only persists the run row; the orchestrator picks it up.

## Local setup

```bash
npm install
uv sync
cp .env.example .env
```

Fill `.env` with Supabase project values, `INTERNAL_API_KEY`, and any
optional `SAM_API_KEY` / `ANTHROPIC_API_KEY` for the path you're
testing.

Run the landing page:

```bash
npm run dev
```

Run the authenticated product shell:

```bash
npm run dev:web
```

Run the API:

```bash
uv run uvicorn api.main:app --reload
```

## Environment variables

Server-only:

- `ANTHROPIC_API_KEY`
- `SAM_API_KEY` (optional; empty falls back to seeded fixtures)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `REDIS_URL`
- `INTERNAL_API_KEY`
- `CORS_ALLOWED_ORIGINS`
- `LLM_DEV_MODEL`, `LLM_SYNTH_MODEL`
- `RUN_BUDGET_USD`, `RUN_BUDGET_STEPS`, `RUN_BUDGET_SECONDS`

Browser-safe:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_BASE`

`DATABASE_URL`, `OPENAI_*`, Alembic env vars, `HERMES_HOME`,
`HERMES_MODEL`, `DEMO_USE_SEEDED_ONLY`, and `DEMO_REPLAY_TRACE` are
intentionally not part of the current API runtime contract.
Seeded/demo routing and Hermes runtime configuration belong to the
external orchestrator.

## Validation

```bash
npm run lint
npm run typecheck
npm run build
npm run typecheck:web
npm run build:web
npm -w web run lint
uv run ruff check api
uv run mypy api
uv run pytest -q api/tests
make fixtures-validate
```

Schema changes are applied through Supabase:

```bash
supabase link --project-ref <project-ref>
supabase db push
```

## Deployment

Vercel hosts `/landing/` and `/web/`. Vultr VX1 hosts FastAPI, Redis,
and nginx natively. Supabase hosts Postgres, Auth, and Storage. See
`infra/RUNBOOK.md`. The orchestrator runs separately in
`/root/michealaai`.
