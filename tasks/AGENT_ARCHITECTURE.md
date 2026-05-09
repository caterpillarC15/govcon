# Agent Architecture

The agent system that runs inside Hermes. PRD §4.5 describes the runtime contract; `HERMES.md` describes the integration; `devdocs/V1_PRODUCT_ALIGNMENT.md` describes the product filter. This doc owns the **multi-agent design** — what each agent does, what tools it has, how they coordinate, and why.

This is the document the Agents Track judges will read. It is the difference between "tool-using agent" and "agent system."

---

## At a glance

Five internal agent roles, two-tier delegation, parallelism at the opportunity level. Publicly, this must still feel like one hired bid-desk worker. The §11.1 eligibility rule is owned by a dedicated specialist whose decision the rest of the system respects.

```
                    ┌──────────────────────────┐
                    │  Capture Lead (root)     │
                    └────────────┬─────────────┘
                                 │ spawn N parallel
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
       ┌────────────────┐ ┌──────────────┐ ┌──────────────┐
       │  Capture       │ │  Capture     │ │  Capture     │
       │  Analyst       │ │  Analyst     │ │  Analyst     │
       │  (opp 1)       │ │  (opp 2)     │ │  (opp 3)     │
       └───────┬────────┘ └──────┬───────┘ └──────┬───────┘
               │                  │                │
            (each delegates to up to 3 specialists)
               ▼                  ▼                ▼
       ┌─────────────────────────┐
       │ Compliance Officer      │ — extract reqs + score_fit + §11.1 gate
       └─────────────────────────┘
       ┌─────────────────────────┐
       │ Risk Analyst            │ — §5.8 risks  (skipped on reject)
       └─────────────────────────┘
       ┌─────────────────────────┐
       │ Proposal Strategist     │ — action package (full or reject_summary)
       └─────────────────────────┘
```

---

## Why 5 agents (not 3, not 7)

**3 agents (Lean):** Capture Lead + Capture Analyst calling skills directly. Simpler. But:
- §11.1 has no specialist owner. The eligibility rule is one bullet in a long prompt; drift is the failure mode.
- The demo story is "tool-using agent," not "agent system." Loses the Agents Track narrative.
- Single long prompt is less reliable than three focused ones (especially Haiku in dev mode).

**7 agents (Maximalist):** add Goal Interpreter, Document Parser, separate Outreach Drafter. Hermes' per-agent planner LLM deliberation isn't free. Each extra agent adds delegation handshake cost without proportional benefit.

**5 agents (chosen):** balance. Each specialist has a clear domain; each specialist's prompt is tight; the §11.1 owner is dedicated. Demo storytelling is strong without being baroque.

### Trade-offs accepted

- **More LLM calls** than the lean version (~15-20 vs ~10), but cost still ≤ $0.30/run on the demo profile (well under PRD's $0.50 cap).
- **More moving parts to debug.** The trace bridge must render the agent hierarchy correctly so debugging stays tractable.
- **Specialist isolation can lose context** that a generalist would have. Mitigated by passing rich context in delegation payloads (full requirements list, full fit_score, etc., not just summaries).

---

## The five agents

### 1. Capture Lead (root / orchestrator)

**Role.** Receive `(profile, goal)`. Plan the run. Discover candidates. Rank. Delegate. Summarize.

**The only agent that talks to the user-facing API.** All Hermes runs start with the Capture Lead.

**Tools / skills it can call:**

| Skill | Purpose |
|-------|---------|
| `parse_goal` | NL goal → structured search criteria (NEW skill) |
| `search_sam_opportunities` | Live SAM.gov v2 search |
| `load_seeded_opportunities` | Fixture fallback (PRD §5.4) |
| `rank_opportunities` | Deterministic relevance + recency ranker (NEW skill, no LLM) |
| `delegate(role="capture_analyst", …)` | Hermes' subagent primitive |
| `request_human_review` | Hermes built-in |
| `summarize_run` | Final synthesis (single LLM call) |

**Does NOT have access to:** `parse_pdf`, `extract_requirements`, `score_fit`, `detect_risks`, `generate_action_package`. Those belong to specialists. **This separation forces the main agent to delegate; that's the architectural point.**

**Workflow:**
1. `parse_goal(user_goal)` → structured criteria
2. `search_sam_opportunities(criteria)` (live) or `load_seeded_opportunities(criteria)` (seeded path)
3. `rank_opportunities(candidates, criteria, profile)` → top-N (default N=3)
4. For each opp in top-N: `delegate(role="capture_analyst", opportunity, profile)` — **fan out, await all** (Hermes parallel delegation)
5. `summarize_run(results)` → final summary
6. Return.

**Prompt:** `dev1-backend/prompts/agent_capture_lead.md`.

### 2. Capture Analyst (per-opportunity, spawned N times in parallel)

**Role.** Take ONE opportunity. Produce its full analysis bundle: `(requirements, fit_score, risks, action_package)`.

**Owns** all per-opportunity work. Same logic across instances; instances differ only in input.

**Tools / skills:**

| Skill | Purpose |
|-------|---------|
| `fetch_attachment` | Hermes built-in (HTTP/browser); pulls PDFs |
| `verify_source_page` | Hermes built-in; only when API metadata is incomplete |
| `parse_pdf` | Per attachment — parallelizable inside this agent |
| `delegate(role="compliance_officer", …)` | Hermes subagent |
| `delegate(role="risk_analyst", …)` | Hermes subagent |
| `delegate(role="proposal_strategist", …)` | Hermes subagent |

**Workflow:**
1. Fetch all attachments in parallel.
2. Parse each PDF in parallel via `parse_pdf`.
3. `delegate(role="compliance_officer", opportunity, profile, parsed_chunks)` → returns `{requirements, fit_score}` with §11.1 enforced.
4. **If `fit_score.decision == "reject"`:**
   - `delegate(role="proposal_strategist", mode="reject_summary", …)` → slim reject package (no LLM call needed; deterministic).
   - Return bundle. Skip Risk Analyst.
5. **Else:**
   - `delegate(role="risk_analyst", profile, requirements, fit_score)` → `risks`
   - `delegate(role="proposal_strategist", mode="full", …)` → action package
   - Return bundle.

**Prompt rules** (`agent_capture_analyst.md`):
- Respect the Compliance Officer's reject decision. Do not delegate to Risk Analyst or Proposal Strategist with `mode="full"` for a reject opportunity. Ever.
- If parse_pdf returns unparseable for ALL attachments, escalate to `request_human_review` rather than fabricate.
- Emit one-sentence rationales for each tool call (the trace bridge surfaces these to the UI).

### 3. Compliance Officer (specialist sub-agent)

**Role.** Extract requirements from parsed chunks. Apply the §5.7 fit-score rubric WITH the §11.1 short-circuit. Return `(requirements, fit_score)`.

**The single source of truth for eligibility decisions.** No other agent can override its verdict.

**Tools / skills:**

| Skill | Purpose |
|-------|---------|
| `extract_requirements` | LLM, structured §10.1 output |
| `score_fit` | Deterministic dimension math + LLM rationale; §11.1 hard-gate is INSIDE this skill (A6) |

**Specialist prompt rules** (`agent_compliance_officer.md`):
- "You are the gate keeper for PRD §11.1. Eligibility uncertainty = score 0 + critical blocker. Capability strengths CANNOT soften the eligibility decision."
- "Every requirement with confidence ≥ medium must include an evidence_snippet from the source text."
- "Return only structured output. No prose explanation outside the schema."

**Why a specialist:** prompt tightening. A generalist with all rules in one prompt drifts; a Compliance Officer with a focused prompt is reliable. Also: §11.1 has a clear owner — easy to audit, test, harden.

### 4. Risk Analyst (specialist sub-agent)

**Role.** Given `(profile, requirements, fit_score)`, produce `RiskFlag[]` per PRD §5.8.

**Skipped for reject opportunities** — the slim reject package goes through Proposal Strategist directly.

**Tools / skills:**

| Skill | Purpose |
|-------|---------|
| `detect_risks` | LLM call |

**Specialist prompt rules** (`agent_risk_analyst.md`):
- 12 categories enumerated with examples; severity tiers defined.
- Cross-check: every blocker the Compliance Officer surfaced must reappear here as a `critical_blocker`.
- Cap output at 8 risks; prioritize actionable items over comprehensive lists.

### 5. Proposal Strategist (specialist sub-agent)

**Role.** Given `(profile, opportunity, requirements, fit_score, risks)`, produce the §10.3 action package.

**Two modes:**

| Mode | When | Behavior |
|------|------|----------|
| `mode="full"` | strong_pursue / pursue / maybe | All 11 §10.3 sections via LLM |
| `mode="reject_summary"` | reject | Deterministic slim shape: executive_summary, decision, fit_rationale, compliance_matrix (blockers only), risk_register (criticals only), human_approval_required. **No proposal_checklist, no timeline, no outreach, no partner_suggestions.** No LLM call. |

**Tools / skills:**

| Skill | Purpose |
|-------|---------|
| `generate_action_package` | Sonnet LLM (full mode); deterministic constructor (reject mode, no LLM) |

**Specialist prompt rules** (`agent_proposal_strategist.md`):
- §5.13 approval gate is non-negotiable: every package emits `human_approval_required` with at least 4 entries.
- No fabricated names, contacts, or claims. Salutations are generic ("Contracting Officer").
- For `maybe` decisions: proposal_checklist starts with "Resolve [the gap]" before tactical items.

---

## Two new skills (Capture Lead's tooling)

### `parse_goal`

**Input.** `{goal: string, profile: CompanyProfile}`.

**Output.** Structured search criteria:

```jsonc
{
  "keywords": ["cybersecurity", "vulnerability assessment"],
  "naics_hints": ["541512"],
  "set_aside_preference": "small_business",
  "deadline_window_days": 60,
  "place_of_performance_states": ["TX"],
  "agency_filter": null,
  "opportunity_size_hint": null
}
```

**Implementation.** LLM call (Haiku is sufficient). The profile is used to bias missing fields (e.g., default state from profile.location).

**File.** `/api/skills/parse_goal/`. Owned by A11 task (renamed/expanded from "search/load skills").

### `rank_opportunities`

**Input.** `{candidates: Opportunity[], criteria: ParsedGoal, profile: CompanyProfile}`.

**Output.** Same opportunities, sorted, with a `relevance_score` 0-100 attached.

**Implementation.** Pure deterministic. No LLM. Heuristic:
- Keyword overlap: title + description vs criteria.keywords (+30 if any match)
- NAICS exact match (+25)
- Set-aside compatibility with profile.certifications (+20)
- Deadline within window (+15 if yes; -25 if outside)
- Place-of-performance match (+10)

Top-N (default 3) returned.

**File.** `/api/skills/rank_opportunities/`. Owned by A11 task.

**Why deterministic:** ranking is cheap, fast, debuggable, testable. We don't need an LLM for this.

---

## Trace event extensions (CONTRACTS.md §3 update)

The frontend's Timeline (B5) renders the agent hierarchy. Two new event types:

```jsonc
{ "type": "subagent_spawned",
  "run_id": "uuid",
  "parent_id": "uuid | null",          // null when Capture Lead spawns
  "subagent_id": "uuid",
  "role": "capture_lead | capture_analyst | compliance_officer | risk_analyst | proposal_strategist",
  "context": { /* role-specific summary, e.g., {opportunity_id} for capture_analyst */ },
  "ts": "ISO-8601" }

{ "type": "subagent_completed",
  "run_id": "uuid",
  "subagent_id": "uuid",
  "status": "complete | failed | skipped",
  "ts": "ISO-8601" }
```

Existing events (`step_started`, `tool_called`, etc.) gain an implicit `subagent_id` from context — every tool call belongs to the most recently spawned, not-yet-completed sub-agent on its branch.

The frontend (B5b/c) renders the timeline as an indented tree. **This is the demo's wow shot.**

```
▼ Capture Lead
  ├─ tool: parse_goal              "Parsing user goal into search criteria…"
  ├─ tool: search_sam              "Searching SAM.gov for federal opportunities…"
  ├─ tool: rank_opportunities      "Ranking 12 candidates by relevance…"
  ├─▼ Capture Analyst (opp 1)      [parallel branch]
  │  ├─ tool: fetch_attachment     ×2
  │  ├─ tool: parse_pdf            ×2 (parallel)
  │  ├─▼ Compliance Officer
  │  │  ├─ tool: extract_requirements
  │  │  └─ tool: score_fit         → decision: strong_pursue (88/100)
  │  ├─▼ Risk Analyst
  │  │  └─ tool: detect_risks      → 0 critical
  │  └─▼ Proposal Strategist (mode=full)
  │     └─ tool: generate_action_package
  ├─▶ Capture Analyst (opp 2)       → maybe (64/100; partner suggested)
  ├─▶ Capture Analyst (opp 3)       → reject (clearance blocker, p.2)
  └─ tool: summarize_run
```

---

## §11.1 enforcement under multi-agent

Five enforcement points layered. PRD §11.1 is the highest-user-harm rule; it deserves redundancy.

| # | Where | What |
|---|-------|------|
| 1 | `score_fit` skill (deterministic, A6) | Short-circuit returns `decision=reject` when a hard blocker is present, regardless of capability dimensions. |
| 2 | Compliance Officer prompt | "You are the gate keeper for §11.1. Capability strengths cannot soften eligibility." |
| 3 | Capture Analyst prompt | "Respect the Compliance Officer's reject decision. Skip Risk Analyst; only call Proposal Strategist with `mode=reject_summary`." |
| 4 | Capture Lead prompt | "Your final summary cannot upgrade a reject. Pass through subagent verdicts faithfully." |
| 5 | Eval harness (A12) | Assertion: capability ≥ 15 AND decision = reject for the reject fixture. Catches regressions in CI. |

**Belt + suspenders + parachute + backup parachute + ground.**

If you find yourself wanting to weaken any one of these layers, stop. PRD §17 calls eligibility hallucination "a serious user harm." The redundancy is intentional.

---

## Memory and isolation

Hermes has agent-curated memory. Defaults for v1:

- **Per-run memory only.** No cross-run persistence in v1.
- **Per-agent isolation.** Sub-agents don't see other sub-agents' memory. State sharing happens via delegation return values.
- **Capture Lead remembers the run.** It can reference earlier tool outputs in `summarize_run`.
- **Specialists are stateless across opportunities.** Each Compliance Officer instance starts fresh — no contamination between opp 1 and opp 2.

To clear between dev runs: `hermes memory clear` (per RUNBOOK).

Cross-run learning ("agent improves over time") is a Hermes feature we acknowledge but disable for v1. Post-MVP path.

---

## Cost & latency estimates

For a 3-opportunity run (typical demo):

| Step | LLM calls | Estimated cost |
|------|-----------|----------------|
| Capture Lead: parse_goal + summarize_run | 2× Haiku | $0.002 |
| Capture Lead: planner deliberation | ~3× Sonnet small | $0.015 |
| 3× Capture Analyst: planner deliberation | 3× ~3 Haiku | $0.009 |
| 3× Compliance Officer: extract_requirements + rationale | 3× (1 Sonnet + 1 Haiku) | $0.07 |
| 2× Risk Analyst (skip reject): detect_risks | 2× Haiku | $0.004 |
| 3× Proposal Strategist: generate_action_package | 2× Sonnet (full) + 1 deterministic (reject) | $0.10 |
| **Total** |  | **≈$0.20** |

Comfortably under PRD's $0.50 cap.

Latency:

| Path | Time |
|------|------|
| Sequential (no parallelism) | ~2.5 min |
| Parallel Capture Analysts | ~1.0 min |
| Within each Capture Analyst (PDFs + 3 specialists) | ~30 s |

PRD's 6-minute budget is comfortable.

---

## Failure modes per agent

| Agent | Failure | Recovery |
|-------|---------|----------|
| Capture Lead: `search_sam` 429 / 5xx | rate-limited / outage | falls back to `load_seeded_opportunities` |
| Capture Lead: `rank_opportunities` crash | deterministic shouldn't fail | log + abort run with `needs_human` |
| Capture Analyst: `fetch_attachment` fails | network / portal issue | retry once, then degrade (mark missing, continue) |
| Capture Analyst: `parse_pdf` unparseable for ALL attachments | image-only, encrypted | escalate to `request_human_review` |
| Compliance Officer: `extract_requirements` low-confidence | bad solicitation or model | re-chunk smaller; retry once; on second failure, accept degraded output |
| Compliance Officer: `score_fit` deterministic crash | profile shape mismatch | abort opp; report partial to Capture Lead |
| Risk Analyst: invalid JSON | LLM | retry with stricter prompt; on failure, return empty risks (degraded) |
| Proposal Strategist: invalid JSON (full mode) | LLM | retry once; on failure, fall back to deterministic minimal package |
| Sub-agent timeout | wall-clock | parent records partial result; continues with siblings |

The Capture Lead always emits `run_completed`, even with partial sub-agent failures.

---

## Open questions (resolve during A9 spike)

These need answers from a 30-minute Hermes-CLI exploration. Pin in `dev1-backend/STANDUP.md`.

1. **Subagent API surface.** Function signature for `hermes.delegate(role, instructions, tools, …)`?
2. **Trace event emission.** Does Hermes emit per-subagent lifecycle events natively, or do we instrument? Affects the bridge.
3. **Memory namespace per agent.** Confirm sub-agents get isolated memory by default.
4. **Concurrency limits.** Hermes' subagent-spawn cap. Our 3-parallel design assumes 3+ allowed.
5. **Per-subagent model override.** Compliance Officer = Sonnet, Risk Analyst = Haiku. Saves cost.
6. **Skill whitelisting per agent.** Restrict each agent's tool set so it cannot bypass delegation. Preserves the architectural invariant.

---

## Build order (revises A9)

This architecture lands inside A9 (Hermes integration). Sequence:

1. **Define agent modules.** `/api/agents/<role>/` per role. Each contains an instructions text + tool list + skill bindings.
2. **Implement the 2 new skills:** `parse_goal`, `rank_opportunities`. (Move into A11 or split out as A11.5.)
3. **Implement `summarize_run` as Capture Lead's last LLM call** (inline, not a separate skill).
4. **Wire skill ownership per agent.** Each agent's tool list excludes skills not in its registry. **Capture Lead must not have parse_pdf, etc.** Enforce via Hermes' subagent skill-whitelist mechanism.
5. **Trace bridge:** translate Hermes' subagent events to our extended CONTRACTS.md §3 union (`subagent_spawned`, `subagent_completed`).
6. **Test against the three demo fixtures.** Verify the agent tree visually in the UI.
7. **Tune sub-agent prompts** based on `make eval` output.

Estimated A9 effort with this architecture: **~1.5× the original A9 estimate.** The added complexity is what makes this an Agents Track submission.

---

## Demo moment (the multi-agent reveal)

When the timeline shows the agent tree expanding live:

> "The Capture Lead just spawned three Capture Analysts — one per top-ranked opportunity. They're working in parallel. Inside each, you can see the Compliance Officer extracting requirements and applying the eligibility rule.
>
> For opportunity 3, the Compliance Officer just returned `decision = reject` because of the clearance blocker on page 2. The Capture Analyst respects that — it skips Risk Analyst entirely and asks the Proposal Strategist for a slim reject summary.
>
> The Capture Lead summarizes all three: one strong pursue with a full action package, one maybe with a partner suggestion, one reject with a sourced blocker. Total cost: 19 cents. Total time: 47 seconds.
>
> This is what an agent system looks like."

This is the Agents Track narrative. Practice it.

---

## Hermes specifics — confirmed via research

After querying Context7's `/nousresearch/hermes-agent` index and Hermes' official docs, here are the runtime mechanics that this architecture relies on. Source URLs are in the dev1-backend `STANDUP.md` notes.

### Hermes "skills" vs. our "domain logic" — important terminology

Hermes' **`SKILL.md`** is a markdown procedure document with frontmatter (name, description, version, tags, optional toolsets/platforms gating). Skills are loaded **on demand** by the agent's planner (progressive disclosure — minimizes token usage). They contain `When to Use`, `Procedure`, `Pitfalls`, `Verification` sections — they are **memory-aiding procedures**, not Python modules.

Our domain logic (`parse_pdf`, `extract_requirements`, `score_fit`, `detect_risks`, `generate_action_package`, `search_sam`, `load_seeded`, `parse_goal`, `rank_opportunities`) is implemented as **toolsets** — Python tools with declared input/output schemas, registered with Hermes and callable via the agent's tool-calling loop.

In this doc, when we wrote "skill" earlier we meant "tool / Python module that does work." That's a **toolset** in Hermes terms. We may *additionally* author SKILL.md procedures (e.g., `analyze_opportunity` SKILL.md that says "1. fetch_attachment, 2. parse_pdf, 3. delegate to Compliance Officer, 4. ..." with §11.1 pitfalls noted) — these are progressive-disclosure docs the agents consult at runtime. Skills layered on toolsets is the right composition.

### `delegate_task` API (confirmed)

```python
# Single subagent
delegate_task(
    goal="Analyze opportunity 00000000-...-0001 end to end",
    role="orchestrator",       # default "leaf"; we use orchestrator for Capture Analyst (depth-2)
    toolsets=["gov_documents", "gov_compliance", "gov_risks", "gov_proposals", "human_review"],
    context="<rich context: opportunity + profile + parsed_chunks>",
)

# Parallel subagents (Capture Lead's fan-out)
delegate_task(tasks=[
    {"goal": "Analyze opportunity 1", "role": "orchestrator", "toolsets": [...], "context": ...},
    {"goal": "Analyze opportunity 2", "role": "orchestrator", "toolsets": [...], "context": ...},
    {"goal": "Analyze opportunity 3", "role": "orchestrator", "toolsets": [...], "context": ...},
])
```

Defaults: `max_concurrent_children: 3`, `max_spawn_depth: 1` (flat — orchestrator parents spawn leaf children that cannot delegate further).

**Our 5-agent design needs `max_spawn_depth: 2`** in `~/.hermes/config.yaml`:

```yaml
delegation:
  max_concurrent_children: 3            # 3 Capture Analysts in parallel
  max_spawn_depth: 2                    # Lead → Analyst (orchestrator) → Specialists (leaves)
  orchestrator_enabled: true            # required so role="orchestrator" is honored
  max_iterations: 50                    # default
  # Optional: model override per delegation level
  # model: "claude-haiku-4-5-20251001"
  # provider: "anthropic"
```

Without `max_spawn_depth: 2`, our Capture Analysts cannot spawn Compliance Officer / Risk Analyst / Proposal Strategist subagents — they'd be forced to leaf and have to inline all that work themselves. That defeats the architecture.

### Toolset restriction enforces skill ownership

Per-`delegate_task` `toolsets=[...]` restricts what tools the subagent has. This is the mechanism that prevents Capture Lead from accidentally calling `extract_requirements` directly. Capture Lead's own toolset list (set when Hermes spawned it as the root agent) excludes `gov_documents` / `gov_compliance` / `gov_risks` / `gov_proposals`. When it delegates to Capture Analysts, it grants them those toolsets via the `toolsets=[...]` parameter. Capture Analyst then re-grants narrower subsets to specialists.

The toolsets we register:

| Toolset | Tools | Granted to |
|---------|-------|------------|
| `gov_discovery` | `parse_goal`, `search_sam_opportunities`, `load_seeded_opportunities`, `rank_opportunities`, `summarize_run` | Capture Lead only |
| `gov_documents` | `fetch_attachment`, `parse_pdf`, `verify_source_page` | Capture Analyst |
| `gov_compliance` | `extract_requirements`, `score_fit` | Compliance Officer |
| `gov_risks` | `detect_risks` | Risk Analyst |
| `gov_proposals` | `generate_action_package` | Proposal Strategist |
| `human_review` | `request_human_review` | All agents (escalation gate) |

`fetch_attachment` and `verify_source_page` could be Hermes' built-in `web` toolset rather than custom — TBD in A9 spike. If Hermes' `web` is sufficient, we save effort and use what's already there.

### Personality: SOUL.md, AGENTS.md, HERMES.md, /personality

Hermes loads project context with priority `.hermes.md` > `HERMES.md` > `AGENTS.md` > `CLAUDE.md` > `.cursorrules`, walking from cwd to git root. **We wrote `HERMES.md` at the repo root** containing the project-wide rules (PRD §11.1 enforcement, evidence binding, no fabrication, approval gate, toolset list). Every agent (root and subagent) loads this automatically.

`SOUL.md` is the primary identity file in `HERMES_HOME` (`/var/lib/hermes` per CONTRACTS.md §4). It carries the overall Hermes-instance persona. We may not need to customize SOUL.md for the MVP — the per-agent personality is encoded in:

1. The **per-role prompt files** in `dev1-backend/prompts/agent_*.md` — these become the `goal` + `context` strings in `delegate_task`.
2. The repo-root `HERMES.md` for shared rules.

The `/personality [name]` command lets us swap presets per session. Useful for demoing different personas (e.g., a "Compliance Officer in DoD mode" with extra clearance vigilance).

### Memory strategy

- Per-run only for v1. `MEMORY.md` and `USER.md` files would persist; we can either point Hermes at an empty `HERMES_HOME` per run OR call `hermes memory clear` between dev runs.
- Cross-run learning (Hermes' "agent that grows with you") is post-MVP. Worth showcasing in a stretch demo if time.

### Trace events from subagents

Open question: does Hermes natively emit per-subagent lifecycle events to stdout/JSON, or do we instrument? The A9 integration spike will resolve this. If Hermes emits, we map to our `subagent_spawned` / `subagent_completed` event types in the bridge. If not, we wrap `delegate_task` ourselves.

---

## Why this beats a flat "agent with tools" architecture

For the Agents Track judges:

- **"What's reasoning, what's planning?"** → Capture Lead does goal parsing and ranking before delegating; each sub-agent has its own planning loop within its scope.
- **"How does it handle ambiguity?"** → Compliance Officer escalates `needs_human` on extraction collapse. Capture Lead respects subagent verdicts.
- **"How does it recover from errors?"** → Per-agent recovery branches; one Capture Analyst's failure doesn't crash siblings; Capture Lead emits partial results.
- **"What tools does it use, and why those?"** → Skills are scoped by agent role. Skills tell you what each agent CAN do. Prompt-level rules tell you what each SHOULD do.
- **"Does this feel like the future of software?"** → A run produces an audited, parallelized, source-cited capture analysis package in under a minute. Yes.
