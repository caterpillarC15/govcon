# V1 Product Alignment

This doc is the product filter for every Michaela prompt, Hermes skill, UI
surface, and demo decision.

## One-Line V1

Hire an AI bid-desk operator that finds government contracts worth pursuing and turns each one into a clear bid/no-bid decision, action plan, and team follow-up list.

## What We Sell

We do not sell "compliance automation," "an agent platform," "MCP," or "OpenClaw."

We sell a worker:

- Finds opportunities that match the company.
- Explains whether the company can realistically win.
- Tells the team what to do next.
- Turns dense solicitation material into a pursuit brief.
- Chases missing inputs before deadlines slip.
- Keeps humans in control before any external action.

Internal language may use "capture." Public language should use plain terms: bid, proposal, pursuit, contract, opportunity, action plan.

## Primary Buyer

V1 is for teams already close to revenue:

- Small or mid-size government contractors already bidding.
- Proposal or capture consultants with multiple clients.
- Commercial SMBs with real capabilities and an urgent first government-contract push.

The strongest first customer is an existing contractor or consultant. They already know the pain, have deadlines, and can judge whether the output saves hours.

## Core Job

Given a company profile and either a target market or a solicitation:

1. Find or ingest relevant opportunities.
2. Decide pursue / maybe / reject.
3. Explain the decision in business language.
4. Produce the first action package: required docs, owners, deadlines, missing inputs, questions, and optional outreach draft.
5. Ask for human approval before any external message, certification claim, or submission.

## What Makes It Valuable

The value is not "we extracted requirements." That is a hidden mechanism.

The value is:

- Fewer bad bids.
- Faster bid/no-bid decisions.
- More proposal throughput.
- Less deadline chaos.
- A reusable memory of the company's capabilities, certifications, past performance, preferred agencies, and bid decisions.

## Architecture Stance

Michaela is the agent workloop and product architecture. Hermes is the runtime
shell/tool harness around it. Anthropic/OpenRouter are provider transports, not
the product architecture.

The bench is **Michaela (CEO) + Scot (discovery) + Lenny (fit ranking) +
Gate (eligibility) + Ledger (competitive intel) + Happer (execution runner) +
Roy (packaging)**. See `devdocs/MICHAELA_SYSTEM_MODEL.md` for the
canonical design.

OpenClaw is a channel/tool substrate when useful: browser work, web chat,
WhatsApp, Slack, or other customer surfaces. It is not a second peer brain
for V1.

The customer experiences one named worker (Michaela). The other six are
sub-agents she delegates to and never surfaces directly to the user.

## Public Terms

Prefer:

- bid-desk operator
- proposal operator
- contract scout
- bid readiness agent
- opportunity brief
- pursuit plan
- bid/no-bid decision

Avoid public-first use of:

- capture, unless speaking to govcon insiders
- compliance matrix as the headline
- agent platform
- MCP
- Hermes
- OpenClaw

## V1 Output Standard

Every run should produce a short, executive-usable package:

- Decision: pursue / maybe / reject.
- Why: fit, eligibility, deadlines, evidence.
- What to do next: actions, owners, dates.
- Missing inputs: what the team must provide.
- Questions to ask: contracting officer or internal team.
- Human approval gate: external contact, certification claims, compliance attestation, submission.

If the agent cannot produce a trustworthy package, it should say what is missing and ask a narrow follow-up.

## North Star Behavior

Be useful like a strong junior operator who has read the documents and knows when to say no.

Do not sound like a consultant selling process. Do not bury the user in rubric mechanics. Lead with the decision and the next action.
