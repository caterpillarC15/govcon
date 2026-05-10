# Everything-to-v1.0.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take GovCon from its current "v1.2.6 refactor branch in flight + multi-Supabase discovery + drift on three fronts" state to a tagged `v1.0.0` shipped on `origin/main`. This is the cleanup-and-finish plan that sits *on top of* the executed `2026-05-10-skills-deterministic-only.md` plan and the still-running `2026-05-10-finish-it-all.md` plan.

**Architecture:** 7 phases sequenced by dependency. Phases 0–4 are `[ENG]` (executable autonomously now). Phase 5 is `[USER]`-action (third-party accounts + DNS + cross-repo). Phase 6 is the tag, gated on everything before. Each phase emits one or more commits and ends with a verification gate that must hold before the next phase starts.

**Tech stack:** Python 3.12 · FastAPI · supabase-py PostgREST · Redis · Next 15 + Tailwind 4 · `uv` · Resend HTTP API · Vultr VX1 + nginx + systemd · Vercel.

**What's verified before this plan starts (state at 2026-05-10):**

- `refactor/skills-deterministic-only` branch is at commit `175cbe4`, 11 commits ahead of `origin/main`. Pushed to `origin/refactor/skills-deterministic-only`.
- 206 pytest pass on the branch; ruff + mypy clean across 87 files.
- Eval goldens already bootstrapped under `fixtures/<slug>/goldens/` (deterministic byte-exact, free).
- §5.14 weekly opportunity email shipped end-to-end behind `EMAIL_DRY_RUN=true`.
- 10 Supabase migrations applied to `vvyxjdoenjujkxwbnzyl`.
- `.env` updated with the v1.2.6 contract + three-Supabase comment block.
- Working tree clean except for `.env.example` and `package.json` (user edits in flight; left alone).

**Out of scope** (logged but not in this plan):

- Bench-naming sweep (Gate/Ledger ↔ Gabby/Lance) — requires user decision + cross-repo coordination, tracked in Phase 2 as a *decision-only* item with the implementation deferred.
- Updating `/root/michealaai/DATA-SOURCES.md` — cross-repo, surfaced as a USER-action item.
- Native `hermes_plugin_govcapture/` Python plugin — superseded by MCP bridge.
- TS codegen for `/web` types — listed open in `tasks/CONTRACTS.md §2`.
- Vendoring the two REMOTE-ONLY drift placeholder migrations — post-v1 schema squash.
- CI / Sentry / FedRAMP / shadcn-ui / dark mode — same exclusions as `finish-it-all.md`.

**Continuous verification gates** (must hold at every commit):

```bash
uv run pytest api/tests/ -q             # ≥ 206 passed
uv run ruff check api                   # All checks passed
uv run mypy api                         # Success: no issues found
make fixtures-validate                  # OK for all 4 fixtures
make eval                               # PASS against committed byte-exact goldens
git status --short                      # clean (intended changes only)
```

---

## Phase 0 — Branch reconciliation [ENG, ASK FIRST]

**Goal:** bring `refactor/skills-deterministic-only` onto `origin/main` so the rest of the plan operates on one canonical history. Today the deterministic-skills code lives only on the topic branch; main has documentation about the refactor (commit `6420d29`) but not the actual code.

### Task 0.1: Confirm the merge plan with the user

- [ ] **Step 1 [USER ASK]: Surface the merge choice**

> "About to merge `refactor/skills-deterministic-only` (11 commits) into `main` via `--no-ff` so the topic branch's history is preserved. Three commits land docs (deterministic contract, three-Supabase disambiguation, v1.2.6 envelope alignment); eight commits land the actual deterministic skill refactor + the eval rewrite. After the merge, `api/llm.py` is gone, `anthropic` SDK is gone, all skills are deterministic, eval is byte-exact. Proceed?"

Wait for explicit yes. Do NOT continue without ack.

- [ ] **Step 2 [ENG]: Verify both branches are at the SHAs we expect**

```bash
git fetch origin
git log --oneline -1 origin/main
git log --oneline -1 origin/refactor/skills-deterministic-only
```

Expected: `origin/main = 6420d29`, `origin/refactor/skills-deterministic-only = 175cbe4`.

If either has moved, re-run §0.1 step 1 with the updated SHAs before merging.

### Task 0.2: Merge the branch

- [ ] **Step 1 [ENG]: Switch to main and pull**

```bash
git checkout main
git pull --ff-only origin main
```

Expected: HEAD at `6420d29` (or whatever step 0.1.2 showed).

- [ ] **Step 2 [ENG]: Merge with `--no-ff`**

```bash
git merge --no-ff refactor/skills-deterministic-only -m "Merge refactor/skills-deterministic-only — PRD v1.2.6 deterministic-only skills

Drops api/llm.py, the anthropic SDK, ANTHROPIC_API_KEY, LLM_DEV_MODEL,
LLM_SYNTH_MODEL, RUN_BUDGET_USD/STEPS/SECONDS. Every skill in this repo
is now deterministic; Michaela's bench in /root/michealaai owns LLM
calls + budget tracking.

Per-skill changes (from the topic branch):
- parse_goal: keyword/NAICS extraction by deterministic rules
- extract_requirements: chunks emitter + JSON-Schema validator
- score_fit: §11.1 short-circuit + decision-band normalizer
- detect_risks: PRD §5.8 taxonomy validator
- generate_action_package: schema validator + reject_summary mode
- /tools/<name> envelope: drop metrics field (no LLM = no LLMMetrics)
- eval/runner: byte-exact diff against committed goldens (no tolerance)

Plus three docs commits:
- 765bde0: PRD v1.2.6 changelog + integration spec
- afafcf6: three-Supabase disambiguation
- 175cbe4: public agent surfaces aligned with v1.2.6 envelope

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 3 [VERIFY]: Sanity check after merge**

```bash
uv run pytest api/tests/ -q             # ≥ 206 passed
uv run ruff check api                   # clean
uv run mypy api                         # clean
test ! -f api/llm.py                    # exit 0 — file is gone
grep -rn "ANTHROPIC_API_KEY" api/ || echo "clean"   # no live references
```

If any verification fails, `git reset --hard ORIG_HEAD` and surface the failure with the user.

- [ ] **Step 4 [ENG]: Push**

```bash
git push origin main
```

Expected: `6420d29..<merge-sha>  main -> main`.

### Task 0.3: Delete the topic branch (local + remote)

- [ ] **Step 1 [ENG]: Local delete**

```bash
git branch -d refactor/skills-deterministic-only
```

Expected: `Deleted branch refactor/skills-deterministic-only` (no `-D` needed; the branch is fully merged).

- [ ] **Step 2 [USER ASK]: Confirm before remote delete**

> "Branch is merged + locally deleted. Delete `origin/refactor/skills-deterministic-only` too? (yes / keep)"

- [ ] **Step 3 [ENG, on yes]: Remote delete**

```bash
git push origin --delete refactor/skills-deterministic-only
```

### Phase 0 verification gate

- [ ] `git branch --show-current` → `main`
- [ ] `git rev-list --count origin/main..HEAD` → `0`
- [ ] `git log --oneline origin/main -1 | grep -q "Merge refactor/skills-deterministic-only"` → success
- [ ] All three lint/test/type checks green
- [ ] `api/llm.py` does not exist
- [ ] `grep -rn "from anthropic" api/` returns empty

---

## Phase 1 — Doc sync to v1.2.6 [ENG]

**Goal:** scrub the four docs that still reference v1.2.5-era LLM-cost language. The deterministic refactor moved LLM concerns out of this repo, but several docs still say "real ANTHROPIC_API_KEY + ~$0.50 budget" or list dropped env vars. Fix them.

### Task 1.1: Audit the staleness

- [ ] **Step 1 [ENG]: Grep for the most-likely stale phrases**

```bash
grep -rn "ANTHROPIC_API_KEY\|LLM_DEV_MODEL\|LLM_SYNTH_MODEL\|RUN_BUDGET_USD\|costs Anthropic tokens\|\$0\.40\|\$0\.50\|\$0\.60\|LLM ranks" \
  devdocs/ tasks/ docs/superpowers/plans/2026-05-10-everything-to-v1.0.0.md \
  --include='*.md' \
  | grep -v "_archive" \
  | grep -v "PRD\.md.*changelog"
```

Capture every hit in `/tmp/v126-staleness.txt`. Each hit is a possible Phase 1 edit.

- [ ] **Step 2 [ENG]: Confirm `.env.example` is already clean**

```bash
grep -E "^ANTHROPIC_API_KEY|^LLM_|^RUN_BUDGET" .env.example || echo "clean"
```

Expected: `clean`. (Last session removed those keys from `.env.example` already.)

### Task 1.2: Refresh `devdocs/LAUNCH_CHECKLIST.md`

**Files:** Modify `devdocs/LAUNCH_CHECKLIST.md`

The file references "real ANTHROPIC_API_KEY" and the eval-bootstrap budget in §6.3 (.env block) + §8 (Phase 8.2). Replace those sections.

- [ ] **Step 1 [ENG]: Drop the LLM env vars from the §6.3 .env-paste-in block**

Find the block under "### 6.3 Clone repo + drop `.env` [USER]" and remove these lines:

```diff
-ANTHROPIC_API_KEY        — sk-ant-api…(real)
-LLM_DEV_MODEL            — claude-haiku-4-5-20251001
-LLM_SYNTH_MODEL          — claude-sonnet-4-6
-RUN_BUDGET_USD           — 0.50
-RUN_BUDGET_STEPS         — 40
-RUN_BUDGET_SECONDS       — 360
```

Add immediately above the §5.14 block (the line beginning `# §5.14 weekly opportunity…`):

```
# PRD v1.2.6: every skill is deterministic. Anthropic, model selection,
# and budget caps live with Michaela in /root/michealaai. This repo's
# .env carries Supabase + Resend + Redis + INTERNAL_API_KEY only.
```

- [ ] **Step 2 [ENG]: Replace the entire Phase 8 (`§6 · Phase 8 — Eval goldens bootstrap`) section**

Find `## 6 · Phase 8 — Eval goldens bootstrap` and the §11 row that says `Real Anthropic key in \`.env\` | "Run eval bootstrap"`. Replace the whole §6 with:

```markdown
## 6 · Phase 8 — Eval goldens (already bootstrapped, byte-exact)

PRD v1.2.6 made every skill deterministic, so `make eval` is now a
**byte-exact** regression gate against goldens already committed under
`fixtures/<slug>/goldens/`. No LLM call, no Anthropic key, no budget.
The harness PASSes today; treat it like the test suite.

### 8.1 Daily-use [ENG]

```bash
make eval         # diff committed goldens vs current skill output
```

Run on every PR that touches `api/skills/`, `schemas/*.json`, or any
fixture under `fixtures/`. Failure means a skill's behavior drifted —
either the change is intentional (and the golden needs re-bootstrapping
in 8.2) or it's a regression (fix the skill).

### 8.2 Re-bootstrap when behavior changes intentionally [ENG]

```bash
make eval-bootstrap            # rewrites every golden from current skill output
git diff fixtures/*/goldens/   # hand-review what changed before committing
git add fixtures/*/goldens/
git commit -m "feat(eval): re-bootstrap goldens — <what changed and why>"
```

Hand-review IS the gate. A drifted golden is only correct if the human
agrees the new behavior is the intended one.
```

Replace the §11 row `| Real Anthropic key in \`.env\` | "Run eval bootstrap" |` with `| Skill behavior intentionally changed | "Re-bootstrap goldens" — I run `make eval-bootstrap`, you hand-review the diff, we commit |`.

- [ ] **Step 3 [ENG]: Drop the dropped-env-vars line from §11 re-engagement script**

Same file, find and remove (or update) any row referencing Anthropic key in `.env` since the pack no longer reads it.

- [ ] **Step 4 [ENG]: Bump §0 status snapshot to mention "v1.2.6 deterministic" and the eval gate is live**

Find `| Eval | 15 fixture × skill `eval_inputs` authored; goldens NOT yet bootstrapped |` and replace:

```markdown
| Eval | Goldens bootstrapped (byte-exact, deterministic per PRD v1.2.6); `make eval` is the regression gate |
```

- [ ] **Step 5 [VERIFY]: Re-run the staleness grep**

```bash
grep -n "ANTHROPIC_API_KEY\|costs Anthropic tokens\|\$0\.50.*budget" devdocs/LAUNCH_CHECKLIST.md
```

Expected: empty (no live references; only the `EMAIL_LEGAL_FOOTER_ADDRESS` placeholder language survives, which is correct).

- [ ] **Step 6 [ENG]: Commit**

```bash
git add devdocs/LAUNCH_CHECKLIST.md
git commit -m "docs(checklist): scrub v1.2.5 LLM-cost language — eval is byte-exact + free now (PRD v1.2.6)

Drops the eval-bootstrap budget paragraph, the ANTHROPIC_API_KEY env
block, the LLM_*/RUN_BUDGET_* paste-in rows, and the 're-engagement
trigger that mentioned the Anthropic key. Replaces §6 (Phase 8) with
the v1.2.6 byte-exact regression-gate workflow.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 1.3: Refresh `devdocs/HANDOFF_PROMPT.md` §1 + §5

**Files:** Modify `devdocs/HANDOFF_PROMPT.md`

- [ ] **Step 1 [ENG]: Update the §1 verified-state table**

Find rows referencing 183 / 186 tests and replace `186 passed` (or `183 passed`) with `≥ 206 passed`.

Find any row mentioning the Anthropic SDK + replace with: `| LLM-touch | None — PRD v1.2.6 dropped api/llm.py and the anthropic SDK; every skill is deterministic |`.

- [ ] **Step 2 [ENG]: Drop the §5 provider/key conventions for ANTHROPIC_API_KEY / LLM_DEV_MODEL / LLM_SYNTH_MODEL / RUN_BUDGET_***

Find the table under `## 5 · Provider / key conventions for THIS repo` and delete those rows. Add a one-paragraph note above the table:

```markdown
**PRD v1.2.6:** This pack carries no LLM credential. The model-provider
boundary moved entirely to `/root/michealaai`. The env vars below are
the ONLY credentials the FastAPI service reads.
```

- [ ] **Step 3 [ENG]: Add a §1 row pointing at `everything-to-v1.0.0.md`**

In the §1 verified-state table, append:

```markdown
| Active plan | docs/superpowers/plans/2026-05-10-everything-to-v1.0.0.md (this file's parent plan; Phase 0 + 1 already executed at the time you read this) |
```

- [ ] **Step 4 [ENG]: Commit**

```bash
git add devdocs/HANDOFF_PROMPT.md
git commit -m "docs(handoff): drop v1.2.5 LLM env-var rows; bump test count; cite the active plan

Section 1 verified-state row count refreshed. Section 5 'Provider / key
conventions' loses ANTHROPIC/LLM_*/RUN_BUDGET_* — those moved to
/root/michealaai per PRD v1.2.6. New row pointing at the parent plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 1.4: Refresh `devdocs/CURRENT_STATE.md` §5 (tech stack)

**Files:** Modify `devdocs/CURRENT_STATE.md`

- [ ] **Step 1 [ENG]: Drop the LLM line from §5 tech stack table**

Find `| LLM         | Anthropic SDK (Sonnet 4.6 synth, Haiku 4.5 dev)                      |` and delete it. The skills-are-deterministic story already lives elsewhere in the doc.

- [ ] **Step 2 [ENG]: Update the "Dropped from earlier states" paragraph**

Find the paragraph beginning `Dropped from earlier states:` and append:

```markdown
PRD v1.2.6 (2026-05-10) further dropped: api/llm.py, the anthropic SDK,
ANTHROPIC_API_KEY, LLM_DEV_MODEL, LLM_SYNTH_MODEL, and the
RUN_BUDGET_USD/STEPS/SECONDS env vars. Skills are deterministic; LLM
calls live in /root/michealaai with Michaela's bench.
```

- [ ] **Step 3 [ENG]: Commit**

```bash
git add devdocs/CURRENT_STATE.md
git commit -m "docs(state): drop Anthropic-SDK row from §5 tech stack; cite v1.2.6 LLM rip-out

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 1.5: Verify the README + tasks/ + .env.production.example are aligned

**Files (read-only audit, fix if needed):**
- `README.md`
- `tasks/CONTRACTS.md`
- `.env.production.example`

- [ ] **Step 1 [ENG]: Grep each file for stale references**

```bash
grep -nE "ANTHROPIC_API_KEY|LLM_DEV_MODEL|LLM_SYNTH_MODEL|RUN_BUDGET_USD|run_budget" \
  README.md tasks/CONTRACTS.md .env.production.example
```

- [ ] **Step 2 [ENG]: For each hit:**
  - If the hit is in a "dropped vars" / changelog / "do NOT add back" comment, leave it.
  - If the hit is presented as a current/required env var, delete the line + add a one-line replacement comment noting v1.2.6 dropped it.

- [ ] **Step 3 [ENG]: Commit only if changes were needed**

```bash
git add -p README.md tasks/CONTRACTS.md .env.production.example
git commit -m "docs: drop live ANTHROPIC/LLM_*/RUN_BUDGET_* references (post-v1.2.6 audit)"
```

### Task 1.6: Comprehensive doc cleanup — old / redundant / poor [ENG]

**Goal:** beyond the v1.2.5 → v1.2.6 staleness sweep, take a quality pass on every long-form doc. Three orthogonal axes:

- **Old:** content describing retired sprints, deleted modules, removed env vars, abandoned approaches (e.g., Alembic, in-repo orchestration, the Hermes Python plugin that was replaced by MCP).
- **Redundant:** the same architectural fact repeated in 3+ docs (the 4-layer diagram, the bench list, the §11.1 rule). One canonical source per fact, every other reference points there.
- **Poor:** docs that grew without pruning, mixing current state with historical narrative; sections that no first-time reader would understand without context.

The cleanup target is one canonical answer to "what's true now," not a museum of every architectural decision the project has ever made.

#### 1.6a Plan archival

**Files:**
- Create: `docs/superpowers/plans/_archive/`
- Move: `docs/superpowers/plans/2026-05-10-finish-it-all.md` → `_archive/`
- Move: `docs/superpowers/plans/2026-05-10-frontend-cleanup-fixes.md` → `_archive/`
- Move: `docs/superpowers/plans/2026-05-10-skills-deterministic-only.md` → `_archive/`
- Create: `docs/superpowers/plans/README.md` (one-page index)

- [ ] **Step 1 [ENG]: Confirm each candidate plan is fully executed**

```bash
# All three should have most/all checkboxes ticked or commits cited.
grep -c '^\- \[x\]' docs/superpowers/plans/2026-05-10-finish-it-all.md
grep -c '^\- \[x\]' docs/superpowers/plans/2026-05-10-frontend-cleanup-fixes.md
grep -c '^\- \[x\]' docs/superpowers/plans/2026-05-10-skills-deterministic-only.md
```

If any has zero ticks but its outcome is verifiably shipped, that's fine — historical plans don't always get checkboxes ticked retroactively. Spot-check by reading the goal + verifying the listed commits are on `main`.

- [ ] **Step 2 [ENG]: Move them**

```bash
mkdir -p docs/superpowers/plans/_archive
git mv docs/superpowers/plans/2026-05-10-finish-it-all.md \
       docs/superpowers/plans/_archive/2026-05-10-finish-it-all.md
git mv docs/superpowers/plans/2026-05-10-frontend-cleanup-fixes.md \
       docs/superpowers/plans/_archive/2026-05-10-frontend-cleanup-fixes.md
git mv docs/superpowers/plans/2026-05-10-skills-deterministic-only.md \
       docs/superpowers/plans/_archive/2026-05-10-skills-deterministic-only.md
```

- [ ] **Step 3 [ENG]: Author `docs/superpowers/plans/README.md`**

```markdown
# Plans

Active plans live at this directory's root. Once a plan is fully
executed and its outcome is verifiably on `main`, move it to
`_archive/` so future agents reading the plan list see only what's
in flight.

## Active

- `2026-05-10-everything-to-v1.0.0.md` — drift cleanup + launch finish.
  This is the parent plan. When it's done, move it to `_archive/` and
  delete this README's bullet for it.

## Archived

See `_archive/`. Each archived plan is a historical record; do not edit.
```

- [ ] **Step 4 [ENG]: Commit**

```bash
git add docs/superpowers/plans/
git commit -m "docs(plans): archive executed plans; one-page index for the plans directory

Three plans are fully executed and on main: finish-it-all (most §5.14
+ launch-runway items shipped), frontend-cleanup-fixes (skeletons,
auth hardening, SSE polish), skills-deterministic-only (PRD v1.2.6
deterministic skill rewrite). Move to _archive/ so the active plans
directory shows only what's in flight.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

#### 1.6b devdocs/ audit + prune

For each devdocs file, run a fixed mini-audit and execute the verdict.

The verdict per file is one of:
- **KEEP** — accurate + readable + no overlap; leave alone
- **REFRESH** — stale content; rewrite the affected section in place
- **MERGE** — significant overlap with another doc; pick one canonical home, replace the other with a one-line pointer
- **ARCHIVE** — historically valuable but no longer load-bearing; move to `devdocs/_archive/` (note: that dir was deleted in commit `3288798`; recreate)
- **DELETE** — superseded entirely; remove

The audit lives below. After running each, commit per logical chunk so reverts are surgical.

##### Audit table — devdocs/

| File | Verdict | Rationale | Action |
|---|---|---|---|
| `CURRENT_STATE.md` | **REFRESH** | Single-page state-of-repo. Already updated for multi-Supabase + v1.2.6. §10 "Done" list has accumulated; "Next" needs to point only at things still owed. | Step 1 below |
| `HANDOFF_PROMPT.md` | **REFRESH (heavy prune)** | 1057 lines. Sections §8–§14 describe Sprints A–G, all of which are done. They were a menu for a fresh agent picking next-work; now they're history. Replace with a 1-paragraph "see PRD changelog + LAUNCH_CHECKLIST" pointer. | Step 2 below |
| `CAPABILITY_PACK_INTEGRATION.md` | **KEEP** | Cross-repo contract Michaela's side reads. Current. | No action. |
| `CAPABILITY_PACKS_CANVAS.md` | **KEEP-OR-MERGE** | Strategic horizon doc. Currently overlaps slightly with `V1_PRODUCT_ALIGNMENT.md`. Decide whether to merge in step 3 below. | Step 3 below |
| `MICHAELA_SYSTEM_MODEL.md` | **REFRESH** | Bench layer relationship. The bench-naming sweep in Phase 2.1 may have edited this; otherwise check that worker descriptions match Michaela's runtime introduction (deepseek-v4-pro primary; CEO model). | Step 4 below |
| `V1_PRODUCT_ALIGNMENT.md` | **KEEP** | Public-framing filter; tight + intentional. Spot-check only. | No action unless §1.5 grep finds banned terms. |
| `HERMES_LINK.md` | **KEEP** (created in Phase 3) | New canonical doc for the integration. | No action. |
| `LAUNCH_CHECKLIST.md` | **KEEP** (already refreshed in 1.2) | The operational checklist. | No action. |

##### Step 1: Refresh `devdocs/CURRENT_STATE.md` §10

- [ ] Read §10 "What ships today vs. what's next"
- [ ] Move every "Done" bullet that's been verified into a one-paragraph "Shipped to v1.0.0" summary. Keep individual commit citations only for items where the commit hash is genuinely useful for debugging.
- [ ] Reduce "Next" to a 4–6 line list that mirrors LAUNCH_CHECKLIST §0 status snapshot. Don't duplicate detail; cite the checklist.
- [ ] Verify §6 (data model) reflects the v1.2.6 schema (api_keys, competitor_history, weekly_opportunity_*) but doesn't re-list every column — that's what `supabase/migrations/` is for.
- [ ] Commit:

```bash
git add devdocs/CURRENT_STATE.md
git commit -m "docs(state): tighten §10 — collapse 'Done' history; trim 'Next' to 4 lines

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

##### Step 2: Heavy prune of `devdocs/HANDOFF_PROMPT.md`

- [ ] **Step 2.1 [ENG]: Delete §8–§14 (Sprint A through G specs)**

These were the "next-sprint menu" for picking work. Sprints A, B, C, E, F, G are done; D is in-flight as Phase 5c. Replace the entire block (`## 8 · Sprint A` through the end of `## 14 · Sprint G`) with:

```markdown
## 8 · Active work

The active plan is `docs/superpowers/plans/2026-05-10-everything-to-v1.0.0.md`.
Sprint-specific menus that previously lived in §§8–14 of this file
are archived in commit history; their outcomes shipped in commits
listed under `devdocs/CURRENT_STATE.md` §10.
```

- [ ] **Step 2.2 [ENG]: Compress §16 (verification gates)**

The eight gates (GL1–GL8) are still useful but the per-sprint gates underneath them are now stale. Keep GL1–GL8; delete the per-sprint subsections.

- [ ] **Step 2.3 [ENG]: Update §17 (ask-first triggers)**

Drop trigger #11 ("Removing DEMO_* from anywhere they still appear") — they're already removed and not coming back. Trigger #2 (branching strategy) is now settled by the standing direct-to-main authorization. Keep the rest.

- [ ] **Step 2.4 [ENG]: Update §18 (risk register)**

R1 (concurrent edits) is still active; keep. R2 (Hermes plugin spec drift) is moot — plugin replaced by MCP; delete. R3 (web UI without orchestrator) is mitigated by the SSE stub; rephrase. R4–R10 most still apply; spot-edit.

- [ ] **Step 2.5 [VERIFY]: After prune, `wc -l devdocs/HANDOFF_PROMPT.md` should drop from ~1057 to ~400.**

- [ ] **Step 2.6 [ENG]: Commit**

```bash
git add devdocs/HANDOFF_PROMPT.md
git commit -m "docs(handoff): heavy prune — drop Sprint A-G specs (all shipped); trim verification + ask-first + risk sections

Sprint-specific menus belonged to a 2-week-old planning posture;
they're now history. Active work lives in
docs/superpowers/plans/2026-05-10-everything-to-v1.0.0.md. Verification
gates GL1-GL8 retained; per-sprint gates deleted. Drops ~600 lines.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

##### Step 3: Decide on `CAPABILITY_PACKS_CANVAS.md` ↔ `V1_PRODUCT_ALIGNMENT.md`

- [ ] **Step 3.1 [ENG]: Read both files in full**

```bash
wc -l devdocs/CAPABILITY_PACKS_CANVAS.md devdocs/V1_PRODUCT_ALIGNMENT.md
diff <(grep '^#' devdocs/CAPABILITY_PACKS_CANVAS.md) <(grep '^#' devdocs/V1_PRODUCT_ALIGNMENT.md)
```

- [ ] **Step 3.2 [ENG]: Decide**

| Outcome | Action |
|---|---|
| Both add unique value (canvas = strategic horizon, alignment = public-framing filter) | **KEEP both.** Add a one-line pointer at the top of each: "See ALIGNMENT.md for public-framing rules; see CANVAS.md for the multi-pack horizon." |
| Significant overlap (≥ 30% of headlines duplicated) | **MERGE into V1_PRODUCT_ALIGNMENT.md.** Title becomes "Product Alignment + Strategic Horizon"; CANVAS.md becomes a one-line redirect. |
| CANVAS.md is mostly aspirational about packs we're not building | **ARCHIVE CANVAS.md** to `devdocs/_archive/`; delete is fine since git history retains it. |

- [ ] **Step 3.3 [ENG]: Execute the chosen verdict + commit**

##### Step 4: Refresh `MICHAELA_SYSTEM_MODEL.md`

- [ ] **Step 4.1 [ENG]: Read top + bottom of file**

```bash
head -60 devdocs/MICHAELA_SYSTEM_MODEL.md
tail -60 devdocs/MICHAELA_SYSTEM_MODEL.md
```

- [ ] **Step 4.2 [ENG]: Verify against Michaela's actual runtime intro from this session's transcript**

Spot-check: Hermes v0.13.0; primary model deepseek-v4-pro; bench naming matches the Phase 2.1 choice; `~/.hermes/skills/samrail/` has 8 entries (5 from this repo + 3 orchestration recipes she owns).

- [ ] **Step 4.3 [ENG]: Patch any drift in place**

The doc may say "Anthropic Sonnet" in the model section — replace with "DeepSeek primary, Anthropic fallback (per Michaela's `~/.hermes/config.yaml`)". Bench names per Phase 2.1.

- [ ] **Step 4.4 [ENG]: Commit**

```bash
git add devdocs/MICHAELA_SYSTEM_MODEL.md
git commit -m "docs(michaela): refresh runtime details — DeepSeek primary; bench-naming sync

Aligns with Michaela's actual self-introduction (Hermes v0.13.0,
deepseek-v4-pro primary, Anthropic fallback, bench per Phase 2.1's
canon).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

#### 1.6c Top-level docs audit + prune

| File | Verdict | Action |
|---|---|---|
| `README.md` | **REFRESH** | Top-level entry point. Verify the install + run commands work post-v1.2.6 (`uv sync`, `uv run uvicorn`, etc). Drop any lines mentioning Anthropic / LLM_DEV_MODEL / RUN_BUDGET. | Step 1 below |
| `HERMES.md` | **KEEP** | Short doc about pointing HERMES_HOME at this repo's `.hermes/` for testing. Spot-check that the 5 SKILL.md files listed match what's on disk. | Step 2 below |
| `tasks/README.md` | **REFRESH** | Build-plan index. The "frozen decisions" table is post-it for newcomers; verify it's current. The decision log at the bottom may have grown; trim entries older than 30 days. | Step 3 below |
| `tasks/CONTRACTS.md` | **REFRESH** | Schemas, SSE, env contract, skill registry. Likely has stale env section + needs the §5.14 routes added to §6 if not already. | Step 4 below |
| `tasks/FIXTURES.md` | **KEEP** (verify) | Fixture content spec. Should match the 4 fixtures + the eval_inputs blocks we authored. | Step 5 below |
| `tasks/LANDING_BRIEF.md` | **KEEP** (verify) | Marketing copy brief. Spot-check brand-string consistency. | Step 6 below |

##### Step 1: Refresh `README.md`

- [ ] **Step 1.1 [ENG]: Read it end-to-end**

```bash
cat README.md
```

- [ ] **Step 1.2 [ENG]: Verify each install/run command actually works on a clean checkout**

```bash
# Set up a fresh worktree, clone, and run the README's commands.
# If anything errors, fix the README — not the command.
```

- [ ] **Step 1.3 [ENG]: Drop stale env-var mentions**

If the README lists `ANTHROPIC_API_KEY`, `LLM_DEV_MODEL`, `LLM_SYNTH_MODEL`, `RUN_BUDGET_*`, or `HERMES_HOME`/`HERMES_MODEL` in a "required" or "set this" context, delete those lines. Keep them only in a "previously, no longer required as of v1.2.6" footnote if useful.

- [ ] **Step 1.4 [ENG]: Verify the validation block is post-v1.2.6**

```bash
grep -A 12 "## Validation" README.md
```

The block should NOT include any LLM-cost commands. If it includes `uv run pytest api/tests/`, it should now say "≥ 206 passed" not "≥ 113 passed".

- [ ] **Step 1.5 [ENG]: Commit**

```bash
git add README.md
git commit -m "docs(readme): post-v1.2.6 cleanup — drop ANTHROPIC/LLM_*/RUN_BUDGET; bump test count

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

##### Step 2: Spot-check `HERMES.md`

- [ ] **Step 2.1 [ENG]: Verify the SKILL.md list matches `.hermes/skills/samrail/`**

```bash
ls .hermes/skills/samrail/
grep -E "extract_requirements_with_evidence|score_fit_with_eligibility_check|detect_risks_calibrated|generate_full_action_package|generate_reject_summary" HERMES.md | wc -l
```

Expected: `5` (one mention each).

- [ ] **Step 2.2 [ENG]: Cross-link to HERMES_LINK.md**

Add a one-line pointer near the top:

```markdown
> For wiring this pack into a real Hermes runtime (Michaela's host or
> any other), see `devdocs/HERMES_LINK.md`. This file documents only
> the dev-time `HERMES_HOME=$(pwd)/.hermes hermes` testing pattern.
```

- [ ] **Step 2.3 [ENG]: Commit**

```bash
git add HERMES.md
git commit -m "docs(hermes): cross-link to HERMES_LINK.md for the production-wiring story"
```

##### Step 3: Refresh `tasks/README.md`

- [ ] **Step 3.1 [ENG]: Verify the layout block matches reality**

```bash
ls tasks/
```

The layout in the doc should list only the files that exist (CONTRACTS, FIXTURES, LANDING_BRIEF, README — DEMO and INTERFERENCE_MAP are gone per commit `3288798`).

- [ ] **Step 3.2 [ENG]: Trim the decision log**

The decision log at the bottom of the file may carry entries older than 30 days that are now uninteresting. Move pre-2026-05-09 entries into a one-paragraph summary.

- [ ] **Step 3.3 [ENG]: Commit**

```bash
git add tasks/README.md
git commit -m "docs(tasks): trim decision log; verify layout block matches disk"
```

##### Step 4: Refresh `tasks/CONTRACTS.md`

- [ ] **Step 4.1 [ENG]: Audit each section**

```bash
grep -nE '^## ' tasks/CONTRACTS.md
```

For each section:
- §1 (intro) — KEEP
- §2 (schemas) — verify the JSON Schema list matches `schemas/*.schema.json`
- §3 (trace events) — single source of truth; verify 8 event types match `schemas/trace-event.schema.json`
- §4 (env contract) — DROP ANTHROPIC/LLM_*/RUN_BUDGET; ADD §5.14 RESEND_*/EMAIL_* if missing
- §5 (skill registry) — verify 11 skills listed
- §6 (route registry) — verify 53+ routes listed including §5.14 routes

- [ ] **Step 4.2 [ENG]: Patch each in place**

Use `Edit` calls; commit per section.

##### Step 5–6: Spot-check `tasks/FIXTURES.md` and `tasks/LANDING_BRIEF.md`

- [ ] **Step 5.1 [ENG]: FIXTURES — read + verify**

```bash
diff <(ls fixtures/ | grep -v _template) \
     <(grep -E '^- ' tasks/FIXTURES.md | head -10)
```

If the doc lists 4 fixtures matching disk, KEEP. Otherwise patch.

- [ ] **Step 6.1 [ENG]: LANDING_BRIEF — banned-terms grep**

```bash
grep -nE '(compliance automation|agent platform|capture agent)' tasks/LANDING_BRIEF.md
```

Expected: empty. If a hit, fix per `devdocs/V1_PRODUCT_ALIGNMENT.md` voice rules.

- [ ] **Step 5/6 [ENG]: Commit any patches**

```bash
git add -p tasks/FIXTURES.md tasks/LANDING_BRIEF.md
git commit -m "docs(tasks): spot-check fixtures + landing brief"
```

#### 1.6d Final all-pass

- [ ] **Step 1 [ENG]: Total line-count delta**

```bash
git diff --stat docs/superpowers/plans/_archive/2026-05-10-finish-it-all.md \
                docs/superpowers/plans/_archive/2026-05-10-frontend-cleanup-fixes.md \
                docs/superpowers/plans/_archive/2026-05-10-skills-deterministic-only.md \
                devdocs/HANDOFF_PROMPT.md devdocs/CURRENT_STATE.md \
                README.md tasks/README.md tasks/CONTRACTS.md
```

Expected: net negative (we deleted more than we added).

- [ ] **Step 2 [ENG]: Sweep for the last v1.2.5 references**

```bash
grep -rn "PRD v1\.2\.5\b" devdocs/ tasks/ README.md HERMES.md \
  --include='*.md' \
  | grep -v _archive \
  | grep -vE "deprecat|v1\.2\.5 →|v1\.2\.5 →"
```

Expected: empty (every live mention should be either v1.2.6 or a changelog deprecation note).

- [ ] **Step 3 [ENG]: Push**

```bash
git push origin main
```

### Phase 1 verification gate

- [ ] `grep -rn "ANTHROPIC_API_KEY" devdocs/ tasks/ README.md .env.production.example | grep -v _archive | grep -v -i "dropped\|removed\|no longer"` → empty
- [ ] `grep -rn "make eval-bootstrap.*\\\$0\\.[3-7]0" devdocs/` → empty
- [ ] `wc -l devdocs/HANDOFF_PROMPT.md` returns ≤ 500
- [ ] `docs/superpowers/plans/` shows only `everything-to-v1.0.0.md` + `README.md` at root; everything else under `_archive/`
- [ ] `git status --short` → clean
- [ ] All Phase 1 commits pushed (`git push origin main`)

---

## Phase 2 — Bench naming + Supabase risk verifications [USER decision + 5-min Studio check]

**Goal:** resolve the two outstanding drift items the user must decide.

### Task 2.1: Bench naming — pick a canon [USER DECISION ONLY]

The repo's PRD/CURRENT_STATE/HANDOFF/score_fit-prompt all say **Gate** (eligibility) and **Ledger** (competitive intel). Michaela's runtime introduces her bench as **Gabby** and **Lance**. Both can't be canonical.

- [ ] **Step 1 [USER]: Pick one**

Three options:

| Choice | Implication | Effort |
|---|---|---|
| A — Repo follows Michaela: rename Gate → Gabby, Ledger → Lance | Friendlier names; matches what users hear from her in chat | ~30 min sweep across PRD, CURRENT_STATE, HANDOFF, MICHAELA_SYSTEM_MODEL, V1_PRODUCT_ALIGNMENT, HERMES.md, tasks/CONTRACTS, score_fit prompt.txt, detect_risks prompt.txt |
| B — Michaela follows the repo: rename Gabby → Gate, Lance → Ledger in `/root/michealaai` | Keeps PRD as canon; cross-repo work | Cross-repo |
| C — Both retain, document the alias | Weakest option; future drift inevitable | Light doc edits, ongoing confusion |

**Recommendation:** A. Michaela's runtime is what users encounter; the repo docs are internal. Renaming the repo is reversible; renaming a running agent's persona memory is not.

- [ ] **Step 2 [USER]: Tell me the choice**

> "Bench naming: pick A (rename in repo to Gabby/Lance), B (rename Michaela), or C (alias both)."

- [ ] **Step 3 [ENG, ON CHOICE A]: Sweep the rename**

```bash
# Files where Gate/Ledger appear as bench-role labels (not as English words):
grep -rln "\bGate\b.*eligibility\|\bLedger\b.*competitive" PRD.md devdocs/ tasks/ HERMES.md README.md api/skills/score_fit/prompt.txt api/skills/detect_risks/prompt.txt
```

For each file, replace `Gate` → `Gabby` (eligibility owner) and `Ledger` → `Lance` (competitive intel owner). Use `Edit` (not Write) and verify each replacement is in a context that's specifically a bench reference (not the English word "gate" / "ledger" / "gateway").

After sweep:

```bash
# Old names should appear ONLY in PRD changelog deprecation notes + _archive.
grep -rn "\bGate\b\|\bLedger\b" PRD.md devdocs/ tasks/ HERMES.md README.md \
  | grep -v _archive \
  | grep -vE "deprecat|legacy|formerly|renamed"
```

Expected: empty.

- [ ] **Step 4 [ENG, ON CHOICE A]: Add a PRD changelog deprecation note**

Append to `PRD.md` changelog under v1.2.6:

```markdown
- 2026-05-10 — Bench naming aligned with Michaela's runtime: Gate → Gabby
  (eligibility), Ledger → Lance (competitive intel). The other four
  workers (Scot, Lenny, Happer, Roy) and Michaela the orchestrator
  unchanged. Old names retained only in this changelog.
```

- [ ] **Step 5 [ENG, ON CHOICE A]: Run all-suite + commit**

```bash
uv run pytest api/tests/ -q
make eval
npm -w web run typecheck && npm -w landing run build && npm -w web run build
git add -A PRD.md devdocs/ tasks/ HERMES.md README.md api/skills/
git commit -m "docs+prompts: rename bench Gate→Gabby, Ledger→Lance (PRD v1.2.6)

Aligns the repo with Michaela's runtime persona. Old names retained
only in the PRD changelog deprecation note.

Files swept: PRD.md, devdocs/CURRENT_STATE.md, devdocs/HANDOFF_PROMPT.md,
devdocs/MICHAELA_SYSTEM_MODEL.md, devdocs/V1_PRODUCT_ALIGNMENT.md,
HERMES.md, README.md, tasks/CONTRACTS.md, api/skills/score_fit/prompt.txt,
api/skills/detect_risks/prompt.txt.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 2.2: Storage bucket privacy — 5-min Studio check [USER]

- [ ] **Step 1 [USER]: Open Supabase Studio for `vvyxjdoenjujkxwbnzyl`**

Navigate to: **Storage → Buckets**.

- [ ] **Step 2 [USER]: Verify each bucket's `Public` flag**

| Bucket | Required state |
|---|---|
| `govcapture-attachments` | **Public: OFF** (private) |
| `persona-assets` | Public: ON (this is the persona project's, intentional) |

- [ ] **Step 3 [USER]: If `govcapture-attachments` shows Public: ON**, click into it → Settings → toggle off → Save. Then in `tasks/CONTRACTS.md` add a one-line incident note dated today.

- [ ] **Step 4 [USER]: Tell me the result**

> "Bucket privacy verified" or "Found public; flipped private; logging incident."

- [ ] **Step 5 [ENG, ON FOUND-PUBLIC]: Append to `tasks/CONTRACTS.md` an incident-log line + commit**

### Task 2.3: Schema collision spot-check on `vvyxjdoenjujkxwbnzyl` [USER]

The persona project documents tables `personas`, `persona_*`, `agent_actions`, `social_threads`, etc. on the same Supabase project as our pack. The user's note also lists `agent_runs` under the persona table set — same name as ours.

- [ ] **Step 1 [USER]: In Supabase Studio for `vvyxjdoenjujkxwbnzyl` → Database → Tables**

Compare to the migrations in this repo:

```bash
ls supabase/migrations/
```

Note any `public.<table>` that exists in Studio but does NOT come from a file in `supabase/migrations/`. Those are persona's. Note any naming overlap (`agent_runs` is the most likely candidate).

- [ ] **Step 2 [USER]: For each overlap, click into the table → SQL editor → run**

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'agent_runs'
ORDER BY ordinal_position;
```

Compare the columns to `supabase/migrations/20260509132830_create_govcon_core.sql`'s CREATE TABLE statement.

- [ ] **Step 3 [USER]: Tell me the result**

Three possible outcomes:

| Outcome | Action |
|---|---|
| `agent_runs` columns match our migration exactly | No issue. Document the cohabitation in `tasks/CONTRACTS.md` and move on. |
| `agent_runs` has extra columns we don't know about | Coordinate with persona project owner; do not drop anything. Document. |
| `agent_runs` has missing columns or wrong types | Real conflict. Coordinate before any production write. |

- [ ] **Step 4 [ENG, ON OUTCOMES 1 OR 2]: Append to `tasks/CONTRACTS.md` a "schema cohabitation" note + commit**

### Phase 2 verification gate

- [ ] Bench-naming choice made and (if A) swept and committed
- [ ] Storage bucket privacy verified
- [ ] Schema collision check completed; results documented
- [ ] All resulting commits pushed (`git push origin main`)

---

## Phase 3 — HERMES_LINK.md doc + cross-repo coordination handoff [ENG]

**Goal:** commit a permanent doc with the exact steps to wire this pack into Michaela's running Hermes (so the next agent or you in three weeks doesn't re-derive it).

### Task 3.1: Author `devdocs/HERMES_LINK.md`

**Files:**
- Create: `devdocs/HERMES_LINK.md`

- [ ] **Step 1 [ENG]: Author the file**

Content (verbatim — every step from the recent conversation, plus the cross-repo + Sprint G coordination notes):

````markdown
# Wiring this pack into Hermes

Last session's authoritative answer compressed into one durable doc.
The two artifacts Michaela's host needs are (1) the
`mcp-server-samrail` Python package from `mcp_server_samrail/`,
and (2) two keys in `~/.hermes/config.yaml`. Source of authority for
the integration shape: PRD §5.14, `devdocs/CAPABILITY_PACK_INTEGRATION.md`.

## On Michaela's host (Ubuntu 24.04, hostname `govcon`)

```bash
# 1. Hermes MCP extra (one-time)
cd /usr/local/lib/hermes-agent
uv pip install -e ".[mcp]"

# 2. This pack's MCP server
pip install --user "git+https://github.com/caterpillarC15/govcon.git#subdirectory=mcp_server_samrail"
which mcp-server-samrail   # should resolve
```

## `~/.hermes/config.yaml` on her host

```yaml
mcp_servers:
  govcapture:
    command: "mcp-server-samrail"
    env:
      GOVCAPTURE_API_BASE: "https://api.<your-domain>"
      GOVCAPTURE_API_KEY: "gck_..."

skills:
  external_dirs:
    - /opt/govcapture-pack/.hermes/skills
```

`gck_…` is minted at `/web → /app/keys` (`POST /api/keys` with a
Supabase JWT also works). The `external_dirs` entry exposes our 5
SKILL.md tool-procedure files (`extract_requirements_with_evidence`,
`score_fit_with_eligibility_check`, `detect_risks_calibrated`,
`generate_full_action_package`, `generate_reject_summary`) without
copying them.

## In her CLI

```
hermes
> /reload-mcp
> /skills
```

`/skills` should list the 5 govcapture procedures. The tool registry
should include 11 entries prefixed `mcp_govcapture_*` (one per
`/api/v1/tools/<name>`).

Smoke test:

```
> /tool mcp_govcapture_parse_goal {"goal":"find SOC contracts in next 60 days","company_profile":{"naics_codes":["541512"]}}
```

Expected: `{"data": {...}}` (no `metrics` field — PRD v1.2.6 dropped
it for non-LLM skills, which is now all of them).

## Network layout

```
Michaela (Hermes v0.13.0, Ubuntu, DeepSeek)
  │  MCP / stdio
  ▼
mcp-server-samrail (Python pkg from this repo, on her box)
  │  HTTPS + Authorization: Bearer gck_…
  ▼
FastAPI /api/v1/tools/<name> (this repo, VX1 prod or local + ngrok)
  │
  ▼
Supabase (vvyxjdoenjujkxwbnzyl) / Redis / fixtures
```

The MCP server is the bridge; the HTTP API is the contract; the `gck_`
key is the auth. She doesn't need source access to this repo.

## Cross-repo coordination owed by `/root/michealaai`

Per `devdocs/CAPABILITY_PACK_INTEGRATION.md` "Three Supabase projects":

1. **Update `/root/michealaai/DATA-SOURCES.md`** to distinguish:
   - `ktygrvbpugqhfyibzirr` — Lance's competitive-intel reads
     (agencies, contractors, contracts, psc_win_patterns,
     customer_profiles)
   - `vvyxjdoenjujkxwbnzyl` — `agent_runs` pickup + writebacks
     (this pack's project; `INTERNAL_API_KEY` writes land here)

   Without this, Michaela polling the wrong project will silently never
   see our `POST /agent-runs` rows.

2. **Mirror `INTERNAL_API_KEY`** between `/opt/govcapture/.env` (VX1
   prod) and `/root/michealaai`'s env on her host. Same string both
   sides, generated once with `openssl rand -hex 32`. The pack's
   `require_internal_actor` rejects mismatches with 401.
````

- [ ] **Step 2 [ENG]: Verify the file is well-formed**

```bash
test -f devdocs/HERMES_LINK.md && wc -l devdocs/HERMES_LINK.md
```

Expected: file exists with ≥ 70 lines.

- [ ] **Step 3 [ENG]: Commit**

```bash
git add devdocs/HERMES_LINK.md
git commit -m "docs: HERMES_LINK.md — concrete steps to wire this pack into Michaela's Hermes

Captures the answer derived in this session: install mcp-server-samrail
on Michaela's host, add two keys to ~/.hermes/config.yaml, mint a gck_
key, /reload-mcp, smoke-test. Plus the cross-repo coordination owed by
/root/michealaai (DATA-SOURCES.md fix + INTERNAL_API_KEY mirror).

Source: NousResearch/hermes-agent docs (MCP integration + skills system),
verified against the .hermes/config.yaml schema in this repo.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 4 [ENG]: Push**

```bash
git push origin main
```

### Phase 3 verification gate

- [ ] `devdocs/HERMES_LINK.md` exists on `origin/main`
- [ ] `grep -l HERMES_LINK devdocs/CURRENT_STATE.md devdocs/HANDOFF_PROMPT.md` (optional cross-link — leave alone if dirty)

---

## Phase 4 — Sprint G stub verification [ENG]

**Goal:** prove the SSE pipeline (Redis → FastAPI SSE proxy → /web EventSource) works end-to-end against a local stack, without depending on `/root/michealaai`. This was the R3 mitigation in `devdocs/HANDOFF_PROMPT.md` §10. The stub publisher is already shipped; we just haven't run it through `/web` yet.

### Task 4.1: Bring the local stack up

- [ ] **Step 1 [ENG]: Start Redis**

```bash
make services-up
redis-cli ping   # PONG
```

- [ ] **Step 2 [ENG]: Start FastAPI in a background terminal**

```bash
uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 &
sleep 3
curl -s http://127.0.0.1:8000/healthz
```

Expected: `{"status":"ok",…}` with supabase + redis green.

- [ ] **Step 3 [USER]: Start `/web` in a separate terminal**

```bash
npm -w web run dev   # http://localhost:3001
```

### Task 4.2: Trigger a real run from `/web` and replay events

- [ ] **Step 1 [USER]: Sign in via magic link at http://localhost:3001/login**

(Default Supabase SMTP delivers the magic link — fine for dev.)

- [ ] **Step 2 [USER]: Submit a goal at `/app/goal`**

Note the run-uuid in the URL after the redirect to `/app/runs/<uuid>`.

- [ ] **Step 3 [USER]: Replay events**

```bash
make sse-stub RUN_ID=<run-uuid> DELAY_MS=500
```

Expected output:

```
Publishing 20 events to agent-run:<uuid> on redis://localhost:6379/0
Cadence: 500ms between events; total ~10.0s
  [ 1/20] run_started …
  [ 2/20] step_started Search opportunities
  …
  [20/20] run_completed complete
```

- [ ] **Step 4 [VERIFY]: Watch `/app/runs/<uuid>` populate live**

In the browser, the timeline should show:
- Run started indicator
- 4 steps (Search opportunities → Parse PDF → Score fit → Generate package)
- needs_human banner appears mid-run
- Completion badge with the summary line

If any step doesn't render: open DevTools Network → confirm one (and ONLY one) `/api/run-stream/<uuid>` connection. The dedupe-on-step_id fix from `0f03693` should prevent doubled rows under React Strict Mode.

### Task 4.3: Update the integration doc with verification status

**Files:** Modify `devdocs/CAPABILITY_PACK_INTEGRATION.md` § "Known unknowns"

- [ ] **Step 1 [ENG]: Flip the relevant rows in the Known-unknowns table**

Find the table at the bottom of the file and update:

```markdown
| TraceEvent emission to Redis `agent-run:{run_id}` | SSE forwarder live | **stub-verified 2026-MM-DD** | A real run produces `run_started` + ≥1 `tool_*` + `run_completed` events on the channel — verified via `make sse-stub` |
```

Other rows that depend on the live orchestrator (`agent_runs poll loop`, `crash recovery`) stay `unknown` since they need `/root/michealaai`.

- [ ] **Step 2 [ENG]: Commit**

```bash
git add devdocs/CAPABILITY_PACK_INTEGRATION.md
git commit -m "docs(integration): SSE pipeline stub-verified end-to-end (Phase 4 of everything plan)

Redis publish → FastAPI /agent-runs/{id}/stream → /web RunTimeline
verified via scripts/sse_stub_publisher.py. The orchestrator-side
verification (real agent_runs poll loop) still owed by /root/michealaai.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 4.4: Tear down

- [ ] **Step 1 [USER]: Stop the dev servers**

```bash
# Ctrl-C the foreground npm run dev
kill %1   # the backgrounded uvicorn
make services-down  # optional — leave Redis up if you want
```

### Phase 4 verification gate

- [ ] All 20 events published; ≥ 19 received in the browser
- [ ] All 8 distinct event types rendered in the timeline
- [ ] No duplicate rows under React Strict Mode
- [ ] CAPABILITY_PACK_INTEGRATION.md "Known unknowns" updated and committed

---

## Phase 5 — External-credential phases [USER]

**Goal:** the LAUNCH_CHECKLIST already documents these in detail; this phase is just the dependency-graph + the "ask me to resume" trigger phrases.

```
5a Resend SMTP (Channel A, magic-link)  ──┐
                                          ├── 5c VX1 deploy ── 5d Sprint G real
5b §5.14 production-flip (Channel B) ─────┘
```

### Task 5.1: Resend SMTP for Channel A magic-link [USER]

Run `devdocs/LAUNCH_CHECKLIST.md` §3 verbatim. When done, tell me:

> "Phase 5a done — Resend SMTP wired in Studio."

I'll run the smoke test: request a magic link from a clean Gmail or Outlook, confirm it arrives from `noreply@<your-domain>` and the magic link works.

### Task 5.2: §5.14 production-flip [USER]

Run `devdocs/LAUNCH_CHECKLIST.md` §9 verbatim. The 6-step sequence:

1. Set `RESEND_API_KEY`, `EMAIL_UNSUBSCRIBE_SECRET`, `EMAIL_LEGAL_FOOTER_ADDRESS` in VX1 `.env`.
2. With `EMAIL_DRY_RUN=true`, trigger the auto-pick cron route → verify pick row.
3. Trigger the send cron route → verify dry_run log rows.
4. Flip `EMAIL_DRY_RUN=false`, restart `govcapture-api.service`.
5. Self-test send (set yourself as sole eligible subscriber).
6. Re-enable other subscribers + enable both timers.

When done: "Phase 5b done — §5.14 sending live."

### Task 5.3: VX1 production deploy [USER]

Run `devdocs/LAUNCH_CHECKLIST.md` §4 verbatim. 8 steps from `infra/RUNBOOK.md` §0–§8. Approximately 4–8 contiguous hours.

When done: "Phase 5c done — VX1 at https://api.<your-domain>."

### Task 5.4: Sprint G real verification [USER + ENG]

Per `devdocs/LAUNCH_CHECKLIST.md` §5 (option 7-real). Once `/root/michealaai`'s `DATA-SOURCES.md` is updated (per Phase 3.1's HERMES_LINK.md guidance) and `INTERNAL_API_KEY` is mirrored, trigger a real run from prod `/web` and watch the orchestrator pick it up.

When done: "Phase 5d done — real run verified end-to-end."

I will then flip the remaining "Known unknowns" rows in `CAPABILITY_PACK_INTEGRATION.md` to verified, commit, and we move to Phase 6.

### Phase 5 verification gate

- [ ] Magic link arrives from `noreply@<your-domain>` (not Supabase shared SMTP) on Gmail + Outlook
- [ ] §5.14 first real send delivered + recorded in `weekly_opportunity_email_log` with `status='sent'`
- [ ] `https://api.<your-domain>/healthz` 200 from outside the box
- [ ] Real `agent_runs` row claimed by Michaela within ≤ 5 s; full SSE timeline; `action_packages` row created with correct `owner_profile_id`
- [ ] `INTERNAL_API_KEY` mirrored across both repos
- [ ] All "Known unknowns" rows in `CAPABILITY_PACK_INTEGRATION.md` flipped to verified

---

## Phase 6 — v1.0.0 tag [ENG]

**Goal:** annotated tag on `main`, all-suite gates green, release notes on the changelog.

### Task 6.1: Final all-suite verification

- [ ] **Step 1 [ENG]: Backend gates**

```bash
uv run pytest api/tests/ -q                          # ≥ 206 passed
uv run ruff check api && uv run mypy api             # both clean
make fixtures-validate                               # OK for all 4 fixtures
make eval                                            # PASS (byte-exact)
```

- [ ] **Step 2 [ENG]: Frontend gates**

```bash
npm -w landing run lint && npm -w landing run build
npm -w web run lint && npm -w web run typecheck && npm -w web run build
```

- [ ] **Step 3 [ENG]: Production smoke**

```bash
curl -s https://api.<your-domain>/healthz
curl -s https://api.<your-domain>/.well-known/agent.json | jq .
```

- [ ] **Step 4 [ENG]: Schema parity**

```bash
supabase migration list
```

Expected: every row local + remote.

- [ ] **Step 5 [ENG]: Old-name scan**

```bash
# Whatever the bench-naming choice was in Phase 2:
# - If A: old names should appear ONLY in PRD changelog deprecation note
# - If B: same, but reversed
grep -rnE '<old-bench-names>' --exclude-dir=_archive --exclude-dir=node_modules \
  --exclude-dir=.venv --exclude-dir=.next --exclude-dir=dist .
```

- [ ] **Step 6 [ENG]: api/agent/ stays out**

```bash
find api/agent -type f 2>/dev/null
grep -rnE 'from api\.agent' api/
```

Both expected empty.

### Task 6.2: Release-notes commit + tag

**Files:**
- Modify: `PRD.md` (append v1.0.0 release entry to changelog)
- Modify: `devdocs/CURRENT_STATE.md` §9 timeline + §10 done list
- Modify: `devdocs/HANDOFF_PROMPT.md` §1 + §7

- [ ] **Step 1 [ENG]: Append to PRD changelog**

```markdown
## v1.0.0 — 2026-MM-DD

First public release. Schema reconciled, VX1 prod live, cross-repo
e2e verified against /root/michealaai, eval gate live (byte-exact
deterministic), production email via Resend, mobile + a11y +
copy-aligned with V1_PRODUCT_ALIGNMENT.

Stack frozen at this tag:
- Pack: 11 deterministic skills, 53+ routes, 206+ tests, ruff/mypy clean
- Email: §5.14 weekly opportunity (Resend HTTP) + Channel A magic-link (Resend SMTP)
- Hosting: Vultr VX1 (FastAPI + nginx + Redis) + Vercel (/web + /landing) + Supabase
- Bench: Michaela + 6 workers in /root/michealaai (separate repo)
```

- [ ] **Step 2 [ENG]: Update §10 of CURRENT_STATE**

Append a "Released" entry to the §9 timeline + drop everything from "Next" that's now done.

- [ ] **Step 3 [ENG]: Update HANDOFF §7**

Mark every row done.

- [ ] **Step 4 [ENG]: Commit + tag**

```bash
git add PRD.md devdocs/CURRENT_STATE.md devdocs/HANDOFF_PROMPT.md
git commit -m "docs(release): v1.0.0 — first public release

See PRD changelog and CURRENT_STATE §10 for state at this tag.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"

git tag -a v1.0.0 -m "SamRail v1.0.0 — first public release.

See PRD.md changelog and devdocs/CURRENT_STATE.md for the full state
at this tag."

git push origin main --follow-tags
```

- [ ] **Step 5 [VERIFY]: Tag visible**

```bash
git tag --list | grep v1.0.0
gh api repos/caterpillarC15/govcon/git/refs/tags/v1.0.0 | jq .object.sha
```

### Task 6.3: Cross-repo signal

- [ ] **Step 1 [USER]: In `/root/michealaai`, drop a CHANGELOG entry pinning v1.0.0 as the integration target.**

(Cross-repo; can't do from here.)

### Phase 6 verification gate

- [ ] All Phase 0–5 gates green
- [ ] `git tag --list` includes `v1.0.0`
- [ ] PRD changelog has v1.0.0 entry
- [ ] `https://api.<your-domain>/healthz` still 200
- [ ] `gh api …/refs/tags/v1.0.0` resolves

---

## Re-engagement script

Drop a one-liner when each blocker clears:

| Phase | Trigger phrase |
|---|---|
| 0 (branch) | "Merge the refactor branch" — I run §0.2 |
| 2.1 (bench naming) | "Bench naming: A" / "B" / "C" — I run the appropriate sweep |
| 2.2 (bucket) | "Bucket privacy verified" / "Found public; flipped" |
| 2.3 (schema) | "Schema check: clean" / "Schema check: <findings>" |
| 4 (SSE stub) | "Local stack up; run-uuid is <uuid>" — I run the publisher |
| 5a (Resend Channel A) | "Resend SMTP wired in Studio" — I smoke-test |
| 5b (§5.14 flip) | "Resend keys are in VX1 .env" — I run the §9 sequence |
| 5c (VX1) | "VX1 at <IP>, domain <domain>" — I walk through 6.4–6.8 |
| 5d (Sprint G real) | "michealaai is on commit <sha>" — I trigger the real run |
| 6 (tag) | "Tag v1.0.0" — I run §6.1 verification + tag + push |

---

## Self-Review

**Spec coverage** — every drift item from the recent conversation has a phase:

- ✅ Three Supabase projects: surfaced in Phase 0 (branch already has the doc) + Phase 2.3 (verification step) + Phase 3.1 (HERMES_LINK cross-repo handoff to michealaai)
- ✅ Storage bucket cohabitation: Phase 2.2
- ✅ Schema collision (`agent_runs` namespace): Phase 2.3
- ✅ Bench naming: Phase 2.1
- ✅ Branch merge: Phase 0
- ✅ LAUNCH_CHECKLIST staleness: Phase 1.2
- ✅ HANDOFF v1.2.5 references: Phase 1.3
- ✅ CURRENT_STATE Anthropic SDK row: Phase 1.4
- ✅ HERMES_LINK.md: Phase 3.1
- ✅ SSE stub never run through /web: Phase 4
- ✅ Resend / VX1 / Sprint G / tag: Phases 5–6
- ✅ michealaai DATA-SOURCES.md fix: Phase 3.1 (in HERMES_LINK.md as cross-repo handoff)

**Placeholder scan** — searched for "TBD", "implement later", "fill in details", "similar to Task N", "Add error handling". None present. Where flexibility is intentional (Phase 2.1's three options, Phase 5's user-paced phases), I named the options explicitly.

**Type/name consistency** — bench names use placeholders intentionally (the choice in 2.1 determines them); commit messages mention every renamed file by path; the verbatim YAML for `~/.hermes/config.yaml` matches NousResearch/hermes-agent's docs format.

**Risk awareness:**

- R1 — mid-merge a test fails in Phase 0.2: explicit `git reset --hard ORIG_HEAD` step.
- R2 — the user picks bench-naming option B (cross-repo) and we can't act on it from here: Phase 2.1 step 5 only fires for option A; B/C are no-ops on this side.
- R3 — Studio cohabitation discovers a real schema conflict: Phase 2.3 step 3's "outcome 3" (real conflict) flags coordination need, doesn't auto-fix.
- R4 — VX1 isn't deployed when 5d's "real run" is attempted: 5d explicitly waits on 5c.

If you find a spec requirement with no task, add the task. (None found at this read.)

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-10-everything-to-v1.0.0.md`.

**1. Subagent-driven (recommended for Phase 1 doc sweeps + Phase 2.1 rename)** — fresh subagent per file/task, two-stage review. Best for the high-multiplicity edits.

**2. Inline execution (recommended for Phase 0 merge, Phase 4 SSE smoke, Phase 6 tag)** — context-continuous; these phases need careful state observation and quick rollback.

**3. Mixed (suggested):**
- Phase 0 — inline (one-shot, needs careful rollback story)
- Phase 1 — subagent-driven (parallelize the four file sweeps)
- Phase 2 — inline (bench-rename is wide; user-decisions are blocking)
- Phase 3 — inline (one new file, minimal touch)
- Phase 4 — inline (live dev stack)
- Phase 5 — user-paced; I re-engage on each trigger phrase
- Phase 6 — inline

When you're ready, drop the trigger phrase or just say "Phase 0" and I'll start.
