# Michaela System Model

This document separates three layers that are easy to conflate:

1. **Michaela** is the product and workloop architecture.
2. **Hermes** is the runtime shell/tool harness around that architecture.
3. **Anthropic/OpenRouter** are model transport options used only when an
   agent needs LLM tokens.

GovCapture is the current GovCon capability pack running on the Michaela
system. The product logic is provider-agnostic; changing a model route should
not change how tasks are captured, assigned, stored, or surfaced.

## Repo Boundary

This GovCapture repo is the GovCon capability/application surface: FastAPI,
Supabase schema, seeded skills, landing, `/web`, and Hermes-facing project
context.

The Michaela core workloop lives separately from this repo. Expected core repo
shape:

```txt
/root/michealaai
package: michealaai
runtime/tests: bun test tests/*.test.ts
workloop test: bun test tests/workloop.test.ts
core files:
  src/workloop/types.ts
  src/workloop/agentPool.ts
  src/workloop/defaultAgents.ts
  src/workloop/taskQueue.ts
  src/workloop/openLoopStore.ts
  src/workloop/surfacing.ts
  src/workloop/workLoop.ts
docs:
  docs/WORKLOOP.md
  agent-bootstrap/README.md
  agent-bootstrap/DIRECTIVES.md
  agent-bootstrap/TOOLS.md
```

Do not judge the Michaela architecture by whether this GovCapture repo has a
TypeScript workloop directory. This repo consumes/implements the GovCon mission
surface and should remain compatible with the core workloop model.

## Core Pattern

Michaela is an operating agent, not a chatbot:

```
conversation
-> capture useful observation / open loop
-> queue a microtask
-> assign by capability
-> worker returns proof, gap, or result
-> Michaela resurfaces only when useful
```

For GovCon, a user mentioning that they sell security assessments can become an
open loop. Scot or Lenny can later look for matching federal opportunities, and
Michaela resurfaces a compact result:

```
Found: 1 relevant notice
Proof: SAM notice ID
Gap: past performance requirement unclear
Next: confirm eligibility
```

## Current Bench

Michaela owns the board and the final user-facing answer. The named workers are
specialists, not managers:

| Agent | Owns |
|-------|------|
| Michaela | Orchestration, priorities, final user-facing answer |
| Scot | SAM discovery and top-of-funnel scanning |
| Lenny | Fit ranking and profile matching |
| Lance | Incumbents, awards, and competitive intelligence |
| Gabby | Eligibility and compliance blockers |
| Happer | Execution, browser/files, repeat jobs, overflow work |
| Roy | Packaging, emails, handoff artifacts |

Correct:

```
Michaela -> Scot -> artifact
Michaela -> Lenny -> artifact
Michaela -> Roy -> user package
```

Wrong:

```
Michaela -> manager -> sub-manager -> worker -> status updater
```

## Runtime Boundary

Hermes gives the project a CLI/chat runtime, skills, tools, memory, provider
configuration, subagents, cron/profile support, and isolated homes. Hermes is
not the product itself. Michaela uses Hermes as infrastructure.

Clean mental model:

```
Michaela project = application logic / agent workloop
Hermes = runtime / container / tool harness
Anthropic or OpenRouter = model transport
FastAPI skills = service processes with their own environment
```

If Hermes has a model key but FastAPI does not, Hermes can chat while project
skills fail with auth errors. That is a credential-source split, not proof that
the architecture is OpenRouter.

## Provider Guidance

Use **direct Anthropic** for the project-isolated Hermes environment unless
there is a specific model-routing reason to use OpenRouter.

Reasons:

- fewer moving parts
- clearer auth path
- easier 401 debugging
- FastAPI skills and Hermes workers can share `ANTHROPIC_API_KEY`
- no confusion between OpenRouter and Anthropic credentials

Project config must reference environment variables and must not contain
literal secrets:

```yaml
providers:
  anthropic:
    api_key: null
    api_key_env: ANTHROPIC_API_KEY
```

Global personal Hermes can keep separate provider settings. Project Hermes
should be deterministic through `HERMES_HOME=<repo>/.hermes` and a project
`.env`/isolated Hermes `.env` that both expose the same `ANTHROPIC_API_KEY`.

## Data Boundary

Raw files do not belong in the database.

Planned durable split:

- **Object storage:** PDFs, attachments, CSV snapshots.
- **Supabase:** metadata, parsed chunks, analyses, matches, run events.
- **GBrain later:** long-term compiled knowledge, memory, and retrieval.

Today this repo uses Supabase Storage for object storage. The planned R2 split
is a storage implementation change, not a change to the Michaela workloop.

## Planned Production State

The current Michaela core is an in-memory MVP:

- `TaskQueue` in memory
- `OpenLoopStore` in memory
- `TaskResult` in memory

Production persistence target:

- `TaskQueue` -> Supabase `agent_tasks`
- `OpenLoopStore` -> Supabase `open_loops`
- `TaskResult` -> analyses / `run_events`

## GovCon Rule Of Thumb

Mechanics belong in shared tools. Judgment belongs in agents. Contracts belong
in schemas. Michaela owns the board.

Example: Scot should call a shared SAM parser/downloader, then apply discovery
judgment. Scot should not hand-roll a parser every time.
