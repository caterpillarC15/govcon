# Interference Map

> **2026-05-09 update.** The two-track Dev 1 / Dev 2 layout is retired.
> Active development happens on `main` with per-feature branches. The
> file-ownership table below is preserved as a useful map of what file
> lives where; treat "Track A" / "Track B" as historical metadata.
>
> Recent additions to the boundary:
> - `supabase/migrations/*.sql` — schema source of truth (PRD v1.2.4).
> - `api/auth.py` — JWT + InternalActor verification.
> - `api/repositories/{profile,waitlist}.py` — new resources (2026-05-09).
>
> **PRD v1.2.5 removal.** `api/agent/` (the in-repo orchestration code:
> `hermes_runner`, `hermes_bridge`, `replay`) is gone. Michaela's
> orchestrator + worker bench live in `/root/michealaai`. File ownership
> in this repo now centers on `api/skills/`, `api/routes/`,
> `supabase/migrations/`, `web/`, `fixtures/`.

File ownership, shared-file protocols, and conflict-resolution rules.

---

## 1. File ownership

**Single-owner files (no merge conflicts expected):**

| Path | Owner |
|------|-------|
| `/api/**` (except `/api/schemas/` generated files) | Track A |
| `/api/skills/**` | Track A |
| `/api/storage.py` (Supabase Storage wrapper, PRD v1.2.4) | Track A |
| `/infra/**` | Track A |
| `Makefile` (top-level) | Track A |
| `/web/**` | Track B |
| `/fixtures/<slug>/manifest.json` | Shared |
| `/fixtures/<slug>/attachments/*.pdf` | Shared |
| `/web/public/demo/**` (recorded demo assets) | Track B |

**Shared files — require care:**

| Path | Protocol |
|------|----------|
| `/schemas/*.json` | Schema source. Changes need both-dev ack on the PR. Regenerate `/api/schemas/` with `make schemas` when Python models are affected. |
| `/api/schemas/**` (generated) | Prefer regeneration via `make schemas`. Commit with the source schema change. |
| `/.env.example` | Append-only. New var added here AND in `CONTRACTS.md §4` in the same PR. |
| `/PRD.md` | Current product truth is v1.2.4. Any edit is a joint decision logged in `tasks/README.md` decision log + a PRD changelog entry. |
| `/tasks/README.md` decision log | Append-only. Both devs add entries; never edit prior. |
| `/Makefile` (top level) | Track A owns; B can request additions via standup. |

---

## 2. Shared-file protocols

### Schema change protocol

1. Author edits `/schemas/<name>.schema.json`.
2. Author runs `make schemas`. This regenerates `/api/schemas/`; TypeScript
   schema codegen is not currently wired.
3. Author runs `make typecheck` and the relevant npm typecheck target, then
   confirms both halves still build.
4. Author opens a PR with all three sets of files in one commit.
5. Other dev acks within ~30 min (use Slack/standup if longer). Merge after ack.
6. After merge, both devs `git pull` and rebuild locally.

If a schema change breaks the other side's build, the author owns the fix or revert.

### Fixture authoring protocol (B → A)

1. Author edits `/fixtures/<slug>/manifest.json` and attachments.
2. Author runs `make fixtures-validate` and the relevant skill tests to confirm
   the pipeline accepts the fixture.
3. If extraction fails, log the diagnosis in `tasks/README.md` decision log:
   fixture issue, prompt/parser issue, or expected-behavior change.
4. B never edits the schema to fit a fixture. If a fixture needs a field the schema doesn't support, raise it as a schema change.

### Env var protocol

- New var → add to `.env.example` AND `CONTRACTS.md §4` in the same PR.
- Never read env outside `/api/config.py` or `/web/src/lib/supabase/env.ts`
  and middleware code that imports that helper.
- Don't commit `.env`. `gitignore` enforces.

### PRD change protocol

- Frozen except for joint edits. If a PRD edit is needed mid-build (e.g., scope clarification), both devs agree, edit together, bump version, log in changelog and decision log.

---

## 3. Sync checkpoints

These are the moments where both halves of the system meet. Calendar them.

| # | Trigger | Goal | Time | Output |
|---|---------|------|------|--------|
| S1 | End of Phase 0 | Contracts locked, mock API up, schemas generating | ~30 min | Both ack in `tasks/README.md` |
| S2 | A3 merges (real CRUD endpoints) | B drops mock client, points at real `/api` | ~10 min | B's UI fetches real data; smoke-test happy paths |
| S3 | A9 merges (agent loop end-to-end) | First localhost dry-run of full §13.1 demo | ~30 min | Recorded screen capture; bug list |
| S4 | A13 merges (VX1 deployed) | Cutover to VX1 URL; B records backup demo video | ~30 min | Stable URL; backup .mp4 in `/web/public/demo/` |
| S5 | T-2h before stage | Full dress rehearsal; `make fixtures-validate` + tests green | ~30 min | Stage-ready |

Skipped checkpoints become integration debt that surfaces during the demo. Don't skip.

---

## 4. Conflict resolution

**Rule of thumb:** the file's owner has final say on their files. For shared files, both devs must ack. For disputes that can't be resolved in 5 minutes:

1. Prefer the option that keeps the demo (§13.1) working.
2. Prefer the option that doesn't require a schema change.
3. If still tied, the dev whose track is currently on the critical path decides; the other gets a follow-up task.

Log the dispute and resolution in the decision log (`README.md`).

---

## 5. Branch strategy

Suggested:

- `main` — always green. Merges only after the other dev acks (small PRs) or after the owner's CI passes (single-track changes).
- Feature branches per task: `a5-extract-requirements`, `b9-fixture-strong-pursue`, etc. Short-lived (< 4 hours). Merge fast.
- No long-lived branches. Schema PRs merge same-day to avoid rebase pain.

If the remote is on a host that requires PRs (GitHub), use PRs. If the remote allows direct push to `main` and trust is high, direct push for single-track changes is fine; schema PRs always go through review.

---

## 6. Failure-mode prevention

Concrete things that have killed past parallel hackathon teams. Each has a mitigation we've already baked in:

| Failure | Mitigation |
|---------|------------|
| Schemas drift mid-build | P0.2 codegen pipeline; no hand-edits |
| B builds against assumed event shape | P0.3 freezes shape; example JSONL committed |
| Fixture written to a not-yet-existent schema | Schema PRs merge before fixture PRs depending on them |
| Both devs editing `/infra/**` (bootstrap, systemd, nginx) | Single owner (A) |
| LLM cost runaway during dev | `LLM_DEV_MODEL=claude-haiku-4-5-20251001` default; Sonnet only on tagged tests |
| Michaela runtime issues block demo | Use a pre-cached run or fixture-only orchestrator path outside this repo; `/web` should not pretend to run agents locally |
| Fixture PDFs mis-author so parser fails | A and B jointly draft fixture-PDF guidelines in P0.4; A reviews each fixture PR |
| First end-to-end test happens during stage | S2 + S3 + S5 are mandatory |
| Forgotten env var on VX1 | A13 verifies all `.env.example` keys are set in prod |
