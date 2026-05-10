# Dev 2 Runbook

Common commands, debugging patterns, and pitfalls. Open this when something breaks.

---

## Common commands

### Local dev

```bash
cd web
npm install
npm run dev                 # http://localhost:3000

npm run typecheck           # tsc --noEmit
npm run lint                # eslint
npm run build               # production build
npm run preview             # serve the production build locally

# Regenerate types after schema changes:
cd .. && make schemas       # populates /web/lib/schemas/
```

### Mock API (during pre-S2)

```bash
# Track A's mock server runs from /api with stub responses; A keeps it alive until S2.
# Native Postgres + Redis must be running first (see dev1-backend/RUNBOOK.md).
cd ../ && make services-up        # brew/apt-managed Postgres + Redis
cd api && uv run uvicorn api.main:app --reload --port 8000
```

Set `NEXT_PUBLIC_API_BASE=http://localhost:8000` in `web/.env.local`.

### Hitting endpoints manually

```bash
# Get a profile
curl http://localhost:8000/company-profiles/<id>

# Watch SSE stream
curl -N http://localhost:8000/agent-runs/<id>/stream

# Replay the example JSONL via the mock SSE endpoint:
curl -N http://localhost:8000/agent-runs/00000000-0000-0000-0000-000000000001/stream
```

### Vercel preview

- Push a feature branch → Vercel deploys a preview URL.
- Production: connect `main` → `https://govcapture.vercel.app` (or your domain).

---

## Debugging patterns

### Timeline doesn't update

Most common. Steps:

1. Open browser DevTools → Network → filter by `EventStream`.
2. Confirm the request is open and receiving events. If "pending" forever with no events, the API isn't emitting (check A's logs).
3. Confirm content-type is `text/event-stream`. If it's `application/json`, the API is returning a regular response, not SSE.
4. Check for `:keepalive` lines. Some proxies drop SSE without keepalives.
5. Open DevTools → Sources → set a breakpoint in `lib/sse.ts`'s message handler. Confirm events arrive but aren't parsing.
6. If pre-S2: confirm you're hitting the mock SSE endpoint (some mock impls return on-demand only after the run is "complete").

### Zod validation errors in the console

The shape of the API response doesn't match the generated schema. Steps:

1. Look at the actual response in DevTools.
2. Compare against `/schemas/<name>.schema.json`.
3. Two possibilities:
   - **A regenerated schemas but didn't update the API.** Ping A.
   - **You haven't run `make schemas` since pulling.** Run it.

### Profile form submits but nothing persists

1. Check Network tab — is the POST returning 201? If 422, the request shape is wrong (zod at the API rejected).
2. Check that the form sends a JSON body with the right field names (camelCase from generated schemas).

### Evidence-snippet click doesn't open the PDF at the cited page

1. Confirm the `page_number` exists on the requirement (post-A5 validation should ensure this).
2. Confirm the PDF route is correct: `<NEXT_PUBLIC_API_BASE>/fixtures/<slug>/attachments/<filename>` or however you serve PDFs.
3. `react-pdf` accepts `pageNumber` prop — confirm you're passing the right value (1-indexed).
4. CORS: if the PDF is served from VX1 and the web from Vercel, the PDF endpoint needs CORS headers.

### Hot-reload broken in dev

Next.js + Tailwind sometimes lose track. Restart `npm run dev`. If it persists, `rm -rf .next` and restart.

### Fixture fails the eval

1. Run `make eval-fixture FIXTURE=<slug>` from repo root.
2. Look at the JSON diff between expected and actual.
3. Common causes:
   - PDF text extraction missed a section — re-render the PDF more cleanly.
   - Expected title wording too strict — relax or fix the source PDF wording.
   - A's prompt drifted — coordinate with A.

### Vercel build fails on a feature branch

1. `npm run build` locally first — same Node version (Vercel's default is current LTS; pin in `package.json` engines).
2. Most common: missing env var at build time. `NEXT_PUBLIC_*` vars must exist in Vercel project settings.
3. Generated schemas not committed: confirm `/web/lib/schemas/` is checked in.

---

## Pitfalls

| Pitfall | Prevention |
|---------|------------|
| Hand-editing generated zod schemas | `make schemas` only. Add a CI check that generated files match source. |
| Reading env vars in random files | Centralized in `/web/lib/env.ts`. Add an ESLint rule that flags `process.env.*` outside that file. |
| SSE consumer that ignores `event:` lines | Standard `EventSource` only fires `message` events; for typed events you need `addEventListener('<type>', ...)`. See B5a. |
| Building UI for events not yet in the union | Trace event union is locked in P0.3. Adding a new event = schema PR. |
| Fixture PDFs that aren't text-extractable for the demo set | Use a text-source export (LibreOffice, weasyprint), not print-to-image. |
| Forgetting the approval-gate UI on the action package | PRD §5.13 — every package shows it prominently. Lint rule: search for "ApprovalGate" import in action-package page. |
| Demo overlap on the same shadcn component name | shadcn copies components into your repo; if you customize, document in DESIGN.md. |
| Authoring fixtures that the demo company doesn't hit cleanly | Re-verify all three fixtures against B13's profile after any change. |

---

## When to ask Dev 1

- The API response shape disagrees with the schema.
- You need a new endpoint, query param, or response field.
- A trace event you need isn't in the example JSONL.
- The PDF endpoint CORS doesn't work cross-origin.
- A fixture passes locally for you but fails A's eval — diagnose together.
- You're about to push a change that touches `/schemas/` — co-author the schema PR.
