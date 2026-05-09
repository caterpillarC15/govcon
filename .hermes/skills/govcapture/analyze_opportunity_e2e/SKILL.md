---
name: analyze_opportunity_e2e
description: Capture Analyst procedure for analyzing one opportunity end to end. Fetches attachments, parses PDFs, delegates to Compliance Officer (extraction + scoring), then conditionally to Risk Analyst and Proposal Strategist based on the §11.1-aware verdict.
version: 1.0.0
metadata:
  hermes:
    tags: [govcapture, analysis, capture-analyst, delegation]
    category: gov
    requires_toolsets: [gov_documents]
---

# Analyze Opportunity End-to-End

Per-opportunity orchestration. Spawned once per top-ranked opportunity by the Capture Lead, in parallel with siblings. You own ONE opportunity from raw record to action-package bundle.

## When to Use

- You are a Capture Analyst (orchestrator role, depth 1).
- You've been delegated a single opportunity + the company profile.
- Output: bundle of `{requirements, fit_score, risks, action_package}` returned to Capture Lead.

## Procedure

1. **Fetch attachments** (parallel):
   ```
   for attachment_url in opportunity.attachments:
     fetch_attachment(attachment_url)   # parallel via Hermes' built-in HTTP
   ```
   On individual fetch failure: retry once. If still failing, mark missing and continue.

2. **Parse all fetched PDFs** (parallel):
   ```
   for path in fetched_paths:
     chunks_per_doc = parse_pdf(path)
   parsed_chunks = flatten(chunks_per_doc)
   ```
   If `unparseable=true` for ALL attachments and there's no other text source: escalate to `request_human_review`. If at least one parses, continue.

3. **Delegate to Compliance Officer** (leaf subagent):
   ```
   compliance_result = delegate_task(
     role="leaf",
     goal="Extract requirements and score fit. Apply PRD §11.1.",
     toolsets=["gov_compliance"],
     context={
       "opportunity": opportunity,
       "profile": profile,
       "parsed_chunks": parsed_chunks,
     }
   )
   # Returns {requirements, fit_score}
   ```

4. **BRANCH on the verdict** (this is the §11.1 enforcement at the orchestrator level):

   **If `compliance_result.fit_score.decision == "reject":**
   ```
   action_package = delegate_task(
     role="leaf",
     goal="Produce slim reject summary action package",
     toolsets=["gov_proposals"],
     context={
       "profile": profile,
       "opportunity": opportunity,
       "requirements": compliance_result.requirements,
       "fit_score": compliance_result.fit_score,
       "risks": [],   # don't run risks for reject
       "mode": "reject_summary",
     }
   )
   return {
     requirements: compliance_result.requirements,
     fit_score: compliance_result.fit_score,
     risks: [],   # explicitly empty
     action_package: action_package,
   }
   ```
   **DO NOT delegate to Risk Analyst. DO NOT delegate to Proposal Strategist with `mode="full"`. Ever.**

   **Else (strong_pursue / pursue / maybe):**
   ```
   risks = delegate_task(role="leaf", goal="Detect risks", toolsets=["gov_risks"], context={...})
   action_package = delegate_task(
     role="leaf",
     goal="Generate full action package",
     toolsets=["gov_proposals"],
     context={...with mode="full"...}
   )
   return {requirements, fit_score, risks, action_package}
   ```

5. **Return the bundle** to the Capture Lead.

## Pitfalls

- **PDFs parsed sequentially when they could be parallel.** The planner may default to a serial loop. Express parallel intent: "Parse these N attachments in parallel" — Hermes' parallel-tool-call feature should handle this.
- **Compliance Officer reject not respected.** The most dangerous failure mode. If you call Risk Analyst or Proposal Strategist (mode=full) for a reject opportunity, you're violating §11.1. The trace bridge logs every delegation; eval harness asserts. Don't.
- **Re-fetching the same attachment.** If you've already pulled it, use the local_path you got. Don't re-network.
- **Failure of one attachment cascading.** One PDF unparseable doesn't fail the whole opp. Continue with what you have. Mark missing in `requirements.missing_fields`.
- **Specialist timeout.** If Compliance Officer or Risk Analyst exceeds wall-clock, return partial bundle to Capture Lead with the missing pieces marked. Don't block the whole run.

## Verification

- The bundle returned has all 4 keys: `requirements`, `fit_score`, `risks`, `action_package`.
- For reject decisions: `risks == []` and `action_package.decision == "reject"` and the package's `proposal_checklist == []` (slim shape).
- For non-reject: all 4 keys populated; `action_package.human_approval_required` has at least 4 entries.
- Trace contains: 1+ `fetch_attachment` events, 1+ `parse_pdf` events, exactly 1 `delegate_task → compliance_officer` event, conditional `delegate_task → risk_analyst` and `delegate_task → proposal_strategist` events.
- Total tool calls in this analyst's branch ≤ 12 typically (more if many attachments).
