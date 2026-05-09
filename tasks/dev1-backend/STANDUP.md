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

---

## 2026-05-09 (later) — Dev 1 (Track A) — Supabase pivot

**Done since last entry:**
- [x] PRD bumped to v1.2.3. §7.5 / §7.6 rewritten: Postgres + Storage move to Supabase; Redis stays native on VX1; Auth and Realtime explicitly deferred.
- [x] `api/db/__init__.py` — engine adds `connect_args={"ssl": "require"}` only for non-localhost hosts. Local PG dev still works; Supabase pg works without code change.
- [x] `api/config.py` — added `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_STORAGE_BUCKET` settings.
- [x] `api/storage.py` (new) — httpx-based wrapper around Supabase Storage REST API: `upload_bytes`, `upload_file`, `download_bytes`, `download_to_tmp`, `delete`. Service-role keyed; bypasses RLS. `parse_pdf` keeps taking local paths — caller downloads from Storage to `/tmp` first.
- [x] `.env.example` + `tasks/CONTRACTS.md §4` updated with the four Supabase vars and Direct-Connection-not-pooler note.
- [x] `infra/bootstrap.sh` shrinks ~40%: dropped `postgresql-16` + `postgresql-client-16` install, role/db setup, `systemctl enable postgresql`, and the `/var/lib/govcapture/{raw,parsed}` working dirs. Bootstrap now installs just Redis + Python + Hermes-via-uv + nginx + certbot.
- [x] `infra/systemd/govcapture-api.service` — dropped `After=postgresql.service` and `Wants=postgresql.service`; `ReadWritePaths` no longer includes `/var/lib/govcapture`.
- [x] Deleted `infra/backup.sh`, `infra/systemd/govcapture-backup.service`, `infra/systemd/govcapture-backup.timer` — Supabase handles pg backups.
- [x] `infra/RUNBOOK.md` rewritten end-to-end: §1 now covers creating the Supabase project + bucket; §5 runs Alembic against Supabase; §9 backups section says "Supabase handles it"; new gotchas table entry for the pgBouncer-vs-direct trap.
- [x] All 71 tests still green against local PG (`DATABASE_URL=postgresql+asyncpg://govcon@localhost:5432/govcon`). Verified the SSL detection doesn't break loopback.

**Doing next:**
- A6 — `score_fit` with §11.1 deterministic short-circuit. Same prompt-template + structured-output pattern as A5.

**Blocked on:**
- Need a Supabase project URL + service-role key in `.env` to run live migrations against Supabase. Not blocking A6/A7 (those are skill code, infra-agnostic).

**Decisions / questions for the other dev:**
- @Dev2: schema codegen to TypeScript is still gated on `/web/` existing. Once you have a `/web/` dir, `make schemas` will populate `/web/lib/schemas/` automatically. (Or you can keep using `/landing/` and import from `/schemas/*.json` directly — your call.)
- @Dev2: front-end uses `SUPABASE_ANON_KEY` only (never `SERVICE_ROLE_KEY`). For v1.2.3 there's no direct browser→Supabase wiring required — the FastAPI proxy mediates everything.

**Notes for posterity:**
- pgBouncer-on-port-6543 vs Direct-Connection-on-port-5432: asyncpg's prepared statements break transaction-mode pooling. The tested path is the direct URL; documented prominently in `.env.example`, CONTRACTS.md §4, the RUNBOOK gotchas table, and the bootstrap next-steps message.
- `parse_pdf` deliberately stays local-path-only — keeps the skill testable with a synthesized PDF. Storage round-trips are the *caller's* responsibility (eval harness in A12, Hermes bridge in A9). This keeps skill unit tests fast and hermetic.
- Supabase's free tier gives 7-day rolling backups; PRD §7.6 calls that out instead of the previous on-box pg_dump cron.
- Auth (§17 Q5) and Supabase Realtime are deliberately not adopted in v1.2.3 — keeps the surface change scoped to "managed PG + Storage."
