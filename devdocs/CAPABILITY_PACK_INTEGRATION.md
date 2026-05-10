# GovCon Capability Pack Integration

Status: current as of 2026-05-09.

This repo is the GovCon Bid Desk capability pack. It exposes tools,
schemas, storage, and HTTP routes that Michaela can call. It is not the
Michaela workloop runtime.

## Layer Boundary

| Layer | Owner | Repo |
|---|---|---|
| Michaela workloop, task queue, open-loop store, agent pool | Michaela project | `/root/michealaai` |
| Hermes runtime shell, tool calling, provider config, isolated home | Runtime infrastructure | project-specific `HERMES_HOME` |
| GovCon deterministic tools, schemas, persistence, API, direct-user UI | This capability pack | this repo |
| Model provider transport | Anthropic direct by default; routing optional later | environment/config |

Michaela owns orchestration. The named workers own judgment. This pack owns
mechanics and contracts.

## Current Integration Surface

### HTTP API

Michaela or a service process may call FastAPI routes directly.

- Public: `GET /healthz`, `POST /waitlist`
- User JWT: profiles, company profiles, agent-run reads, run outputs
- Internal service key: requirements, fit scores, risks, action packages,
  and `POST /tools/<name>` skill wrappers

Internal writebacks and tool calls must include:

```http
X-Internal-API-Key: <INTERNAL_API_KEY>
```

Browser user tokens cannot write generated analysis artifacts.

#### `POST /tools/<name>` — direct skill dispatch (live 2026-05-09)

Any caller that doesn't run Hermes (TypeScript shim from `/root/michealaai`,
Codex, Cursor, curl) can drive the pack's skills through ten POST endpoints
under `/tools/<name>`. Each route requires `X-Internal-API-Key` and accepts a
typed JSON body matching the schema in `api/schemas/tool_requests.py`.

Responses share the uniform envelope:

```json
{ "data": <skill output>, "metrics": <LLMMetrics | null> }
```

`metrics` is null for non-LLM skills (parse_pdf, rank_opportunities,
search_sam, fetch_attachment, load_seeded_opportunities) and populated with
token counts and cost for LLM-backed skills (parse_goal,
extract_requirements, score_fit, detect_risks, generate_action_package).
The full table of routes lives in `tasks/CONTRACTS.md` §6.

This is parity with — not a replacement for — the planned Hermes plugin
(Sprint A). The plugin gives Michaela's Hermes-hosted workers native tool
calls with lower latency; this HTTP surface gives every other caller a
zero-research integration path.

### Agent Run Rows

`POST /agent-runs` creates a run-request row. It does not start an in-repo
Hermes subprocess and does not execute a seeded bridge. The external
Michaela orchestrator is expected to pick up the request, call pack tools,
write artifacts, update the `agent_runs` row, and publish trace events if
real-time UI updates are desired.

`GET /agent-runs/{id}/stream` is only an SSE forwarder over Redis channel
`agent-run:{id}`. It emits what another process publishes. It is not itself
a runner.

### Python Skills

Domain mechanics live under `api/skills/<name>/`:

- `parse_goal`
- `search_sam`
- `load_seeded_opportunities`
- `rank_opportunities`
- `fetch_attachment`
- `parse_pdf`
- `extract_requirements`
- `score_fit`
- `detect_risks`
- `generate_action_package`

These functions are provider-agnostic except where an LLM call is explicit.
Inputs and outputs must stay aligned with `schemas/*.json` and
`api/schemas/*.py`.

### Hermes Skill Procedures

`.hermes/skills/govcapture/*/SKILL.md` files describe how an agent should
use the pack's tools. They are local procedure docs, not the canonical
agent registry. The worker bench definitions live with Michaela.

## Data Boundary

Raw files do not belong in Postgres.

- Supabase Storage: PDFs, fixture attachments, parsed-file artifacts
- Supabase Postgres: metadata, parsed chunks, analyses, matches, run rows
- Future long-term memory: Michaela/GBrain layer outside this repo

## Model Provider Boundary

The clean project-isolated default is direct Anthropic:

```bash
ANTHROPIC_API_KEY=...
```

OpenRouter is a future model-routing option, not the project architecture.
If Hermes can chat but FastAPI skills fail with provider auth errors, treat
that as an environment split: different processes are reading different
credential sources.

## Integration Checklist

- `INTERNAL_API_KEY` is set in Michaela and FastAPI.
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and browser anon keys are set
  for the environments that need them.
- Michaela never trusts client-provided user IDs; it passes authenticated
  user context or internal service credentials according to route class.
- Generated artifacts are written through internal routes or service-role
  repositories with ownership fields populated.
- Real-time UI traces are published to Redis channel `agent-run:{run_id}` in
  the `TraceEvent` shape documented in `tasks/CONTRACTS.md`.
- Seeded fixtures are used by explicitly calling `load_seeded_opportunities`;
  there is no in-repo seeded run bridge.
