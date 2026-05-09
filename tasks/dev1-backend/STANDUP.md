# Standup Log

Append-only daily log. Both devs write entries. Async-friendly so this works across timezones/shifts.

**Format:** one section per dev per day. Don't edit prior entries.

**Template (copy-paste, fill in):**

```markdown
## YYYY-MM-DD — Dev N (Track A|B)

**Done since last entry:**
- [ ] task ID — one-line outcome
- [ ] task ID — one-line outcome

**Doing next:**
- task ID — what specifically

**Blocked on:**
- (nothing) OR (task ID, waiting for X from other track, ETA)

**Decisions / questions for the other dev:**
- (none) OR (specific question; tag the other dev's name)

**Notes for posterity:**
- (anything surprising; non-obvious; corrections to prior plans)
```

---

## Sync-checkpoint sign-offs

When a sync checkpoint completes (S1–S5 from `../INTERFERENCE_MAP.md §3`), both devs sign off here:

```markdown
### Sync S<n> — YYYY-MM-DD HH:MM
- ✅ Dev 1: <one-line confirm>
- ✅ Dev 2: <one-line confirm>
- Notes: <anything that surfaced; followup tasks>
```

---

## Entries

<!-- Append below this line. -->

## 2026-05-09 — Dev 1 (Track A)

**Done since last entry:**
- [x] A1 — FastAPI skeleton boots; native Postgres 17 + Redis up; `hermes --version` returns `v0.13.0 (2026.5.7)`; `/healthz` green.
- [x] P0.2 — Authored 10 JSON Schemas (`/schemas/*.schema.json`, including `company-profile-create` and `agent-run-create` variants for POST input); `make schemas` runs `datamodel-code-generator` → `/api/schemas/*.py` with the `_schema` suffix stripped. Authored `/schemas/trace-event.example.jsonl` for B5 timeline replay (one of each event type per CONTRACTS.md §3, run-completion summary at the end).
- [x] A2 — `api/db/{__init__.py, models.py}`, Alembic env using async SQLAlchemy, migration `0001_initial` creates all 7 tables + indices + cascade FKs. `make migrate` / `make migrate-down` / `make migration MSG=...` work end-to-end.
- [x] A3 — 11 endpoints from CONTRACTS.md §6 implemented; CORS allows localhost dev + `*.vercel.app`; SSE forwarder subscribes to Redis pub/sub `agent-run:{id}`, sends `:keepalive\n\n` every 15 s, closes on `run_completed`. **Pre-A9 replayer** at `api/agent/replay.py` rewrites `run_id` in the example JSONL and publishes events at demo-friendly cadence so the timeline has real, well-shaped events to render until the Hermes bridge (A9) lands. Verified end-to-end: `POST /company-profiles` → `POST /agent-runs` → `GET /stream` emits a properly-framed SSE chain starting with `run_started` and run_id rewritten to the persisted run.
- [x] A4 — `parse_pdf` skill at `api/skills/parse_pdf/`. Pure pypdf, marks unparseable on missing/encrypted/<50-char extracts and on pages whose extract is mostly non-printable (custom-font garbage). Hermetic synthesis tests via `reportlab` gated by `pytest.importorskip` so the suite stays green if `reportlab` isn't installed.
- [x] A5 — `extract_requirements` skill at `api/skills/extract_requirements/`. Anthropic structured outputs (`output_config.format`) so the API enforces the JSON shape — no parse-and-retry loop. Prompt template at `prompt.txt`. Post-validation enforces PRD §11: out-of-range `page_number` → null + downgrade; `confidence ∈ {high, medium}` without an `evidence_snippet` → downgrade; `evidence_snippet` that doesn't substring/fuzzy-match (≥0.3) any chunk → downgrade. Unparseable input short-circuits with no LLM call. LLM error returns degraded-but-valid output (planner recovery branch — PRD §4.5).
- [x] Shared LLM client (`api/llm.py`) — `AsyncAnthropic`, structured output, top-level `cache_control` on system prompt, per-model pricing (Haiku/Sonnet/Opus), surfaces `cache_read_input_tokens` for hit verification. Used by every LLM-backed skill.

**Doing next:**
- A6 — `score_fit` with **§11.1 deterministic short-circuit BEFORE the rubric math.** Eligibility/clearance/set-aside mismatch carrying `is_blocker=true` MUST yield `decision="reject"` regardless of capability score. The LLM rationale is downstream of the math; if the model contradicts the math, math wins.

**Blocked on:**
- (nothing for A6/A7) — `.env` still empty; tests use a `FakeLLM` stub so no Anthropic budget is consumed.
- A13 will need VX1 IP/domain/SSH key when we get there (user confirmed VX1 is provisioned).

**Decisions / questions for the other dev:**
- @Dev2: **S2 is ready.** A3 is live on `localhost:8000`; switch `NEXT_PUBLIC_API_BASE` and smoke-test happy paths. The pre-A9 SSE replayer means `/agent-runs/{id}/stream` already emits a real event chain — your Timeline (B5) can render against it without waiting for A9.
- @Dev2: 2 fixture-dependent tests in `test_parse_pdf.py` are gracefully skipped (`pytest.skipif _has_pdfs(slug)`). They'll un-skip the moment `/fixtures/strong-pursue/attachments/*.pdf` and `/fixtures/adversarial-image-pdf/attachments/*.pdf` exist.
- @Dev2: `/web/` doesn't exist yet (you're on `/landing/`?). The `make schemas` target prints a one-line warning and skips TS codegen until `/web/` is present — no error, just a flag for when you wire up the app.

**Notes for posterity:**
- Skills moved from A-spec's `/api/agent/tools/` to `/api/skills/<name>/` so the public path stays stable when the Hermes toolset wrapper layers on in A9.
- LLM wrapper uses `output_config.format` (Anthropic's structured-outputs feature) instead of the parse-and-retry loop A5.md skeleton suggested. This eliminates a class of "model returned markdown-fenced JSON" failure modes.
- Pre-A9 replayer's 250 ms `initial_delay` matters — pubsub drops messages without listeners, so the SSE subscriber needs time to connect after `POST /agent-runs` returns. Without the delay, the test client misses `run_started`.
- Migration revision id pinned to `0001` (vs the autogen hash) for stable ordering. Future autogenerates pick up wherever Alembic's chain leaves off; pin manually if order matters.
- `LLMMetrics.attempts` allows `0` so the unparseable-input short-circuit can return a metrics object without claiming an LLM call happened.
