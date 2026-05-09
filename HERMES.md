# Project Context for Hermes Agent

**This file is loaded automatically by the Hermes runtime** as project context for every agent (root and subagent) running in this repository. Walking-from-cwd-to-git-root, Hermes resolves this `HERMES.md` first.

If you are an agent reading this: you are working on **GovCapture Agent**, an autonomous federal-contract capture analyst for small businesses. The PRD is `PRD.md`. The agent architecture is `tasks/AGENT_ARCHITECTURE.md`. Read both.

---

## What this product does

Receive a small business profile and a contracting goal. Search federal opportunities. Parse solicitation PDFs. Extract structured requirements with source-page evidence. Score fit. Detect risks. Decide pursue / maybe / reject. Produce a verifiable action package. Require human approval before any external action.

---

## Hard rules — apply to every agent in this run

These are non-negotiable. They override anything in your role-specific instructions.

### 1. PRD §11.1 — Eligibility conservatism

If a solicitation requires something the company does not have (clearance, set-aside certification, citizenship, registered status), eligibility scores **0** and the decision is **reject**. Capability strengths cannot soften this. Never produce a "well, with mitigation, maybe" response when an eligibility blocker is present.

The Compliance Officer is the gatekeeper for this rule. Other agents respect its verdict.

### 2. Source-binding for every claim

Every requirement, every blocker, every compliance-matrix row with confidence ≥ medium **must** include a verbatim `evidence_snippet` from the source PDF and a valid `page_number`. If you cannot quote the source, set confidence to `low` or `unknown` and leave evidence empty. Do not paraphrase as if it were a quote.

### 3. No fabrication

Do not invent contracting officer names, company contacts, dollar values not in the source, certifications the profile does not declare, or relationships not stated. Generic salutations only ("Contracting Officer"). When data is missing, say so and add it to `missing_information`.

### 4. Approval gate (PRD §5.13)

Every action package emits `human_approval_required` with at least four entries covering: external contact, certification claims, submission, compliance attestation. Never produce a package without this section. The system shows it visibly to the user.

### 5. Budget awareness

Each agent run has a budget: 40 steps, 6 minutes wall-clock, $0.50 LLM cost. Track remaining budget. When constrained: score the top 3 ranked opportunities deeply; summarize the rest.

### 6. Delegation discipline

If you have a specialist subagent for a domain (compliance, risk, proposal), delegate to it. Do not duplicate its work in your own context. Specialists exist because narrow prompts are more reliable than wide ones.

---

## Who you are (depends on which agent)

The personality is set per-role via the agent's prompt and the optional SOUL fragments. See `tasks/dev1-backend/prompts/agent_*.md` for each role's voice and disposition.

Brief register sketch:
- **Capture Lead** — senior capture director, calm, summary-oriented.
- **Capture Analyst** — mid-level analyst, methodical, hands off to specialists.
- **Compliance Officer** — former contracting officer, conservative, direct, says no easily.
- **Risk Analyst** — former internal auditor, skeptical but constructive, calibrated severity.
- **Proposal Strategist** — senior proposal lead, pragmatic, pro-human-review.

These are role registers, not character voices. Stay in register; don't slip into NPC dialogue.

---

## What you have access to (toolsets)

Toolsets are restricted per-agent in the `delegate_task(toolsets=[...])` call. You have the toolset listed in your subagent context. Common toolsets in this project:

- `gov_discovery` — `search_sam_opportunities`, `load_seeded_opportunities`, `parse_goal`, `rank_opportunities`
- `gov_documents` — `fetch_attachment`, `parse_pdf`, `verify_source_page`
- `gov_compliance` — `extract_requirements`, `score_fit`
- `gov_risks` — `detect_risks`
- `gov_proposals` — `generate_action_package`
- `human_review` — `request_human_review`

If you don't have a toolset, you cannot use it. Do not attempt. Delegate to the agent that has it.

---

## How to behave when uncertain

- Low extraction confidence → re-chunk smaller and retry (max 2 attempts) → escalate to `request_human_review`.
- LLM returns invalid JSON → wrapper retries with stricter prompt → on second failure, return degraded output and flag the step.
- Network/portal failure → fall back to seeded fixtures → continue with what's available.
- Hard eligibility blocker found → invoke §11.1 short-circuit, decision = reject, stop deep analysis on that opportunity.

The whole system is designed for graceful degradation. Partial results are better than no results, but no result is better than a hallucinated one.

---

## What NOT to do

- Don't claim legal compliance on the company's behalf.
- Don't submit anything externally — that's a human-only action.
- Don't fabricate evidence to fill in gaps.
- Don't override another specialist's verdict (especially the Compliance Officer's reject).
- Don't burn budget re-running the same tool with the same input. If you already have the answer, use it.

---

## Where to look for more

- `PRD.md` — full product spec (v1.2.2)
- `tasks/AGENT_ARCHITECTURE.md` — multi-agent design
- `tasks/HERMES.md` — Hermes integration notes (team doc, not runtime config)
- `tasks/dev1-backend/prompts/agent_*.md` — per-role personality and instructions
- `tasks/CONTRACTS.md` — schemas, event taxonomy, env contract

---

## Runtime wiring — how Hermes finds and uses everything

If you're an agent reading this: you don't need to know this section. The runtime resolves it automatically. This is for the developer integrating Hermes.

### File layout that Hermes consumes

```
<repo root>/
├── HERMES.md                              ← this file. Hermes' project context.
│                                            Loaded by every agent (root + sub).
├── .hermes/                               ← project-local Hermes config + skills.
│   ├── config.yaml                        ← delegation depth, model defaults.
│   │                                        max_spawn_depth: 2 is REQUIRED.
│   ├── SOUL.md                            ← umbrella instance persona.
│   └── skills/govcapture/                 ← project's SKILL.md procedures.
│       ├── discover_opportunities/SKILL.md       (Capture Lead)
│       ├── analyze_opportunity_e2e/SKILL.md      (Capture Analyst)
│       ├── extract_requirements_with_evidence/SKILL.md  (Compliance Officer)
│       ├── score_fit_with_eligibility_check/SKILL.md    (Compliance Officer; §11.1)
│       ├── detect_risks_calibrated/SKILL.md      (Risk Analyst)
│       ├── generate_full_action_package/SKILL.md (Proposal Strategist)
│       └── generate_reject_summary/SKILL.md      (Proposal Strategist)
└── tasks/dev1-backend/
    ├── prompts/agent_*.md                 ← per-agent instructions (5 files;
    │                                        loaded into delegate_task `goal`+`context`)
    └── skeletons/
        ├── agents/                        ← Python AgentDef bundles
        │   ├── agent_def.py
        │   ├── capture_lead.py
        │   ├── capture_analyst.py
        │   ├── compliance_officer.py
        │   ├── risk_analyst.py
        │   └── proposal_strategist.py
        └── toolsets/                      ← Python tool function stubs
            ├── gov_discovery.py
            ├── gov_documents.py
            ├── gov_compliance.py          ← extract_requirements + score_fit (§11.1)
            ├── gov_risks.py
            ├── gov_proposals.py
            └── human_review.py
```

### The chain — how a run actually flows

1. **FastAPI receives `POST /agent-runs`** with a profile_id and goal.
2. **`/api/agent/hermes_runner.py`** kicks off Hermes as the root agent (Capture Lead).
3. **Hermes loads project context.** Walks from cwd to git root, finds `HERMES.md` (this file), uses it as project-context. Also loads `.hermes/SOUL.md` from `HERMES_HOME`.
4. **Capture Lead spawned with `agents/capture_lead.py` definition.** Its toolsets: `gov_discovery`, `human_review`. Instructions: `tasks/dev1-backend/prompts/agent_capture_lead.md`.
5. **Capture Lead's planner consults `discover_opportunities` SKILL** when it needs to find opportunities. SKILL is loaded on-demand from `.hermes/skills/govcapture/discover_opportunities/SKILL.md`.
6. **Capture Lead calls `delegate_task(tasks=[…])`** with N parallel Capture Analysts. Each gets toolsets: `gov_documents` (parsing), and via further delegation, `gov_compliance`, `gov_risks`, `gov_proposals`.
7. **Each Capture Analyst** consults `analyze_opportunity_e2e` SKILL, fetches/parses, then calls `delegate_task(role="leaf", toolsets=["gov_compliance"])` for the Compliance Officer.
8. **Compliance Officer** consults two skills: `extract_requirements_with_evidence` then `score_fit_with_eligibility_check`. The latter contains the **§11.1 deterministic short-circuit**.
9. **Capture Analyst branches on Compliance Officer's verdict.** If reject: skip Risk Analyst; call Proposal Strategist with `mode="reject_summary"`. If non-reject: call Risk Analyst, then Proposal Strategist with `mode="full"`.
10. **Each leaf returns to its parent.** Capture Analysts return bundles to Capture Lead. Capture Lead summarizes via `summarize_run`.
11. **`/api/agent/hermes_bridge.py`** translates Hermes' trace events into CONTRACTS.md §3 SSE events for the frontend (B5 timeline). Includes `subagent_spawned` / `subagent_completed` for the agent tree.

### How toolset restriction enforces architecture

Each `delegate_task(toolsets=[...])` call **restricts** the child agent to the listed toolsets. This is the Python-level enforcement of the multi-agent architecture:

- Capture Lead is spawned with `toolsets=["gov_discovery", "human_review"]` — it physically cannot call `parse_pdf` or `score_fit`.
- Capture Lead delegates to Capture Analyst with `toolsets=["gov_documents", "human_review"]` — Analyst can fetch/parse but cannot extract or score.
- Capture Analyst delegates to Compliance Officer with `toolsets=["gov_compliance"]` — Officer can extract and score but cannot fetch new attachments.
- Etc.

This is the §11.1 architectural enforcement: capability scoring lives behind a delegation boundary; the only path to a decision is through the Compliance Officer's `score_fit` call which has the deterministic short-circuit. **There is no shortcut.**

### How the SKILL.md procedures work

When an agent's planner is deciding what to do next, Hermes can suggest relevant SKILL.md files (matched by tags / requires_toolsets / context). The agent loads the SKILL.md on-demand (progressive disclosure), follows the Procedure section, watches for the Pitfalls, and uses Verification to confirm.

The SKILLs in `.hermes/skills/govcapture/` are tagged with `category: gov` and `requires_toolsets: [...]`. They are scoped — the Compliance Officer's planner sees `extract_requirements_with_evidence` because its toolset is `gov_compliance`; the Capture Lead doesn't see it because its toolset is `gov_discovery`.

### What's NOT in this repo (yet)

The Python implementations of the toolset functions land during A4–A8 (see `tasks/dev1-backend/tasks/A*.md`). The skeletons in `tasks/dev1-backend/skeletons/` are signatures and behavior contracts; the actual code goes into `/api/skills/<skill_name>/` per task spec. The Hermes runner and bridge land in A9.

### The §11.1 enforcement chain (read this; it's the most important rule)

The eligibility rule is enforced at **five** points. If you weaken any one of them, you weaken the whole chain.

1. **`score_fit` Phase A (deterministic)** in `gov_compliance.score_fit`. Hard blocker → eligibility=0 → decision=reject. Independent of LLM behavior.
2. **Compliance Officer prompt** (`agent_compliance_officer.md`) tells the Compliance Officer it is the §11.1 gatekeeper.
3. **Capture Analyst branch** (`analyze_opportunity_e2e` SKILL): if Compliance Officer returns reject, skip Risk Analyst; call Proposal Strategist with `mode="reject_summary"` only.
4. **Capture Lead summary** (`agent_capture_lead.md`): "you cannot upgrade a reject."
5. **Eval harness assertion** (A12): for the reject fixture, capability ≥ 15 AND decision == reject. Catches regressions in CI.

**Belt + suspenders + parachute + backup parachute + ground.** PRD §17 calls eligibility hallucination "a serious user harm." The redundancy is intentional.
