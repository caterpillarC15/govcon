---
name: extract_requirements_with_evidence
description: Compliance Officer procedure for converting parsed solicitation chunks into structured requirements with hard evidence-binding rules. Every medium/high confidence requirement must include a verbatim source quote and page number.
version: 1.0.0
metadata:
  hermes:
    tags: [govcapture, extraction, compliance-officer, evidence]
    category: gov
    requires_toolsets: [gov_compliance]
---

# Extract Requirements with Evidence Binding

The Compliance Officer's first procedure. Convert parsed PDF text into structured requirements per PRD §10.1, with mandatory source quotes for every confident extraction.

## When to Use

- You are the Compliance Officer (leaf agent, depth 2).
- You've received `parsed_chunks` from the Capture Analyst.
- Output: §10.1 `RequirementExtractionOutput` with full evidence binding.

## Procedure

1. **Call `extract_requirements`:**
   ```
   raw = extract_requirements(parsed_chunks, opportunity_metadata)
   ```
   The skill internally:
   - Runs LLM with the per-type prompt (§11 of PRD).
   - Validates JSON shape against the §10.1 schema.
   - Retries once on invalid JSON with a stricter reminder.

2. **Post-validate evidence binding (the wrapper does this; verify the output):**
   - Every `requirement` with `confidence ∈ {high, medium}` MUST have:
     - Non-empty `evidence_snippet`
     - Valid `page_number` (1 ≤ page_number ≤ document page_count)
   - Verify `evidence_snippet` actually appears in the source chunk (fuzzy match ≥ 0.6 ratio).
   - If any of the above fails, downgrade that requirement's confidence to `low` and clear evidence.

3. **Surface conflicts:**
   - If the same field appears with contradictory values across chunks (e.g., two due dates), populate `conflicts[]` with `requires_human_review: true`.

4. **Surface missing fields:**
   - List every PRD §10.1 field type the document doesn't appear to address (e.g., insurance not mentioned) in `missing_fields[]`.

5. **Return** the `RequirementExtractionOutput` to the next step (`score_fit_with_eligibility_check`).

## Pitfalls

- **Hallucinated evidence snippets.** The most common failure. Even if the LLM produces high-confidence extractions, if the snippet doesn't appear in the source, downgrade to `low`. The fuzzy-match check is your guardrail — don't skip it.
- **Page numbers off-by-one.** Solicitation printed page numbers may differ from PDF physical page indices. Use `page_number` from `parse_pdf` (1-indexed PDF pages) consistently. Don't try to reconcile with printed numbers.
- **Per-type prompting drift.** If recall is below 80% on the demo fixtures, the wrapper will re-run with smaller chunks (low-confidence retry rule). Don't hand-craft alternative prompts at runtime.
- **Conflating capability gaps with eligibility blockers.** A requirement is `is_blocker: true` ONLY when it's a hard eligibility gate (set-aside, clearance, citizenship, certification mismatch). A capability gap or weak past performance is NOT a blocker — it's a weakness for `score_fit` to weigh.
- **Soft language interpreted as hard requirement.** "Cleared personnel preferred" → moderate risk, NOT a blocker. "Shall hold active Secret clearance" → blocker. Verb matters: shall/must/required = hard; preferred/encouraged = soft.

## Verification

- Every requirement with `confidence ∈ {high, medium}` has non-empty `evidence_snippet` AND valid `page_number`.
- Every requirement evidence_snippet appears in the source text (fuzzy match passes).
- For demo fixtures, recovers ≥ 80% of expected titles in `expected.json.required_titles`.
- For the reject fixture, the clearance requirement is extracted with `is_blocker: true` and evidence quoted from page 2.
- For the maybe-needs-partner fixture, the past-performance threshold ($10M aggregate) is extracted with `is_blocker: false` (it's a weakness, not an eligibility gate).
- For the adversarial image-only-PDF fixture, returns `requirements: []` and `missing_fields: ["all"]` — does not invent.

## Cross-skill note

This skill produces input for `score_fit_with_eligibility_check`. The two skills run in sequence within the Compliance Officer's turn. The §11.1 short-circuit lives in the next skill's deterministic logic — your job here is faithful, evidence-bound extraction.
