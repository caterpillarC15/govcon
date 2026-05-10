---
name: score_fit_with_eligibility_check
description: Gate procedure for scoring fit against the §5.7 rubric WITH the §11.1 eligibility short-circuit. Capability strengths CANNOT override hard eligibility blockers. This is the highest-stakes skill in the system; the deterministic short-circuit is non-negotiable.
version: 1.0.0
metadata:
  hermes:
    tags: [samrail, scoring, compliance-officer, eligibility, "section-11.1", critical]
    category: gov
    requires_toolsets: [gov_compliance]
---

# Score Fit with Eligibility Check (PRD §11.1)

**The most important skill in the system.** This is where the eligibility rule is enforced. PRD §17 calls eligibility hallucination "a serious user harm." This skill prevents it.

## When to Use

- You are Gate.
- You've completed `extract_requirements_with_evidence` and have a `RequirementExtractionOutput`.
- You need to produce a §10.2 `FitScoreOutput` with decision band and (potentially) reject short-circuit.

## Procedure

1. **Call `score_fit`:**
   ```
   fit_score = score_fit(profile, requirements, opportunity.due_date)
   ```

   The skill is **two-phase**:

   **Phase A — Deterministic dimension math (Python, no LLM):**

   For each of the 9 dimensions (§5.7), a Python function computes the score deterministically. Weights sum to 100:
   - capability: 20 (LLM-aided — capability matching against profile)
   - **eligibility: 15 (PURE DETERMINISTIC — see below)**
   - naics: 10 (deterministic — exact match)
   - past_performance: 15 (deterministic threshold check + LLM rationale)
   - certification: 10 (deterministic match against profile.certifications)
   - insurance_bonding: 10 (deterministic comparison)
   - deadline: 10 (deterministic days-until-due math)
   - complexity: 5 (LLM-aided)
   - geography: 5 (deterministic match)

   **Eligibility scoring (the §11.1 short-circuit):**
   ```
   blockers = []

   # Set-aside check
   for each requirement of type=eligibility with set-aside language:
     if requires 8(a) and "8(a)" not in profile.certifications: blockers.append(...)
     if requires HUBZone and "HUBZone" not in profile.certifications: blockers.append(...)
     if requires WOSB and "WOSB" not in profile.certifications: blockers.append(...)
     if requires SDVOSB and "SDVOSB" not in profile.certifications: blockers.append(...)

   # Clearance check
   for each requirement of type=security:
     if "Secret" required and profile.clearance_status != "secret": blockers.append(...)
     if "Top Secret" required and profile.clearance_status != "top_secret": blockers.append(...)

   # Critical-blocker requirements (is_blocker=True from extraction)
   for each requirement where is_blocker=True and confidence in {high, medium}:
     blockers.append(...)

   if blockers:
     eligibility_score = 0
     decision = "reject"  # FORCED
   else:
     eligibility_score = 15
     decision = compute_band_from_total(total)
   ```

   **Critical: `decision = "reject"` when blockers exist, regardless of `total_score`.**

   **Phase B — LLM rationale generation (Sonnet):**

   Given the breakdown + decision (already final), the LLM generates:
   - `strengths[]`
   - `weaknesses[]`
   - `missing_information[]`
   - `recommended_next_action`

   The LLM is constrained to **explain the decision, not change it.** If you find yourself producing prose that justifies a different decision than what Phase A computed, stop. The LLM cannot override the math.

2. **Validate output shape:**
   - `total_score` is sum of breakdown dimensions (assert == 100 ceiling check).
   - `decision` is one of: `strong_pursue` | `pursue` | `maybe` | `reject`.
   - `decision == "reject"` IF AND ONLY IF (`eligibility == 0` OR `total < 55`).
   - `blockers[]` populated when decision is reject due to eligibility (not when reject is due to low total without blockers).

3. **Return** the `FitScoreOutput`.

## Hard rules — PRD §11.1 enforcement

These rules are encoded at multiple layers. Memorize them.

- If eligibility is uncertain, score eligibility dimension **0** (not partial credit) AND emit a critical blocker AND set `decision = "reject"`.
- Set-aside mismatches (8(a), HUBZone, WOSB, EDWOSB, SDVOSB, VOSB) where the company has not declared the matching certification → **always** critical blocker. Never soft penalty.
- Clearance requirements not held by the company → **always** critical blocker.
- Foreign-ownership / citizenship requirements → critical blocker if unclear.
- Any critical eligibility blocker forces `decision = "reject"` regardless of capability/NAICS strengths. **Capability cannot soften eligibility.**

### Example (correct)

> Requirement: "Active U.S. Government Secret clearance required for all key personnel." Profile.clearance_status: "none".
>
> → Eligibility score: 0/15. Critical blocker added. Decision: reject. Capability score (e.g., 18/20) is recorded honestly but does NOT change the decision.

### Example (forbidden — must not produce)

> "Solicitation requires Secret clearance. Profile has no clearance. However, capability is strong and the NAICS aligns, so score 72, decision = pursue with note about clearance partner."
>
> This is the failure mode §11.1 exists to prevent. Don't produce it.

## Pitfalls

- **Letting Phase B (LLM rationale) override Phase A (math).** Never. Phase A is the source of truth for `decision`. Phase B explains; it doesn't decide.
- **Ignoring `is_blocker: true` flags from extraction.** Gate's previous step (`extract_requirements_with_evidence`) marks blockers. Honor them in the eligibility scoring.
- **Off-by-one on weights.** Sum the breakdown — assert it equals the maximum possible (100). Catch in tests.
- **Soft penalty for "maybe eligible".** Banned. If eligibility is uncertain, score is 0 + critical blocker + reject. There's no review path for v1.
- **Over-rewarding partial NAICS matches.** Match codes by full string equality. Partial-prefix matching (e.g., 5415 ≈ 541512) is a stretch and not in v1.

## Verification

- For the **reject fixture** (B11):
  - `eligibility_score == 0`
  - `decision == "reject"`
  - `blockers[]` is non-empty
  - `score_breakdown.capability >= 15` (capability is honestly strong; reject is due to clearance)
  - **Critical assertion (eval harness A12):** capability strong + decision reject = §11.1 enforcement working.

- For the **strong-pursue fixture** (B9):
  - `eligibility_score == 15` (no blockers)
  - `decision == "strong_pursue"`
  - `total_score >= 80`

- For the **maybe-needs-partner fixture** (B10):
  - `eligibility_score == 15` (no blockers; past-performance gap is a weakness, not an eligibility gate)
  - `decision == "maybe"`
  - `total_score in [55, 69]`
  - `weaknesses[]` includes a past-performance entry.

- The eval harness (A12) explicitly asserts §11.1: capability ≥ 15 AND decision == reject for the reject fixture. This catches regressions in CI.

## Cross-skill note

This skill returns to Gate's exit. Gate then returns `{requirements, fit_score}` to Michaela's opportunity branch, which branches on `fit_score.decision`. If reject, Michaela skips full packaging and calls Roy with `mode="reject_summary"`. **The §11.1 enforcement chain depends on every link respecting the verdict produced here.**
