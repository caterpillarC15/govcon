# GovCapture

GovCapture is a GovCon bid-desk operator. It takes a company profile plus a
contracting goal, finds or loads opportunities, extracts source-cited
requirements, scores bid/no-bid fit, flags blockers, and produces a reviewable
action package with human approval gates.

The product truth is `PRD.md` v1.2.4. The current system model is
`devdocs/MICHAELA_SYSTEM_MODEL.md`: Michaela is the product/workloop, Hermes is
the runtime shell, and Anthropic/OpenRouter are model transport choices.
Runtime context for the project-isolated Hermes home lives in `HERMES.md` and
`.hermes/`.

## Current State

Implemented now:

- Premium one-page landing app in `landing/`, with a real `POST /waitlist`
  integration.
- FastAPI routes for health, profiles, company profiles, agent runs,
  opportunity reads, internal analysis writebacks, action packages, and waitlist
  signup.
- Supabase Auth verification for user routes in `api/auth.py`.
- Internal write protection for sub-agent/tool writebacks through
  `X-Internal-API-Key`.
- Supabase PostgREST repositories and SQL migrations under
  `supabase/migrations/`.
- `/web` Supabase magic-link auth with a protected seeded demo console for
  profile creation, Michaela run start, SSE trace viewing, opportunity results,
  and Roy action package review.
- Seeded fixture skills and tests for loading, ranking, scoring, risk detection,
  SAM search, attachment fetch, goal parsing, and action package generation.
- Michaela bench docs/config for Michaela, Scot, Lenny, Lance, Gabby, Happer,
  and Roy.
- Tracked FastAPI seeded runner/trace bridge in `api/agent/hermes_runner.py` and
  `api/agent/hermes_bridge.py`.

Not implemented yet:

- Live Hermes CLI execution through the seven-agent bench. The current bridge
  executes the seeded path truthfully and writes real run/fit/risk/package rows;
  it does not claim live SAM or LLM-backed synthesis.
- Payment. The PRD keeps payment out of MVP scope.
- Supabase Realtime. Redis remains the SSE pub/sub path.
- Production-grade profile/run UI beyond the seeded `/web` console.

## Local Setup

```bash
npm install
uv sync
cp .env.example .env
```

Fill `.env` with Supabase project values, `INTERNAL_API_KEY`, and any optional
SAM/Anthropic keys needed for the path you are testing.

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

## Environment Variables

Server-only:

- `ANTHROPIC_API_KEY`
- `SAM_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `REDIS_URL`
- `INTERNAL_API_KEY`
- `CORS_ALLOWED_ORIGINS`
- `HERMES_HOME` (project-isolated; use `.hermes` locally and
  `/opt/govcapture/.hermes` in production)
- `HERMES_MODEL`
- `LLM_DEV_MODEL`
- `LLM_SYNTH_MODEL`
- `RUN_BUDGET_USD`
- `RUN_BUDGET_STEPS`
- `RUN_BUDGET_SECONDS`
- `DEMO_USE_SEEDED_ONLY`
- `DEMO_REPLAY_TRACE`

Browser-safe:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_BASE`

`DATABASE_URL`, `OPENAI_*`, and Alembic env vars are intentionally not part of
the current architecture.

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

Vercel hosts `landing/` and `web/`. Vultr VX1 hosts FastAPI, Hermes, Redis, and
nginx natively. Supabase hosts Postgres, Auth, and Storage. See
`infra/RUNBOOK.md`.
