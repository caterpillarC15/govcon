---
name: generate_reject_summary
description: Roy procedure for producing a slim, deterministic action package when fit_score.decision == "reject". No LLM call; the package's purpose is to document the blocker, not prepare a proposal.
version: 1.0.0
metadata:
  hermes:
    tags: [samrail, action-package, proposal-strategist, reject-mode, deterministic]
    category: gov
    requires_toolsets: [gov_proposals]
---

# Generate Reject Summary

Roy's procedure for **reject decisions only.** Slim shape; deterministic; no LLM call. The package's purpose is to **document the blocker** so the user can verify the decision and remember the constraint for future opportunities.

**For non-reject decisions, use `generate_full_action_package`** instead.

## When to Use

- You are Roy.
- The fit_score.decision is `reject`.
- Your delegate context includes `mode="reject_summary"`.

## Procedure

This procedure is deterministic — `generate_action_package` with `mode="reject_summary"` does NOT call an LLM. It constructs the slim package directly from inputs.

1. **Call `generate_action_package(mode="reject_summary")`:**
   ```
   pkg = generate_action_package(
     profile, opportunity, requirements, fit_score, risks,
     mode="reject_summary"
   )
   ```

2. **The skill returns this slim shape (no LLM):**
   ```json
   {
     "executive_summary": "Decision: REJECT — <opportunity title>. Critical blockers prevent pursuit: <first 2 blockers>.",
     "decision": "reject",
     "fit_score": <total_score>,
     "fit_rationale": "Per PRD §11.1, eligibility uncertainty or hard mismatch forces a reject decision regardless of capability strengths. See risk register for blockers.",
     "compliance_matrix": [
       { "requirement": <blocker_text>, "status": "missing", "evidence": "",
         "next_action": "Do not pursue — blocker cannot be resolved within scope.",
         "owner": "—" }
       /* one row per blocker */
     ],
     "risk_register": [
       /* only severity in {critical_blocker, major} */
     ],
     "proposal_checklist": [],
     "timeline": [],
     "partner_suggestions": [],
     "outreach_draft": { "subject": "", "body": "" },
     "human_approval_required": [
       "This opportunity is marked REJECT. Do not pursue without overriding the eligibility analysis.",
       "Confirm the eligibility blocker with a contracting officer or counsel before any external action.",
       "Human approval required before contacting a contracting officer.",
       "Human approval required before claiming compliance or certifications."
     ]
   }
   ```

3. **Return** the slim package.

## Why no LLM

- We're not preparing a proposal — there's nothing to prepare. The opportunity rejects.
- Generating a checklist or outreach for a reject opportunity wastes user time and budget. Worse, it could send a confusing signal that pursuit is still on the table.
- Deterministic construction is faster, cheaper, and more reliable.

## Pitfalls

- **Tempted to "write something useful" anyway.** Don't. The user needs to see clearly: "We rejected this. Here's why. Don't pursue." Empty arrays for proposal_checklist, timeline, partner_suggestions, and outreach are intentional.
- **Approval gate absent.** Even reject packages must show approval-required messages — specifically the "do not pursue without overriding" warning. The wrapper enforces this.
- **Mode confusion.** If you somehow get called with `mode="full"` on a reject decision, refuse. Michaela should never produce that combination; if it does, that's a §11.1 violation upstream.
- **Soft-pedaling the blocker.** "Can be addressed via teaming" is wrong here. The decision is final; teaming arrangements don't grant clearance, citizenship, or set-aside certification within reasonable timeframes.

## Verification

- `decision == "reject"`.
- `proposal_checklist == []`.
- `timeline == []`.
- `partner_suggestions == []`.
- `outreach_draft.subject == ""` AND `outreach_draft.body == ""`.
- `human_approval_required[0]` contains "REJECT" (the warning is unmissable).
- `compliance_matrix[]` has at least one row per blocker; status == "missing".
- Total cost: ~$0 (deterministic construction; no LLM call).

## Cross-skill note

This skill is invoked by Michaela on the reject branch of her per-opportunity orchestration recipe (which lives in `/root/michealaai`, not this pack). The §11.1 chain depends on:
1. Gate correctly returning `decision = "reject"` (via `score_fit_with_eligibility_check`).
2. Michaela correctly branching on the reject and calling THIS skill (not `generate_full_action_package`).
3. This skill returning the slim shape without re-running the LLM (which might be tempted to pad with optimistic prose).

Every link in the chain is enforced; the eval harness catches regressions.
