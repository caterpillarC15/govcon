# GovCon Capability Pack Integration

Status: current as of 2026-05-10.

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
Codex, Cursor, curl) can drive the pack's skills through eleven POST
endpoints under `/tools/<name>` (mirrored at `/api/v1/tools/<name>` for
per-agent gck_ bearer tokens). Each route requires `X-Internal-API-Key`
(or a valid `gck_…` bearer on the public mirror) and accepts a typed JSON
body matching the schema in `api/schemas/tool_requests.py`.

Responses share the uniform envelope:

```json
{ "data": <skill output> }
```

**PRD v1.2.6 contract change.** Every skill is deterministic; the
envelope no longer carries a `metrics` field. Cross-repo callers that
previously read `response.metrics` (token counts, cost, latency) must
stop — those measurements move to the orchestrator side, where the
LLM calls now actually happen. The full table of routes lives in
`tasks/CONTRACTS.md` §6.

This is parity with — not a replacement for — the planned Hermes plugin
(Sprint A). The plugin gives Michaela's Hermes-hosted workers native tool
calls with lower latency; this HTTP surface gives every other caller a
zero-research integration path.

### Agent Run Rows

`POST /agent-runs` creates a run-request row. It does not start an in-repo
Hermes subprocess and does not execute a seeded bridge. The external
Michaela orchestrator picks the row up out of band, drives the work, writes
artifacts via the internal routes, and updates the row. `GET
/agent-runs/{id}/stream` is only an SSE forwarder over Redis channel
`agent-run:{id}`; it emits what another process publishes.

#### Pickup contract (Sprint G — v1, no schema change)

The contract uses only the existing `agent_runs` columns (see
`supabase/migrations/20260509132830_create_govcon_core.sql:238`). No new
migration is required for v1; future revisions may add `started_at`,
`worker_id`, and `error` if richer debuggability is needed.

**Discovery.** The orchestrator polls Supabase periodically for unclaimed
rows. Recommended initial cadence: every 2–5 seconds. Switch to Postgres
`LISTEN/NOTIFY` later if poll cost becomes material.

```sql
SELECT id, goal, company_profile_id, created_at
FROM agent_runs
WHERE status = 'pending'
ORDER BY created_at ASC
LIMIT 8;
```

**Claim (atomic, no double-pickup).** A row transitions out of `pending`
exactly once via an optimistic update. If the update affects 0 rows, another
worker won the race; skip and re-poll.

```sql
UPDATE agent_runs
SET status = 'running'
WHERE id = $1 AND status = 'pending'
RETURNING *;
```

The `idx_agent_runs_status` index makes the predicate scan cheap.

**Progress + final write.** Steps accumulate into `agent_runs.steps` (jsonb
array; orchestrator's choice of shape, but the `TraceEvent` taxonomy in
`tasks/CONTRACTS.md §3` is the canonical envelope and SHOULD be the
serialized form). On completion the orchestrator sets the terminal columns
in a single update:

```sql
UPDATE agent_runs
SET status = 'complete',         -- or 'partial' or 'failed'
    completed_at = now(),
    selected_opportunity_id = $1, -- optional
    action_package_id = $2,       -- optional
    opportunities = $3            -- optional matched-opp UUIDs
WHERE id = $4;
```

**Status state machine (no backward transitions):**

```
pending ──claim──▶ running ──complete──▶ complete
                       │
                       ├──partial──▶ partial   (some artifacts produced; degraded)
                       │
                       └──fail────▶ failed    (caller-visible error)
```

The pack's API treats any status other than `pending` as "claimed"; it
will not reanimate a row.

**Idempotency on the writeback side.** All `POST /opportunities/{id}/...`
and `POST /action-packages` routes are idempotent on natural keys:
opportunity by `slug`, others by `(opportunity_id, owner_profile_id)`. A
worker that retries after a transient failure will not duplicate.

**Trace events (live UI updates).** The orchestrator publishes
`TraceEvent` JSON to Redis channel `agent-run:{run_id}` as each step
proceeds. The pack's `GET /agent-runs/{id}/stream` route is a pure SSE
forwarder; it does not interpret events. Event taxonomy is locked in
`tasks/CONTRACTS.md §3` and MUST NOT drift between this repo and
`/root/michealaai` — schema change requires ack on both sides.

**Crash recovery (orchestrator-side).** If a worker crashes mid-run, the
row remains in `running` indefinitely. The orchestrator's recovery loop
SHOULD scan `WHERE status = 'running' AND started_at < now() - interval
'30 minutes'` (or equivalent heuristic on `created_at` if `started_at` is
not yet a column) and either resume or mark `failed`. Recovery policy is
the orchestrator's call; the pack does no GC.

### Trace event format (locked across repos)

`tasks/CONTRACTS.md §3` is the **single source of truth** for trace event
shapes. Both this repo and `/root/michealaai` consume it. Adding or
changing an event type is a coordinated change:

1. Author edits `tasks/CONTRACTS.md §3` in this repo.
2. Author opens a PR; the orchestrator-side maintainer acks within ~30 min
   that `/root/michealaai` will be updated to emit/consume the new shape.
3. Both sides land their respective changes; this repo's `/agent-runs/{id}/stream`
   forwarder is intentionally event-type-agnostic, so no code change is
   usually needed here unless a frontend renderer in `/web` needs the new
   event type.

If `/root/michealaai` emits an event type not in §3, the SSE forwarder
will pass it through unchanged (the route does not validate). The frontend
renderer should treat unknown types as opaque "trace step" rows rather
than dropping them.

### Python Skills (deterministic — PRD v1.2.6)

Domain mechanics live under `api/skills/<name>/`. Per the operating
rule (`devdocs/MICHAELA_SYSTEM_MODEL.md` line 175), this repo holds
mechanics only; Michaela's bench in `/root/michealaai` does the
LLM judgment and passes its results back to these skills as input
for shape validation.

| Skill | Caller worker | Skill role |
|---|---|---|
| `parse_goal` | Michaela | input pass-through validator |
| `search_sam` | Scot | SAM.gov v2 query |
| `load_seeded_opportunities` | Scot | fixture loader |
| `rank_opportunities` | Lenny | deterministic decision-band sort |
| `fetch_attachment` | Happer | URL → Supabase Storage |
| `parse_pdf` | Happer | pypdf chunking + page metadata |
| `extract_requirements` | Gate | chunks emitter + §11 evidence-binding validator |
| `score_fit` | Lenny + Gate | §11.1 short-circuit + decision-band normalizer |
| `detect_risks` | Gate | §5.8 taxonomy + cap-at-8 + critical-blocker carry-forward |
| `generate_action_package` | Roy | reject_summary mode + §5.13 enforcer |
| `query_usaspending` | Ledger | USASpending HTTP query → `competitor_history` |

No skill calls an LLM. `ANTHROPIC_API_KEY`, `LLM_DEV_MODEL`,
`LLM_SYNTH_MODEL`, `RUN_BUDGET_*` env vars were dropped at v1.2.6 —
those concerns live in `/root/michealaai`'s environment now.

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

### Three Supabase projects (do not conflate)

Discovered 2026-05-10 by walking Michaela's host. Three distinct
Supabase instances are in play; the orchestrator's data fan-out
needs to talk to two of them, the pack to one.

| Project ref | Owner | This repo's relationship |
|---|---|---|
| **`vvyxjdoenjujkxwbnzyl`** | **This pack + persona/public-presence** (shared) | Canonical home for our 10 migrations. Michaela's `agent_runs` pickup loop polls here. `INTERNAL_API_KEY` writebacks land here. Bucket `govcapture-attachments` is ours (private); bucket `persona-assets` is the persona project's (public). |
| `ktygrvbpugqhfyibzirr` | Michaela's competitive-intel warehouse | Holds `agencies`, `contractors`, `contracts`, `psc_win_patterns`, `customer_profiles`. Lance reads it for incumbent + award lookups. **Not** referenced by any code in this repo. Our `query_usaspending` skill calls the public USAspending API — different path. |
| `pooler.supabase.com` (GBrain) | `/root/gbrain` | Knowledge-base pgvector store. Wholly unrelated; mentioned only because someone wiring Michaela might trip over the third project. |

**Action item for `/root/michealaai`:** the `DATA-SOURCES.md` file in
that repo describes "GovCon Supabase" as `ktygrvbpugqhfyibzirr` — that's
correct for Lance's intel reads, but the **`agent_runs` pickup contract
documented in this file lives on `vvyxjdoenjujkxwbnzyl`**, not on
`ktygrvbpugqhfyibzirr`. Add an explicit second-row entry on the
michealaai side so the orchestrator polls the right project. Without
this, Michaela watching `ktygrvbpugqhfyibzirr.agent_runs` would never
see the rows our `POST /agent-runs` writes.

**Cohabitation note for the pack side:** the same project also hosts
the persona/public-presence schema (`personas`, `persona_profiles`,
`persona_assets`, …) and a public storage bucket `persona-assets`.

**Verified clean 2026-05-10:**

- `govcapture-attachments` bucket — Public OFF (private). Confirmed in Studio.
- `persona-assets` bucket — Public ON (intentional, persona's bucket).
- Table-name collision check: no overlap between our migrations and persona's schema. The `agent_runs` reference in the persona skill's documented table list was aspirational / never materialized as a separate table.

Re-verify if Studio is touched by anyone unfamiliar with both halves.

## Model Provider Boundary

**This repo no longer holds an LLM credential** (PRD v1.2.6). All
LLM calls happen in `/root/michealaai` against whatever provider
Michaela's environment is configured for (Anthropic direct, OpenRouter,
etc.). Cross-repo concern: the orchestrator side owns model selection,
budget tracking, and provider auth.

If a developer wants to run Hermes against this pack's tools for
isolated testing (`HERMES_HOME=$(pwd)/.hermes hermes`), the credential
goes in their per-user `~/.hermes/auth.json` or in `HERMES_HOME/.env`,
not in this repo's `.env`.

## INTERNAL_API_KEY provisioning

`INTERNAL_API_KEY` is the single shared secret that authorizes all
sub-agent writebacks (the existing `POST /opportunities/{id}/...` and
`POST /action-packages` routes) and all `POST /tools/<name>` skill
dispatches. It MUST be identical in both repos' runtime environments.

**Generate.** Once per environment (dev / staging / prod):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Treat the output as a long-lived secret; no expiry, rotated only on suspected
compromise.

**Distribute.**

| Where it lives | How it's set |
|---|---|
| This repo, dev | `.env` (gitignored), key `INTERNAL_API_KEY=…` |
| This repo, prod (VX1) | systemd unit `Environment=` directive in `infra/systemd/govcapture-api.service` |
| `/root/michealaai`, dev | the orchestrator's `.env` (gitignored), under whatever name the TS env loader expects (likely `INTERNAL_API_KEY`); MUST be the same string |
| `/root/michealaai`, prod | same systemd / process manager mechanism on its host, same string |

**Mirror, don't fork.** There is no key exchange or per-worker key. Both
sides hold the same string. If you find yourself wanting per-worker keys
for audit trails, that's a Sprint G+ enhancement (add a `worker_id` claim
on the route + a per-worker secret table) — out of scope here.

**Rotation.**

1. Generate the new secret.
2. Add it as `INTERNAL_API_KEY_NEXT` on both sides (dual-key window).
3. Update the pack's `require_internal_actor` to accept either current or
   next during the window — *not yet implemented; current code is single-key*.
4. Roll the orchestrator's outgoing key from current → next.
5. Remove the old key from both sides.

For v1, simpler: schedule a brief outage, swap on both sides simultaneously.

## Integration Checklist

- `INTERNAL_API_KEY` is set identically in this repo and `/root/michealaai`
  (per the §INTERNAL_API_KEY provisioning section above).
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and browser anon keys are set
  for the environments that need them.
- Michaela never trusts client-provided user IDs; it passes authenticated
  user context or internal service credentials according to route class.
- Generated artifacts are written through internal routes or service-role
  repositories with ownership fields populated.
- Real-time UI traces are published to Redis channel `agent-run:{run_id}` in
  the `TraceEvent` shape documented in `tasks/CONTRACTS.md §3`.
- Seeded fixtures are used by explicitly calling `load_seeded_opportunities`;
  there is no in-repo seeded run bridge.

## Known unknowns — owed by `/root/michealaai`

Sprint G locks the contract from this repo's side. The following are
verification gates that require work in `/root/michealaai` before the
end-to-end flow is provably live:

| Item | Status (this repo) | Status (orchestrator) | Verification gate |
|---|---|---|---|
| `agent_runs` poll loop | N/A | unknown | A `pending` row inserted via `POST /agent-runs` is claimed (`status='running'`) within N seconds |
| Optimistic-claim race-safety | N/A | unknown | Two simultaneous claim attempts on the same row produce exactly one winner |
| `TraceEvent` emission to Redis `agent-run:{run_id}` | SSE forwarder live | unknown | A real run produces `run_started` + ≥1 `tool_*` + `run_completed` events on the channel |
| Calls to `POST /tools/<name>` with `INTERNAL_API_KEY` | 11 routes live, tested | unknown | An e2e run produces an `action_packages` row owned by the original requester |
| Crash recovery for stale `running` rows | not enforced (no GC) | unknown | A killed worker's row is reaped or completed via the orchestrator's recovery loop |

**Sprint G is "spec-done" when this section is filled in.** It is
"verification-done" when the rightmost column is green for every row, which
requires the orchestrator-side work in `/root/michealaai`.
