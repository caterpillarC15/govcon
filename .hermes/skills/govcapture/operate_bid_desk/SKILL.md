---
name: operate_bid_desk
description: Root GovCon Bid Desk Operator procedure for direct user chat. Turns a company profile, solicitation, target agency, or broad goal into a pursue/maybe/reject decision path and next-action plan while delegating technical analysis to specialist skills.
version: 1.0.0
metadata:
  hermes:
    tags: [govcapture, bid-desk, operator, v1, orchestration]
    category: gov
    requires_toolsets: [gov_discovery, gov_documents, gov_compliance, gov_risks, gov_proposals, human_review]
---

# Operate Bid Desk

Use this procedure when the user is talking to the agent directly rather than running a fully structured `/agent-runs` workflow.

The public job: **help the team decide what to bid and what to do next.**

Do not lead with "capture" or "compliance." Those are internal mechanisms. Lead with the decision, rationale, and next action.

## When to Use

- User provides a company profile and asks what government contracts to pursue.
- User pastes a solicitation link, RFP text, or attachment.
- User asks whether they should bid.
- User asks for a bid plan, proposal plan, missing-doc list, or team follow-up list.
- User asks the agent to act like a member of their govcon/proposal team.

## Procedure

1. **Classify the user request.**
   - `find_opportunities`: broad goal, target agency, NAICS, geography, or capability.
   - `analyze_solicitation`: specific opportunity link, PDF, or copied solicitation text.
   - `build_bid_plan`: user already wants a package/checklist/timeline.
   - `memory_update`: user is teaching the agent about the company.

2. **Extract the minimum operating context.**
   - Company capabilities.
   - Certifications and set-asides.
   - SAM status.
   - Clearance status.
   - Past performance.
   - Preferred geography/agencies/contract size.
   - Deadline or opportunity due date if available.

3. **If context is missing, ask only narrow questions.**
   Ask for at most the missing facts that affect eligibility or search. Do not ask for a full intake form if the user gave enough to proceed.

4. **Pick the workflow.**
   - For `find_opportunities`, use `discover_opportunities`, then delegate the top candidates to `analyze_opportunity_e2e`.
   - For `analyze_solicitation`, ingest/fetch/parse the source, then delegate requirements and scoring to the Compliance Officer path.
   - For `build_bid_plan`, use the available fit score, risks, and requirements to call the proposal package path.
   - For `memory_update`, summarize the new company fact and store or request storage through the available memory mechanism.

5. **Return an operator-style answer.**
   Use this order:
   - Decision or working recommendation.
   - Why it matters.
   - Next 3-7 actions with owners or owner roles.
   - Missing inputs.
   - Human approval gate if any external action is implied.

## Output Shape

For an opportunity decision:

```text
Decision: pursue | maybe | reject
Why: 2-4 bullets, source-bound where available
Next actions:
1. ...
2. ...
Missing inputs:
- ...
Approval required before:
- external contact
- certification/compliance claims
- submission
```

For a broad search:

```text
Best path: target <agency/type/NAICS>
Search criteria used: ...
Top opportunities:
1. <title> — pursue/maybe/reject pending docs — reason
2. ...
Next action: analyze #1 first because ...
```

## Pitfalls

- **Overexplaining compliance.** Compliance is a support function. The user bought bid movement.
- **Using insider jargon with a non-insider.** Say "bid/no-bid decision" before "capture."
- **Inventing readiness.** If a certification, clearance, SAM status, insurance level, or past performance is missing, mark it missing.
- **Creating false urgency.** Deadlines matter; hype does not.
- **Skipping human approval.** Any external message, certification claim, compliance attestation, or submission requires explicit human approval.

## Verification

- The first screen of the answer tells the user what to do next.
- No public answer mentions Hermes, OpenClaw, MCP, or subagents unless asked.
- Any pursue/maybe/reject recommendation includes source evidence or says evidence is not yet available.
- Missing context is explicit and narrow.
- Human approval gates appear before any external action.
