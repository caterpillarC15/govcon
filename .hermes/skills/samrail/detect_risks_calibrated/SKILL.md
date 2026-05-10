---
name: detect_risks_calibrated
description: Gate procedure for identifying risks across the 12 PRD §5.8 categories with calibrated severity. Cross-checks eligibility blockers; caps output at 8 actionable risks. Skipped for reject decisions.
version: 1.0.0
metadata:
  hermes:
    tags: [samrail, risk, gabby]
    category: gov
    requires_toolsets: [gov_risks]
---

# Detect Risks (Calibrated Severity)

Gate's risk-calibration procedure. Take profile + requirements + fit_score → produce calibrated `RiskFlag[]`.

**Skipped for reject decisions** by Michaela's branching logic (the per-opportunity orchestration recipe lives in `/root/michealaai`, not in this pack). You only run when decision ∈ {strong_pursue, pursue, maybe}.

## When to Use

- You are Gate.
- You've been delegated with `(profile, requirements, fit_score)` context.
- The opportunity is NOT a reject — Michaela already filtered.

## Procedure

1. **Call `detect_risks`:**
   ```
   risks = detect_risks(profile, requirements, fit_score)
   ```
   Returns up to 8 `RiskFlag` items. The skill enforces the cap; if the LLM produced more, the wrapper truncates by severity priority.

2. **Cross-check Gate's blockers (the wrapper handles this; verify):**
   - For each entry in `fit_score.blockers[]`, ensure a corresponding `RiskFlag` with `severity == "critical_blocker"` exists.
   - If the LLM missed one, the wrapper deterministically appends it. Verify post-call.

3. **Set `requires_human_review: true`** for:
   - Every `critical_blocker` (always).
   - Any risk where you're uncertain about severity.

4. **Return** the `RiskFlag[]`.

## The 12 risk categories (PRD §5.8)

Use these exact names — the schema validates against them:

| Category | When to flag |
|----------|--------------|
| `clearance_required_but_unavailable` | Solicitation requires clearance level the profile doesn't hold |
| `set_aside_mismatch` | Set-aside type doesn't match profile certifications |
| `certification_gap` | Required cert (CMMC L3, ISO 27001, etc.) not held |
| `past_performance_weakness` | Profile aggregate / similarity below requirement threshold |
| `deadline_too_close` | Days-until-due ≤ 14 with significant proposal effort |
| `missing_or_unclear_attachments` | Referenced doc absent or unparseable |
| `submission_ambiguity` | Format / portal / contact not clearly specified |
| `insurance_or_bonding_gap` | Required level above profile coverage |
| `scope_mismatch` | Solicitation scope outside profile capabilities (partial overlap only) |
| `legal_compliance_review_required` | Unusual clauses (ITAR, classified handling, foreign-ownership) |
| `pricing_complexity` | Cost-reimbursement, T&M ceiling, audited rate requirements |
| `required_document_not_found` | Specific form/narrative referenced but not attached |

## Severity calibration

Use these definitions, not your gut:

| Severity | Definition |
|----------|------------|
| `critical_blocker` | Unresolved = company cannot win or would be non-compliant |
| `major` | Significant; likely to lose without active mitigation |
| `moderate` | Requires attention; not pursuit-killing |
| `minor` | Worth noting, unlikely to affect outcome |

**Rule of thumb:** when between two severities, pick the **lower** one and set `requires_human_review: true`. Forces the human to decide rather than your guess becoming policy.

## Mitigation rules

- Be **concrete.** "Team with a partner" is too vague. "Identify a past-performance partner with $8M+ in similar SOC engagements within two weeks" is concrete.
- Don't invent procedures. "Apply for clearance" is not a mitigation for a 60-day deadline — clearance processes take 6-18 months.
- For deadline risks: name a specific cut-off. "If a teaming agreement isn't signed by [date], walk away."
- For document risks: name what to request. "Request the missing Q&A attachment from the contracting officer."

## Pitfalls

- **Over-flagging.** Models tend to surface every conceivable risk. The cap-at-8 rule and post-truncation handle this, but you should produce relevant risks, not exhaustive ones.
- **Severity inflation.** "Major" for things that are "moderate." Use the calibration table.
- **Forgetting the cross-check.** If a Gate blocker doesn't appear here as a critical_blocker risk, the wrapper adds it. Don't rely on the wrapper as a crutch — produce them yourself.
- **Mitigation hallucination.** Mitigations like "obtain SCIF facility" are obvious; don't invent specific government processes.
- **Running on a reject opportunity.** You shouldn't be running. If your context says decision == reject, return `[]` with a log message — Michaela should not have delegated risk calibration to you.

## Verification

- Output is `RiskFlag[]` with at most 8 items.
- For strong-pursue fixture: 0 critical_blockers; possibly some moderate/minor.
- For maybe-needs-partner fixture: 1+ major risk for past-performance weakness; 0 critical.
- For reject fixture (if you somehow run on it): 1+ critical_blocker matching the eligibility issue. But Michaela SHOULD NOT have delegated; flag this in standup if it happens.
- Every critical_blocker has `requires_human_review: true`.
- Every risk has a non-empty `mitigation` field.
- Every Gate blocker appears as a critical_blocker risk in your output.
