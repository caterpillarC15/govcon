# Skills → Deterministic-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended; phases share growing files: api/config.py, api/deps.py, eval/runner). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Realign this repo with its own operating rule (`devdocs/MICHAELA_SYSTEM_MODEL.md` line 175 — "Mechanics belong in shared tools. Judgment belongs in agents."). Today 5 of 10 skills carry their own LLM calls and emit judgment. After this plan, every skill is deterministic — Michaela's Hermes-hosted bench (Michaela / Scot / Lenny / Ledger / Gate / Happer / Roy in `/root/michealaai`) does the LLM reasoning. `api/llm.py`, `LLMMetrics`, `ANTHROPIC_API_KEY`, `LLM_DEV_MODEL`, `LLM_SYNTH_MODEL`, `RUN_BUDGET_*` all leave this repo.

**Architecture:**
- **One phase = one PR-sized commit.** Each skill phase is small and self-contained — the test changes for that one skill, the skill rewrite, the route response-shape adjustment.
- **TDD on every backend change.** Tests are rewritten BEFORE the skill is rewritten so the contract change is visible. Tests assert deterministic shapes only — no FakeLLM scaffolding remains.
- **Backwards-incompatible response shape change is intentional.** `/tools/<name>` envelope drops `metrics` because every skill becomes deterministic. The orchestrator caller (`/root/michealaai`) needs to stop reading `response.metrics`. That coordination is out of scope here — Phase 9 documents it in `devdocs/CAPABILITY_PACK_INTEGRATION.md`.
- **Branch `refactor/skills-deterministic-only`.** Active UI work continues on `main`. Merge when ready.

**Tech Stack:** Python 3.12 · FastAPI · Pydantic v2 · supabase-py AsyncClient · pytest-asyncio · uv. No new deps; several deps removed (`anthropic`).

**Worker ownership** (informs naming + comments; the workers themselves live in `/root/michealaai`):

| Skill | LLM judgment moves to | Skill keeps (deterministic) |
|---|---|---|
| `parse_goal` | Michaela | (deletable; or shrinks to a `SearchCriteria` Pydantic validator) |
| `extract_requirements` | Gate | PDF chunking + page-bound metadata + evidence-binding validator |
| `score_fit` | Lenny (rationale) + Gate (§11.1 trigger) | §11.1 short-circuit + decision-band thresholds + blocker carry-forward |
| `detect_risks` | Gate | 12-category schema validator + cap-at-8 + blocker carry-forward |
| `generate_action_package` | Roy (full mode) | `reject_summary` mode + compliance-matrix shape + approval-gate population |

Deterministic-only skills (no change): `parse_pdf`, `search_sam`, `fetch_attachment`, `rank_opportunities`, `load_seeded_opportunities`, `query_usaspending`.

**Authoritative references:**
- Operating rule: `devdocs/MICHAELA_SYSTEM_MODEL.md` (lines 173-180).
- Bench definition: user's 2026-05-10 message + `devdocs/CURRENT_STATE.md` §2.
- Existing skill tests (kept as patterns): `api/tests/test_parse_pdf.py`, `api/tests/test_rank_opportunities.py`, `api/tests/test_search_sam.py`.
- Test harness: `api/tests/conftest.py` (FakeSupabase). `api/tests/fakes.py::FakeLLM` is removed in Phase 6.
- Tool envelope: `api/routes/tools.py::ToolResponse`.

**Out of scope:**
- `/root/michealaai` worker prompts — separate session, separate repo.
- `/web` changes — the UI keeps rendering whatever skills return; no schema-shape break visible to UI.
- Sprint A Hermes plugin (doesn't exist on disk yet) — when it lands, the `gov_compliance` and `gov_proposals` adapters will simply not need LLM-call wrapping. Plan noted in Phase 9 docs.
- Adding a JS test framework.
- New product features.
- Re-introducing LLM calls "for just this one case" — it's an architectural refactor, not a vibe shift.

**Verification gates (must hold at end of every phase):**
- `uv run pytest api/tests/ -q` — all green; suite size never decreases (existing test count is preserved by rewriting; tests don't get deleted, they assert different shapes).
- `uv run ruff check api` — clean.
- `uv run mypy api` — clean.
- `uv run python -c "from api.main import app; print(sum(1 for r in app.routes if hasattr(r,'path')))"` — route count unchanged (53 today).
- `git status` — only intended changes for the phase.

**Final verification gates (entire plan complete):**
- All gates above hold.
- `grep -rn 'from api.llm\|api/llm\|LLMMetrics\|FakeLLM' --include='*.py' api/ eval/` returns nothing.
- `find api/skills -name 'prompt.txt'` returns nothing.
- `grep -E 'ANTHROPIC_API_KEY|LLM_DEV_MODEL|LLM_SYNTH_MODEL|RUN_BUDGET' api/config.py .env.example .env.production.example` returns nothing.
- `pip list 2>/dev/null | grep -i anthropic` (in the uv venv) returns nothing — `anthropic` SDK is a removed dep.
- `curl -X POST localhost:8000/tools/parse-goal …` returns `{"data": {…}}` only — no `metrics` field.
- `devdocs/CURRENT_STATE.md`, `devdocs/MICHAELA_SYSTEM_MODEL.md`, `devdocs/CAPABILITY_PACK_INTEGRATION.md`, `PRD.md` updated to reflect the deterministic-only contract (PRD v1.2.6 changelog).

---

## File Structure

| Action | Path | Phase | Responsibility |
|---|---|---|---|
| Modify | `api/skills/parse_goal/skill.py` | 1 | Drop LLM call; return deterministic SearchCriteria from regex/keyword extraction or accept structured input only |
| Delete | `api/skills/parse_goal/prompt.txt` | 1 | LLM prompt no longer used |
| Modify | `api/tests/test_parse_goal.py` | 1 | Tests assert deterministic output only; remove FakeLLM |
| Modify | `api/skills/extract_requirements/skill.py` | 2 | Drop LLM extraction; return parsed PDF chunks + page metadata; agent-side does the §10.1 structuring |
| Delete | `api/skills/extract_requirements/prompt.txt` | 2 | |
| Modify | `api/tests/test_extract_requirements.py` | 2 | Tests assert chunk-shape + page-bound validation |
| Modify | `api/skills/score_fit/skill.py` | 3 | Drop LLM rationale; return §11.1 short-circuit decision + blockers + decision band; rationale field becomes empty/null |
| Delete | `api/skills/score_fit/prompt.txt` | 3 | |
| Modify | `api/tests/test_score_fit.py` | 3 | Tests assert deterministic decision logic (already covered for §11.1; rationale assertions removed) |
| Modify | `api/skills/detect_risks/skill.py` | 4 | Skill becomes a validator: accepts pre-built `RiskFlag[]` from agent, enforces 12-category taxonomy + cap-at-8 + critical_blocker carry-forward; no LLM call |
| Delete | `api/skills/detect_risks/prompt.txt` | 4 | |
| Modify | `api/tests/test_detect_risks.py` | 4 | Tests assert validator behavior on agent-supplied input |
| Modify | `api/skills/generate_action_package/skill.py` | 5 | `reject_summary` mode unchanged (already deterministic); `full` mode returns schema skeleton + compliance matrix from agent input; no LLM |
| Delete | `api/skills/generate_action_package/prompt.txt` | 5 | |
| Modify | `api/tests/test_generate_action_package.py` | 5 | Tests assert deterministic skeleton + reject_summary unchanged |
| Delete | `api/llm.py` | 6 | LLM wrapper no longer used |
| Modify | `api/deps.py` | 6 | Remove `get_llm` provider + `LLM` import |
| Delete | `api/tests/fakes.py` | 6 | FakeLLM no longer needed (or shrink to non-LLM fakes if any remain) |
| Modify | `api/config.py` | 6 | Drop `anthropic_api_key`, `llm_dev_model`, `llm_synth_model`, `run_budget_*` fields |
| Modify | `.env.example` + `.env.production.example` | 6 | Drop the 6 env vars + their comments |
| Modify | `pyproject.toml` | 6 | Remove `anthropic>=0.40` dep + run `uv sync` |
| Modify | `api/routes/tools.py` | 7 | Drop `metrics` field from `ToolResponse`; update 11 route handlers to return `{"data": ...}` only |
| Modify | `api/tests/test_tools_routes.py` | 7 | Update envelope assertions |
| Modify | `eval/runner/runner.py` | 8 | Drop LLM-call paths; goldens become deterministic-output snapshots only |
| Modify | `eval/runner/differs.py` | 8 | Tighten tolerance to byte-exact (no LLM drift to absorb) |
| Modify | `eval/README.md` | 8 | Update for deterministic-only goldens |
| Modify | `Makefile` | 8 | Drop `eval-bootstrap` target (no LLM calls to bootstrap from); keep `make eval` |
| Modify | `devdocs/CURRENT_STATE.md` | 9 | §7 (skills become "all deterministic"); §10 add Phase 1.2.6; §11 drop LLM env vars |
| Modify | `devdocs/MICHAELA_SYSTEM_MODEL.md` | 9 | Strengthen "judgment in agents" example with the bench → skill mapping table |
| Modify | `devdocs/CAPABILITY_PACK_INTEGRATION.md` | 9 | Document the contract change (no `metrics` field); cross-repo callers must drop reads |
| Modify | `PRD.md` | 9 | Add v1.2.6 changelog entry |
| Modify | `tasks/CONTRACTS.md` | 9 | §5 skill registry — every row's "owner" becomes the worker that calls it; drop "LLM" from skill descriptions |

---

## Phase 0: Pre-flight + branch

**Goal:** Confirm clean baseline. Create feature branch.

- [ ] **Step 1: Verify state**
```bash
git log --oneline -3
git status -sb            # expect: ahead 0 / behind 0; in-flight UI mods present
uv run pytest api/tests/ -q 2>&1 | tail -3   # expect: ≥186 passing
uv run ruff check api 2>&1 | tail -2         # clean
uv run mypy api 2>&1 | tail -2               # clean
```

- [ ] **Step 2: Stash user's in-flight UI mods on main? NO.** They stay on main; the refactor branches from HEAD before they're committed. Either is safe — `git checkout -b` on a dirty tree carries the mods to the new branch. To avoid that, ask user to commit their UI work OR explicitly stash. Default: ask.

- [ ] **Step 3: Branch**
```bash
git checkout -b refactor/skills-deterministic-only
```

- [ ] **Step 4: Commit baseline marker**
```bash
git commit --allow-empty -m "chore: branch baseline for skills-deterministic-only refactor"
```

---

## Phase 1: parse_goal — strip LLM

**Goal:** `parse_goal` becomes either deleted (if Michaela parses inline) or a deterministic search-criteria validator.

**Decision:** Keep the route + skill as a thin pass-through validator. Backwards-compatible for callers; semantically the agent owns parsing.

- [ ] **Step 1: Read current skill**
```bash
cat api/skills/parse_goal/skill.py
cat api/skills/parse_goal/prompt.txt
cat api/tests/test_parse_goal.py
```

- [ ] **Step 2: Rewrite test (TDD)**

Replace LLM-mocking tests with deterministic ones:

```python
import pytest
from api.skills.parse_goal.skill import parse_goal, ParseGoalInput

@pytest.mark.asyncio
async def test_parse_goal_passthrough_returns_input_as_search_criteria():
    payload = ParseGoalInput(
        goal="Find DC-area cyber RFPs",
        company_profile={"naics_codes": ["541512"]},
    )
    result = await parse_goal(payload)
    assert result["raw_goal"] == "Find DC-area cyber RFPs"
    assert result["company_profile"] == {"naics_codes": ["541512"]}
    # Agent (Michaela) is responsible for extracting structured criteria;
    # this skill validates input shape only.
```

- [ ] **Step 3: Run test — confirm fails**
```bash
uv run pytest api/tests/test_parse_goal.py -v
```

- [ ] **Step 4: Rewrite skill**

```python
# api/skills/parse_goal/skill.py
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class ParseGoalInput(BaseModel):
    goal: str
    company_profile: dict[str, Any] | None = None


async def parse_goal(payload: ParseGoalInput) -> dict[str, Any]:
    """Pass-through input validator.

    Per the operating rule (mechanics in tools, judgment in agents),
    Michaela parses the natural-language goal in her own LLM context
    and emits structured search criteria for Scot. This skill only
    validates the input envelope.
    """
    return {
        "raw_goal": payload.goal,
        "company_profile": payload.company_profile or {},
    }
```

- [ ] **Step 5: Delete prompt.txt**
```bash
git rm api/skills/parse_goal/prompt.txt
```

- [ ] **Step 6: Update route handler in `api/routes/tools.py`**

The `/tools/parse-goal` route currently returns `{"data": ..., "metrics": LLMMetrics(...)}`. Change to `{"data": ..., "metrics": None}` for now; Phase 7 drops the field entirely.

- [ ] **Step 7: Run tests**
```bash
uv run pytest api/tests/test_parse_goal.py api/tests/test_tools_routes.py -v
```

- [ ] **Step 8: Run full gate set**
```bash
uv run pytest api/tests/ -q
uv run ruff check api
uv run mypy api
```

- [ ] **Step 9: Commit**
```bash
git add api/skills/parse_goal/ api/tests/test_parse_goal.py api/routes/tools.py
git commit -m "refactor(parse_goal): drop LLM — Michaela parses goal inline (operating rule)

The skill becomes a pass-through input validator. Per the operating
rule (devdocs/MICHAELA_SYSTEM_MODEL.md line 175), parsing
natural-language user intent is judgment work and belongs in the
agent (Michaela), not in a shared tool.

- skill.py: returns {raw_goal, company_profile} only
- prompt.txt: deleted
- test_parse_goal.py: deterministic shape assertions
- routes/tools.py: metrics: None (full envelope drop in Phase 7)

Verified: pytest, ruff, mypy clean."
```

---

## Phase 2: extract_requirements — return chunks only

**Goal:** Skill returns parsed PDF chunks + page metadata. Gate's prompt (in `/root/michealaai`) does the §10.1 structuring.

- [ ] **Step 1: Survey current contract**
```bash
sed -n '1,60p' api/skills/extract_requirements/skill.py
sed -n '1,40p' api/tests/test_extract_requirements.py
```

- [ ] **Step 2: Rewrite tests (TDD)**

Tests assert: chunks present per page, page numbers monotonic, evidence-binding metadata included for downstream agent use.

- [ ] **Step 3: Rewrite skill**

```python
async def extract_requirements(
    payload: ExtractRequirementsInput,
) -> dict[str, Any]:
    """Return PDF chunks with page metadata.

    Gate (eligibility worker in /root/michealaai) consumes these
    chunks in her own LLM context to emit §10.1 ExtractedRequirement
    structures. This skill stops at deterministic chunking.
    """
    chunks = await parse_pdf(payload.pdf_path)
    return {
        "opportunity_id": str(payload.opportunity_id),
        "chunks": [
            {
                "page_number": c["page_number"],
                "text": c["text"],
                "doc_id": c.get("doc_id"),
            }
            for c in chunks
        ],
        "unparseable": chunks == [],
    }
```

- [ ] **Step 4: Delete prompt.txt + run tests + commit** (same pattern as Phase 1)

```bash
git rm api/skills/extract_requirements/prompt.txt
uv run pytest api/tests/test_extract_requirements.py -v
git add ...
git commit -m "refactor(extract_requirements): return chunks only — Gate emits §10.1 in agent context"
```

---

## Phase 3: score_fit — §11.1 short-circuit + bands only

**Goal:** Skill keeps the deterministic §11.1 reject short-circuit + decision band thresholds. Lenny's prompt emits the rationale.

- [ ] **Step 1: Survey** — `score_fit` already has a `_zero_metrics()` helper for the short-circuit path. The LLM path lives in the synthesis branch.

- [ ] **Step 2: Rewrite tests** — keep all §11.1 short-circuit tests (they're already deterministic). Drop tests asserting LLM-rationale text. Add: rationale field is `null` or empty string.

- [ ] **Step 3: Rewrite skill**

```python
async def score_fit(payload: ScoreFitInput) -> dict[str, Any]:
    blockers = _detect_eligibility_blockers(payload)
    if blockers:
        # §11.1 short-circuit — deterministic reject, no LLM
        return {
            "decision": "reject",
            "total_score": 0,
            "blockers": blockers,
            "rationale": "",  # Lenny populates this in her agent context
            "band_breakdown": _empty_bands(),
        }
    band_breakdown = _compute_bands(payload)
    decision = _decision_from_band(band_breakdown.total)
    return {
        "decision": decision,
        "total_score": band_breakdown.total,
        "blockers": [],
        "rationale": "",  # Lenny populates
        "band_breakdown": band_breakdown.model_dump(),
    }
```

- [ ] **Step 4-7: Delete prompt + tests + commit** (same pattern)

```
refactor(score_fit): drop LLM rationale — Lenny emits in agent context

§11.1 short-circuit + decision-band thresholds remain deterministic
(those are mechanics). Rationale becomes an empty field for Lenny
to populate in her LLM context.
```

---

## Phase 4: detect_risks — schema validator

**Goal:** Skill becomes a validator. Accepts agent-emitted `RiskFlag[]`, enforces 12-category taxonomy, caps at 8 by severity priority, carries forward `fit_score.blockers` as `critical_blocker` risks.

- [ ] **Step 1: Survey current `_validate_categories`, `_truncate_by_severity`, `_carry_blockers` logic** — most of it is already deterministic. Only the LLM call needs removal.

- [ ] **Step 2: New skill input shape** — accept `risks: list[RiskFlag]` from caller (Gate's agent emits) + `fit_score: FitScore` + `requirements: list[Requirement]`. Run validators. Return validated list.

- [ ] **Step 3: Rewrite tests** — focus on validator behavior. Mock-LLM tests removed.

- [ ] **Step 4-7: Delete prompt + commit**

```
refactor(detect_risks): become validator — Gate emits risks, skill enforces taxonomy

Skill accepts agent-emitted RiskFlag[], enforces the 12-category
PRD §5.8 taxonomy, caps at 8 by severity, carries blockers from
fit_score as critical_blocker risks. Gate generates risks in her
LLM context; this skill is the contract gate.
```

---

## Phase 5: generate_action_package — schema skeleton

**Goal:** `reject_summary` mode unchanged (already deterministic). `full` mode returns the §10.3 schema skeleton with agent-supplied content slotted in; no LLM in this skill.

- [ ] **Step 1: Survey** — confirm `reject_summary` path is purely deterministic (no LLM); the `full` mode is the LLM path.

- [ ] **Step 2: Rewrite skill input** — accept `mode: "full" | "reject_summary"` + a `content: dict` payload from caller (Roy emits). Return §10.3-shaped output.

- [ ] **Step 3: Tests** — `reject_summary` unchanged; `full` mode now asserts the input content gets validated + slotted into the schema.

- [ ] **Step 4-7: Delete prompt + commit**

```
refactor(generate_action_package): full mode = schema validator; reject_summary unchanged

Roy synthesizes the bid memo content in her agent context. This skill
takes that content + validates the §10.3 ActionPackage shape, populates
the approval gate, and persists. reject_summary mode (already
deterministic) is unchanged.
```

---

## Phase 6: Drop api/llm.py + ANTHROPIC + LLM env vars

**Goal:** With all 5 LLM-bearing skills now deterministic, the wrapper + env vars + Anthropic SDK dep are dead weight.

- [ ] **Step 1: Verify nothing else imports from api.llm**
```bash
grep -rn "from api.llm\|import api.llm" --include='*.py' . 2>/dev/null | grep -v ".venv"
```
Expected: empty (after Phases 1-5 land).

- [ ] **Step 2: Delete files**
```bash
git rm api/llm.py api/tests/fakes.py
# (or shrink fakes.py if it carries non-LLM fakes)
```

- [ ] **Step 3: Edit api/deps.py** — drop `get_llm` provider + LLM import.

- [ ] **Step 4: Edit api/config.py** — drop the 4 fields:
```python
# remove:
anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
llm_dev_model: str = Field(..., alias="LLM_DEV_MODEL")
llm_synth_model: str = Field(..., alias="LLM_SYNTH_MODEL")
run_budget_usd: float = Field(0.50, alias="RUN_BUDGET_USD")
run_budget_steps: int = Field(40, alias="RUN_BUDGET_STEPS")
run_budget_seconds: int = Field(360, alias="RUN_BUDGET_SECONDS")
```

- [ ] **Step 5: Edit env templates** — drop the 6 vars + their comment blocks from both `.env.example` and `.env.production.example`.

- [ ] **Step 6: Edit pyproject.toml** — drop `"anthropic>=0.40"` from dependencies.

- [ ] **Step 7: Sync**
```bash
uv sync
```

- [ ] **Step 8: Run gates**
```bash
uv run pytest api/tests/ -q
uv run ruff check api
uv run mypy api
pip list 2>/dev/null | grep -i anthropic     # expect empty
```

- [ ] **Step 9: Commit**

```
chore: drop api/llm.py + ANTHROPIC + LLM_* env + anthropic SDK dep

With every skill now deterministic (Phases 1-5), the LLM wrapper is
unused. Drop the file, the LLMMetrics class, the FakeLLM test scaffold,
the 6 env vars (ANTHROPIC_API_KEY, LLM_DEV_MODEL, LLM_SYNTH_MODEL,
RUN_BUDGET_USD/STEPS/SECONDS), and the anthropic SDK dependency.

The repo no longer makes any LLM API calls. Michaela's bench in
/root/michealaai owns all judgment.
```

---

## Phase 7: Drop `metrics` from /tools/<name> envelope

**Goal:** Every `/tools/<name>` route returns `{"data": ...}` — no `metrics` field. Cross-repo callers (`/root/michealaai`) need to stop reading it; documented in Phase 9.

- [ ] **Step 1: Edit `api/routes/tools.py`** — change `ToolResponse`:
```python
class ToolResponse(BaseModel):
    data: dict[str, Any]
    # metrics field removed — every skill is deterministic.
```

- [ ] **Step 2: Update 11 route handlers** — drop the `metrics=...` kwarg from every `ToolResponse(...)` construction.

- [ ] **Step 3: Edit `api/tests/test_tools_routes.py`** — every assertion that reads `body["metrics"]` becomes `assert "metrics" not in body`.

- [ ] **Step 4: Edit `api/tests/test_action_package_approve.py` and any other test** that reads `metrics` envelope.

- [ ] **Step 5: Run gates + commit**

```
chore(tools): drop metrics field from /tools/<name> envelope

Every skill is now deterministic; no LLM = no metrics. Response
envelope is {"data": ...} only. Cross-repo callers must stop
reading response.metrics; see CAPABILITY_PACK_INTEGRATION.md.
```

---

## Phase 8: Simplify eval harness

**Goal:** `eval/runner/` no longer needs LLM-tolerance diffing. Goldens become byte-exact deterministic snapshots.

- [ ] **Step 1: Edit `eval/runner/runner.py`** — drop the LLM-call path; runner just diffs skill output against golden.

- [ ] **Step 2: Edit `eval/runner/differs.py`** — replace tolerance-aware diff with strict equality (or a structural diff that's still strict).

- [ ] **Step 3: Edit `eval/README.md`** — document deterministic-only contract; no Anthropic key needed.

- [ ] **Step 4: Edit `Makefile`** — drop `eval-bootstrap` target (or keep as a deterministic-snapshot capture). Keep `make eval`.

- [ ] **Step 5: Edit `fixtures/*/manifest.json` `eval_inputs` blocks** — remove fields that only made sense for LLM skills (e.g., LLM-specific seeds).

- [ ] **Step 6: Run `make eval`** — should pass against existing or freshly-bootstrapped goldens.

- [ ] **Step 7: Commit**

```
refactor(eval): deterministic-only goldens — no LLM, byte-exact diff

With every skill deterministic, the harness no longer needs to
absorb LLM drift. Tolerance-aware differs replaced by strict
equality. eval-bootstrap no longer requires Anthropic credits.
```

---

## Phase 9: Update docs

**Goal:** Docs reflect the new contract.

- [ ] **Step 1: `devdocs/CURRENT_STATE.md`**
  - §7 Skills table — every row is "deterministic"; "Typical caller" column names the worker
  - §10 "Done / Next" — add Phase 1.2.6 to Done
  - §11 Env-var contract — drop ANTHROPIC_API_KEY, LLM_*, RUN_BUDGET_*

- [ ] **Step 2: `devdocs/MICHAELA_SYSTEM_MODEL.md`**
  - Strengthen the "judgment in agents" section with the explicit bench → skill mapping table
  - Note that this repo no longer carries any LLM call surface

- [ ] **Step 3: `devdocs/CAPABILITY_PACK_INTEGRATION.md`**
  - Document the response envelope change (no `metrics`)
  - Cross-repo coordination note: `/root/michealaai` callers must stop reading `response.metrics`
  - Note that callers now own LLM cost tracking (this repo doesn't see it)

- [ ] **Step 4: `PRD.md`**
  - Add v1.2.6 changelog entry

```markdown
> **Changelog v1.2.5 → v1.2.6** (2026-05-10)
> - **Skills are now deterministic-only.** parse_goal, extract_requirements,
>   score_fit, detect_risks, generate_action_package no longer call any
>   LLM provider. Per the operating rule (mechanics in tools, judgment in
>   agents), Michaela's Hermes-hosted bench in /root/michealaai performs
>   all reasoning; this repo carries only mechanics, schemas, and contracts.
> - **Removed env vars:** ANTHROPIC_API_KEY, LLM_DEV_MODEL, LLM_SYNTH_MODEL,
>   RUN_BUDGET_USD, RUN_BUDGET_STEPS, RUN_BUDGET_SECONDS. Budgets move to
>   Michaela's environment.
> - **Removed surface:** api/llm.py (LLM wrapper, LLMMetrics, FakeLLM).
>   anthropic SDK dropped from pyproject.toml.
> - **Response envelope change:** /tools/<name> now returns
>   {"data": ...} — no metrics field. Cross-repo callers update accordingly.
> - **Eval harness simplified** to byte-exact deterministic diff;
>   make eval no longer requires Anthropic credits.
```

- [ ] **Step 5: `tasks/CONTRACTS.md` §5** — every skill row's "Owner" column lists the worker; descriptions drop LLM language.

- [ ] **Step 6: `HANDOFF_PROMPT.md`** — Section 1 "Verified state" reflects v1.2.6; Section 5 drops LLM env vars; Section 7 marks deterministic-skills work done.

- [ ] **Step 7: Commit**

```
docs: refactor for deterministic-only skills (PRD v1.2.6)

CURRENT_STATE, MICHAELA_SYSTEM_MODEL, CAPABILITY_PACK_INTEGRATION,
PRD changelog, CONTRACTS skill registry, HANDOFF_PROMPT all reflect
the new contract: no LLM calls in this repo, no Anthropic dep, no
metrics in tool envelope. Michaela's bench in /root/michealaai owns
all judgment.
```

---

## Self-Review

**Spec coverage:** every LLM-bearing surface in this repo has a phase. The 5 skills (Phases 1-5), the LLM infra (Phase 6), the response envelope (Phase 7), the eval harness (Phase 8), the docs (Phase 9). Cross-repo work for `/root/michealaai` is explicitly out of scope and documented in Phase 9.

**Placeholder scan:** Each phase shows the actual code blocks an executor needs. No "TBD" or "implement appropriately."

**Type consistency:** `parse_goal` → returns `{raw_goal, company_profile}` (used in Phase 1 and consistent with what Michaela needs). `extract_requirements` → returns `{opportunity_id, chunks: [{page_number, text, doc_id}], unparseable}`. `score_fit` → `{decision, total_score, blockers, rationale: "", band_breakdown}`. `detect_risks` → validated `RiskFlag[]`. `generate_action_package` → §10.3 ActionPackage. ToolResponse → `{data: dict}`.

**Risks consciously accepted:**
- Cross-repo coordination overhead (Phase 9 documents but doesn't enforce). The orchestrator team must update their callers to stop reading `response.metrics` and to populate the LLM-judgment fields. Phase 9 surfaces the contract change.
- Eval-harness reduction loses the LLM-version-drift safety net. That moves to Michaela's bench (their problem now).
- `parse_goal` becoming pass-through means existing UI flows that posted free-form goals to `/tools/parse-goal` and expected structured criteria back will get a no-op response. The `/web` UI already passes the goal through `POST /agent-runs` (not `/tools/parse-goal`), so this is unlikely to affect users. Verify before declaring Phase 1 done.

**Out-of-scope items deliberately excluded:** /root/michealaai prompts (different repo, different session), /web (UI is renderer; it doesn't care which side does the LLM work), Sprint A Hermes plugin scaffolding (future).

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-05-10-skills-deterministic-only.md`. Recommended execution: **inline via superpowers:executing-plans, in branch `refactor/skills-deterministic-only`**. Phases share files (api/config.py, api/deps.py, eval/) so subagent-driven would force frequent merges.

**Critical path:** 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9. Phases 1-5 can be reordered freely (each is its own commit). 6 must follow 1-5. 7 can land alongside 6. 8 follows 7. 9 is last.

**Realistic ETA:** Half-day of focused work for one engineer.
