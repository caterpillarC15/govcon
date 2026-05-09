# Phase 0 — Joint Setup

Both devs in the room (or pair-screen, screen-shared). Estimated ~3 hours. **No track work starts until every box below is ticked.** Skipping P0 guarantees expensive rework around hour 30.

---

## P0.1 — Repo + writable remote (~20 min)

The current remote `caterpillarC15/govcon` returned 403 to `AayushBaniya2006`. Resolve before doing anything else.

- [ ] Decide remote owner: collaborator on `caterpillarC15/govcon`, fork to a writable account, or new repo. Log decision in `README.md`.
- [ ] If switching remote: `git remote set-url origin <new-url>` and `git push -u origin main`.
- [ ] Verify the v1.2.1 PRD commit (`b007d38`) is on the remote.
- [ ] Create empty subdirs per `CONTRACTS.md §1`:
  ```
  mkdir -p api/skills infra eval/runner eval/goldens web fixtures schemas
  touch api/.gitkeep api/skills/.gitkeep infra/.gitkeep eval/runner/.gitkeep \
        eval/goldens/.gitkeep web/.gitkeep fixtures/.gitkeep schemas/.gitkeep
  ```
- [ ] Author `.gitignore` covering Python (`__pycache__`, `*.pyc`, `.venv`, `dist/`, `*.egg-info`), Node (`node_modules`, `.next`, `dist`), env (`.env`, `.env.local`), OS (`.DS_Store`). **Keep** `/fixtures/<slug>/attachments/*.pdf` (do NOT gitignore PDFs — they are content).
- [ ] Commit `.gitignore` and the empty-subdir layout.

## P0.2 — Schema codegen pipeline (~60 min)

Source of truth: `/schemas/*.json`, JSON Schema draft 2020-12.

- [ ] Author `/schemas/company-profile.schema.json` from PRD §8.1.
- [ ] Author `/schemas/opportunity.schema.json` from PRD §8.2.
- [ ] Author `/schemas/extracted-requirement.schema.json` from PRD §8.3 + §10.1 (include `RequirementExtractionOutput` wrapper with `requirements`, `missing_fields`, `conflicts`).
- [ ] Author `/schemas/fit-score.schema.json` from PRD §8.4 + §10.2.
- [ ] Author `/schemas/risk-flag.schema.json` from PRD §8.5.
- [ ] Author `/schemas/action-package.schema.json` from PRD §8.6 + §10.3.
- [ ] Author `/schemas/agent-run.schema.json` from PRD §8.7.
- [ ] Author `/schemas/trace-event.schema.json` per CONTRACTS.md §3 (discriminated union on `type`).
- [ ] Add `Makefile` target:
  ```make
  schemas:
      datamodel-codegen --input schemas --input-file-type jsonschema \
          --output api/schemas --output-model-type pydantic_v2.BaseModel \
          --use-double-quotes --target-python-version 3.12
      json-schema-to-zod -i schemas -o web/lib/schemas
  ```
- [ ] Both devs run `make schemas` and confirm both target dirs populate.
- [ ] Decide commit policy for generated files: **commit them**, so devs without codegen tools installed locally can still build. Add a CI check (or pre-commit hook) that `make schemas` produces no diff.

**Rule:** any future schema change runs `make schemas` and commits the regenerated outputs in the same PR. See `INTERFERENCE_MAP.md §2`.

## P0.3 — Trace event taxonomy + example replay (~20 min)

B's timeline (B5) is blocked without this. Lock it now even though A9 won't ship for a while.

- [ ] Confirm `/schemas/trace-event.schema.json` covers all 8 event types from CONTRACTS.md §3.
- [ ] Author `/schemas/trace-event.example.jsonl` — one recorded happy-path run with one of each event type. Use realistic timing (500ms–2s gaps between events). Include:
  - `run_started`
  - 3 steps each emitting `step_started` → `tool_called` → `tool_returned` → `step_completed`
  - 3 `opportunity_ranked` events (one strong_pursue, one maybe, one reject)
  - `run_completed`
- [ ] Confirm B can read and render this file. (B builds B5 against it before A9 exists.)

## P0.4 — Fixture template + authoring guidelines (~30 min)

Joint authoring so B's content matches A's parser.

- [ ] Create `/fixtures/_template/opportunity.json` matching `opportunity.schema.json`. All required fields present, placeholders clearly marked.
- [ ] Create `/fixtures/_template/expected.json` per FIXTURES.md golden shape.
- [ ] Create `/fixtures/_template/attachments/SAMPLE.pdf` — one page, plain text, includes a fake solicitation header. Use this as a structure reference.
- [ ] Author fixture-PDF guidelines section in `FIXTURES.md` (e.g., text-extractable PDFs only for the 3 demo fixtures; image-only is reserved for the adversarial fixture). Both devs review and ack.
- [ ] A confirms that `parse_pdf` (A4) will be tested against `_template/attachments/SAMPLE.pdf` from day 1 to keep parser and fixtures aligned.

## P0.5 — Env contract (~15 min)

- [ ] Author `/.env.example` exactly per CONTRACTS.md §4.
- [ ] Both devs copy to `/.env` and fill secrets (Anthropic key required; SAM key can be blank for dev).
- [ ] Author `/api/config.py` and `/web/lib/env.ts` as the only places that read env. Each fails loudly on missing required vars at startup.
- [ ] Confirm `.env` is in `.gitignore` and not committed.

## P0.6 — Hermes Agent install

Per PRD v1.2.2. Both devs install on their machines (Track A drives the integration but Track B may want it for local end-to-end tests).

- [ ] Run installer:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
  ```
- [ ] Configure model: `hermes model` → set to `claude-sonnet-4-6` (synthesis) and confirm Anthropic API key is wired.
- [ ] Smoke-test: `hermes` opens REPL; basic `who are you` interaction works.
- [ ] Commit `hermes` config notes to `tasks/HERMES.md` if anything is non-default.

## P0.7 — Mock API server (was P0.6 in v1.2.1; renumbered after Hermes addition) (~45 min)

A authors; B verifies. Unblocks B for the entire build.

- [ ] FastAPI scaffold in `/api/main.py` with all PRD §9 endpoints (CONTRACTS.md §6) returning canned JSON.
- [ ] Canned data sourced from `/fixtures/_template/opportunity.json` and a single hand-written canned `ActionPackage`. (Real fixtures land later via B9–B12.)
- [ ] SSE mock for `GET /agent-runs/:id/stream` that replays `/schemas/trace-event.example.jsonl` at the captured cadence. Use `text/event-stream` with `event:` and `data:` framing per CONTRACTS.md §3.
- [ ] `GET /healthz` returns `{"status": "ok"}`.
- [ ] `make dev` brings up the mock server on `:8000`.
- [ ] B fetches every endpoint via curl or browser and confirms shapes match generated zod types (`tsc` passes).

---

## Done when

All boxes above are ticked AND:

- [ ] Both devs run `make schemas` successfully and commit the generated files.
- [ ] Mock API responds on all §9 endpoints; SSE replay works.
- [ ] `make dev` (mock API) and B's `npm run dev` both start cleanly with the locked env contract.
- [ ] Both devs sign off in `STANDUP.md` with date and a one-line "Phase 0 complete."

After Phase 0, Track A and Track B run independently except at the sync checkpoints in `INTERFERENCE_MAP.md §3`.
