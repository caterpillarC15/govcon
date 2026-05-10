# Hermes Integration Notes

`HERMES.md` at the repo root is the live project context loaded by Hermes. This
file is the developer-facing checklist for keeping the tracked app honest.

Layer boundary: Michaela is the product/workloop, Hermes is the runtime
shell/tool harness, and Anthropic/OpenRouter are model transports only.

## Current Bench

GovCapture uses the Michaela system:

| Agent | Owns |
|---|---|
| Michaela | CEO/orchestrator, whole-board priority, final user answer |
| Scot | SAM.gov discovery and bulk opportunity filtering |
| Lenny | Fit ranking and pursue/monitor/skip support |
| Gabby | Eligibility blockers, compliance gates, hard-no decisions |
| Lance | Incumbents, USASpending, award history, win difficulty |
| Happer | Repeatable execution, fetch/parse/status/file jobs |
| Roy | Bid memo, capability statement, CO email, user-ready package |

The bench procedures live in `.hermes/skills/govcapture/*/SKILL.md`.

## Implementation Truth

Implemented:

- Hermes CLI is installed on the development machine.
- `.hermes/config.yaml`, `.hermes/SOUL.md`, and the GovCapture SKILL.md
  procedures define the seven-agent bench.
- FastAPI has deterministic domain skills under `api/skills/`.
- Internal writeback routes require `X-Internal-API-Key`.
- `api/agent/hermes_runner.py` starts the current seeded Michaela run path.
- `api/agent/hermes_bridge.py` emits CONTRACTS.md §3 events and persists seeded
  opportunity, fit, risk, and action-package rows.
- Project-isolated Hermes should run with `HERMES_HOME=<repo>/.hermes` and
  direct Anthropic credentials via `ANTHROPIC_API_KEY`. Do not depend on a
  personal/global `~/.hermes/config.yaml`.

Not implemented in tracked code:

- Live Hermes CLI/sub-agent execution through Michaela.
- Live SAM discovery inside `/agent-runs`.

`api/agent/replay.py` is a trace replay fallback only. Keep
`DEMO_REPLAY_TRACE=false` unless intentionally running a local demo replay, and
do not describe replay output as a real Hermes run.

## Live Bridge Contract

The current seeded bridge satisfies the API/SSE/persistence contract. The live
Hermes bridge still must:

- Start Michaela as the root agent for a user-owned `agent_runs` row.
- Pass only the signed-in user's run/profile context to the runner.
- Send specialist writebacks through the internal API key path, not a user JWT.
- Emit CONTRACTS.md §3 SSE events through the Redis channel
  `agent-run:{run_id}`.
- Preserve Gabby's §11.1 hard eligibility short-circuit.
- Persist trace/run state without trusting client-provided user IDs.
