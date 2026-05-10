# Hermes context for the GovCon Bid Desk capability pack

> For wiring this pack into a real Hermes runtime (Michaela's host or
> any other), see **`devdocs/HERMES_LINK.md`**. This file documents only
> the dev-time `HERMES_HOME=$(pwd)/.hermes hermes` testing pattern.

This file gives a Hermes runtime project-context when a developer points
their `HERMES_HOME` at this repo's `.hermes/` to test the pack's tools in
isolation. It is **NOT** loaded by FastAPI or by any production process.

The orchestrator (Michaela) and her worker bench (Scot, Lenny, Lance,
Gabby, Happer, Roy) live in **/root/michealaai**. This repo is the
**GovCon Bid Desk capability pack**: shared tools, data layer, HTTP API,
and the direct-user product surface (`/web`).

## What you can do here

When a developer runs:

```bash
HERMES_HOME=$(pwd)/.hermes hermes
```

…they get a Hermes REPL with this project's isolated state:

- `model.provider: anthropic, default: claude-sonnet-4-6` (per `.hermes/config.yaml`)
- The five tool-usage SKILL.md procedures under `.hermes/skills/govcapture/`
- Memory storage isolated to `.hermes/memories/`

This is for testing tool calls in isolation. It is not a production
runtime.

## Hard rules (apply when an agent runs against this pack's tools)

1. **§11.1 — Eligibility conservatism.** Hard eligibility blockers
   (clearance, set-aside, citizenship, certification) deterministically
   produce `decision = reject` regardless of capability strength. The
   short-circuit lives in Python inside `score_fit`. Don't let an agent
   talk its way around it.

2. **Source-binding.** Every claim with confidence ≥ medium must carry a
   verbatim quote + page_number from the source. If you can't quote it,
   set confidence to `low` / `unknown` and leave evidence empty.

3. **No fabrication.** Don't invent CO names, dollar values, or
   certifications the profile didn't declare. Generic salutations only
   ("Contracting Officer").

4. **Approval gate.** Action packages always emit
   `human_approval_required` covering at least: external contact,
   certification claims, submission, compliance attestation.

5. **Budget.** 40 steps / 6 minutes / $0.50 per agent run.

## What's NOT here

- Michaela's persona/SOUL — lives in `/root/michealaai`'s `HERMES_HOME`.
- Worker definitions, agent-bootstrap, work-loop logic — `/root/michealaai`.
- Orchestration recipes (the equivalent of `operate_bid_desk`,
  `analyze_opportunity_e2e`) — `/root/michealaai`.
- A runtime that boots Hermes from `POST /agent-runs`. The HTTP route
  now only persists the run row; the orchestrator picks it up out of
  band.

## Where to look

- `tasks/CONTRACTS.md` — schemas, SSE event taxonomy, env contract.
- `devdocs/CURRENT_STATE.md` — single-page state of this pack.
- `devdocs/MICHAELA_SYSTEM_MODEL.md` — orchestrator + pack relationship.
- `devdocs/CAPABILITY_PACK_INTEGRATION.md` — how Michaela TS calls into
  this pack's tools (Hermes plugin + HTTP API surfaces).
- `PRD.md` — product spec (current v1.2.5).
