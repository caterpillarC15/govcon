---
name: generate_full_action_package
description: Proposal Strategist procedure for producing the §10.3 action package for pursue/strong_pursue/maybe decisions. All 11 sections; Sonnet-backed; approval gate non-negotiable; no fabrication.
version: 1.0.0
metadata:
  hermes:
    tags: [govcapture, action-package, proposal-strategist, full-mode]
    category: gov
    requires_toolsets: [gov_proposals]
---

# Generate Full Action Package

The Proposal Strategist's primary procedure for non-reject decisions. Produces the §10.3 deliverable — the artifact a small business owner reviews and acts on.

**For reject decisions, use `generate_reject_summary` instead** (deterministic, no LLM). The Capture Analyst calls one or the other, never both.

## When to Use

- You are the Proposal Strategist (leaf agent).
- The fit_score.decision is `strong_pursue`, `pursue`, or `maybe`.
- Your delegate context includes `mode="full"`.

## Procedure

1. **Call `generate_action_package(mode="full")`:**
   ```
   pkg = generate_action_package(
     profile, opportunity, requirements, fit_score, risks,
     mode="full"
   )
   ```
   The skill internally:
   - Constructs `compliance_matrix` deterministically where possible (status from profile match).
   - Calls Sonnet for the LLM-synthesized sections (executive_summary, fit_rationale, proposal_checklist, timeline, partner_suggestions, outreach_draft).
   - Validates output against §10.3 schema.
   - Appends approval-gate defaults if the LLM omitted any.

2. **Validate the package:**
   - All 11 §10.3 sections present.
   - `human_approval_required[]` has ≥ 4 entries.
   - `compliance_matrix[]` has at least one row per high/medium-confidence requirement.
   - `outreach_draft.body` uses generic salutation ("Contracting Officer" or similar) — no fabricated names.
   - For `decision == "maybe"`: `partner_suggestions[]` is populated AND `proposal_checklist[0]` resolves the gap before tactical items.

3. **Return** the `ActionPackageOutput`.

## Section-by-section guidance

### `executive_summary`
3-4 sentences. Decision, rationale headline, top action. Cite specialist verdicts ("Compliance Officer scored 88; Risk Analyst flagged no critical risks; first action: confirm SAM registration").

### `compliance_matrix`
One row per high/medium-confidence requirement. Status:
- `met` — profile data clearly satisfies (NAICS exact match, certification listed, insurance level adequate)
- `missing` — clear gap
- `unclear` — extraction confidence low or profile data ambiguous
- `not_applicable` — irrelevant to this profile/opp combo

Determine status deterministically when possible. Use LLM only for "unclear" judgments and to fill `next_action` and `owner`.

### `risk_register`
Pass-through from Risk Analyst output, filtered to severity ≥ moderate. Don't re-rank or re-severity.

### `proposal_checklist`
Concrete actions, ordered by deadline. Dated where possible.

**For `decision == "maybe"`: the FIRST item resolves the gap** (e.g., "Identify and sign teaming agreement with past-performance partner with $8M+ in SOC engagements — by 2026-05-16"). Tactical items follow.

### `timeline`
Date-anchored milestones from today through proposal due date minus 5 working days (review buffer). If due date < 7 days, surface as a critical risk and note in executive_summary that timeline is compressed.

### `partner_suggestions`
- Only for `decision == "maybe"` typically (and only when there's a real gap).
- Generic role descriptions only — no invented company names.
- Each suggestion: `partner_type`, `gap_solved`, `why_needed`, `outreach_angle`, `confidence`.

### `outreach_draft`
- `subject`: "Solicitation [number] — [title]" (no editorializing).
- `body`: 3 paragraphs. (1) Acknowledge solicitation + brief company intro. (2) Capability relevance to scope. (3) Clarifying question OR signal of interest. **Generic salutation only; never fabricate recipient names.**
- Body must NOT claim certifications, past performance, clearances, or compliance the company hasn't declared.

### `human_approval_required`
At minimum, these four:
- "Human approval required before contacting a contracting officer."
- "Human approval required before sending the outreach draft externally."
- "Human approval required before claiming compliance or certifications."
- "Human approval required before submitting any proposal materials."

The wrapper appends these defaults if you omitted them, but produce them yourself — don't rely on the wrapper.

## Pitfalls

- **Outreach hallucinating recipient names.** The most common §5.13 violation. Generic salutation only.
- **Compliance status hallucinated.** LLM will say `met` for things it didn't verify. Drive status from deterministic checks where possible.
- **Approval block buried at the bottom.** B's UI displays it prominently; ensure it's populated, not whether it's first or last in the JSON.
- **Generating a checklist for a reject.** Wrong skill. Use `generate_reject_summary` for reject.
- **Claiming certifications the profile doesn't declare.** Even if obvious from context, only profile-declared facts are usable.
- **Fabricated dollar values in outreach.** Don't. If the outreach mentions past contract values, only those that appear in `profile.past_performance`.

## Verification

- All 11 §10.3 sections present and non-empty (except `partner_suggestions` and `risk_register` which can be empty for clean strong-pursue cases).
- `human_approval_required` has ≥ 4 entries.
- `outreach_draft.body` does NOT contain any name string from a known list of fabrication test phrases (test in eval).
- For maybe decisions: `proposal_checklist[0]` mentions the gap (e.g., "partner", "team", or "resolve").
- Print preview renders document-grade (Dev 2's B8 verifies in UI).

## Cost note

This is the most expensive call in the run (~$0.04-0.05 per package on Sonnet). Plan accordingly — three pursue/maybe opportunities → ~$0.15. Stays well under PRD's $0.50 cap when paired with cheap extraction (Haiku).
