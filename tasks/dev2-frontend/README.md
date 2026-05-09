# Dev 2 — Track B — Frontend / Fixtures / Demo

You own the Next.js app on Vercel, the agent-run timeline, opportunity rendering, the action-package UI, the four fixtures (PDFs + JSON), the demo company profile, and the §13.1 stage choreography. Dev 1 (Track A) owns the backend, Hermes integration, and Vultr VX1 deployment.

Joint docs live at the parent (`../`); your dev-specific files live here.

---

## Read order before any code

1. `README.md` (this file) — your map.
2. `../HERMES.md` — agent runtime spec (good context; you don't implement it but the SSE you consume comes from a Hermes run).
3. `../CONTRACTS.md` — schemas, SSE event shapes, env vars, skill registry. **The contract you build against.**
4. `../INTERFERENCE_MAP.md` — file ownership and shared-file protocols.
5. `../PHASE_0.md` — joint setup; you and Dev 1 do P0.1–P0.7 together before splitting.
6. `../FIXTURES.md` — the spec for the four fixtures you author. **Critical — your content drives every demo and eval.**
7. `../DEMO.md` — the §13.1 stage script. **You drive this on stage.**
8. `RUNBOOK.md` — commands, debugging tips, common pitfalls.
9. `DESIGN.md` — UI tokens, layout patterns, component conventions.
10. Start with `tasks/B1.md`.

`STANDUP.md` here is your append-only log; check `../dev1-backend/STANDUP.md` for A's updates.

`fixture-content/` contains text drafts of solicitation PDFs you can adapt — copy, customize, render to PDF.

---

## Your surface

| Path | Owner | Notes |
|------|-------|-------|
| `/web/**` | You | Except `/web/lib/schemas/` (codegen'd from `/schemas/`) |
| `/fixtures/<slug>/opportunity.json` | You | Per fixture, validates against `opportunity.schema.json` |
| `/fixtures/<slug>/attachments/*.pdf` | You | Authored from `fixture-content/` text drafts |
| `/fixtures/_demo-company/profile.json` | You | The demo company that hits all three bands |
| `/eval/goldens/**` | You | Paired with A's eval runner; declare expected behavior per fixture |
| `/web/public/demo/**` | You | Backup demo video + pre-cached run JSON |
| `/schemas/*.json` | Shared | Schema PRs need both devs to ack |
| `/web/lib/schemas/` | Generated | Never hand-edit |

---

## Your task list (suggested order)

| # | Task | Type | File | Done |
|---|------|------|------|------|
| B1 | Next.js + Tailwind + shadcn skeleton, Vercel preview | Plumbing | `tasks/B1.md` | [ ] |
| B2 | API client + zod-validated types, mock-first | Plumbing | `tasks/B2.md` | [ ] |
| B3 | Profile entry screen | UI | `tasks/B3.md` | [ ] |
| B4 | Goal entry screen | UI | `tasks/B4.md` | [ ] |
| B5a | SSE consumer + typed event union | UI | `tasks/B5a.md` | [ ] |
| B5b | Timeline component (page-level) | UI | `tasks/B5b.md` | [ ] |
| B5c | Step row + tool-call detail expander | UI | `tasks/B5c.md` | [ ] |
| B6 | Ranked opportunity cards | UI | `tasks/B6.md` | [ ] |
| B7a | Opportunity detail layout + sections | UI | `tasks/B7a.md` | [ ] |
| B7b | PDF viewer integration + evidence-snippet deep links | UI | `tasks/B7b.md` | [ ] |
| B7c | Score breakdown chart + risk list | UI | `tasks/B7c.md` | [ ] |
| B8a | Action package: executive brief + decision header | UI | `tasks/B8a.md` | [ ] |
| B8b | Compliance matrix component | UI | `tasks/B8b.md` | [ ] |
| B8c | Risk register + proposal checklist + timeline | UI | `tasks/B8c.md` | [ ] |
| B8d | Outreach draft + approval gate + export/print | UI | `tasks/B8d.md` | [ ] |
| B9 | Strong-pursue fixture | Content | `tasks/B9.md` | [ ] |
| B10 | Maybe-needs-partner fixture | Content | `tasks/B10.md` | [ ] |
| B11 | Reject fixture (§11.1 enforcement) | Content | `tasks/B11.md` | [ ] |
| B12 | Adversarial image-only-PDF fixture | Content | `tasks/B12.md` | [ ] |
| B13 | Demo company profile | Content | `tasks/B13.md` | [ ] |
| B14 | Demo rehearsal + backup recording (S5 trigger) | Demo | `tasks/B14.md` | [ ] |

**Critical path:** B1 → B2 → (B3 || B4 || B6 || B9-B13) → B5a → B5b → B5c → B7a → B7b → B7c → B8a → B8b → B8c → B8d → B14.
**Parallel-safe** (when waiting for A's endpoints): B9, B10, B11, B12, B13.

---

## When Dev 1 needs you

| Trigger | What A needs from you | Time |
|---------|----------------------|------|
| End of P0 | Your `npm run dev` works against the mock API; you've consumed the trace-event example JSONL | ~5 min ack |
| S2 — A3 lands | You switch `NEXT_PUBLIC_API_BASE` from mock to real; smoke-test together | ~10 min |
| S3 — A9 lands | You sit together for first end-to-end localhost dry-run | ~30 min |
| Schema PR | One-line ack; verify your `tsc --noEmit` still passes after `make schemas` | ~2 min |
| Fixture PR review | Confirm A's `parse_pdf` handles your PDF; A's eval matches your `expected.json` | ~5 min per fixture |
| Demo rehearsal (S5) | You drive the stage; A is at the laptop | ~30 min |

---

## Critical rules

- **The frontend is build-against-mock-first.** P0.6 stands up a mock API; you build until S2 without waiting for A.
- **Every API response runs through zod validation.** Catches A's accidental schema drift loudly.
- **Trace event types are a discriminated union.** Use `switch (event.type)` exhaustively in B5a; let TypeScript catch missed cases.
- **Fixtures co-evolve with the demo company profile (B13).** If you change the profile, re-verify all three fixtures still hit their expected bands.
- **§11.1 visible in the UI:** the reject fixture's evidence (clearance blocker on page 2) must deep-link from the timeline → opportunity detail → PDF viewer at the cited page. This is the demo's wow moment.
- **Don't put real PII or real procurement data into fixtures.** Synthetic only — realistic but invented.
- **Every action package shows the approval gate prominently.** PRD §5.13 is non-negotiable.

---

## When you're stuck

1. Re-read the PRD section linked in the task (`../PRD.md`).
2. Check `STANDUP.md` for prior decisions.
3. If schema-related: stop, ping Dev 1, change together.
4. If API behavior is unexpected: check that A has cut over from mock (S2). If pre-S2, you're hitting canned data; treat any anomaly as a mock issue, not real.
5. If fixture eval fails: the issue is either your fixture (likely if a small detail) or A's prompt (likely if systemic across fixtures). Tag it in standup; collaborate to diagnose.

Don't relitigate frozen decisions. Append a note to STANDUP.md and move on.
