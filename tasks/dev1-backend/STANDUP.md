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
- [x] Milestone 0 / Hermes spike — `scripts/spike_hermes.py` runs green: custom toolset registration ✓, in-process `AIAgent` with `tool_start_callback` / `tool_complete_callback` capturing structured events ✓, subprocess `hermes -z` invocation + session-snapshot persistence ✓.
- [x] Authored `tasks/HERMES_SPIKE.md` answering all 7 open questions in `tasks/HERMES.md` with working-code citations.
- [x] `tasks/CONTRACTS.md §3.1` — bridge translation table (Hermes callbacks + session snapshots → §3 SSE events). Both invocation modes covered. Pinned now so A9 has a contract to implement against.
- [x] Reconciled stale "PRD v1.2.1" references in `tasks/CONTRACTS.md §1` and `tasks/INTERFERENCE_MAP.md §1` → v1.2.2.
- [x] Confirmed runtime state on this host: Hermes Agent v0.13.0; `delegation.{max_spawn_depth: 2, max_concurrent_children: 3, orchestrator_enabled: true}` already correct in `~/.hermes/config.yaml`; symlink `~/.hermes/skills/govcapture` resolves; all 7 govcapture SKILL.md files load via `hermes skills list`.

**Doing next:**
- Milestone 1 / Phase 0 — `/tasks/PHASE_0.md` P0.1 through P0.7. First commits land repo skeleton (`/api`, `/infra`, `/eval`, `/schemas`, `/fixtures`), then schemas + codegen, then mock API on `:8000`.

**Blocked on:**
- (nothing). Spike findings unblock all of Phase 0.

**Decisions / questions for the other dev:**
- (none — spike decisions are recorded in `tasks/HERMES_SPIKE.md` and the `tasks/README.md` decision log.)

**Notes for posterity:**
- Hermes credentials on this host live in `~/.hermes/auth.json` `credential_pool.anthropic[]` as an OAuth `access_token`, not as a static API key in `~/.hermes/.env`. `/api/config.py` (Milestone 1, P0.5) must handle all three storage paths (`.env`, `auth.json`, shell env) the same way `scripts/spike_hermes.py::_load_env_files` does.
- Frontend stack note: the original brief said Vite for `/landing/`, but commit 170d60f had already migrated it to Next.js. Therefore CONTRACTS.md §4's `NEXT_PUBLIC_API_BASE` is correct — no `VITE_API_BASE` rename. Confirmed and logged.
- Hermes' `delegate_task` does NOT accept a per-call `model` kwarg — only `~/.hermes/config.yaml` `delegation.model` is honored. AGENT_ARCHITECTURE.md's per-role model-split optimization is therefore deferred until/unless we hit the $0.50 cap. Cost estimate (≈$0.20/run) leaves comfortable headroom.
