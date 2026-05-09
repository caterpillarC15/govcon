# GovCapture Agent PRD

## Product Requirements Document

**Product name:** GovCapture Agent
**Document status:** MVP PRD v1.1
**Primary track:** Agents Track
**Primary objective:** Build an autonomous AI capture agent that turns a small business profile and government contracting goal into a useful federal opportunity analysis package by searching opportunities, parsing solicitation documents, extracting requirements, scoring fit, detecting blockers, and producing actionable next steps with human approval gates.

> **Changelog v1.0 → v1.1**
> - Fixed corrupted text in §2 ("compliance requihe valuable" → "compliance requirements").
> - Fixed typos: "caanalysis", "complet", "le" (risk Title field).
> - Restored missing scoring weight in §5.7 ("Certification/compliance readiness: 10"). Verified weights sum to 100.
> - Added §17 Open Questions & Risks and §18 Data Handling & Privacy.
> - Tightened §5.4 to specify the MVP fallback hierarchy (live → cached → seeded).
> - Clarified that the SAM.gov API requires an API key and has rate limits; seeded fixtures are required for demo reliability.

---

# 1. Executive Summary

GovCapture Agent is an autonomous capture workflow for small businesses pursuing federal contracts. The system starts with a company profile and a contracting goal, searches or loads relevant government opportunities, retrieves and parses solicitation documents, extracts structured requirements, compares those requirements against the company profile, identifies blockers and risks, recommends pursue/maybe/reject decisions, and generates a practical action package.

The MVP is designed around one useful workflow:

> Company profile + contracting goal → relevant opportunities → parsed solicitation requirements → fit score → blocker detection → action package.

The product is not a generic chatbot. It is an agentic operations workflow that uses tools, reads documents, reasons over requirements, produces structured outputs, and keeps humans in the loop before sensitive actions.

The MVP should be good enough to show real companies immediately after build completion. It should produce outputs that a small business owner, operator, or proposal consultant can understand, verify, and act on.

---

# 2. Product Thesis

Small businesses do not only need help finding government contracts. They need help deciding which opportunities are worth pursuing and what to do next.

Government contracting opportunities are often buried inside portals, dense PDFs, amendments, eligibility rules, deadlines, certifications, set-asides, submission instructions, and compliance requirements. The valuable workflow is turning that chaos into a clear pursuit decision and action package.

GovCapture Agent acts as an autonomous capture analyst that performs the first-pass work a business owner or junior capture analyst would otherwise do manually.

---

# 3. Target Users

## 3.1 Primary User: Small Business Owner / Operator

Profile:

* 1–50 person company
* Has real capabilities but limited government contracting experience
* Wants federal, state, or local government work
* May not have a dedicated capture or proposal team
* Needs clear guidance on eligibility, requirements, blockers, and next actions

Desired outcome:

> "Tell me which contracts we should pursue, which ones we should avoid, and what we need to do next."

## 3.2 Secondary User: Proposal Consultant / Capture Consultant

Profile:

* Helps companies identify and pursue government opportunities
* Understands GovCon but is bottlenecked by manual research and document review
* Works with multiple clients
* Needs faster first-pass capture analysis

Desired outcome:

> "Help me quickly qualify opportunities and produce a first-pass pursuit package for my client."

## 3.3 Tertiary User: Subcontractor Seeking Teaming Opportunities

Profile:

* Has a niche capability
* May not be ready to bid as prime
* Wants to identify contracts where they can support a prime contractor

Desired outcome:

> "Find opportunities where we could be valuable as a subcontractor and help us understand the teaming angle."

---

# 4. Core MVP Workflow

The MVP supports one complete capture run.

## User flow

1. User enters or reviews a company profile.
2. User enters a contracting goal.
3. Agent starts a capture run.
4. Agent searches or loads relevant opportunities.
5. Agent retrieves or loads solicitation documents.
6. Agent parses solicitation PDFs or attachments.
7. Agent extracts structured requirements with evidence.
8. Agent scores company fit.
9. Agent detects blockers and risks.
10. Agent ranks opportunities.
11. Agent generates an action package for relevant opportunity.
12. Agent shows human approval gates for sensitive actions.

---

# 5. MVP Feature Scope

## 5.1 Company Profile Input

The system must support a company profile with enough detail to compare against solicitation requirements.

Required fields:

* Company name
* Company website
* Company description
* Capabilities
* Industry keywords
* Location
* Service area
* NAICS codes, optional
* Certifications
* Small business status
* SAM registration status
* Clearance status
* Past performance
* Insurance/bonding status if known
* Preferred contract size
* Preferred role: prime, subcontractor, or either

The profile can be created through structured fields or pasted as messy text that the system normalizes.

### Output

The system creates a normalized company profile object used for search, scoring, blocker detection, and package generation.

---

## 5.2 Contracting Goal Input

The system must support a plain-language goal.

Example goal types:

```txt
Find cybersecurity opportunities we can pursue in the next 30 days.
Find facilities maintenance contracts near Texas.
Find software development opportunities where we can subcontract.
Find small business set-aside contracts that match our capabilities.
```

The system converts the goal into internal search criteria:

* Keywords
* Capability tags
* Due date window
* Target geography
* Target agencies if specified
* Opportunity type
* Set-aside preference
* Relevant NAICS hints if available

---

## 5.3 Agent Run Timeline

The UI must show the agent's progress through the workflow.

Timeline steps:

```txt
1. Read company profile
2. Parsed contracting goal
3. Searched opportunities or loaded cached opportunities
4. Found relevant opportunities
5. Retrieved solicitation documents
6. Parsed solicitation documents
7. Extracted structured requirements
8. Scored company fit
9. Detected blockers and risks
10. Ranked opportunities
11. Generated action package
12. Awaiting human approval
```

Each step should have a status:

* pending
* running
* complete
* failed
* needs review

The timeline is a product feature, not only a visual flourish. It lets users understand what the agent did and where outputs came from.

---

## 5.4 Opportunity Search / Opportunity Loader

The system must retrieve or load a set of relevant opportunities.

The MVP uses a fallback hierarchy for reliability during demos:

1. **Live SAM.gov API search** (preferred when API key is available and rate limits allow)
2. **Cached SAM.gov opportunities** (recent results stored locally)
3. **Seeded realistic opportunities** (hand-curated fixtures that always work)
4. **User-uploaded solicitation documents** (founder-led onboarding override)

> Note: SAM.gov's `opportunities/v2/search` API requires a registered API key and enforces per-key rate limits. Seeded fixtures are mandatory for demo reliability and offline development.

Each opportunity should include:

* Title
* Agency
* Solicitation number
* Source URL
* Due date
* NAICS
* Set-aside status
* Location/place of performance if available
* Short description
* Attachment/document references

### Output

The system displays ranked opportunity cards with:

* Fit score
* Decision: pursue / maybe / reject
* Main reason
* Main risk
* Link to detail view

---

## 5.5 Solicitation Document Parsing

The system must parse solicitation documents and preserve source context.

Supported MVP document types:

* PDF
* text extracted from PDF
* DOCX if easy
* manually uploaded solicitation files

The parser should extract text from documents and preserve page-level references where possible.

The parser must support:

* PDF text extraction
* Page-level text
* Basic chunking
* Source document metadata
* Extraction confidence

### Required extracted categories

The MVP should extract as many of the following as available:

* Opportunity title
* Solicitation number
* Agency
* Due date
* Questions deadline
* NAICS
* Set-aside status
* Submission instructions
* Required documents
* Evaluation criteria
* Technical requirements
* Past performance requirements
* Clearance/security requirements
* Insurance or bonding requirements
* Place of performance
* Period of performance
* Contract type if available
* Pricing instructions if available

---

## 5.6 Requirement Extraction

The system must turn raw solicitation text into structured requirements.

Each extracted requirement must include:

* Requirement type
* Title
* Extracted value
* Description
* Confidence level
* Evidence snippet
* Source document
* Page number if available
* Blocker flag if relevant

### Requirement types

Supported MVP types:

* eligibility
* technical
* past_performance
* certification
* insurance
* bonding
* security
* submission
* evaluation
* deadline
* location
* pricing
* document_required

### Confidence levels

* high: explicit source text found
* medium: likely supported by source text
* low: ambiguous extraction
* unknown: not found or not enough evidence

### Evidence requirement

The system should show source-backed evidence snippets for important requirements. This is required for credibility and user trust.

---

## 5.7 Fit Scoring

The system must compare the company profile against each opportunity's requirements and generate a score.

Total score: 100 points.

Scoring dimensions (weights sum to 100):

```txt
Capability match:                    20
Eligibility/set-aside match:         15
NAICS/industry match:                10
Past performance fit:                15
Certification/compliance readiness:  10
Insurance/bonding readiness:         10
Deadline feasibility:                10
Proposal complexity:                  5
Geography/place of performance fit:   5
-----------------------------------
Total:                              100
```

### Decision bands

```txt
85–100: Strong pursue
70–84:  Pursue
55–69:  Maybe / needs partner
 0–54:  Reject / weak fit
```

### Output

Each fit score must include:

* Total score
* Decision
* Confidence
* Score breakdown
* Strengths
* Weaknesses
* Blockers
* Missing information
* Recommended next action

---

## 5.8 Risk and Blocker Detection

The system must flag issues that affect whether the company should pursue the opportunity.

Risk categories:

* Clearance required but unavailable
* Set-aside mismatch
* Certification gap
* Past performance weakness
* Deadline too close
* Missing or unclear attachments
* Submission ambiguity
* Insurance or bonding gap
* Scope mismatch
* Legal/compliance review required
* Pricing complexity
* Required document not found

Risk severities:

* critical blocker
* major risk
* moderate risk
* minor concern

### Output

Each risk must include:

* Title
* Severity
* Explanation
* Evidence if available
* Recommended mitigation
* Whether human review is required

---

## 5.9 Opportunity Ranking

The system must display ranked opportunity cards.

Each card should show:

* Opportunity title
* Agency
* Due date
* NAICS
* Set-aside
* Fit score
* Decision
* Top reason
* Main risk

The ranking should prioritize opportunities that are both relevant and realistically pursuable.

---

## 5.10 Opportunity Detail View

The system must provide a detail view for analyzed opportunities.

Detail view sections:

* Summary
* Extracted requirements
* Evidence snippets
* Fit score breakdown
* Risk flags
* Missing information
* Recommended next action
* Source documents

This screen should make the decision explainable and verifiable.

---

## 5.11 Action Package Generator

The system must generate a final action package for a selected opportunity.

Required sections:

1. Executive pursuit brief
2. Pursue/no-pursue decision
3. Fit score rationale
4. Compliance matrix
5. Risk register
6. Proposal checklist
7. Timeline to submission
8. Partner or teaming suggestion if relevant
9. Outreach draft if relevant
10. Human approval checklist

### Compliance matrix fields

Each compliance row should include:

* Requirement
* Status: met / missing / unclear / not applicable
* Evidence
* Next action
* Owner

### Risk register fields

Each risk should include:

* Risk
* Severity
* Explanation
* Mitigation

### Proposal checklist

Checklist should include concrete next actions such as:

* Verify SAM registration
* Confirm eligibility
* Review required documents
* Draft technical response
* Prepare past performance references
* Confirm submission deadline
* Review pricing requirements
* Confirm insurance/bonding requirements
* Get authorized approval before submission

---

## 5.12 Partner / Teaming Suggestion

The MVP should include a lightweight partner suggestion section when the company has a gap that a partner could solve.

Examples:

* Need a cleared prime
* Need a past performance partner
* Need a local delivery partner
* Need a specialized compliance partner
* Need a subcontractor with a missing technical capability

The system should not invent contact information.

Each suggestion should include:

* Partner type needed
* Gap being solved
* Why the partner matters
* Suggested outreach angle
* Confidence level

A full partner marketplace is not part of the MVP.

---

## 5.13 Human Approval Gates

The system must clearly require human approval before sensitive actions.

Human approval required before:

* Contacting a contracting officer
* Contacting a partner company
* Sending outreach email
* Submitting proposal materials
* Claiming compliance
* Claiming certifications
* Sending pricing
* Uploading signed documents
* Making legal representations

MVP implementation:

The product should show an approval block in the action package.

Example:

```txt
Human approval required before using this output externally.
Do not send emails, submit materials, claim certifications, or mark compliance complete without authorized review.
```

Buttons may include:

* Copy outreach draft
* Mark reviewed
* Export package

No real email sending is required for MVP.

---

# 6. Non-Goals for MVP

The MVP will not include:

* Official proposal submission
* SAM.gov account registration
* Automated legal review
* Insurance procurement
* Bonding procurement
* Full CRM
* Full partner marketplace
* Payment system
* Team workspaces
* Real email sending
* Google Docs export
* Full proposal drafting from scratch
* Self-hosted models
* GPU infrastructure
* Classified or controlled document workflows

---

# 7. Technical Stack

## 7.1 Frontend

Recommended:

```txt
Next.js
TypeScript
Tailwind CSS
shadcn/ui
Vercel
```

Frontend responsibilities:

* Profile and goal screen
* Agent run timeline
* Opportunity ranking cards
* Opportunity detail page
* Action package page
* Approval gate UI

---

## 7.2 Backend

Recommended:

```txt
Python FastAPI
Docker
Vultr VPS
```

Backend responsibilities:

* Agent run orchestration
* Opportunity loading/search
* Document parsing
* Requirement extraction
* Fit scoring
* Risk detection
* Action package generation
* API endpoints

---

## 7.3 Agent / Automation Layer

Recommended:

```txt
OpenClaw
Playwright
```

OpenClaw responsibilities:

* Controlled browser/tool execution
* Opportunity page inspection if needed
* Attachment retrieval if needed
* Source page verification
* Tool action logging

The backend owns state. OpenClaw performs bounded tool actions.

---

## 7.4 AI Layer

Recommended:

```txt
Hosted LLM API
Structured JSON outputs
Schema validation
```

Use LLMs for:

* Goal parsing
* Requirement extraction
* Fit scoring explanation
* Risk analysis
* Action package generation
* Outreach draft generation

All structured model outputs must be validated before display.

---

## 7.5 Data Storage

Recommended:

```txt
PostgreSQL for structured data
Cloudflare R2 or Supabase Storage for PDFs and parsed files
Redis/RQ optional for background jobs
```

For MVP speed, a seeded JSON dataset is acceptable for opportunity and package data as long as the product still performs a real analysis workflow.

---

# 8. Minimal Data Model

## 8.1 CompanyProfile

```txt
id
name
website
description
capabilities
industry_keywords
location
service_area
naics_codes
certifications
small_business_status
sam_status
clearance_status
past_performance
insurance_bonding_status
preferred_contract_size
preferred_role
created_at
updated_at
```

## 8.2 Opportunity

```txt
id
title
agency
solicitation_number
source_url
due_date
naics
set_aside
place_of_performance
description
attachments
raw_payload
created_at
updated_at
```

## 8.3 ExtractedRequirement

```txt
id
opportunity_id
type
title
value
description
confidence
evidence_snippet
source_document
page_number
is_blocker
created_at
```

## 8.4 FitScore

```txt
id
opportunity_id
company_profile_id
total_score
decision
confidence
breakdown
strengths
weaknesses
blockers
missing_info
recommended_next_action
created_at
```

## 8.5 RiskFlag

```txt
id
opportunity_id
company_profile_id
category
severity
title
description
evidence
mitigation
requires_human_review
created_at
```

## 8.6 ActionPackage

```txt
id
opportunity_id
company_profile_id
executive_summary
decision
fit_score
fit_rationale
compliance_matrix
risk_register
proposal_checklist
timeline
partner_suggestions
outreach_draft
approval_required
created_at
```

## 8.7 AgentRun

```txt
id
goal
company_profile_id
status
steps
opportunities
selected_opportunity_id
action_package_id
created_at
completed_at
```

---

# 9. Minimal API Requirements

## Required endpoints

```txt
POST /company-profiles
GET  /company-profiles/:id
POST /agent-runs
GET  /agent-runs/:id
GET  /agent-runs/:id/opportunities
GET  /opportunities/:id
GET  /opportunities/:id/requirements
GET  /opportunities/:id/fit-score
GET  /opportunities/:id/risks
GET  /action-packages/:id
```

For MVP speed, the company profile may also be included directly when creating an agent run.

---

# 10. Structured Output Schemas

## 10.1 Requirement Extraction Output

```json
{
  "requirements": [
    {
      "type": "eligibility | technical | past_performance | certification | insurance | bonding | security | submission | evaluation | deadline | location | pricing | document_required",
      "title": "string",
      "value": "string",
      "description": "string",
      "confidence": "high | medium | low | unknown",
      "evidence_snippet": "string",
      "source_document": "string",
      "page_number": 1,
      "is_blocker": false
    }
  ],
  "missing_fields": ["string"],
  "conflicts": [
    {
      "field": "string",
      "candidates": ["string"],
      "requires_human_review": true
    }
  ]
}
```

## 10.2 Fit Score Output

```json
{
  "total_score": 82,
  "decision": "strong_pursue | pursue | maybe | reject",
  "confidence": "high | medium | low",
  "score_breakdown": {
    "capability": 18,
    "eligibility": 14,
    "naics": 9,
    "past_performance": 10,
    "certification": 8,
    "insurance_bonding": 7,
    "deadline": 9,
    "complexity": 4,
    "geography": 3
  },
  "strengths": ["string"],
  "weaknesses": ["string"],
  "blockers": ["string"],
  "missing_information": ["string"],
  "recommended_next_action": "string"
}
```

## 10.3 Action Package Output

```json
{
  "executive_summary": "string",
  "decision": "string",
  "fit_score": 82,
  "fit_rationale": "string",
  "compliance_matrix": [
    {
      "requirement": "string",
      "status": "met | missing | unclear | not_applicable",
      "evidence": "string",
      "next_action": "string",
      "owner": "string"
    }
  ],
  "risk_register": [
    {
      "risk": "string",
      "severity": "critical | major | moderate | minor",
      "explanation": "string",
      "mitigation": "string"
    }
  ],
  "proposal_checklist": ["string"],
  "timeline": [
    {
      "date": "string",
      "task": "string",
      "owner": "string"
    }
  ],
  "partner_suggestions": [
    {
      "partner_type": "string",
      "gap_solved": "string",
      "why_needed": "string",
      "outreach_angle": "string",
      "confidence": "high | medium | low"
    }
  ],
  "outreach_draft": {
    "subject": "string",
    "body": "string"
  },
  "human_approval_required": ["string"]
}
```

---

# 11. Prompting Requirements

Every agent prompt must include:

* Role
* Objective
* Inputs
* Output schema
* Guardrails
* Uncertainty behavior
* Requirement to distinguish extracted facts from inferences
* Requirement to include source evidence when available
* Requirement to avoid legal/compliance overclaims

## Requirement extraction prompt behavior

The model must:

* Extract only supported requirements
* Preserve exact dates and deadlines
* Include source snippets
* Include confidence levels
* Mark missing information
* Identify conflicts
* Avoid inventing requirements

## Fit scoring prompt behavior

The model must:

* Compare solicitation requirements against the company profile
* Apply the scoring rubric
* Identify blockers
* Be conservative on eligibility
* Explain the decision
* Recommend a next action

## Action package prompt behavior

The model must:

* Generate practical business artifacts
* Include uncertainty where needed
* Preserve human approval requirements
* Avoid claiming legal compliance unless verified
* Produce concise, useful next steps

---

# 12. Build Plan

## Phase 1: Foundation

Deliverables:

* Frontend shell
* Backend shell
* Company profile creation
* Contracting goal input
* Agent run object
* Agent run timeline
* Seeded opportunity loading

Success criteria:

* User can create a profile, enter a goal, start a run, and see workflow progress.

---

## Phase 2: Opportunity Workflow

Deliverables:

* Opportunity loader or SAM.gov connector
* Opportunity normalization
* Ranked opportunity cards
* Opportunity detail page
* Source URL and metadata preservation

Success criteria:

* System displays relevant opportunities with enough metadata for analysis.

---

## Phase 3: Document Parsing

Deliverables:

* PDF upload or retrieval
* PDF text extraction
* Page-level snippets
* Chunking
* Requirement extraction schema
* Requirement display UI

Success criteria:

* System extracts structured requirements from at least one solicitation document.

---

## Phase 4: Fit Scoring and Risk Detection

Deliverables:

* Scoring rubric
* Fit score output
* Blocker detection
* Risk flags
* Missing information detection

Success criteria:

* System recommends pursue/maybe/reject with explanations and evidence.

---

## Phase 5: Action Package

Deliverables:

* Executive brief
* Compliance matrix
* Risk register
* Proposal checklist
* Timeline
* Partner/team suggestion
* Outreach draft
* Approval gate

Success criteria:

* System generates one complete action package that a real business could review.

---

## Phase 6: Outreach Readiness

Deliverables:

* Stable deployed URL
* Reliable seeded sample run
* Ability to create or edit company profiles
* Ability to analyze at least one opportunity end-to-end
* Clean product explanation
* Clear output that can be shown to small businesses or consultants

Success criteria:

* Team can reach out to companies and show a working product flow, not only slides or mockups.

---

# 13. Acceptance Criteria

The MVP is acceptable if:

* User can enter or create a company profile
* User can enter a contracting goal
* Agent run timeline shows workflow steps
* System displays relevant opportunities
* System parses at least one solicitation document
* System extracts structured requirements with evidence
* System scores fit against the company profile
* System recommends pursue/maybe/reject
* System flags clear blockers and risks
* System generates an action package
* System shows human approval gates
* Product can be shown to real target users for feedback

The MVP is not acceptable if:

* It only summarizes pasted text
* It only lists opportunities without decisions
* It cannot explain why an opportunity was accepted or rejected
* It has no source evidence
* It invents requirements or contact information
* It claims to submit official proposals
* It lacks human approval gates

---

# 14. Product Success Metrics

## Early user validation metrics

* Number of companies or consultants shown the product
* Number of users willing to share their company profile or opportunity target
* Number of users who say the output would save them time
* Number of users who request a follow-up analysis
* Number of users willing to pay or pilot
* Number of useful corrections users make to the agent output

## Product utility metrics

* Opportunities analyzed per run
* Requirements extracted per opportunity
* Percentage of requirements with evidence snippets
* Fit score completion rate
* Action package generation rate
* Number of blocker/risk flags surfaced
* User-rated usefulness of action package

## Reliability metrics

* Agent run completion rate
* Document parse success rate
* Structured extraction success rate
* Invalid JSON/error rate
* Average run time
* Number of manual fallbacks required

---

# 15. Outreach Positioning

For early company outreach, position the product as:

> GovCapture Agent helps small businesses quickly understand which government contracts are worth pursuing. It reads solicitation documents, extracts requirements, scores fit, flags blockers, and generates a first-pass action package.

Avoid claiming:

* guaranteed eligibility
* guaranteed compliance
* automatic proposal submission
* legal review
* guaranteed contract wins

Use language like:

* first-pass capture analysis
* opportunity qualification
* pursuit readiness
* requirements extraction
* blocker detection
* action package
* human-reviewed workflow

---

# 16. Final Product Positioning

GovCapture Agent turns a small business profile into a government contract action package. It searches opportunities, reads solicitation documents, extracts requirements, scores fit, identifies blockers, and generates next actions so businesses know what to pursue and what to avoid.

The product should be described as:

> An autonomous capture analyst for small businesses pursuing government contracts.

The product should make early users think:

> This helps me avoid wasting time on bad-fit opportunities and gives me a concrete starting point for the ones worth pursuing.

---

# 17. Open Questions & Risks

These are unresolved decisions to track during build. None block Phase 1, but each should be resolved before its corresponding phase ships.

| # | Question | Phase | Default if undecided |
|---|----------|-------|----------------------|
| 1 | Which hosted LLM provider, and what is the per-run cost ceiling? | Phase 3 | Use cheapest model that produces valid JSON; cap at $0.50/run. |
| 2 | OCR fallback for image-only PDFs (e.g., scanned solicitations)? | Phase 3 | Skip OCR in MVP; mark document as "unparseable" and surface to user. |
| 3 | How are SAM.gov API keys provisioned per environment, and what is the rate-limit budget? | Phase 2 | Single shared key with seeded-fixture fallback on 429. |
| 4 | Is multi-tenancy (multiple companies per account) in scope? | Phase 1 | No — single profile per session for MVP. |
| 5 | Authentication model for the deployed app? | Phase 6 | Magic-link email auth or none (anonymous run + share link). |
| 6 | How long is parsed document text retained? | Phase 3 | 30 days, then purge raw text; keep extracted requirements. |
| 7 | What happens when fit score is borderline (e.g., 54 vs. 55)? | Phase 4 | Display score with confidence band; do not treat boundary as binary. |
| 8 | Do we need amendment-detection (solicitation modifications)? | Phase 3 | Out of scope for MVP; document as known limitation. |

## Top product risks

* **Hallucinated requirements.** Extraction without strict evidence-binding will produce confident-sounding wrong answers. Mitigation: every non-`unknown`-confidence requirement must include an `evidence_snippet`; UI must visibly link to source page.
* **Demo fragility.** Live SAM.gov calls fail or rate-limit during demos. Mitigation: seeded fixtures are first-class, not a fallback hack.
* **Eligibility overclaim.** Telling a non-set-aside-eligible company they can pursue a set-aside contract is a serious user harm. Mitigation: scoring prompt must be conservative on eligibility; eligibility mismatch is always a critical blocker, never a soft penalty.
* **PDF parsing variance.** Solicitations vary wildly in structure. Mitigation: page-level chunking + per-requirement-type extraction prompts, not a single mega-prompt.

---

# 18. Data Handling & Privacy

The MVP processes company profile data and government solicitation documents. Solicitations on SAM.gov are public, but company profiles may contain non-public information (past performance, certifications, internal capabilities).

MVP commitments:

* Company profile data is stored only as needed to run analyses; no third-party sharing.
* LLM calls send profile + solicitation text to the chosen hosted provider — users must be told this in the profile-creation UI.
* No CUI (Controlled Unclassified Information) or classified material should be uploaded; the upload UI must display this restriction.
* Raw uploaded documents are retained per §17 question 6; users can request deletion.
* No PII beyond user email and company-volunteered profile data is collected.

Out of scope for MVP: SOC 2, FedRAMP, ITAR handling, encrypted-at-rest guarantees beyond cloud provider defaults.
