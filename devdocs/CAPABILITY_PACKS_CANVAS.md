# Capability Packs Canvas

Working thesis for the company, hackathon demo, and first sellable agents.

## One-Line Thesis

Software is moving in-house. Companies will not subscribe to 80 SaaS dashboards; their agents will call specialist capability packs that already know how to complete valuable jobs.

## What We Are Building

Capability packs for agents.

A pack is a callable specialist your agent can use when it needs a domain outcome: process a complex document, find a government contract, qualify an Amazon product, draft an ad set, or produce a proposal action plan.

The buyer does not want "AI document extraction" or "workflow automation." The buyer wants their agent to suddenly have senior experience in a domain without weeks of setup.

Marketing frame:

```text
Give your agent senior experience in government contracting in five minutes.
Give your agent a document team without hiring one.
Give your agent product research instincts trained on FBA patterns.
```

## Why Now

Codex, Claude, Hermes, OpenClaw, Grok custom agents, and other agent runtimes are getting good enough to operate real workflows. The missing layer is not another chat app. The missing layer is maintained, callable expertise that agents can rent instead of rebuilding from scratch.

Grok custom agents point in the same direction: persistent configurable agents with tool access and instruction sets. But most systems still make the user configure the agent manually. Our wedge is lower-friction: let any agent call a trained capability pack and get the job done.

## Codex Operating Model

Codex can run any CLI or system command available in the environment, including other model CLIs, as long as the tool is installed and credentials are present.

Examples:

```bash
claude "review this RFP and return risks"
gemini "extract table structure from this PDF"
ollama run deepseek-r1 "clean this OCR output"
ssh govcon "systemctl status hermes"
docker compose up -d
crontab -e
```

Codex can also SSH into boxes, install runtimes, wire services, create cron jobs, and call APIs. It is good as the build/operator layer. It is weaker as long-term domain memory. Hermes/OpenClaw-style agents are better for persistent learning loops, scheduled work, and org-specific adaptation.

## Core Product Shape

Two modes:

1. **Hosted pack**
   - Agent calls our endpoint or MCP server.
   - We manage model routing, OCR, Document AI, storage, cache, retries, and updates.
   - Customer pays per use, credit balance, or subscription.

2. **Self-hosted pack**
   - Customer installs the pack into Hermes/OpenClaw/Claude Code/other runtime.
   - They bring their own API keys and storage.
   - They can still pay for updates, training, evals, or managed upgrades.

The pack can be:

- a single deterministic skill,
- an MCP endpoint,
- a hosted API,
- a multi-agent worker,
- or a hybrid.

The customer should not care. They care whether their agent gets the outcome.

## Difference From Skill.md

Plain `SKILL.md` is useful but limited:

- It often clogs the main context window.
- It requires every company to wire the same APIs and storage.
- It does not automatically improve across deployments.
- It does not provide managed caching, retries, evals, or version updates.
- It is hard to price as a reusable business capability.

A capability pack is a maintained product:

- isolated context and execution,
- typed inputs/outputs,
- cache and re-run economics,
- managed API keys and model routing if hosted,
- optional local/private mode,
- versioned domain training,
- analytics without identifiable customer data,
- revenue share or subscription for pack creators.

## First Product Candidates We Discussed

1. **Document Processor Pack**
   - Any agent sends a PDF/doc/image bundle.
   - Gets back Markdown, JSON, tables, citations, extracted fields, or a custom schema.
   - Stores outputs for 7 days or longer for paid accounts if enabled.
   - Cache prevents paying full price twice for the same document.

2. **GovCon Bid Desk / Michaela**
   - Learns what a company does.
   - Finds government opportunities that matter.
   - Produces bid/no-bid decisions and action plans.
   - Uses document processing as a capability pack, not as the headline.

3. **SAM.gov Opportunity Pack**
   - Callable API/agent for searching, ranking, and monitoring SAM.gov opportunities.
   - Can be used by Michaela or any external business agent.

4. **FBA Product Finder Pack**
   - Agent for Amazon resellers.
   - Uses marketplace APIs, margin rules, competition signals, and business preferences.
   - Sends product decisions instead of another Helium10-style dashboard.

5. **Ads Maker Pack**
   - Takes product, audience, offer, and direction from another agent.
   - Produces ad concepts, copy, images/video prompts, landing variants, and testing plan.

6. **Restaurant Growth Pack**
   - Local restaurant operator agent.
   - Finds promo ideas, reviews menu economics, drafts local ads, monitors competitors.

7. **Design Taste Pack**
   - Opinionated design capability for agents.
   - Knows industry-specific visual patterns, what to avoid, and how to differentiate.

8. **Bookkeeping / Ops Pack**
   - Turns messy invoices, receipts, and reports into categorized records and exceptions.

9. **Legal / Compliance Pack**
   - Private/local mode for sensitive documents.
   - Produces summaries, issue lists, clause extraction, and review checklists.

10. **Healthcare Intake Pack**
   - High-privacy version of document processing and structured intake.
   - Requires stronger compliance posture before launch.

## Best Hackathon MVP

Build one demo where an agent uses one capability pack and the value is obvious in seconds.

Best wedge:

```text
Document Processor Pack -> GovCon Bid Desk demo
```

The demo:

1. User gives a company name or profile plus one RFP/SAM opportunity.
2. Michaela calls the Document Processor Pack.
3. Pack returns structured requirements, dates, forms, clauses, and evidence.
4. Michaela returns:
   - bid/no-bid decision,
   - why,
   - missing inputs,
   - next actions,
   - owner/date plan,
   - approval gates.

The story is not "we read PDFs." The story is:

```text
Michaela joined your bid team, read the contract, and told you what to do next.
```

## Product 1: Michaela, GovCon Bid Desk

Public description:

```text
Michaela learns what your company does, finds the government opportunities that fit, and helps your team move on them before the deadline.
```

What it does:

- learns company capabilities, certifications, SAM status, past performance, target agencies, and bid capacity;
- searches or monitors opportunities;
- reads solicitation docs through the document pack;
- says pursue, maybe, or reject;
- creates an action plan with owners, dates, missing inputs, questions, and approval gates;
- keeps memory of what the team cares about.

Copy:

```text
Add Michaela to your bid team.

She learns your company, finds contracts worth bidding, and turns each opportunity into a clear next move before the deadline.
```

Do not lead with:

```text
PDF parsing, compliance matrix, workflow automation, SAM.gov integration.
```

Those are proof, not promise.

## Product 2: Atlas, Document Processor Pack

Public description:

```text
Atlas turns messy documents into clean, reusable knowledge your agent can call again.
```

What it does:

- accepts PDFs, scans, screenshots, Word docs, spreadsheets, and zipped document sets;
- routes to the best OCR/model/parser path;
- returns Markdown, JSON, tables, citations, or a requested schema;
- stores results if enabled;
- returns a document handle your agent can call later;
- supports do-not-store mode;
- caches prior work so repeat calls are cheaper.

Copy:

```text
Give your agent a document team.

Send the file once. Get clean Markdown, JSON, tables, citations, and a reusable document handle back.
```

This is likely the fastest product to launch because every serious agent workflow eventually needs document processing.

## Architecture For Atlas

Minimum stack:

- Next.js marketing + account page.
- Supabase auth and metadata.
- Stripe or credit wallet.
- Cloudflare R2 for optional document/output storage.
- Cloudflare Workers for MCP/API edge entrypoint.
- Queue for long jobs.
- Provider routing:
  - Google Document AI / AWS Textract / OCR for extraction,
  - cheap model for cleanup,
  - stronger model for structure and reasoning,
  - deterministic validators for schema and citations.

Two rails:

1. **New document**
   - upload or URL,
   - hash,
   - parse,
   - structure,
   - cache,
   - return output + handle.

2. **Existing document**
   - call by handle/hash,
   - ask for a new schema or correction,
   - pay less if cached parse can be reused.

## Pricing Shape

Simple:

- Load `$10` in credits.
- Pay per document/page/model pass.
- Cached re-use is cheaper.
- Do-not-store mode costs more because cache cannot help.
- Subscription unlocks retention, higher limits, and pack updates.

Hosted margin can be modest, like 20% over pass-through, because volume and lock-in come from reliability and cache, not huge markup.

## YC Pitch

Agents are becoming the new in-house software layer. But every agent still has to relearn the same hard capabilities: document processing, government contracting, product research, ads, bookkeeping, industry design, compliance.

We sell capability packs that any agent can call.

Our first pack gives an agent a document team. Our first vertical agent, Michaela, uses that pack to help companies find and act on government contracts before deadlines. The wedge is high-friction document-heavy work where not using the agent is obviously stupid once the output is in front of you.

We start with hosted MCP/API packs, then let advanced customers self-host. Over time the marketplace becomes a maintained library of specialist abilities for agents, with paid updates, private deployments, and usage-based economics.

## YC-Style One-Liner

We let companies give their agents specialist abilities, starting with document processing and government contracting.

## What The Landing Page Should Say

Hero:

```text
Give your agent a specialist.
```

Subhead:

```text
Add trained capability packs for documents, bids, product research, ads, and ops without rebuilding the same tools in every agent.
```

Alternate, more outcome-led:

```text
Add Michaela to your bid team.

She learns your company, finds contracts worth bidding, and turns each opportunity into a clear next move before the deadline.
```

For Atlas:

```text
Give your agent a document team.

Send a messy file. Get clean Markdown, JSON, tables, citations, and a reusable handle back.
```

## What Not To Build First

- A marketplace with many empty categories.
- A generic dashboard.
- A giant agent framework.
- A SaaS where users must learn workflows before seeing value.
- WhatsApp-first distribution unless the customer already lives there.

## What To Build First

One callable capability pack with one stunning demo.

Recommended:

```text
Atlas Document Processor Pack
Michaela GovCon Bid Desk using Atlas
```

That proves:

- packs can be called by agents,
- packs have isolated context and tools,
- packs can be reused across vertical agents,
- one vertical worker can feel like a real hire,
- the business can charge for usage and retention.

## Open Questions

- Is the hackathon judged more on Codex usage or product outcome?
- Do we lead with Atlas as universal infrastructure or Michaela as the vivid customer outcome?
- Should the first public page be the pack marketplace or the Michaela vertical page?
- Which channel matters first: MCP, REST API, Hermes skill, OpenClaw channel, or Claude Code config snippet?
- What privacy promise is credible for day one?
- What is the shortest path to first dollar: govcon consultant, FBA seller, or agent-builder audience?

## Current Call

For the hackathon:

Build **Michaela** using **Atlas**.

For the company:

Position as **capability packs for agents**.

For first revenue:

Sell one concrete outcome to one reachable niche, not the whole marketplace.
