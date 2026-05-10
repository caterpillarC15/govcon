# Demo Script — Stage Directions

Canonical hackathon demo. Source: PRD §13.1, expanded with practical stage directions, fallback plans, and rehearsal checklist.

**Owner:** Track B drives the stage; Track A is on the laptop's terminal in case live tools need restart. B has final say on choreography.

---

## Pre-stage checklist (T-30 min)

- [ ] VX1 deployed, `https://<demo-host>/healthz` returns 200.
- [ ] `make fixtures-validate` and the backend skill/API tests pass locally and on VX1.
- [ ] Demo company profile seeded through Supabase/API if the run UI is being shown.
- [ ] All four fixtures loaded; `load_seeded_opportunities` returns strong-pursue, maybe, reject, and adversarial-image-pdf.
- [ ] Backup demo video exists and plays, if a video fallback has been produced.
- [ ] Browser tab open to the deployed landing or authenticated `/web` shell.
- [ ] Real run UI is only shown after the seeded runner/bridge has been verified against prod Supabase.
- [ ] Phone WiFi tethered as a backup network.
- [ ] LLM cost dashboard checked; budget remaining for ~10 demo runs.
- [ ] `DEMO_USE_SEEDED_ONLY=true` set on VX1 to force seeded path (no SAM live calls during stage).

---

## Stage script (3:00 total)

### 0:00 — 0:30 — Problem framing

> Small businesses leave billions in federal contracts on the table because qualifying an opportunity takes hours of PDF reading, eligibility-checking, and compliance-matrix building. We built an autonomous capture analyst that does the first-pass work in minutes. Every output is source-cited; every sensitive action requires human approval.

**On screen:** Title slide or landing page.

**Energy:** confident, fast. Don't over-explain — the next 2:30 is the proof.

### 0:30 — 1:00 — Setup

Show the demo profile (B13: Lone Star CyberWorks, Austin TX, no 8(a), CMMC L2, no clearance, $1.5M past performance).

> This is a real-shaped small business. Twelve people. Texas. Cybersecurity. Limited past performance. No clearance.

Type the goal:

> Find cybersecurity opportunities we can pursue in the next 60 days.

Click **Start Capture Run**.

**On screen:** profile summary panel + goal text + agent run timeline.

### 1:00 — 2:00 — Live agent run

The §5.3 timeline animates as `trace-event` SSE events arrive. **Talking track while the agent works:**

> The agent is choosing its own tools. There's the planner picking `search_sam_opportunities`, then `parse_pdf` on the attachments, then `extract_requirements` against each document, then `score_fit` against our profile, and `detect_risks` against the rubric.

**Click into a tool call** (e.g., `extract_requirements` on opportunity 1). Show the input/output JSON in the timeline expansion.

> Every tool call is logged with its input, output, latency, and cost. This is what makes the agent verifiable instead of magical.

When the three opportunities settle into ranked cards:

- **Strong-pursue** (88/100). Click into it.
  > Capability match, NAICS match, set-aside compatible, deadline 35 days out. Action package generated.

- **Maybe — needs partner** (64/100). Click into it.
  > Past-performance threshold of $10M. We have $1.5M. Agent surfaces a partner suggestion: "team with a past-performance partner who has $8M+ in similar contracts." Concrete gap, concrete next step.

- **Reject** (clearance blocker). Click into it.
  > Solicitation requires Secret clearance. We have none. Even though capability and NAICS are strong, the agent short-circuits: eligibility score zero, critical blocker, decision = reject. No optimistic "well, maybe with a teaming arrangement." The eligibility rule is hard.

**Click an evidence snippet** on the reject card → source PDF opens at the cited page.

> Every claim is source-cited. The blocker isn't a hallucination. It's on page 2 of the solicitation.

### 2:00 — 2:30 — Output

Open the action package on the strong-pursue opportunity.

> Executive brief. Compliance matrix — every requirement has a status, evidence, next action, and owner. Risk register. Proposal checklist with concrete deadlines. Outreach draft. And — critically — a human approval block before any of this gets sent or claimed externally.

Scroll through quickly. Don't dwell on any one section.

### 2:30 — 3:00 — Close

> Every claim has source evidence. Every sensitive action requires human approval. The agent picks tools, recovers from failures, stays within a 50-cent cost budget per run, and produces output a small business owner can verify and act on. This is the first-pass capture analyst that small businesses can't afford to hire — running on a single sixty-four-gig box, costing pennies per run.

(Beat.)

> Questions?

---

## Backup demo paths

Things that fail live, and what to do.

### Live agent run hangs or errors

**Trigger:** any timeline step shows `failed` and doesn't recover within ~10 seconds.

**Action:**
1. Don't panic. Say: "the agent is recovering — you can see the recovery branch in the trace." Give it 5 more seconds.
2. If still stuck, switch tabs to the **pre-cached run** (a saved completed `agent-run` from the same fixtures). Walk the action package as if live.
3. Backup video as last resort: `/web/public/demo/backup-run.mp4`.

### VX1 unreachable

**Trigger:** browser shows network error or 502.

**Action:**
1. Switch to localhost: `http://localhost:8000` (already running on the demo laptop). Same fixtures, same flow.
2. If localhost also fails: play backup video.

### Specific skill fails (e.g., Hermes browser tool)

**Trigger:** `tool_returned` with `error` for `fetch_attachment`, `verify_source_page`, or any other skill.

**Action:** This is actually a feature — narrate it.
> The agent caught the failure. Look — it's falling back to the seeded path. This is the recovery logic in action.

The planner has fallbacks per PRD §4.5; Hermes' planner respects the rule "if a skill fails, try the fallback skill listed in the planner instructions." Trust them.

### Cost budget exceeded mid-run

Should never happen with seeded fixtures (they're cheap). If it does, the planner emits a partial action package and flags incompleteness. Narrate that as graceful degradation.

---

## Rehearsal checklist (S5, T-2h)

- [ ] Run the full 3-minute script end-to-end on stage hardware.
- [ ] Time it. If over 3:30, cut the talking-track in 1:00–2:00 segment.
- [ ] Have the second dev sit in the audience and identify any UI element that doesn't read clearly from 30 feet (font size, contrast).
- [ ] Try one intentional failure (kill the Hermes/FastAPI bridge mid-run) to confirm the recovery narrative works once the bridge exists.
- [ ] Confirm backup video plays from a fresh browser tab (no cached-only).
- [ ] Charge the laptop. Plug it in. Don't trust battery.
- [ ] HDMI / display adapter tested on the actual stage projector if possible.

---

## What NOT to demo

- Live SAM.gov calls (rate limits, latency, demo gods).
- The eval harness output (it's a credibility tool for judges who ask, not a stage feature).
- The Vultr deployment dashboard.
- Anything that requires more than one click to set up on stage.

---

## What to mention if asked

- **"How does it handle edge cases?"** → Show the §19 eval harness output. Mention the adversarial image-only PDF fixture and the recovery path.
- **"What's the cost?"** → "Under 50 cents per run with the current model mix — Sonnet for synthesis, Haiku for cheap passes."
- **"Where does the data live?"** → "Supabase hosts Postgres, Auth, and Storage. The Vultr box hosts FastAPI, Hermes, Redis, and nginx. PRD §18 covers handling rules."
- **"What about Texas data?"** → "Optional layer. We can pull state and local procurement from `data.austintexas.gov` and friends as a stretch. Federal SAM.gov is the v1 focus."
- **"Will this submit proposals?"** → "No. Hard line. Human approval is required before any external action. PRD §5.13."
