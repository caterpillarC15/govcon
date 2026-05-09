# Dev 1 Runbook

Common commands, debugging patterns, and pitfalls. Open this when something breaks.

---

## Status snapshot (2026-05-09)

A1 → P0.2 → A2 → A3 → A4 → A5 complete. `uv run pytest api/tests` → 71 passed, 2 skipped (Dev 2's seed PDFs). S2 trigger ready; pre-A9 SSE replayer at `api/agent/replay.py` produces real events for Dev 2's timeline. See `tasks/dev1-backend/STANDUP.md` for the day-of detail.

`.env` is **not yet populated**; tests use inline env vars (`ANTHROPIC_API_KEY=sk-ant-test ...`) and a `FakeLLM` stub so no Anthropic budget is consumed for CI. Live LLM smoke is deferred until you drop a real key into `.env`.

**Postgres version:** Currently running on Postgres 17 locally. The Makefile pins `postgresql@16` in `services-up`/`services-down` per the original spec — adjust those lines if your machine has only 17 (works fine for our schema; same major-version family).

---

## Common commands

### Local dev

```bash
# Start native Postgres + Redis (idempotent; uses brew on macOS, systemctl on Linux).
# One-time only after a reboot; they keep running in the background.
make services-up

# Run the FastAPI app with --reload (foreground; logs go to this terminal)
make dev

# Stop services when you're done for the day (optional)
make services-down

# Migrations (Alembic config lives in /api/alembic.ini; the Makefile cd's there)
make migrate              # apply all migrations
make migrate-down         # roll back one
make migration MSG="describe change"  # autogenerate a new revision

# Run the test suite (full / one file / one test)
make test                                                # full
uv run pytest api/tests/test_extract_requirements.py -v  # one file
uv run pytest api/tests/test_routes.py::test_sse_replays_first_event -v

# Type-check / lint / format
make typecheck
make lint
make format

# Regenerate Pydantic models from /schemas/*.json (run after any schema edit).
# Strips the `_schema` suffix so `from api.schemas.agent_run import AgentRun` works.
# TS codegen for /web is a no-op until /web exists (Dev 2 wires when ready).
make schemas

# Run the eval harness — A12 lands later; targets are stubs until then.
make eval                              # all 4 fixtures
make eval-fixture FIXTURE=strong-pursue
```

### Pre-A9 SSE smoke (verifies A3 end-to-end)

```bash
# Boot the API, then:
PROFILE_ID=$(curl -fsS -X POST localhost:8000/company-profiles \
  -H 'content-type: application/json' \
  -d '{"name":"Smoke Co","capabilities":["cyber"]}' \
  | uv run python -c "import sys,json; print(json.load(sys.stdin)['id'])")

RUN_ID=$(curl -fsS -X POST localhost:8000/agent-runs \
  -H 'content-type: application/json' \
  -d "{\"goal\":\"smoke\",\"profile_id\":\"$PROFILE_ID\"}" \
  | uv run python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# First few events (replayed from /schemas/trace-event.example.jsonl with run_id rewritten):
curl -N -sS --max-time 3 localhost:8000/agent-runs/$RUN_ID/stream | head -12
```

### Live LLM smoke (run once `.env` has a real `ANTHROPIC_API_KEY`)

```bash
# Synthesize a tiny PDF, then call extract_requirements end-to-end with Haiku.
uv run python -c "
import asyncio
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from api.skills.parse_pdf import parse_pdf, ParsePdfInput
from api.skills.extract_requirements import extract_requirements, ExtractInput

c = canvas.Canvas('/tmp/sm.pdf', pagesize=LETTER)
c.drawString(72, 720, 'Personnel must hold a Secret clearance prior to award.')
c.drawString(72, 700, 'Bid bond required: 5% of total bid amount.')
c.drawString(72, 680, 'Set-aside: Total Small Business.')
c.showPage(); c.save()

async def go():
    parsed = parse_pdf(ParsePdfInput(path='/tmp/sm.pdf'))
    out, m = await extract_requirements(ExtractInput(parsed=parsed, opportunity_metadata={'title':'smoke'}))
    print(f'reqs={len(out.requirements)} cost=${m.cost_usd:.4f} latency={m.latency_ms}ms cache_read={m.cache_read_tokens}')
    for r in out.requirements:
        print(f'  [{r.confidence:7s}] {r.type:14s} {r.title}')

asyncio.run(go())
"
```

### Hitting endpoints manually

```bash
# Health check
curl -fsS localhost:8000/healthz

# Create a profile
curl -X POST localhost:8000/company-profiles \
  -H 'content-type: application/json' \
  -d @fixtures/_demo-company/profile.json

# Start an agent run
curl -X POST localhost:8000/agent-runs \
  -H 'content-type: application/json' \
  -d '{"profile_id": "<uuid>", "goal": "cybersecurity opportunities in 60 days"}'

# Watch SSE stream
curl -N localhost:8000/agent-runs/<run-id>/stream
```

### Postgres + Redis

```bash
# Connect to local Postgres
psql -U govcon -d govcon

# Inspect agent run trace
psql -U govcon -d govcon -c \
  "select id, status, jsonb_array_length(steps) as step_count from agent_runs order by created_at desc limit 5;"

# Watch Redis pub/sub for trace events (debugging A9 / B5 SSE)
redis-cli psubscribe 'agent-run:*'
```

### LLM tracing

```bash
# Tail logs for an agent run — `make dev` is foreground; logs go to its terminal.
# Capture them to a file by redirecting if you need to grep:
#   make dev 2>&1 | tee /tmp/govcon-api.log

# Total cost for a run
psql -U govcon -d govcon -c \
  "select id, sum((step->>'cost_usd')::float) from agent_runs, jsonb_array_elements(steps) step group by id order by 2 desc limit 5;"
```

### VX1 (after A13)

```bash
# SSH in
ssh root@<vx1-ip>

# Tail prod logs (FastAPI runs under govcon-api.service)
journalctl -u govcon-api -f

# Service status
systemctl status govcon-api postgresql redis-server nginx

# Redeploy (pulls, runs migrations, restarts the service)
sudo bash /opt/govcon/infra/redeploy.sh

# Backup right now
sudo /opt/govcon/infra/backup.sh
```

---

## Debugging patterns

### LLM returns invalid JSON

1. Check the actual raw output in the API logs (the wrapper logs the raw model response on validation failure).
2. Look at the prompt: does it explicitly include the schema? Are there examples?
3. Try with `LLM_SYNTH_MODEL` (Sonnet) — Haiku struggles with complex schemas; Sonnet is more reliable.
4. If the model is omitting required fields, add a one-shot example in the prompt.
5. The wrapper retries once with a stricter "you returned invalid JSON, here is the schema again" reminder. If it still fails, the step is marked `failed` and the run continues with degraded output.

### `parse_pdf` returns empty chunks

- Run `pypdf` directly on the PDF: `python -c "import pypdf; r = pypdf.PdfReader('path.pdf'); print(r.pages[0].extract_text())"`.
- Empty? It's image-only. Mark `unparseable: true` and continue (PRD §17 Q2: no OCR in MVP).
- Some text? Check chunking: pages with weird layout may produce noise. Chunk by page, not by character count, for the first pass.

### `extract_requirements` confidence is mostly low/unknown

This is the trigger for the planner's confidence-gating recovery (PRD §4.5). In the tool itself, just return what you have. The planner re-chunks smaller and reruns. If still bad, the planner emits `needs_human`.

### `score_fit` returns wrong decision band

Almost always a §11.1 issue. Check:

1. Is the eligibility short-circuit running before the rubric math? Print eligibility status.
2. Are critical blockers from `extract_requirements` (with `is_blocker: true`) being honored?
3. Does the LLM rationale agree with the math? If not, the math is the source of truth — ignore the LLM rationale on the decision.

### Planner exceeds step budget

Look at the trace. Common causes:

- Re-running `extract_requirements` repeatedly because confidence stays low → confidence gating is too aggressive. Loosen the threshold or accept degraded output sooner.
- Searching for opportunities then re-searching with refined criteria → constrain to one search per run; refine via filtering, not re-querying.
- Tool dispatch loops — planner re-calls the same tool with the same input. Add a "you already called this tool with this input on step N" hint to the planner state.

### Planner's rationale is incoherent

The planner prompt isn't giving it enough state. Make sure each turn includes:

- Steps so far (compact summary, not full I/O)
- Remaining budget
- Which tools have already been called for this opportunity
- The original goal

### Hermes runtime issues during dev

Check that Hermes is installed and the model is configured: `hermes model` shows the active provider/model. The Hermes subprocess from the FastAPI bridge logs to stderr — in dev that's the `make dev` terminal; in prod it's `journalctl -u govcon-api -f | grep hermes`.

Common Hermes issues:
- **Subprocess deadlock** — pipe buffer full. Use unbuffered IO and read stdout in a separate task.
- **Skill not found** — Hermes hasn't picked up newly added `/api/skills/<name>/skill.md`. Restart Hermes (or the api container).
- **Model API rate limit** — Hermes surfaces the upstream provider's 429. Backoff inside the LLM-backed skills, not in Hermes.
- **Memory drift between sessions** — Hermes' long-term memory persists across runs. Wipe with `hermes memory clear` if testing reproducibility.

### SSE stream drops events

- Confirm the API is using `text/event-stream` content type.
- Confirm each event is `event: <type>\ndata: <json-line>\n\n` (note the double newline at the end).
- If using a proxy (nginx in prod), ensure `proxy_buffering off` and `proxy_read_timeout 300s` for the stream endpoint.

---

## Pitfalls (things that have killed past hackathon teams)

| Pitfall | Prevention |
|---------|------------|
| Editing generated `/api/schemas/*.py` by hand | `make schemas` only. Add a CI/pre-commit check that the generated files match the source. |
| Reading env in random files | Centralized in `/api/config.py`. Add a pre-commit hook that flags `os.getenv` outside that file if you have time. |
| LLM cost runaway during prompt iteration | Default to Haiku. Tag tests that need Sonnet. Watch the cost dashboard. |
| Forgetting §11.1 in score_fit | Two enforcement points: A6 deterministic check AND A12 eval assertion. Add a unit test asserting capability=high + decision=reject for the reject fixture. |
| Postgres race conditions on concurrent agent runs | Use SERIALIZABLE only where needed; default to READ COMMITTED. Each agent run writes its own steps; no shared state to conflict on. |
| Forgetting to migrate before running tests | `make migrate` is part of `make dev`. Add `make test` that depends on `migrate`. |
| Hermes runtime flakiness blocking demo | Demo defaults to seeded path (`DEMO_USE_SEEDED_ONLY=true`); pre-cached run in `/web/public/demo/` is the ultimate fallback. |
| Backup script never tested until disaster | Test restore as part of A13. `pg_restore` from yesterday's dump into a clean DB. |

---

## When to ask Dev 2

- Schema you want to change → ping before the PR.
- Fixture seems broken → confirm with B before assuming the parser is wrong.
- Trace event shape needs a new field → that's a schema change, joint decision.
- A change to `Makefile` that affects B's `make schemas` flow → ping.
- About to break something on `main` → just push, but post in standup so B knows.
