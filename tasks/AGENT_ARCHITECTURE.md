# Agent Architecture

The Michaela workloop that runs **on Hermes runtime infrastructure**. PRD §4.5
describes the runtime contract; `HERMES.md` (repo root) is the live runtime
context loaded by every Hermes agent; this doc owns the **multi-agent design**
— what each agent does, what tools it has, how they coordinate, and why.

> **Michaela bench is configured for Hermes.** `.hermes/` contains the current
> Michaela bench context, config, SOUL, and SKILL.md procedures. The tracked
> FastAPI runner/trace bridge now executes the seeded Michaela path; live
> Hermes CLI/sub-agent execution is still the remaining bridge mode. The §11.1
> eligibility short-circuit, evidence binding, no-fabrication rule, and
> approval gate are the active architecture rules.

---

## The bench at a glance

Seven named agents. One CEO (Michaela) plus six specialists. Each owns a
narrow domain; each is restricted at the toolset boundary so it physically
cannot do another agent's job. Publicly the customer sees one hired worker.

```
                    ┌──────────────────────────┐
                    │  Michaela  (root)        │  CEO / orchestrator
                    └────────────┬─────────────┘
                                 │ delegate_task(...)
       ┌─────────────┬───────────┼───────────┬─────────────┐
       ▼             ▼           ▼           ▼             ▼
   ┌────────┐  ┌────────┐  ┌──────────┐ ┌────────┐  ┌──────────┐
   │  Scot  │  │ Lenny  │  │   Gabby   │ │ Lance │  │  Happer  │
   │discovery│ │fit rank│  │eligibility│ │ market │  │executor  │
   └────────┘  └────────┘  └──────────┘ └────────┘  └──────────┘
                                                          │
                                                          ▼
                                                    ┌──────────┐
                                                    │   Roy    │  packaging /
                                                    │ handoff  │  user delivery
                                                    └──────────┘
```

Michaela talks to the user-facing API. Roy is invoked at the end of a run to
produce the bid memo / capability statement / contracting-officer email.
Scot, Lenny, Gabby, and Lance run on every opportunity; Happer is a utility
called by anyone who needs a repeatable retry-able task to land cleanly.

---

## The seven agents

### 1. Michaela — CEO / orchestrator

**Owns.** The whole board. Priorities. The user-facing answer.

**Does.**
- Sees all of the bench's outputs.
- Chooses the next move.
- Creates patterns (scaffolds repeat work).
- Assigns repeat work to Happer.
- Summarizes results for the user.
- Keeps user-facing output simple.

**Sample output.** `1 worth pursuing • 12 days left • 2 gaps • Bid memo ready`

**Toolset.** `gov_discovery_meta` — `parse_goal`, `summarize_run`,
`request_human_review`, plus `delegate_task` (orchestrator role, depth 0).
Michaela is **denied** `parse_pdf`, `extract_requirements`, `score_fit`,
`detect_risks`, `generate_action_package`, `query_usaspending`,
`fetch_attachment`. Specialists own those.

**Spawned with.** `agent_def.michaela` (see `.hermes/skills/govcapture/operate_bid_desk/SKILL.md`).

### 2. Scot — discovery / SAM.gov bulk scan

**Owns.** Top-of-funnel opportunity discovery.

**Does.**
- Downloads / reads the SAM bulk file.
- Filters active opportunities.
- Limits to the next 90 days.
- Matches against the company profile (cheap pre-filter only — Lenny does
  the deep ranking).
- Produces an initial shortlist.

**Sample output.** `Found 81,031 → next 90 days 14,000 → matched 42`

**Toolset.** `gov_discovery` — `search_sam`, `load_seeded_opportunities`,
`fetch_attachment` (light-weight URL pulls).

### 3. Lenny — fit ranking

**Owns.** The pursue / monitor / skip decision **support** (the verdict
itself involves Gabby).

**Does.**
- Scores every opportunity against the company profile.
- Checks NAICS, set-aside, keywords, deadline window, place of performance.
- Downranks bad-fit / sole-source / too-urgent items.
- Ranks opportunities for review.

**Sample output.** `Pursue 2 • Monitor 6 • Skip 39 • Best fit: VA Cybersecurity Support`

**Toolset.** `gov_fit` — `rank_opportunities`, `score_fit` (deterministic
dimension math; LLM rationale only). Writes to `fit_scores` and to
`opportunity_matches` (with `agent_name="lenny"`).

### 4. Gabby — eligibility blocker check (the §11.1 owner)

**Owns.** Hard-no / compliance gate. **The single source of truth for
eligibility.** No other agent can override Gabby's verdict.

**Does.**
- Extracts requirements from parsed solicitation chunks.
- Checks set-aside eligibility.
- Checks clearance requirements.
- Checks certifications.
- Checks citizenship / location restrictions.
- Checks mandatory site visits.
- Checks brand-name / reseller blockers.
- Produces risk flags scoped to compliance.

**Sample output.** `Eligible? no • Blocker: missing clearance • Do not bid`

**Toolset.** `gov_compliance` — `extract_requirements`, `score_fit`
(reads-only; the §11.1 short-circuit lives inside this skill),
`detect_risks` (compliance-tagged risks). Writes to `extracted_requirements`
and `risk_flags`.

**§11.1 enforcement chain.** Five points: (1) deterministic short-circuit
inside `score_fit`, (2) Gabby's own prompt, (3) Michaela's branching rule —
"never upgrade a Gabby reject", (4) Roy's `mode="reject_summary"` output
(no LLM, deterministic slim package), (5) eval harness assertion. Belt +
suspenders + parachute + backup parachute + ground.

### 5. Lance — competitive intelligence

**Owns.** Past awards, incumbents, market history, win-difficulty signal.

**Does.**
- Queries USASpending (and any market-history sources).
- Finds the incumbent.
- Finds prior award amounts.
- Finds recompete patterns.
- Finds likely primes / subs.
- Estimates win difficulty.

**Sample output.** `Incumbent: Tetra Tech • won 3× • difficulty: hard • probability: 22%`

**Toolset.** `gov_intel` — `query_usaspending` (planned),
`fetch_award_history` (planned). Writes to `risk_flags` with
`category="competitor_history"` until a dedicated `competitor_intel` table
lands.

### 6. Happer — execution runner

**Owns.** Repeatable boring jobs that other agents shouldn't context-switch
into.

**Does.**
- Runs boring jobs.
- Checks status.
- Moves files.
- Updates outputs.
- Retries safe failures.
- Keeps work from tying up Michaela.

**Sample output.** `Job done • rows processed • files written • errors found`

**Toolset.** `gov_documents` — `parse_pdf`, `fetch_attachment`,
`verify_source_page`. Writes to `documents` and `document_chunks`.

### 7. Roy — packaging / handoff

**Owns.** User-ready delivery.

**Does.**
- Turns agent outputs into an email / memo / package.
- Prepares the bid memo.
- Drafts the capability statement.
- Drafts the contracting-officer email.
- Packages links / files for human review.

**Sample output.** `Bid memo ready • capability statement drafted • email ready`

**Toolset.** `gov_proposals` — `generate_action_package` (Sonnet on full
mode, deterministic on `reject_summary`). Writes to `action_packages`.

**Two modes.** `full` for pursue / maybe; `reject_summary` for Gabby-rejected
opportunities (no LLM call — slim deterministic shape; `human_approval_required`
still emitted).

---

## How a run flows

A typical Michaela run on a 3-opportunity batch:

1. **`POST /agent-runs`** with `{goal, profile_id?, profile?}`. Auth: JWT.
2. **`api/agent/hermes_runner.py`** currently boots the seeded Michaela bridge;
   live mode boots Hermes with Michaela as root.
3. **Michaela** loads `HERMES.md` (project context) and her own SKILL.md
   (`operate_bid_desk`). She calls `parse_goal(goal)` → criteria.
4. **Michaela delegates to Scot** (`gov_discovery` toolset): bulk-scan SAM,
   match against profile, return shortlist.
5. **Michaela delegates to Lenny** in parallel for each top-N candidate
   (`gov_fit`): rank + deterministic `score_fit`. Returns
   `(opportunity, score, verdict)` triples.
6. **For each ranked opportunity**, Michaela fans out to Happer (parse PDFs)
   then to Gabby (eligibility + risks) and to Lance (market history) in
   parallel. Hermes' `delegate_task(tasks=[…])` runs these concurrently.
7. **If Gabby returns `decision = reject`**, Michaela short-circuits: skips
   Lenny's deep rerank, calls Roy with `mode="reject_summary"`, returns.
8. **Otherwise**, Michaela calls Roy with `mode="full"` to produce the
   action package.
9. **Michaela's `summarize_run` step** turns all bench outputs into the
   one-line user answer.

Trace events are emitted at each step. The seeded bridge already emits
CONTRACTS.md events through `api/agent/hermes_bridge.py`; live mode should map
Hermes subagent-spawn / subagent-complete events onto the same
`/agent-runs/{id}/stream` SSE contract.

---

## Toolset map (the ownership boundary)

Hermes' `delegate_task(toolsets=[…])` is the architectural enforcer.
Michaela cannot accidentally call `parse_pdf` because her toolset list
doesn't include `gov_documents`. The bench enforces architecture at the
Python level, not via prompt rules.

| Toolset           | Tools                                             | Granted to          |
|-------------------|---------------------------------------------------|---------------------|
| `gov_discovery_meta` | `parse_goal`, `summarize_run`, `request_human_review` | Michaela     |
| `gov_discovery`   | `search_sam`, `load_seeded_opportunities`         | Scot                |
| `gov_fit`         | `rank_opportunities`, `score_fit`                 | Lenny               |
| `gov_compliance`  | `extract_requirements`, `score_fit`, `detect_risks` | Gabby              |
| `gov_intel`       | `query_usaspending`, `fetch_award_history` (planned) | Lance           |
| `gov_documents`   | `parse_pdf`, `fetch_attachment`, `verify_source_page` | Happer          |
| `gov_proposals`   | `generate_action_package`                         | Roy                 |
| `human_review`    | `request_human_review`                            | Every agent (escalation) |

`score_fit` appears in two toolsets (Lenny + Gabby) intentionally: Lenny
runs the rubric for ranking; Gabby runs it for the eligibility short-circuit.
Same skill, two callers; the §11.1 deterministic gate fires regardless.

---

## §11.1 enforcement under the bench

| # | Where | What |
|---|-------|------|
| 1 | `score_fit` skill (deterministic, A6) | Short-circuit returns `decision=reject` when a hard blocker is present, regardless of capability dimensions. |
| 2 | Gabby's prompt (`agent_gabby.md`) | "You are the §11.1 gate. Capability strengths cannot soften eligibility." |
| 3 | Michaela's prompt | "Respect Gabby's reject. Skip Lenny's deep rerank; call Roy with `mode=reject_summary` only." |
| 4 | Roy's `reject_summary` mode | Deterministic slim package — no LLM, no upgrade path. |
| 5 | Eval harness (planned) | For the `reject` fixture: capability ≥ 15 AND decision == reject. |

PRD §17 calls eligibility hallucination "a serious user harm." The redundancy
is intentional.

---

## Trace events

The frontend timeline (B5) renders the bench tree live. Two extension events
on top of CONTRACTS.md §3:

```jsonc
{ "type": "subagent_spawned",
  "run_id": "uuid",
  "parent_id": "uuid | null",         // null when Michaela spawns
  "subagent_id": "uuid",
  "agent_name": "michaela | scot | lenny | gabby | lance | happer | roy",
  "context": { /* role-specific summary */ },
  "ts": "ISO-8601" }

{ "type": "subagent_completed",
  "run_id": "uuid",
  "subagent_id": "uuid",
  "status": "complete | failed | skipped",
  "ts": "ISO-8601" }
```

Demo reveal:

```
▼ Michaela
  ├─ tool: parse_goal              "Parsing user goal into search criteria…"
  ├─▶ Scot                          "Bulk-scanning SAM.gov…"   → 42 matched
  ├─▶ Lenny                         "Ranking 42 candidates…"   → top 3
  ├─▼ (parallel per opportunity)
  │  ├─▼ Opportunity 1
  │  │  ├─▶ Happer  parse_pdf ×2
  │  │  ├─▶ Gabby    eligibility ✓   risks: 0 critical
  │  │  ├─▶ Lance  incumbent: Tetra Tech, won 3×, hard
  │  │  └─▶ Roy     bid memo ready
  │  ├─▶ Opportunity 2  → maybe (partner suggested)
  │  └─▶ Opportunity 3  → reject (clearance blocker, p.2)
  └─ tool: summarize_run
```

This is the demo's wow shot.

---

## Cost & latency

For a 3-opportunity run (typical demo):

| Step | LLM calls | Estimated cost |
|------|-----------|----------------|
| Michaela: parse_goal + summarize_run + planning | ~4× Haiku + 2× Sonnet small | $0.02 |
| Scot: deterministic + 1 Haiku rationale | 1× Haiku | $0.001 |
| Lenny: deterministic ranker + LLM scoring rationale | 3× Haiku | $0.005 |
| Gabby ×3 (one per opp): extract_requirements + score_fit rationale | 3× (1 Sonnet + 1 Haiku) | $0.07 |
| Lance ×3: USASpending lookup (no LLM) + 1 Haiku synthesis | 3× Haiku | $0.005 |
| Happer ×3: parse_pdf (no LLM) | 0 | $0 |
| Roy ×3: 2 full mode (Sonnet) + 1 reject_summary (deterministic) | 2× Sonnet | $0.10 |
| **Total** |  | **≈ $0.20** |

Comfortably under the $0.50 cap.

Latency:

| Path | Time |
|------|------|
| Sequential | ~2.5 min |
| Bench parallelized (Hermes `delegate_task(tasks=[…])`) | ~1.0 min |

---

## Failure modes per agent

| Agent | Failure | Recovery |
|-------|---------|----------|
| Michaela | `search_sam` 429 / 5xx (via Scot) | falls back to `load_seeded_opportunities` |
| Scot | Rate limit | exponential backoff, then seeded fallback |
| Lenny | `score_fit` deterministic crash | abort that opp; report partial to Michaela |
| Gabby | `extract_requirements` low confidence | re-chunk smaller; retry once; on second failure, accept degraded output and flag |
| Gabby | hard blocker found | invoke §11.1 short-circuit, decision = reject, stop deep analysis |
| Lance | USASpending unreachable | continue with `incumbent: unknown`, flag |
| Happer | `parse_pdf` unparseable for ALL attachments | escalate to `request_human_review` |
| Roy | invalid JSON (full mode) | retry once; on failure, fall back to deterministic minimal package |
| Sub-agent timeout | wall-clock | parent records partial result; continues with siblings |

Michaela always emits `run_completed`, even with partial sub-agent failures.

---

## Memory and isolation

- **Per-run memory** by default. Cross-run learning ("Hermes remembers your
  company's certifications") is post-MVP.
- **Per-agent isolation.** Sub-agents don't see other sub-agents' memory.
  State sharing happens via delegation return values.
- **Michaela remembers the run.** She can reference earlier bench outputs in
  `summarize_run`.
- **Specialists are stateless across opportunities.** Each Gabby instance
  starts fresh — no contamination between opp 1 and opp 2.

`hermes memory clear` between dev runs.

---

## History (preserved for context)

Earlier iterations of this design used five agents — Capture Lead, Capture
Analyst, Compliance Officer, Risk Analyst, Proposal Strategist — with a
two-tier delegation tree (Lead → Analyst → 3 specialists). The 7-agent
bench is the same structure with named identities and one new specialist
(Lance for competitive intel) plus an explicit execution runner (Happer)
extracted from what used to be Capture Analyst's inline parse work. The
Risk Analyst's role was folded into Gabby (compliance risks) and Lenny
(fit-related downranks). The §11.1 chain, evidence binding, no-fabrication,
and approval gate carry over unchanged.

If a doc still references "Capture Lead" / "Compliance Officer" /
"Proposal Strategist", treat the mapping as: Capture Lead → Michaela,
Compliance Officer → Gabby, Proposal Strategist → Roy. Risk Analyst is
absorbed into Gabby + Lenny. Capture Analyst is no longer a distinct role —
Michaela coordinates the bench directly with `delegate_task(tasks=[…])`.
