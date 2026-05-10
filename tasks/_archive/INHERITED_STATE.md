# Inherited State (as of 2026-05-09)

This directory contains the dev1/dev2 trackers that were active before the consolidated MVP plan replaced them. Below is a compressed snapshot of completed and in-flight work, distilled from `dev1-backend/STANDUP.md`. `dev2-frontend/STANDUP.md` was empty — frontend track had not started.

The active plan is now `/docs/superpowers/plans/2026-05-09-govcapture-mvp-completion.md`. Refer to that plan as the source of truth; this document exists only to preserve historical context.

---

## Backend (Track A) — completed before consolidation

- **A1** — FastAPI skeleton boots; native Postgres 17 + Redis up; `hermes --version` returns `v0.13.0 (2026.5.7)`; `/healthz` green.
- **P0.2** — 10 JSON Schemas authored at `/schemas/*.schema.json` (incl. `company-profile-create` and `agent-run-create` POST-input variants). `make schemas` runs `datamodel-code-generator` → `/api/schemas/*.py`. `/schemas/trace-event.example.jsonl` exists for B5 timeline replay.
- **A2** — `api/db/{__init__.py, models.py}`, async-SQLAlchemy Alembic env, migration `0001_initial` creates all 7 tables + indices + cascade FKs. `make migrate` / `make migrate-down` / `make migration MSG=...` work.
- **A3** — 11 endpoints from CONTRACTS.md §6; CORS allows localhost + `*.vercel.app`; SSE forwarder subscribes to Redis pub/sub `agent-run:{id}`, sends keepalive every 15 s, closes on `run_completed`. **Pre-A9 replayer at `api/agent/replay.py`** rewrites `run_id` in the example JSONL and publishes events at demo-friendly cadence.
- **A4** — `parse_pdf` skill at `api/skills/parse_pdf/`. Pure pypdf, marks `unparseable` on missing/encrypted/<50-char extracts and on pages with mostly-non-printable extracts. Hermetic synthesis tests via `reportlab` gated by `pytest.importorskip`.
- **A5** — `extract_requirements` skill at `api/skills/extract_requirements/`. Anthropic structured outputs (`output_config.format`) — no parse-and-retry loop. Post-validation enforces PRD §11: out-of-range `page_number` → null + downgrade; medium/high `confidence` without `evidence_snippet` → downgrade; `evidence_snippet` not substring/fuzzy-matching (≥0.3) any chunk → downgrade. Unparseable input short-circuits with no LLM call. LLM error returns degraded-but-valid output.
- **Shared LLM client** — `api/llm.py` with class `LLM` (note: `LLM`, not `LLMClient`) and method `complete_structured` (note: not `generate_structured`). `AsyncAnthropic`, top-level `cache_control` on system prompt, per-model pricing (Haiku/Sonnet/Opus), surfaces `cache_read_input_tokens`.

## Supabase pivot (PRD v1.2.3)

- DB connection adds `connect_args={"ssl": "require"}` for non-localhost hosts; loopback unchanged.
- `api/config.py` adds `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_STORAGE_BUCKET`.
- `api/storage.py` (new) — httpx wrapper around Supabase Storage REST: `upload_bytes`, `upload_file`, `download_bytes`, `download_to_tmp`, `delete`. Service-role keyed (bypasses RLS). `parse_pdf` keeps taking local paths — caller downloads from Storage to `/tmp` first.
- `infra/bootstrap.sh` shrinks ~40%: drops Postgres install/role setup; installs Redis + Python + Hermes (via `~/.local/bin`) + nginx + certbot.
- Backups: Supabase handles pg_dump; on-box backup units removed.
- `pgBouncer-on-port-6543` vs Direct-Connection-on-port-5432: asyncpg's prepared statements break transaction-mode pooling. Use Direct Connection (port 5432).

## In-flight at consolidation time

- **A6** (score_fit with §11.1 short-circuit) was the next backend task.
- **Frontend track had not started.** No `/web/` directory yet. `make schemas` prints a warning and skips TS codegen until `/web/` is present.

## Notes for posterity (preserved)

- Skills moved from spec's `/api/agent/tools/` to `/api/skills/<name>/` for stable paths; the Hermes toolset wrapper layers on at A9.
- LLM wrapper uses `output_config.format` (Anthropic structured outputs) instead of parse-and-retry — eliminates markdown-fenced-JSON failure modes.
- Pre-A9 replayer's 250 ms `initial_delay` matters: pubsub drops messages without listeners; SSE subscriber needs time to connect after `POST /agent-runs` returns.
- Migration revision id pinned to `0001` for stable ordering.
- `LLMMetrics.attempts` allows `0` — used by the unparseable-input short-circuit to return metrics without claiming an LLM call.
- `parse_pdf` deliberately stays local-path-only — keeps unit tests fast and hermetic. Storage round-trips are the caller's responsibility.
- Auth and Supabase Realtime are deliberately not adopted in v1.2.3 — keeps the surface change scoped to "managed PG + Storage."
- Hermes is invoked as a **local subprocess** per `tasks/HERMES.md` (not bundled into FastAPI's process). Local install at `~/.local/bin/hermes`; on VX1 install via `infra/bootstrap.sh`. Both processes share the same OS user (`govcapture` in prod).
