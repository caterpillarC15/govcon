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

## P0.2 — Schema codegen pipeline (~60 min) — ✅ Done 2026-05-09

Source of truth: `/schemas/*.json`, JSON Schema draft 2020-12.

- [x] Author `/schemas/company-profile.schema.json` from PRD §8.1.
- [x] **+1** Author `/schemas/company-profile-create.schema.json` (server-set fields omitted; used by `POST /company-profiles`).
- [x] Author `/schemas/opportunity.schema.json` from PRD §8.2.
- [x] Author `/schemas/extracted-requirement.schema.json` from PRD §8.3. (The §10.1 `RequirementExtractionOutput` wrapper lives inline in the skill — `api/skills/extract_requirements/skill.py` — since it's the LLM intermediate shape, not the persisted entity.)
- [x] Author `/schemas/fit-score.schema.json` from PRD §8.4 + §10.2.
- [x] Author `/schemas/risk-flag.schema.json` from PRD §8.5.
- [x] Author `/schemas/action-package.schema.json` from PRD §8.6 + §10.3.
- [x] Author `/schemas/agent-run.schema.json` from PRD §8.7.
- [x] **+1** Author `/schemas/agent-run-create.schema.json` (accepts `goal` + either `profile_id` or inline `profile`).
- [x] Author `/schemas/trace-event.schema.json` per CONTRACTS.md §3 (discriminated union on `type`).
- [x] `Makefile` target wired (Track A owns):
  ```make
  schemas:
      uv run datamodel-codegen --input schemas --input-file-type jsonschema \
          --output api/schemas --output-model-type pydantic_v2.BaseModel \
          --use-standard-collections --use-union-operator \
          --target-python-version 3.12 --use-schema-description \
          --field-constraints --use-default --enum-field-as-literal all \
          --disable-timestamp
      # `_schema` suffix stripped post-generation so `from api.schemas.agent_run import AgentRun` works.
      # TS codegen for /web is a no-op until Dev 2 wires it (see CONTRACTS.md §2).
  ```
- [x] Generated `/api/schemas/*.py` populates correctly; round-trip tests in `api/tests/test_schemas.py` cover every entity (40 tests, all green).
- [x] **TS codegen deferred until `/web/` exists.** Currently Dev 2 is on `/landing/` — `make schemas` prints a one-line warning and skips TS until the directory is present. No drift risk: Dev 2 hand-writes zod from the same JSON sources or imports them directly until then.

**Rule:** any future schema change runs `make schemas` and commits the regenerated outputs in the same PR. See `INTERFERENCE_MAP.md §2`.

## P0.3 — Trace event taxonomy + example replay (~20 min) — ✅ Done 2026-05-09

B's timeline (B5) is blocked without this. Locked now even though A9 won't ship for a while.

- [x] `/schemas/trace-event.schema.json` covers all 8 event types from CONTRACTS.md §3.
- [x] `/schemas/trace-event.example.jsonl` authored — happy-path run with all event types and human-readable cadence (gaps reflect realistic agent timing). Includes `run_started`, 6 step lifecycles each with `tool_called` + `tool_returned`, an `opportunity_ranked`, and `run_completed`. Every line passes `TraceEvent.model_validate` (covered by `test_every_example_trace_event_parses`).
- [x] **A3's pre-A9 SSE bridge already replays this file** at `api/agent/replay.py` — Dev 2 doesn't need to mock anything; `POST /agent-runs` followed by `GET /agent-runs/{id}/stream` emits real, well-shaped events with `run_id` rewritten to the persisted run. Replaced by the Hermes bridge in A9.

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

## P0.6 — Hermes Agent install + wire project config

Per PRD v1.2.2. Both devs install on their machines (Track A drives the integration but Track B may want it for local end-to-end tests).

### Install

- [ ] Run installer:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
  ```
- [ ] Configure model: `hermes model` → set to `claude-sonnet-4-6` (synthesis) and confirm `ANTHROPIC_API_KEY` is wired.
- [ ] Smoke-test: `hermes` opens REPL; basic interaction works.

### Wire project config (so Hermes uses our delegation depth, skills, and persona)

Our project ships its Hermes config in `<repo>/.hermes/`. Symlink so Hermes picks it up:

- [ ] **Config (delegation depth = 2 — required for our 5-agent design):**
  ```bash
  ln -sf "$(pwd)/.hermes/config.yaml" ~/.hermes/config.yaml
  ```
  Confirm: `cat ~/.hermes/config.yaml | grep max_spawn_depth` → `max_spawn_depth: 2`.

- [ ] **Project SKILL.md procedures (7 skills under `.hermes/skills/govcapture/`):**
  ```bash
  mkdir -p ~/.hermes/skills
  ln -sf "$(pwd)/.hermes/skills/govcapture" ~/.hermes/skills/govcapture
  ```
  Confirm: `hermes /skills` lists `discover_opportunities`, `analyze_opportunity_e2e`, `extract_requirements_with_evidence`, `score_fit_with_eligibility_check`, `detect_risks_calibrated`, `generate_full_action_package`, `generate_reject_summary`.

- [ ] **Umbrella persona (SOUL.md):**
  ```bash
  ln -sf "$(pwd)/.hermes/SOUL.md" ~/.hermes/SOUL.md
  ```
  Confirm: `hermes` startup banner mentions GovCapture context.

- [ ] **Project context (HERMES.md at repo root) is auto-detected.** Hermes walks from cwd to git root and loads the first `.hermes.md` / `HERMES.md` it finds. No symlink needed; just run `hermes` from inside the repo.

### Validate the wiring

- [ ] `hermes /skills` lists all 7 GovCapture skills.
- [ ] `hermes config show delegation` confirms `max_spawn_depth: 2` and `max_concurrent_children: 3`.
- [ ] In a test prompt, ask Hermes "what skills do you have available for federal contract analysis?" — it should describe at least the discover_opportunities and score_fit_with_eligibility_check skills.
- [ ] Both devs commit confirmation in `dev1-backend/STANDUP.md` / `dev2-frontend/STANDUP.md`.

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
