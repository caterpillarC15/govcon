# Launch Runway Implementation Plan — everything outstanding to a public v1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended; many phases share growing files) or superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the GovCon Bid Desk pack from "Sprints B + G + A + C(Phases 0–6 + 8 slice) shipped, working tree clean at `f5576b9`, suite green, no live customers" to "**publicly launchable v1**: production-deployed, agent-callable, magic-link-ready, eval-protected, deploy-runbook-tested."

This plan consolidates everything I noted as deferred at the end of the previous session:

1. Live validation of what already shipped (per advisor's gating recommendation)
2. Sprint C Phase 7 — UI polish (skeletons, error boundaries, mobile, a11y)
3. SSE upgrade (replace 2s polling in RunTimeline with EventSource)
4. Sprint C Phase 8 remainder — public agent surface (`api_keys` table, `/api/v1/tools/<name>` mirror, rate limiting, MCP server, public-discovery polish)
5. Sprint E — `query_usaspending` skill for Ledger
6. Sprint F — eval harness for LLM-backed skills
7. Production magic-link email delivery
8. Sprint D — VX1 production deploy
9. Sprint G end-to-end verification (cross-repo; partial — owed by `/root/michealaai`)
10. Final state-of-the-repo updates + v1.0.0 tag

**Architecture:**
- **Each phase opens with a validation gate** confirming the prerequisite still holds. Plans on broken foundations are wishlists; gates catch drift before code lands.
- **Schema-touching tasks pause for explicit user ack** before `supabase db push`. Per handoff §17.3, schema changes are an "ask first" trigger.
- **Independent phases parallelize** (1 + 5, 3 + 4 + 6) — the execution graph below lists what can be sequenced concurrently.
- **Same-origin proxy pattern** for SSE (Next.js Route Handler) avoids the EventSource-no-headers / cross-origin-cookie problem cleanly.
- **Per-agent API keys (`gck_…`) augment, not replace, `INTERNAL_API_KEY`.** The internal-only routes stay; the new `/api/v1/tools/<name>` accept either header. No breaking change to Sprint B callers.
- **MCP server is a thin HTTP wrapper** over `/api/v1/tools/<name>`, same pattern as the Hermes plugin (Sprint A). One canonical code path; lower maintenance.

**Tech Stack:** Python 3.12 · FastAPI · supabase-py AsyncClient · pytest-asyncio · uv · Anthropic SDK · Next 15 · React 19 · Tailwind 4 · `@supabase/ssr` · Redis (Upstash or self-hosted) · `mcp` Python SDK · Vultr VX1 + nginx + systemd · Vercel · Supabase (Postgres + Auth + Storage).

**Out of scope (acknowledge but don't plan):**
- CI / GitHub Actions (no config exists today; add as a follow-up sprint)
- Sentry / structured logging / Grafana dashboards (the handoff alludes to a dashboard pattern, not implemented here)
- Backup / disaster-recovery procedures beyond Supabase's defaults
- Customer support tooling (Intercom, status page)
- FedRAMP / FISMA / CMMC compliance work for selling to defense customers
- Per-tool API-key scopes (every key gets `tools:*` in v1)
- Native MCP transport (stdio is the v1 transport; HTTP/SSE transports are post-v1)
- Internationalization
- Optimistic UI mutations
- Password / OAuth fallback on login (magic link only for v1)

These are real launch concerns but not in the user's "implement it all" scope from the previous session.

**Verification gates (must hold at end of every phase):**
- `uv run pytest api/tests/ -q` — all green; suite size ≥ 154 (current baseline).
- `uv run ruff check api` — clean.
- `uv run mypy api` — 0 errors.
- `npm --prefix /Volumes/CS_Stuff/govcon/web run typecheck` — clean.
- `npm --prefix /Volumes/CS_Stuff/govcon/web run lint` — clean.
- `npm --prefix /Volumes/CS_Stuff/govcon/web run build` — clean.
- `git status` — clean (no unintended changes to user's parallel files).

**Final verification gates (entire plan complete):**
- A naive curl using a minted `gck_…` key calls `/api/v1/tools/parse-goal` and gets a valid envelope.
- `curl https://<prod-host>/.well-known/agent.json` returns the manifest from production.
- A new user can land on `/`, get redirected to `/login`, sign in via magic link delivered by the production email provider (not Supabase's default SMTP), reach `/app`, create a profile, queue a run, see live SSE events flow into the timeline, drill into an opportunity, and approve a bid memo — without any console errors.
- The MCP server's binary is installable via `pip install mcp-server-govcapture`, registers all 10 tools when added to a Claude Desktop config, and successfully calls one tool against the production API.
- `make eval` passes against committed goldens for all 4 fixtures × all LLM-backed skills.
- A real `agent_runs` row created via `POST /agent-runs` from `/web` is picked up by `/root/michealaai`'s orchestrator, drives a real run, and produces a viewable `action_packages` row in the UI (Phase 8 cross-repo gate).
- `git tag v1.0.0` exists at the head; HANDOFF_PROMPT.md Section 1 ("Verified state") reflects v1.0.0.

---

## Branch state going in

Local `main` is at `f5576b9` (Phase 8 slice committed). Working tree has 4 user-edited files (`README.md`, `tasks/README.md`, `landing/next.config.mjs`, `web/next.config.mjs`) which are theirs to handle separately. The branch is ahead of `origin/main` by ~12 commits and not yet pushed; do **not** push during this plan unless explicitly asked.

---

## Execution graph (what can parallelize)

```
Phase 0 (validation) ─┬─▶ Phase 1 (UI polish) ───────────────────────────────────┐
                      ├─▶ Phase 5 (eval harness) ────────────────────────────────┤
                      └─▶ Phase 2 (SSE upgrade) ─────────────────────────────────┤
                                                                                  │
                                                                                  ▼
                                                Phase 6 (production email) ──▶ Phase 7 (VX1 deploy) ──▶ Phase 8 (cross-repo verify) ──▶ Phase 9 (tag + finalize)
                                                          ▲                          ▲
Phase 3 (Agent SEO infra) ──┬──▶ Phase 4 (USASpending) ───┘                          │
                            └──▶ MCP server ──────────────────────────────────────────┘
```

Phase 0 gates everything. Phases 1, 2, 5 are independent — pick by appetite. Phase 3 (Agent SEO) blocks Phase 7 deploy if you want public agent traffic on day 1; Phase 4 (USASpending) is independent additive value. Phases 6 + 7 + 8 + 9 are sequentially load-bearing and should land last in that order.

---

## File Structure (all phases combined)

| Action | Path | Phase | Responsibility |
|---|---|---|---|
| (verify) | (browser, hermes REPL, curl) | 0 | Live validation of shipped work |
| Create | `web/src/app/app/loading.tsx` | 1 | Skeleton for /app dashboard |
| Create | `web/src/app/app/runs/[id]/loading.tsx` | 1 | Skeleton for run page |
| Create | `web/src/app/app/opportunities/[id]/loading.tsx` | 1 | Skeleton for opportunity |
| Create | `web/src/app/app/action-packages/[id]/loading.tsx` | 1 | Skeleton for package |
| Create | `web/src/app/app/profile/loading.tsx` | 1 | Skeleton for profile list |
| Create | `web/src/app/app/error.tsx` | 1 | Error boundary across /app |
| Create | `web/src/app/error.tsx` | 1 | Root error boundary |
| Modify | various `/app/**/page.tsx` | 1 | Mobile + a11y sweep (specific edits per task) |
| Create | `web/src/app/api/run-stream/[id]/route.ts` | 2 | Same-origin SSE proxy |
| Modify | `web/src/app/app/runs/[id]/RunTimeline.tsx` | 2 | EventSource replaces polling |
| Create | `supabase/migrations/<ts>_add_api_keys.sql` | 3 | `api_keys` table + RLS |
| Create | `api/repositories/api_key.py` | 3 | Repo for the table |
| Modify | `api/auth.py` | 3 | `require_agent_or_internal` dep |
| Create | `api/routes/api_keys.py` | 3 | POST / GET / DELETE /api/keys |
| Create | `api/schemas/api_key*.py` (codegen) | 3 | Generated Pydantic |
| Create | `schemas/api-key*.schema.json` | 3 | Source schemas |
| Create | `api/routes/v1_tools.py` | 3 | `/api/v1/tools/<name>` public mirror |
| Create | `api/rate_limit.py` | 3 | Redis token-bucket helper |
| Create | `web/src/app/app/keys/page.tsx` | 3 | API-key UI (server shell) |
| Create | `web/src/app/app/keys/KeysClient.tsx` | 3 | Mint / list / revoke client |
| Create | `web/src/app/agents/page.tsx` (extend existing) | 3 | "Sign in to mint a key" CTA |
| Create | `landing/public/robots.txt` | 3 | Crawl allowlist |
| Modify | `web/src/app/agents/page.tsx` | 3 | JSON-LD `SoftwareApplication` |
| Create | `mcp_server_govcapture/` | 3 | Separate Python package |
| Create | `mcp_server_govcapture/pyproject.toml` | 3 | Entry-point: `mcp-server-govcapture` |
| Create | `mcp_server_govcapture/server.py` | 3 | MCP tool registration via `mcp` SDK |
| Create | `mcp_server_govcapture/README.md` | 3 | Install + Claude-Desktop config |
| Create | `supabase/migrations/<ts>_add_competitor_history.sql` | 4 | `competitor_history` table |
| Create | `schemas/competitor-history.schema.json` | 4 | Source schema |
| Create | `api/schemas/competitor_history*.py` | 4 | Codegen |
| Create | `api/skills/query_usaspending/skill.py` | 4 | USASpending API call + parse |
| Create | `api/skills/query_usaspending/__init__.py` | 4 | Public re-exports |
| Create | `api/repositories/competitor_history.py` | 4 | Repo |
| Create | `api/tests/test_query_usaspending.py` | 4 | Skill tests |
| Modify | `api/routes/opportunities.py` | 4 | New per-opportunity competitor routes |
| Modify | `api/routes/tools.py` | 4 | New `/tools/query-usaspending` |
| Modify | `api/routes/v1_tools.py` | 4 | Mirror in /api/v1/tools |
| Modify | `.hermes/plugins/govcapture/{__init__.py,tools.py}` | 4 | Register `govcapture_query_usaspending` |
| Create | `eval/runner/__init__.py` | 5 | |
| Create | `eval/runner/runner.py` | 5 | Drives a fixture through a skill |
| Create | `eval/runner/differs.py` | 5 | Tolerant structured comparison |
| Create | `eval/goldens/<fixture>/<skill>.json` | 5 | Per-fixture, per-skill golden |
| Create | `eval/README.md` | 5 | Run docs |
| Modify | `Makefile` | 5 | `eval`, `eval-bootstrap` targets |
| Modify | Supabase Auth dashboard config | 6 | SMTP via Resend / Postmark |
| Modify | `.env.production.example` | 6 | New email-provider vars |
| Modify | (VX1 host) | 7 | Provision, bootstrap, deploy |
| Modify | nginx + certbot config | 7 | TLS + reverse proxy |
| Modify | DNS (out of repo) | 7 | A record |
| Modify | Vercel env (out of repo) | 7 | NEXT_PUBLIC_API_BASE → prod URL |
| Modify | `devdocs/HANDOFF_PROMPT.md` | 9 | Section 1 + 7 final |
| Modify | `devdocs/CURRENT_STATE.md` | 9 | Final route count + section 10 |
| Tag | `v1.0.0` | 9 | Annotated git tag |

---

## Phase 0: Validation of shipped work (gates everything)

**Validation gate:** None (this IS the gate). Without 0.1–0.3 green, the rest of the plan is suspect.

### Task 0.1: Live API smoke test (5 min)

**Why:** Proves Sprint B + Phase 8 slice actually work against a running uvicorn, not just against `TestClient`.

- [ ] **Step 1: Start the server with a known internal key**

```bash
INTERNAL_API_KEY=smoke-test-key uv run uvicorn api.main:app --port 8765
```

(Run in background with `&` or in a separate terminal; `Ctrl+C` to stop.)

- [ ] **Step 2: Curl the public discovery endpoints**

```bash
curl -s http://localhost:8765/healthz
curl -s http://localhost:8765/.well-known/agent.json | python3 -m json.tool | head -25
curl -s http://localhost:8765/.well-known/llms.txt | head -20
```

Expected: each returns 200 with sensible content.

- [ ] **Step 3: Curl an internal tool route — happy path, 401, 422**

```bash
# Happy path
curl -s -X POST http://localhost:8765/tools/rank-opportunities \
  -H "X-Internal-API-Key: smoke-test-key" \
  -H "Content-Type: application/json" \
  -d '{"scored":[{"opportunity_id":"a","decision":"strong_pursue","total_score":92,"due_date":"2026-06-15"}]}'
# Expected: {"data":{"ranked":[...]}, "metrics":null}

# Auth fail
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8765/tools/rank-opportunities \
  -H "Content-Type: application/json" -d '{"scored":[]}'
# Expected: 401

# Validation fail
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8765/tools/rank-opportunities \
  -H "X-Internal-API-Key: smoke-test-key" -H "Content-Type: application/json" -d '{}'
# Expected: 422
```

- [ ] **Step 4: Stop the server**

```bash
kill $(lsof -ti :8765)
```

- [ ] **Step 5: Document the result.** Write a one-liner in `tasks/README.md` decision log: `2026-05-10 — Sprint B + Phase 8 slice live-tested against uvicorn; /healthz, well-known, /tools/rank-opportunities happy/401/422 all pass.`

(This task ALREADY ran at the top of the session that produced this plan. Re-run if the working tree has materially changed since `f5576b9`.)

### Task 0.2: Browser walk-through of `/web` (15 min, user-driven)

**Why:** The system prompt's "use the feature in a browser before reporting done" rule is unmet across all of Sprint C Phases 0–6.

- [ ] **Step 1: Confirm Supabase Auth is configured locally**

Check `.env`:
```bash
grep -c "^NEXT_PUBLIC_SUPABASE_URL=https://" .env && \
grep -c "^NEXT_PUBLIC_SUPABASE_ANON_KEY=" .env
```
Both should print `1`.

- [ ] **Step 2: Start the API and the web dev server in two terminals**

Terminal 1:
```bash
INTERNAL_API_KEY=smoke-test-key uv run uvicorn api.main:app --port 8000 --reload
```

Terminal 2:
```bash
npm --prefix /Volumes/CS_Stuff/govcon/web run dev
```

(`/web` runs on port 3001 per `package.json`'s dev script.)

- [ ] **Step 3: Visit and click through**

In the browser at `http://localhost:3001/`:

- [ ] Visit `/` → redirects to `/login` (signed-out) or `/app` (signed-in).
- [ ] On `/login`, enter your email; click "Send magic link"; observe the loading state ("Sending…" with spinner); land on the "Magic link sent" panel.
- [ ] In Supabase Studio (or your inbox), click the magic link.
- [ ] Land on `/app`. Observe either the empty state ("No company profile yet") or the profile list.
- [ ] If empty: click "Create company profile" → land on `/app/profile/new` → fill the form (Name + at least one of NAICS/capabilities) → submit → land on `/app/profile/{id}` → click "Profiles" in the header → see the list at `/app/profile`.
- [ ] Click "Start a run" on the dashboard → land on `/app/goal` → submit → land on `/app/runs/{id}` with the timeline shell. Status will stay `pending` (no orchestrator); that's expected. Observe the polling loop (Network tab shows `GET /agent-runs/{id}` every 2s).
- [ ] Click "Sign out" → land on `/login` → revisit `/app` → bounced back to `/login`.

- [ ] **Step 4: Open browser DevTools console and confirm zero errors across the walk-through.**

If errors surface, log them in `tasks/README.md` decision log AND in this plan's "Discovered issues" section (add inline at the top of Phase 1).

### Task 0.3: Hermes plugin REPL load check (5 min, user-driven)

**Why:** Sprint A shipped the plugin source; this proves it actually loads.

- [ ] **Step 1: Run hermes with project plugins enabled**

```bash
HERMES_ENABLE_PROJECT_PLUGINS=1 HERMES_HOME=/Volumes/CS_Stuff/govcon/.hermes hermes
```

- [ ] **Step 2: List tools in the REPL**

In the hermes prompt:
```
/tools
```

Expected: 10 tools under the `govcapture` toolset:
```
govcapture_parse_goal, govcapture_parse_pdf, govcapture_extract_requirements,
govcapture_score_fit, govcapture_detect_risks, govcapture_generate_action_package,
govcapture_search_sam, govcapture_fetch_attachment, govcapture_rank_opportunities,
govcapture_load_seeded_opportunities
```

- [ ] **Step 3: Call one tool against a running pack**

With Phase 0.1's uvicorn still running:
```
INTERNAL_API_KEY=smoke-test-key (in your shell env before starting hermes)
```

In hermes:
```
Run govcapture_rank_opportunities with scored=[{"opportunity_id":"a","decision":"pursue","total_score":80,"due_date":"2026-06-01"}]
```

Expected: hermes returns the ranked envelope.

- [ ] **Step 4: Document.** If the plugin doesn't load or a tool fails, note the error in `tasks/README.md` and decide whether to fix it inline or bump it to a follow-up task on this plan.

### Task 0.4: Final commit baseline

- [ ] **Step 1:** Confirm working tree clean (apart from user's parallel files):

```bash
git -C /Volumes/CS_Stuff/govcon status --short
```

Expected: only `README.md`, `tasks/README.md`, `landing/next.config.mjs`, `web/next.config.mjs` modified (or empty if user has committed those).

- [ ] **Step 2:** Capture the validation result in `tasks/README.md` decision log:

```
- 2026-05-10 — Phase 0 validation pass: uvicorn smoke (Sprint B + Phase 8
  slice), browser walk-through (Sprint C Phases 0–6), hermes plugin
  load (Sprint A). All green / discovered issues logged.
```

- [ ] **Step 3:** Commit the decision-log update:

```bash
git -C /Volumes/CS_Stuff/govcon add tasks/README.md && git -C /Volumes/CS_Stuff/govcon commit -m "docs: log Phase 0 validation pass"
```

(If `tasks/README.md` is currently a user-staged file with other edits, do NOT bundle. Surface and ask first.)

---

## Phase 1: Sprint C Phase 7 — UI polish

**Validation gate:** Phase 0.2 browser walk-through passed clean.

**Why:** Production-grade loading + error states; mobile and a11y sweep.

### Task 1.1: Loading skeletons at strategic route segments

**Files:** Create five `loading.tsx` siblings.

- [ ] **Step 1: Dashboard loading skeleton**

```tsx
// web/src/app/app/loading.tsx
import { Card } from '@/components/Card'
import { Skeleton } from '@/components/Skeleton'

export default function Loading() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-3 w-24" />
        <Skeleton className="mt-2 h-7 w-48" />
        <Skeleton className="mt-1 h-4 w-72" />
      </div>
      <Card>
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-2 h-6 w-20" />
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Run timeline loading skeleton**

```tsx
// web/src/app/app/runs/[id]/loading.tsx
import { Card } from '@/components/Card'
import { Skeleton } from '@/components/Skeleton'

export default function Loading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-20" />
      <div>
        <Skeleton className="h-3 w-12" />
        <Skeleton className="mt-2 h-7 w-3/4" />
        <Skeleton className="mt-1 h-4 w-48" />
      </div>
      <Card>
        <div className="flex gap-3">
          <Skeleton className="h-7 w-7 rounded-full" />
          <div className="flex-1">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="mt-1 h-5 w-40" />
          </div>
        </div>
        <div className="mt-5 space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </Card>
    </div>
  )
}
```

- [ ] **Step 3: Opportunity detail loading skeleton**

```tsx
// web/src/app/app/opportunities/[id]/loading.tsx
import { Card } from '@/components/Card'
import { Skeleton } from '@/components/Skeleton'

export default function Loading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-20" />
      <div>
        <Skeleton className="h-3 w-32" />
        <Skeleton className="mt-2 h-7 w-3/4" />
        <Skeleton className="mt-1 h-4 w-2/3" />
      </div>
      <Card>
        <Skeleton className="h-4 w-24" />
        <Skeleton className="mt-3 h-20 w-full" />
      </Card>
      <Card>
        <Skeleton className="h-4 w-16" />
        <Skeleton className="mt-3 h-12 w-32" />
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: Action-package loading skeleton**

```tsx
// web/src/app/app/action-packages/[id]/loading.tsx
import { Card } from '@/components/Card'
import { Skeleton } from '@/components/Skeleton'

export default function Loading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-24" />
      <div>
        <Skeleton className="h-3 w-32" />
        <Skeleton className="mt-2 h-7 w-3/4" />
        <Skeleton className="mt-1 h-4 w-48" />
      </div>
      <Card>
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-3 h-20 w-full" />
      </Card>
    </div>
  )
}
```

- [ ] **Step 5: Profile list loading skeleton**

```tsx
// web/src/app/app/profile/loading.tsx
import { Skeleton } from '@/components/Skeleton'

export default function Loading() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-3 w-16" />
        <Skeleton className="mt-2 h-7 w-48" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Verify**

```bash
npm --prefix /Volumes/CS_Stuff/govcon/web run typecheck
```

Expected: clean.

In the browser, throttle network in DevTools to "Slow 3G", navigate `/app`, `/app/profile`, `/app/runs/{any-id}` — observe skeleton flash.

### Task 1.2: Error boundaries

**Files:** Create `web/src/app/error.tsx` and `web/src/app/app/error.tsx`.

- [ ] **Step 1: Root error boundary**

```tsx
// web/src/app/error.tsx
'use client'

import Link from 'next/link'
import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Production sites should pipe this to Sentry / logging.
    // For v1, console is enough.
    console.error(error)
  }, [error])

  return (
    <main className="min-h-screen bg-[#f7f8fb] text-slate-950">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-6 py-12">
        <div className="rounded-[28px] border border-white/80 bg-white/72 p-7 shadow-[0_24px_70px_-36px_rgba(15,23,42,0.42)] backdrop-blur-2xl">
          <p className="text-sm font-medium text-rose-700">Something broke</p>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal">
            We hit an unexpected error
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Try again, or head back to the dashboard. If this keeps happening,
            email{' '}
            <a
              className="font-medium text-blue-900 underline-offset-4 hover:underline"
              href="mailto:support@govcapture.example"
            >
              support@govcapture.example
            </a>
            {error.digest ? ` and quote error id ${error.digest}.` : '.'}
          </p>
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              onClick={() => reset()}
              className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              Try again
            </button>
            <Link
              href="/app"
              className="inline-flex h-10 items-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              Dashboard
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
```

- [ ] **Step 2: /app error boundary**

```tsx
// web/src/app/app/error.tsx
'use client'

import { useEffect } from 'react'
import { Card } from '@/components/Card'
import { PageHeader } from '@/components/PageHeader'

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Error"
        title="That page didn't load"
        subtitle={
          error.digest
            ? `Error id: ${error.digest}`
            : 'Try again, or head back to the dashboard.'
        }
      />
      <Card className="border-rose-200 bg-rose-50/80 text-sm text-rose-900">
        {error.message || 'Unknown error.'}
      </Card>
      <button
        type="button"
        onClick={() => reset()}
        className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
      >
        Try again
      </button>
    </div>
  )
}
```

- [ ] **Step 3: Verify**

```bash
npm --prefix /Volumes/CS_Stuff/govcon/web run typecheck
```

Force a render error temporarily (e.g., add `throw new Error('test')` at the top of `/app/page.tsx`, observe the boundary rendering, then revert).

### Task 1.3: Mobile sweep at 375px / 768px / 1280px

**Files:** Modify various — list per finding.

- [ ] **Step 1: Walk every authed page at 375px in DevTools** and log issues:

| Page | Issue | Fix |
|---|---|---|
| `/login` | (test) | (fix or n/a) |
| `/app` | (test) | (fix or n/a) |
| `/app/profile` | (test) | (fix or n/a) |
| `/app/profile/new` | (test) | (fix or n/a) |
| `/app/profile/[id]` | (test) | (fix or n/a) |
| `/app/goal` | (test) | (fix or n/a) |
| `/app/runs/[id]` | (test) | (fix or n/a) |
| `/app/opportunities/[id]` | (test) | (fix or n/a) |
| `/app/action-packages/[id]` | (test) | (fix or n/a) |
| `/agents` | (test) | (fix or n/a) |

- [ ] **Step 2: For each issue logged, add a sub-task** to this plan inline, fix, verify, move on. Common patterns:

  - Headers that overflow: `flex-wrap` or `text-clip`.
  - Side-by-side grids that crush: switch from `sm:grid-cols-2` to `md:grid-cols-2`.
  - Tables that overflow: wrap in `overflow-auto` (already done in action-package compliance matrix).
  - Buttons that wrap: tighten label text or add `whitespace-nowrap`.

- [ ] **Step 3: Verify** with `npm --prefix /Volumes/CS_Stuff/govcon/web run build` after every fix to catch typecheck regressions early.

### Task 1.4: Accessibility pass

**Files:** Targeted edits per finding.

- [ ] **Step 1:** Run an automated check — install `eslint-plugin-jsx-a11y`:

```bash
npm --prefix /Volumes/CS_Stuff/govcon/web install --save-dev eslint-plugin-jsx-a11y
```

Add to `web/eslint.config.mjs`:
```js
import jsxA11y from 'eslint-plugin-jsx-a11y'
// ... in the config array:
{
  plugins: { 'jsx-a11y': jsxA11y },
  rules: {
    ...jsxA11y.configs.recommended.rules,
  },
}
```

- [ ] **Step 2: Run lint and fix flagged issues:**

```bash
npm --prefix /Volumes/CS_Stuff/govcon/web run lint
```

Common fixes:
- `<button>` without accessible label → add `aria-label` or visible text.
- `<input>` without `<label>` → wrap or `aria-labelledby`.
- `<a>` with no href but click handler → use `<button>` instead.
- Missing `alt` on `<img>` (we use lucide; `aria-hidden` is already pattern).

- [ ] **Step 3: Tab-order check** — open every page, hit Tab repeatedly, confirm focus visits inputs/buttons in reading order.

- [ ] **Step 4: Verify** lint clean.

### Task 1.5: Copy + microcopy pass

**Files:** Sweep all `/app/**/*.tsx` for stale or apologetic copy.

- [ ] **Step 1: Audit for empty states.** Every "No X yet" should have:
  - A clear title.
  - A 1-sentence explainer.
  - A primary CTA.

- [ ] **Step 2: Audit for error states.** Every catch-block should produce a human-readable message, not "Could not load."

- [ ] **Step 3: Audit for loading states.** Every busy boolean should have an accompanying label ("Saving…", "Queuing run…", "Sending…").

- [ ] **Step 4: Final visual sweep** — run the dev server, walk every page, eyeball spacing / alignment / typography. Fix per-issue.

### Task 1.6: Phase 1 verification + commit

- [ ] All Phase 1 verification gates green: pytest 154+, ruff, mypy, typecheck, lint, build.
- [ ] Commit:

```bash
git -C /Volumes/CS_Stuff/govcon add web/src/app/error.tsx web/src/app/app/error.tsx \
  web/src/app/app/loading.tsx web/src/app/app/runs/\[id\]/loading.tsx \
  web/src/app/app/opportunities/\[id\]/loading.tsx \
  web/src/app/app/action-packages/\[id\]/loading.tsx \
  web/src/app/app/profile/loading.tsx \
  web/eslint.config.mjs web/package.json web/package-lock.json \
  $(git -C /Volumes/CS_Stuff/govcon diff --name-only -- web/src/app/)
git -C /Volumes/CS_Stuff/govcon commit -m "feat(web): Sprint C Phase 7 — loading skeletons + error boundaries + mobile + a11y"
```

---

## Phase 2: SSE upgrade (replace 2s polling)

**Validation gate:** Phase 0.2 confirmed RunTimeline polls correctly. Phase 1's Task 1.1's run-page skeleton is in place.

**Why:** Polling burns ~30 RPS per active run watcher; SSE is the original design. Browser `EventSource` doesn't support custom headers, so the same-origin Next Route Handler proxies cookies → bearer.

### Task 2.1: Same-origin SSE proxy route

**Files:** Create `web/src/app/api/run-stream/[id]/route.ts`

- [ ] **Step 1:** Author the proxy

```ts
// web/src/app/api/run-stream/[id]/route.ts
import { NextResponse, type NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { getApiBase } from '@/lib/api'

export const dynamic = 'force-dynamic'

type Params = { id: string }

export async function GET(
  request: NextRequest,
  context: { params: Promise<Params> },
) {
  const { id } = await context.params
  const supabase = await createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (!session) {
    return new NextResponse('Unauthorized', { status: 401 })
  }

  const upstream = await fetch(`${getApiBase()}/agent-runs/${id}/stream`, {
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      Accept: 'text/event-stream',
    },
    cache: 'no-store',
    // Pass through the request's abort signal so disconnect propagates.
    signal: request.signal,
  })

  if (!upstream.ok || !upstream.body) {
    return new NextResponse(`Upstream error ${upstream.status}`, {
      status: upstream.status,
    })
  }

  return new NextResponse(upstream.body, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  })
}
```

- [ ] **Step 2: Verify it doesn't break the build**

```bash
npm --prefix /Volumes/CS_Stuff/govcon/web run typecheck && \
npm --prefix /Volumes/CS_Stuff/govcon/web run build
```

### Task 2.2: Replace polling with EventSource in RunTimeline

**Files:** Modify `web/src/app/app/runs/[id]/RunTimeline.tsx`

- [ ] **Step 1:** Replace the polling `useEffect` with EventSource. Replace the entire current `useEffect` block with:

```tsx
useEffect(() => {
  if (TERMINAL_STATUSES.includes(initial.status)) return undefined

  const es = new EventSource(`/api/run-stream/${run.id}`)
  let stillMounted = true

  function handleEvent(rawType: string, data: string) {
    if (!stillMounted) return
    let event: TraceEvent
    try {
      event = JSON.parse(data) as TraceEvent
    } catch {
      return
    }
    setRun((prev) => ({
      ...prev,
      steps: [...prev.steps, event],
      status: event.type === 'run_completed' ? inferStatusFromEvent(event) : prev.status,
    }))
    if (rawType === 'run_completed') {
      es.close()
      // Refresh once for terminal-state writes (action_package_id, completed_at).
      fetchAndSetTerminalRun()
    }
  }

  // EventSource fires `message` for un-named events; named events need addEventListener.
  ;[
    'run_started',
    'step_started',
    'step_completed',
    'tool_called',
    'tool_returned',
    'opportunity_ranked',
    'needs_human',
    'run_completed',
  ].forEach((type) => {
    es.addEventListener(type, (ev) =>
      handleEvent(type, (ev as MessageEvent).data),
    )
  })

  es.onerror = () => {
    // Browser will auto-reconnect by default; if we'd rather give up:
    // es.close()
    if (stillMounted) setError('Live stream disconnected — retrying.')
  }

  async function fetchAndSetTerminalRun() {
    try {
      const session = (await supabase.auth.getSession()).data.session
      if (!session) return
      const next = await api.getAgentRun(session.access_token, run.id)
      if (!stillMounted) return
      setRun(next)
      if (next.opportunities.length !== opportunities.length) {
        const opps = await api.listAgentRunOpportunities(
          session.access_token,
          run.id,
        )
        if (stillMounted) setOpportunities(opps)
      }
    } catch (err) {
      /* swallow */
    }
  }

  return () => {
    stillMounted = false
    es.close()
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [run.id])

function inferStatusFromEvent(event: TraceEvent): RunStatus {
  if (typeof event.summary === 'string' && event.summary.toLowerCase().includes('fail')) {
    return 'failed'
  }
  // Default: trust the orchestrator's terminal status update on the row.
  return 'complete'
}
```

(Note: this is a structural change to a 200-line file. Read the current file first, replace the `useEffect` body precisely, and remove the now-unused `cancelledRef` and `POLL_INTERVAL_MS` if they become dead code.)

- [ ] **Step 2: Verify**

```bash
npm --prefix /Volumes/CS_Stuff/govcon/web run typecheck && \
npm --prefix /Volumes/CS_Stuff/govcon/web run lint && \
npm --prefix /Volumes/CS_Stuff/govcon/web run build
```

- [ ] **Step 3: Manual test** — run the API, run the dev server, queue a run, manually publish a fake `run_started` event to Redis channel `agent-run:{run_id}`, observe the timeline updating without 2s lag.

  ```bash
  redis-cli PUBLISH agent-run:<the-run-uuid> '{"type":"run_started","run_id":"<uuid>","goal":"x","ts":"2026-05-10T00:00:00Z"}'
  ```

### Task 2.3: Phase 2 commit

```bash
git -C /Volumes/CS_Stuff/govcon add \
  web/src/app/api/run-stream/\[id\]/route.ts \
  web/src/app/app/runs/\[id\]/RunTimeline.tsx
git -C /Volumes/CS_Stuff/govcon commit -m "feat(web): Sprint C Phase 7.4 — SSE upgrade replacing 2s polling"
```

---

## Phase 3: Agent SEO infrastructure (the real Phase 8)

**Validation gate:** Phase 0.1 live smoke test still green.

**Architecture decision recap:** Per-agent `gck_…` keys augment `INTERNAL_API_KEY`. The new `/api/v1/tools/<name>` accepts EITHER. Existing internal callers (Sprint B) are unaffected. The MCP server is a thin HTTP wrapper over `/api/v1/tools/<name>`, same pattern as the Hermes plugin.

### Task 3.1 — `api_keys` schema migration ⚠️ ASK FIRST

**Files:** Create `supabase/migrations/<timestamp>_add_api_keys.sql`

- [ ] **Step 1: Pause and ask the user for explicit confirmation.** Per handoff §17.3, schema changes are an "ask first" trigger. Surface:

> "About to add an `api_keys` table to enable per-agent `gck_…` keys. Proposed columns: id, owner_profile_id, name, key_hash, prefix, scopes, last_used_at, revoked_at, created_at. RLS scoped to owner_profile_id. OK to proceed?"

Do NOT proceed without explicit confirmation.

- [ ] **Step 2: Author the migration.** Use the existing migration timestamp pattern (UTC `YYYYMMDDHHMMSS`):

```sql
-- supabase/migrations/20260510120000_add_api_keys.sql
create table public.api_keys (
  id                  uuid primary key default extensions.gen_random_uuid(),
  owner_profile_id    uuid not null references public.profiles(id) on delete cascade,
  name                text not null,
  key_hash            text not null unique,
  prefix              text not null,
  scopes              text[] not null default '{tools:*}',
  last_used_at        timestamptz,
  revoked_at          timestamptz,
  created_at          timestamptz not null default now()
);
create index idx_api_keys_owner    on public.api_keys(owner_profile_id);
create index idx_api_keys_revoked  on public.api_keys(revoked_at) where revoked_at is null;

alter table public.api_keys enable row level security;
create policy "owner can read own keys" on public.api_keys
  for select using (owner_profile_id = (select auth.uid())::uuid);
create policy "owner can insert own keys" on public.api_keys
  for insert with check (owner_profile_id = (select auth.uid())::uuid);
create policy "owner can revoke own keys" on public.api_keys
  for update using (owner_profile_id = (select auth.uid())::uuid)
  with check (owner_profile_id = (select auth.uid())::uuid);
```

- [ ] **Step 3: Apply** (after user ack):

```bash
supabase db push
```

- [ ] **Step 4: Generate Pydantic schema** if you've authored a JSON Schema source. For v1, hand-roll the Pydantic model directly (api_keys is internal):

  Skip. Build the model directly in `api/schemas/api_key.py` (Task 3.3).

### Task 3.2 — `ApiKeyRepository`

**Files:** Create `api/repositories/api_key.py` and a Pydantic model.

- [ ] **Step 1:** Author the Pydantic models:

```python
# api/schemas/api_key.py
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ApiKey(BaseModel):
    id: UUID
    owner_profile_id: UUID
    name: str
    prefix: str
    scopes: list[str]
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class ApiKeyMint(BaseModel):
    """One-time response when minting; the only place plaintext_key appears."""
    id: UUID
    name: str
    prefix: str
    plaintext_key: str = Field(..., description="Show ONCE. Never retrievable.")
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
```

- [ ] **Step 2:** Author the repository:

```python
# api/repositories/api_key.py
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from supabase import AsyncClient

KEY_PREFIX = "gck"
KEY_RANDOM_BYTES = 32  # 256 bits


def _generate_plaintext_key() -> tuple[str, str, str]:
    """Return (plaintext, prefix, hash). Plaintext form: gck_<urlsafe>."""
    raw = secrets.token_urlsafe(KEY_RANDOM_BYTES)
    plaintext = f"{KEY_PREFIX}_{raw}"
    prefix = plaintext[:12]  # gck_ + first 8 chars of random
    digest = hashlib.sha256(plaintext.encode()).hexdigest()
    return plaintext, prefix, digest


class ApiKeyRepository:
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def list_for_owner(self, owner_id: uuid.UUID) -> list[dict[str, Any]]:
        resp = await (
            self._client.table("api_keys")
            .select("*")
            .eq("owner_profile_id", str(owner_id))
            .execute()
        )
        return resp.data or []

    async def mint(self, owner_id: uuid.UUID, name: str) -> tuple[str, dict[str, Any]]:
        plaintext, prefix, digest = _generate_plaintext_key()
        resp = await (
            self._client.table("api_keys")
            .insert({
                "owner_profile_id": str(owner_id),
                "name": name,
                "key_hash": digest,
                "prefix": prefix,
                "scopes": ["tools:*"],
            })
            .execute()
        )
        rows = resp.data or []
        if not rows:
            raise RuntimeError("api_keys insert returned no row")
        return plaintext, rows[0]

    async def revoke(self, owner_id: uuid.UUID, key_id: uuid.UUID) -> dict[str, Any] | None:
        resp = await (
            self._client.table("api_keys")
            .update({"revoked_at": datetime.now(timezone.utc).isoformat()})
            .eq("owner_profile_id", str(owner_id))
            .eq("id", str(key_id))
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None

    async def find_active_by_hash(self, key_hash: str) -> dict[str, Any] | None:
        resp = await (
            self._client.table("api_keys")
            .select("*")
            .eq("key_hash", key_hash)
            .is_("revoked_at", "null")
            .maybe_single()
            .execute()
        )
        return resp.data
```

- [ ] **Step 3:** Tests in `api/tests/test_api_key_repo.py` against `FakeSupabase` — mint/list/revoke/find-by-hash.

### Task 3.3 — Auth dep accepting either header

**Files:** Modify `api/auth.py`

- [ ] **Step 1:** Add a new dep that accepts either `INTERNAL_API_KEY` (existing) or a `gck_…` bearer key. Append to `api/auth.py`:

```python
import hashlib

from api.deps import get_supabase  # NB: do not introduce import cycle; if cycle, move repo dep wiring out
from api.repositories.api_key import ApiKeyRepository


class AgentActor(BaseModel):
    """An authenticated agent. Either an internal call or a per-user key."""
    is_internal: bool
    owner_profile_id: uuid.UUID | None = None
    api_key_id: uuid.UUID | None = None


async def require_agent_or_internal(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_internal_api_key: Annotated[str | None, Header(alias="X-Internal-API-Key")] = None,
    client: AsyncClient = Depends(get_supabase),
) -> AgentActor:
    # Path A: internal shared secret (Sprint B compatibility)
    configured_internal = settings.internal_api_key
    if x_internal_api_key and configured_internal and secrets.compare_digest(
        x_internal_api_key, configured_internal,
    ):
        return AgentActor(is_internal=True)

    # Path B: per-user gck_… bearer
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing credentials")
    token = authorization.split(" ", 1)[1].strip()
    if not token.startswith("gck_"):
        raise HTTPException(401, "Token must be an X-Internal-API-Key or a gck_ key")

    digest = hashlib.sha256(token.encode()).hexdigest()
    repo = ApiKeyRepository(client)
    row = await repo.find_active_by_hash(digest)
    if row is None:
        raise HTTPException(401, "Invalid or revoked API key")

    return AgentActor(
        is_internal=False,
        owner_profile_id=uuid.UUID(row["owner_profile_id"]),
        api_key_id=uuid.UUID(row["id"]),
    )
```

(Watch the import cycle: `api.auth` cannot import `api.deps`. If a cycle appears, inline `get_supabase` here or accept `AsyncClient` via a local helper. Adapt.)

- [ ] **Step 2:** Tests in `api/tests/test_auth_agent.py` — internal-key path, valid-gck path, revoked-gck path, malformed bearer, missing both headers.

### Task 3.4 — `/api/keys` routes (mint/list/revoke)

**Files:** Create `api/routes/api_keys.py`; register in `api/main.py`.

- [ ] **Step 1:** Author the routes:

```python
# api/routes/api_keys.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from supabase import AsyncClient

from api.auth import AuthenticatedUser, require_user
from api.deps import get_supabase
from api.repositories.api_key import ApiKeyRepository
from api.schemas.api_key import ApiKey, ApiKeyCreate, ApiKeyMint

router = APIRouter(prefix="/api/keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKey])
async def list_keys(
    user: AuthenticatedUser = Depends(require_user),
    client: AsyncClient = Depends(get_supabase),
) -> list[ApiKey]:
    repo = ApiKeyRepository(client)
    rows = await repo.list_for_owner(user.id)
    return [ApiKey.model_validate(r) for r in rows]


@router.post("", response_model=ApiKeyMint, status_code=201)
async def mint_key(
    payload: ApiKeyCreate,
    user: AuthenticatedUser = Depends(require_user),
    client: AsyncClient = Depends(get_supabase),
) -> ApiKeyMint:
    repo = ApiKeyRepository(client)
    plaintext, row = await repo.mint(user.id, payload.name)
    return ApiKeyMint(
        id=row["id"],
        name=row["name"],
        prefix=row["prefix"],
        plaintext_key=plaintext,
        created_at=row["created_at"],
    )


@router.delete("/{key_id}", status_code=204)
async def revoke_key(
    key_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    client: AsyncClient = Depends(get_supabase),
) -> None:
    repo = ApiKeyRepository(client)
    revoked = await repo.revoke(user.id, key_id)
    if revoked is None:
        raise HTTPException(404, "Key not found or not yours")
    return None
```

- [ ] **Step 2:** Register in `api/main.py`:

```python
from api.routes import (
    action_packages, agent_runs, api_keys, company_profiles,
    healthz, opportunities, profiles, tools, waitlist, well_known,
)
# ...
app.include_router(api_keys.router)
```

- [ ] **Step 3:** Tests `api/tests/test_api_keys_routes.py` — mint returns plaintext once, list omits hash, revoke flips revoked_at, 401 without JWT.

### Task 3.5 — `/api/v1/tools/<name>` public mirror

**Files:** Create `api/routes/v1_tools.py`; register.

- [ ] **Step 1:** Author the mirror. Per skill, dispatch to the same handler used by `/tools/<name>` — refactor the dispatch into helper functions if needed, but the simplest path is to literally re-mount the router at a different prefix. **However**, the auth dep needs to change from `require_internal_actor` to `require_agent_or_internal`. So we copy + adapt:

```python
# api/routes/v1_tools.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import AsyncClient

from api.auth import AgentActor, require_agent_or_internal
from api.config import settings
from api.deps import get_llm, get_storage, get_supabase
from api.llm import LLM, LLMMetrics
from api.schemas.tool_requests import (
    DetectRisksRequest, ExtractRequirementsRequest, FetchAttachmentRequest,
    GenerateActionPackageRequest, LoadSeededOpportunitiesRequest,
    ParseGoalRequest, ParsePdfRequest, RankOpportunitiesRequest,
    ScoreFitRequest, SearchSamRequest,
)
from api.skills.detect_risks.skill import detect_risks
from api.skills.extract_requirements.skill import extract_requirements
from api.skills.fetch_attachment.skill import fetch_attachment
from api.skills.generate_action_package.skill import generate_action_package
from api.skills.load_seeded_opportunities.skill import load_seeded_opportunities
from api.skills.parse_goal.skill import parse_goal
from api.skills.parse_pdf.skill import parse_pdf
from api.skills.rank_opportunities.skill import rank_opportunities
from api.skills.score_fit.skill import score_fit
from api.skills.search_sam.skill import search_sam_opportunities
from api.storage_adapter import StorageAdapter

router = APIRouter(prefix="/api/v1/tools", tags=["v1-tools"])


class ToolResponse(BaseModel):
    data: Any
    metrics: LLMMetrics | None = None


# Each handler mirrors api/routes/tools.py, with the auth dep swapped.
# (For brevity in this plan, two examples; replicate the pattern for all 10.)


@router.post("/parse-goal", response_model=ToolResponse)
async def parse_goal_v1(
    payload: ParseGoalRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
    llm: LLM = Depends(get_llm),
) -> ToolResponse:
    data, metrics = await parse_goal(payload.model_dump(), llm=llm)
    return ToolResponse(data=data, metrics=metrics)


@router.post("/rank-opportunities", response_model=ToolResponse)
async def rank_opportunities_v1(
    payload: RankOpportunitiesRequest,
    _actor: AgentActor = Depends(require_agent_or_internal),
) -> ToolResponse:
    out = rank_opportunities(payload.model_dump())
    return ToolResponse(data=out)


# ... 8 more, mirroring api/routes/tools.py exactly except for the auth dep.
```

- [ ] **Step 2:** Register router. **Important:** mount BEFORE `tools.router` so the OpenAPI ordering is sensible.

- [ ] **Step 3:** Tests in `api/tests/test_v1_tools_routes.py` — for each route: 200 with internal key, 200 with valid gck_, 401 with neither, 401 with revoked gck_, 422 with bad payload. Reuse `fake_llm_factory`.

### Task 3.6 — Per-key rate limiter

**Files:** Create `api/rate_limit.py`; integrate into `require_agent_or_internal`.

- [ ] **Step 1:** Token-bucket helper using Redis (existing `api.redis.redis_client`):

```python
# api/rate_limit.py
from __future__ import annotations

import time

from api.redis import redis_client


class RateLimitError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


async def acquire(key: str, *, capacity: int, refill_per_sec: float) -> None:
    """Token-bucket. Raises RateLimitError on empty bucket.

    State stored in Redis hash {tokens, last_refill_ts}. Atomic via Lua script.
    """
    now = time.time()
    lua = """
    local key = KEYS[1]
    local cap = tonumber(ARGV[1])
    local refill = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local b = redis.call('HMGET', key, 'tokens', 'ts')
    local tokens = tonumber(b[1]) or cap
    local ts = tonumber(b[2]) or now
    tokens = math.min(cap, tokens + (now - ts) * refill)
    if tokens < 1 then
      local need = 1 - tokens
      redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
      redis.call('EXPIRE', key, 600)
      return -1 * math.ceil(need / refill)
    end
    redis.call('HMSET', key, 'tokens', tokens - 1, 'ts', now)
    redis.call('EXPIRE', key, 600)
    return 0
    """
    result = await redis_client.eval(lua, 1, key, capacity, refill_per_sec, now)
    if result < 0:
        raise RateLimitError(retry_after=int(-result))
```

- [ ] **Step 2:** Apply per-key limit in v1 handler (or a dedicated middleware). Default: 60 req/min/key:

```python
# In require_agent_or_internal, after determining actor:
from api.rate_limit import RateLimitError, acquire

if not actor.is_internal:
    try:
        await acquire(
            f"rl:apikey:{actor.api_key_id}",
            capacity=60,
            refill_per_sec=1.0,
        )
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(exc.retry_after)},
        )
```

- [ ] **Step 3:** Tests `api/tests/test_rate_limit.py` — happy path, exhaustion produces 429 with Retry-After.

### Task 3.7 — `/app/keys` UI

**Files:** Create `web/src/app/app/keys/{page.tsx,KeysClient.tsx}`; extend api client.

- [ ] **Step 1:** Extend `web/src/lib/api.ts`:

```ts
// types.ts additions:
export type ApiKey = {
  id: string
  name: string
  prefix: string
  scopes: string[]
  last_used_at?: string | null
  revoked_at?: string | null
  created_at: string
}

export type ApiKeyMint = {
  id: string
  name: string
  prefix: string
  plaintext_key: string
  created_at: string
}

// api.ts additions in `export const api = {...}`:
listApiKeys: (token: string) => request<ApiKey[]>('/api/keys', token),
mintApiKey: (token: string, name: string) =>
  request<ApiKeyMint>('/api/keys', token, {
    method: 'POST',
    body: JSON.stringify({ name }),
  }),
revokeApiKey: (token: string, id: string) =>
  request<null>(`/api/keys/${id}`, token, { method: 'DELETE' }),
```

- [ ] **Step 2:** Server shell `web/src/app/app/keys/page.tsx`:

```tsx
import { createClient } from '@/lib/supabase/server'
import { api, ApiError } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Card } from '@/components/Card'
import type { ApiKey } from '@/lib/types'
import { KeysClient } from './KeysClient'

export const dynamic = 'force-dynamic'

async function getToken(): Promise<string | null> {
  const supabase = await createClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

export default async function KeysPage() {
  const token = await getToken()
  if (!token) return null
  let keys: ApiKey[] = []
  let loadError: string | null = null
  try {
    keys = await api.listApiKeys(token)
  } catch (err) {
    loadError = err instanceof ApiError ? err.message : 'Could not load keys.'
  }
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Agent keys"
        title="API keys"
        subtitle="Per-agent gck_… keys. Use these to call /api/v1/tools/<name> from your agent."
      />
      {loadError ? (
        <Card className="border-red-200 bg-red-50/80 text-sm text-red-900">
          {loadError}
        </Card>
      ) : null}
      <KeysClient initial={keys} />
    </div>
  )
}
```

- [ ] **Step 3:** Client `web/src/app/app/keys/KeysClient.tsx`:

```tsx
'use client'

import { useState } from 'react'
import { Copy, KeyRound, Loader2, Trash2 } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import type { ApiKey, ApiKeyMint } from '@/lib/types'

export function KeysClient({ initial }: { initial: ApiKey[] }) {
  const supabase = createClient()
  const [keys, setKeys] = useState<ApiKey[]>(initial)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [justMinted, setJustMinted] = useState<ApiKeyMint | null>(null)

  async function withToken(): Promise<string | null> {
    const session = (await supabase.auth.getSession()).data.session
    if (!session) {
      setError('Session expired. Sign in again.')
      return null
    }
    return session.access_token
  }

  async function refresh() {
    const token = await withToken()
    if (!token) return
    try {
      setKeys(await api.listApiKeys(token))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Refresh failed.')
    }
  }

  async function mint(event: React.FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    setError('')
    try {
      const token = await withToken()
      if (!token) return
      const minted = await api.mintApiKey(token, name.trim())
      setJustMinted(minted)
      setName('')
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Mint failed.')
    } finally {
      setBusy(false)
    }
  }

  async function revoke(id: string) {
    if (!confirm('Revoke this key? Calls using it will start failing.')) return
    setBusy(true)
    try {
      const token = await withToken()
      if (!token) return
      await api.revokeApiKey(token, id)
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Revoke failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      {justMinted ? (
        <Card className="border-emerald-200 bg-emerald-50/80">
          <p className="text-sm font-medium text-emerald-900">
            New key minted — copy it now. We can't show it again.
          </p>
          <pre className="mt-3 overflow-auto rounded-2xl border border-emerald-200 bg-white p-3 text-xs text-emerald-900">
            {justMinted.plaintext_key}
          </pre>
          <div className="mt-3 flex gap-3">
            <button
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(justMinted.plaintext_key)
              }}
              className="inline-flex h-9 items-center gap-2 rounded-full bg-emerald-700 px-3 text-xs font-medium text-white transition hover:bg-emerald-600"
            >
              <Copy size={13} aria-hidden /> Copy
            </button>
            <button
              type="button"
              onClick={() => setJustMinted(null)}
              className="inline-flex h-9 items-center gap-2 rounded-full border border-emerald-200 bg-white px-3 text-xs font-medium text-emerald-900 transition hover:border-emerald-300"
            >
              I've saved it
            </button>
          </div>
        </Card>
      ) : null}

      <Card>
        <form onSubmit={mint} className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <label className="block flex-1">
            <span className="text-xs font-medium text-slate-600">New key name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. claude-desktop, prod-orchestrator"
              className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
            />
          </label>
          <button
            type="submit"
            disabled={busy || !name.trim()}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy ? <Loader2 size={15} className="animate-spin" aria-hidden /> : <KeyRound size={15} aria-hidden />}
            Mint
          </button>
        </form>
        {error ? (
          <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
            {error}
          </p>
        ) : null}
      </Card>

      <Card>
        <p className="text-sm font-medium text-blue-900">Active keys ({keys.filter((k) => !k.revoked_at).length})</p>
        {keys.length === 0 ? (
          <p className="mt-3 text-sm text-slate-600">No keys yet. Mint one to start calling /api/v1/tools/&lt;name&gt;.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {keys.map((key) => (
              <li
                key={key.id}
                className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3"
              >
                <div>
                  <p className="text-sm font-semibold text-slate-950">{key.name}</p>
                  <p className="mt-1 text-xs font-mono text-slate-500">
                    {key.prefix}…{key.revoked_at ? ' · revoked' : ''}
                  </p>
                </div>
                {!key.revoked_at ? (
                  <button
                    type="button"
                    onClick={() => revoke(key.id)}
                    className="inline-flex h-8 items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-3 text-xs font-medium text-rose-900 transition hover:border-rose-300"
                  >
                    <Trash2 size={12} aria-hidden /> Revoke
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
```

- [ ] **Step 4:** Add a header link in `web/src/app/app/layout.tsx` next to "Profiles":

```tsx
<Link
  href="/app/keys"
  className="grid h-10 place-items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
>
  API keys
</Link>
```

### Task 3.8 — MCP server package

**Files:** Create `mcp_server_govcapture/{pyproject.toml,server.py,README.md}`

- [ ] **Step 1:** `pyproject.toml`:

```toml
[project]
name = "mcp-server-govcapture"
version = "0.1.0"
description = "MCP server exposing the GovCon Bid Desk capability pack's 10 tools."
requires-python = ">=3.11"
dependencies = [
  "mcp>=0.10",
  "httpx>=0.28",
  "pydantic>=2.0",
]

[project.scripts]
mcp-server-govcapture = "mcp_server_govcapture.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["mcp_server_govcapture"]
```

- [ ] **Step 2:** `server.py`:

```python
"""MCP server wrapping the GovCon /api/v1/tools/<name> surface.

Same pattern as the Hermes plugin (Sprint A): each MCP tool is a thin
HTTP wrapper around the public /api/v1/tools/<name> route. One canonical
code path; the pack-side route is the source of truth.

Configuration via environment variables:
  GOVCAPTURE_API_BASE         default https://api.govcapture.example
  GOVCAPTURE_API_KEY          required; gck_… key minted at /app/keys
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("govcapture")

_BASE = os.environ.get("GOVCAPTURE_API_BASE", "https://api.govcapture.example").rstrip("/")
_KEY = os.environ.get("GOVCAPTURE_API_KEY")


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not _KEY:
        raise RuntimeError("GOVCAPTURE_API_KEY not set. Mint one at /app/keys.")
    headers = {"Authorization": f"Bearer {_KEY}", "Content-Type": "application/json"}
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(f"{_BASE}/api/v1/tools/{path}", headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def parse_goal(goal: str, company_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Parse a natural-language goal into structured search criteria."""
    return _post("parse-goal", {"goal": goal, "company_profile": company_profile or {}})


@mcp.tool()
def rank_opportunities(scored: list[dict[str, Any]]) -> dict[str, Any]:
    """Sort scored opportunities by (decision band, -score, due asc)."""
    return _post("rank-opportunities", {"scored": scored})


# ... 8 more tools mirroring the Hermes plugin's tools.py.


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3:** `README.md` with Claude-Desktop config snippet:

```markdown
# mcp-server-govcapture

MCP server exposing GovCon Bid Desk's 10 tools.

## Install

    pip install mcp-server-govcapture

## Configure (Claude Desktop)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

    {
      "mcpServers": {
        "govcapture": {
          "command": "mcp-server-govcapture",
          "env": {
            "GOVCAPTURE_API_KEY": "gck_..."
          }
        }
      }
    }

Mint a key at https://app.govcapture.example/app/keys.

## Tools

[10 tools listed]
```

- [ ] **Step 4:** Local test:

```bash
GOVCAPTURE_API_BASE=http://localhost:8000 \
GOVCAPTURE_API_KEY=$(mint a test key via curl) \
uv run python -m mcp_server_govcapture.server
```

(With a recent MCP SDK, `mcp dev` provides an inspector for testing.)

### Task 3.9 — Robots + JSON-LD

**Files:** Create `landing/public/robots.txt`; modify `web/src/app/agents/page.tsx`.

- [ ] **Step 1:** `landing/public/robots.txt`:

```
User-agent: *
Allow: /
Sitemap: https://govcapture.example/sitemap.xml
```

- [ ] **Step 2:** Add JSON-LD to `/agents` page header (insert in `<head>` via a `<script type="application/ld+json">` block in the page component):

```tsx
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{
    __html: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: 'GovCon Bid Desk',
      applicationCategory: 'BusinessApplication',
      description: 'Federal contracting capability pack for AI agents.',
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
    }),
  }}
/>
```

### Task 3.10 — Phase 3 commit

Per-milestone commits within Phase 3 are recommended (each task is independently shippable). At the end:

```bash
# After 3.1–3.4:
git add supabase/migrations/* api/repositories/api_key.py api/schemas/api_key.py \
  api/auth.py api/routes/api_keys.py api/main.py api/tests/test_api_*
git commit -m "feat(agents): api_keys table + repo + /api/keys mint/list/revoke"

# After 3.5:
git add api/routes/v1_tools.py api/main.py api/tests/test_v1_tools_routes.py
git commit -m "feat(agents): /api/v1/tools/<name> public mirror accepting gck_ keys"

# After 3.6:
git add api/rate_limit.py api/auth.py api/tests/test_rate_limit.py
git commit -m "feat(agents): per-key rate limiting (60/min default, 429 + Retry-After)"

# After 3.7:
git add web/src/app/app/keys/* web/src/app/app/layout.tsx web/src/lib/{api,types}.ts
git commit -m "feat(web): /app/keys UI — mint/list/revoke"

# After 3.8:
git add mcp_server_govcapture/
git commit -m "feat(mcp): mcp-server-govcapture package wrapping /api/v1/tools/<name>"

# After 3.9:
git add landing/public/robots.txt web/src/app/agents/page.tsx
git commit -m "feat(agents): robots.txt + JSON-LD on /agents"
```

---

## Phase 4: Sprint E — `query_usaspending` skill

**Validation gate:** Phase 0.1 live smoke green. (Phase 3 is independent; can ship in parallel.)

### Task 4.1 — `competitor_history` migration ⚠️ ASK FIRST

- [ ] **Step 1:** Surface the schema change to the user. Proposed columns: `id`, `opportunity_id`, `incumbent_name`, `awards (jsonb)`, `total_obligated_usd`, `win_difficulty`, `evidence_url`, `owner_profile_id`, `created_at`.

- [ ] **Step 2:** After ack, author migration:

```sql
-- supabase/migrations/<ts>_add_competitor_history.sql
create table public.competitor_history (
  id                    uuid primary key default extensions.gen_random_uuid(),
  opportunity_id        uuid not null references public.opportunities(id) on delete cascade,
  owner_profile_id      uuid not null references public.profiles(id) on delete cascade,
  incumbent_name        text,
  awards                jsonb not null default '[]'::jsonb,
  total_obligated_usd   numeric(14,2),
  win_difficulty        text,
  evidence_url          text,
  created_at            timestamptz not null default now()
);
create index idx_comphist_opp on public.competitor_history(opportunity_id);
create index idx_comphist_own on public.competitor_history(owner_profile_id);
alter table public.competitor_history enable row level security;
create policy "owner read"   on public.competitor_history for select using (owner_profile_id = (select auth.uid())::uuid);
create policy "owner insert" on public.competitor_history for insert with check (owner_profile_id = (select auth.uid())::uuid);
```

- [ ] **Step 3:** `supabase db push`.

### Task 4.2 — Schema source + codegen

- [ ] **Step 1:** Author `schemas/competitor-history.schema.json` matching the table.
- [ ] **Step 2:** Run `make schemas` to regenerate `api/schemas/competitor_history*.py`.
- [ ] **Step 3:** Verify idempotency: re-run `make schemas`; no diff.

### Task 4.3 — `api/skills/query_usaspending/skill.py`

- [ ] **Step 1:** Author the skill — calls USASpending v2 API, normalizes, returns `CompetitorHistory[]`. Pure HTTP, no LLM.

```python
"""query_usaspending — Ledger's competitive-intel skill.

Calls USASpending.gov's award-search endpoint. No LLM. On rate-limit /
5xx / network error, returns degraded=True with empty awards.
"""
from __future__ import annotations
from typing import Any
import httpx

USASPENDING_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


async def query_usaspending(
    payload: dict[str, Any],
    *,
    http: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Query USASpending awards.

    Input shape:
      {"naics": str, "agency": str | None, "limit": int}

    Output:
      {"awards": [...], "incumbents": [...], "degraded": bool, "error": str}
    """
    body = {
        "filters": {
            "naics_codes": [payload["naics"]] if payload.get("naics") else [],
            **({"agencies": [{"name": payload["agency"], "tier": "toptier"}]} if payload.get("agency") else {}),
        },
        "fields": ["Recipient Name", "Award Amount", "Period of Performance Start Date", "Award ID"],
        "limit": payload.get("limit", 25),
    }
    owns = http is None
    client = http or httpx.AsyncClient()
    try:
        try:
            resp = await client.post(USASPENDING_URL, json=body, timeout=20.0)
        except httpx.HTTPError as e:
            return {"awards": [], "incumbents": [], "degraded": True, "error": f"network: {e}"}
        if resp.status_code == 429:
            return {"awards": [], "incumbents": [], "degraded": True, "error": "USASpending rate limit"}
        if resp.status_code >= 500:
            return {"awards": [], "incumbents": [], "degraded": True, "error": f"USASpending 5xx: {resp.status_code}"}
        if resp.status_code >= 400:
            return {"awards": [], "incumbents": [], "degraded": True, "error": f"USASpending client error: {resp.status_code}"}
        data = resp.json()
        awards = data.get("results", [])
        incumbents = sorted(
            {a.get("Recipient Name") for a in awards if a.get("Recipient Name")}
        )
        return {"awards": awards, "incumbents": incumbents, "degraded": False, "error": ""}
    finally:
        if owns:
            await client.aclose()
```

- [ ] **Step 2:** Tests in `api/tests/test_query_usaspending.py` — happy, 429 → degraded, network error → degraded.

### Task 4.4 — Repository, routes, plugin registration

- [ ] **Step 1:** `api/repositories/competitor_history.py` — straightforward repo (mirror `risk_flag.py`).
- [ ] **Step 2:** Per-opportunity routes in `api/routes/opportunities.py`:
  - `GET /opportunities/{id}/competitors`
  - `POST /opportunities/{id}/competitors` (InternalActor)
- [ ] **Step 3:** New `/tools/query-usaspending` and `/api/v1/tools/query-usaspending` routes.
- [ ] **Step 4:** `.hermes/plugins/govcapture/{__init__.py,tools.py}` — register `govcapture_query_usaspending`. Schema mirrors the input. Handler hits the new route.

### Task 4.5 — Phase 4 commit

```bash
git add supabase/migrations/* schemas/* api/schemas/competitor_history* \
  api/skills/query_usaspending/ api/repositories/competitor_history.py \
  api/routes/opportunities.py api/routes/tools.py api/routes/v1_tools.py \
  api/tests/test_query_usaspending.py \
  .hermes/plugins/govcapture/{__init__.py,tools.py}
git commit -m "feat(skill): query_usaspending — Ledger's competitive-intel skill (Sprint E)"
```

---

## Phase 5: Sprint F — eval harness

**Validation gate:** All LLM-backed skills (parse_goal, extract_requirements, score_fit, detect_risks, generate_action_package) test-suite green. Real ANTHROPIC_API_KEY available.

### Task 5.1 — Runner + differs

- [ ] **Step 1:** `eval/runner/differs.py`:

```python
"""Tolerant comparison primitives. LLM outputs aren't bit-stable."""
from __future__ import annotations
from typing import Any


def diff_within_tolerance(
    expected: dict[str, Any],
    actual: dict[str, Any],
    *,
    int_tolerance: int = 5,
    string_substr: bool = True,
) -> list[str]:
    """Return a list of human-readable mismatch lines. Empty = pass.

    - `decision`: must match exactly.
    - `total_score`: numeric ±int_tolerance.
    - `evidence_snippet`: substring match.
    - other fields: structural equality.
    """
    issues: list[str] = []
    for key in expected:
        if key not in actual:
            issues.append(f"missing: {key}")
            continue
        ev = expected[key]
        av = actual[key]
        if key == "total_score" and isinstance(ev, int):
            if abs(ev - int(av)) > int_tolerance:
                issues.append(f"score drift: {ev} vs {av}")
        elif key == "decision":
            if ev != av:
                issues.append(f"decision mismatch: {ev} vs {av}")
        elif key == "evidence_snippet" and string_substr:
            if isinstance(ev, str) and ev[:60] not in (av or ""):
                issues.append(f"evidence_snippet missing substring: {ev[:60]!r}")
        elif ev != av:
            issues.append(f"{key}: {ev!r} != {av!r}")
    return issues
```

- [ ] **Step 2:** `eval/runner/runner.py`:

```python
"""Drive a fixture through a skill, diff vs golden."""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path

from api.llm import LLM
from api.skills.parse_goal.skill import parse_goal
from api.skills.score_fit.skill import score_fit
from api.skills.detect_risks.skill import detect_risks
from api.skills.generate_action_package.skill import generate_action_package
from api.skills.extract_requirements.skill import extract_requirements
from api.skills.parse_pdf.skill import parse_pdf
from eval.runner.differs import diff_within_tolerance


SKILLS = {
    "parse_goal": parse_goal,
    "score_fit": score_fit,
    "detect_risks": detect_risks,
    "generate_action_package": generate_action_package,
    "extract_requirements": extract_requirements,
}


async def run_one(fixture_dir: Path, skill_name: str, *, bootstrap: bool = False) -> int:
    manifest = json.loads((fixture_dir / "manifest.json").read_text())
    inputs = manifest.get("eval_inputs", {}).get(skill_name, {})
    golden = fixture_dir / f"goldens/{skill_name}.json"
    skill = SKILLS[skill_name]
    llm = LLM()
    if skill_name == "extract_requirements":
        # Needs parsed_pdf input; parse on the fly.
        pdf_path = inputs.get("pdf_path")
        if pdf_path:
            parsed = parse_pdf({"path": str(fixture_dir / pdf_path)})
            inputs = {"parsed": parsed.model_dump(), **inputs}
    out, _metrics = await skill(inputs, llm=llm)
    if isinstance(out, dict) is False:
        out = out.model_dump()
    if bootstrap or not golden.exists():
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(json.dumps(out, indent=2, sort_keys=True))
        print(f"BOOTSTRAPPED {skill_name} for {fixture_dir.name}")
        return 0
    expected = json.loads(golden.read_text())
    issues = diff_within_tolerance(expected, out)
    if issues:
        print(f"FAIL {skill_name} / {fixture_dir.name}:")
        for i in issues:
            print(f"  - {i}")
        return 1
    print(f"PASS {skill_name} / {fixture_dir.name}")
    return 0


async def main(argv: list[str]) -> int:
    bootstrap = "--bootstrap" in argv
    fixtures_dir = Path("fixtures")
    rc = 0
    for fixture in sorted(fixtures_dir.iterdir()):
        if not fixture.is_dir() or fixture.name.startswith("_"):
            continue
        for skill_name in SKILLS:
            rc |= await run_one(fixture, skill_name, bootstrap=bootstrap)
    return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
```

### Task 5.2 — Fixture eval inputs + goldens

For each fixture (`strong-pursue`, `maybe-needs-partner`, `reject`, `adversarial-image-pdf`):

- [ ] **Step 1:** Add `eval_inputs` block to `manifest.json` describing the inputs each LLM skill should receive. Skip skills that don't apply (e.g., parse_goal doesn't need a fixture; extract_requirements needs the PDF).
- [ ] **Step 2:** Bootstrap goldens: `make eval-bootstrap` runs `python -m eval.runner.runner --bootstrap`.
- [ ] **Step 3:** Hand-review the bootstrapped JSON for each fixture/skill. If it looks wrong (e.g., reject fixture got "pursue" decision), the skill or prompt is broken — fix BEFORE accepting golden.

### Task 5.3 — Makefile target + CI note

- [ ] **Step 1:** Append to `Makefile`:

```make
.PHONY: eval eval-bootstrap

eval:
	uv run python -m eval.runner.runner

eval-bootstrap:
	uv run python -m eval.runner.runner --bootstrap
```

- [ ] **Step 2:** Note in `eval/README.md`: this consumes real Anthropic tokens (~$0.10 per fixture × 5 skills = $0.40-$0.80 per `make eval` run). Run only on PRs that touch `api/skills/`, `api/llm.py`, fixtures, or migrations. Add to a future CI sprint.

### Task 5.4 — Phase 5 commit

```bash
git add eval/ Makefile fixtures/*/manifest.json
git commit -m "feat(eval): fixture-driven regression harness for LLM-backed skills (Sprint F)"
```

---

## Phase 6: Production magic-link email delivery

**Validation gate:** Phase 0.2 confirmed magic link works in dev (using Supabase's default SMTP).

**Why:** Supabase's default SMTP rate-limits aggressively (4 emails/hour project-wide on free tier). For public launch, you need a real provider.

### Task 6.1 — Pick a provider

- [ ] **Step 1:** Pick: Resend (recommended for low-friction), Postmark (premium deliverability), or SES (cheap if AWS native). For v1: **Resend** — cheapest tier covers 3,000 emails/month free.

### Task 6.2 — Configure in Supabase Dashboard

- [ ] **Step 1:** Sign up for Resend, get an API key.
- [ ] **Step 2:** Add a domain (e.g., `mail.govcapture.example`) and verify DNS (SPF, DKIM, DMARC).
- [ ] **Step 3:** In Supabase Studio → Authentication → Email Templates → SMTP Settings, switch from "Supabase" to "Custom SMTP":
  - Host: `smtp.resend.com`
  - Port: `465`
  - Username: `resend`
  - Password: `<resend api key>`
  - Sender email: `noreply@mail.govcapture.example`
  - Sender name: `GovCapture`
- [ ] **Step 4:** Customize the magic-link template — minimum: replace generic copy with brand-aligned text matching `/login`'s tone.

### Task 6.3 — Test deliverability

- [ ] **Step 1:** From production, request a magic link to a real Gmail / Outlook / Yahoo address. Confirm:
  - Arrives within 30s.
  - Doesn't land in spam (especially Outlook).
  - Link works (single use, 5min TTL).
- [ ] **Step 2:** Stress-test: 5 requests in a minute should all deliver (Supabase default rate limit would block this).

### Task 6.4 — Document

- [ ] **Step 1:** Add to `.env.production.example` (informational; the secret lives in Supabase, not in our env):

```
# Email delivery: set in Supabase Studio → Auth → SMTP Settings.
# Provider: Resend. Sender: noreply@mail.govcapture.example.
```

- [ ] **Step 2:** Commit:

```bash
git add .env.production.example
git commit -m "docs(infra): production magic-link email delivery via Resend SMTP"
```

---

## Phase 7: Sprint D — VX1 production deploy

**Validation gate:** Phase 6 deliverability confirmed. All earlier phases' commits pushed to a deploy-ready branch (or main).

### Task 7.1 — Provision

- [ ] **Step 1:** Vultr VX1 instance. Ubuntu 24.04. Root SSH key.
- [ ] **Step 2:** SSH in. Set hostname (`api-prod-1`).

### Task 7.2 — Bootstrap

- [ ] **Step 1:** Run `infra/bootstrap.sh` from the repo. (Idempotent; installs apt deps, ufw, redis, govcapture user, systemd unit.)
- [ ] **Step 2:** Verify Redis is up: `redis-cli ping` → `PONG`.

### Task 7.3 — Clone + sync

- [ ] **Step 1:** Clone to `/opt/govcapture` (deploy key if private).
- [ ] **Step 2:** `uv sync` as the `govcapture` user.

### Task 7.4 — Production `.env`

- [ ] **Step 1:** Drop `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
SUPABASE_ANON_KEY=sb_publishable_...
SUPABASE_STORAGE_BUCKET=govcapture-attachments
INTERNAL_API_KEY=<long random — same value used in /root/michealaai>
SAM_API_KEY=<optional>
REDIS_URL=redis://localhost:6379/0
LLM_DEV_MODEL=claude-haiku-4-5-20251001
LLM_SYNTH_MODEL=claude-sonnet-4-6
RUN_BUDGET_USD=0.50
RUN_BUDGET_STEPS=40
RUN_BUDGET_SECONDS=360
CORS_ALLOWED_ORIGINS=https://app.govcapture.example,https://govcapture.example
```

- [ ] **Step 2:** `chmod 600 .env` and `chown govcapture:govcapture .env`.

### Task 7.5 — systemd + nginx + certbot

- [ ] **Step 1:** `systemctl enable --now govcapture-api.service`. Check `systemctl status`.
- [ ] **Step 2:** `curl 127.0.0.1:8000/healthz` → 200.
- [ ] **Step 3:** Configure nginx (`/etc/nginx/sites-available/govcapture`):

```nginx
server {
  listen 80;
  server_name api.govcapture.example;
  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    # SSE: disable buffering, long timeouts.
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 24h;
    proxy_send_timeout 24h;
  }
}
```

- [ ] **Step 4:** `certbot --nginx -d api.govcapture.example`. Confirm cert in `/etc/letsencrypt/live/`.
- [ ] **Step 5:** `systemctl reload nginx`.

### Task 7.6 — DNS

- [ ] **Step 1:** Add A record `api.govcapture.example` → VX1 IP.
- [ ] **Step 2:** Wait for propagation (use `dig +short api.govcapture.example` from a remote network).

### Task 7.7 — Production smoke test

- [ ] **Step 1:** From outside the box:

```bash
curl https://api.govcapture.example/healthz
# 200 {"status":"ok"}

curl https://api.govcapture.example/.well-known/agent.json
# 200 manifest

curl -X POST https://api.govcapture.example/tools/rank-opportunities \
  -H "X-Internal-API-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scored":[{"opportunity_id":"a","decision":"pursue","total_score":75,"due_date":"2026-06-01"}]}'
# 200 envelope
```

- [ ] **Step 2:** `journalctl -u govcapture-api -n 50` — no tracebacks.

### Task 7.8 — Vercel `/web` config

- [ ] **Step 1:** In Vercel project settings → Environment Variables:
  - `NEXT_PUBLIC_API_BASE` = `https://api.govcapture.example`
  - `NEXT_PUBLIC_SUPABASE_URL` (already set)
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY` (already set)
- [ ] **Step 2:** Trigger a redeploy.
- [ ] **Step 3:** Visit `https://app.govcapture.example` (or whatever the prod URL is) → click through the full flow:
  - Sign in (Phase 6 SMTP delivers the link)
  - Land on /app
  - Mint an API key
  - Copy → curl `/api/v1/tools/parse-goal` from local terminal with that key

### Task 7.9 — Phase 7 wrap

- [ ] **Step 1:** Update `infra/RUNBOOK.md` with any lessons learned.
- [ ] **Step 2:** Commit:

```bash
git add infra/RUNBOOK.md
git commit -m "docs(deploy): VX1 deploy notes from Sprint D rollout"
```

---

## Phase 8: Sprint G end-to-end verification

**Validation gate:** Phase 7 production deploy complete. `/root/michealaai` is on a known commit that implements the pickup contract from `devdocs/CAPABILITY_PACK_INTEGRATION.md` Sprint G section.

### Task 8.1 — Cross-repo coordinated test

- [ ] **Step 1:** Confirm `/root/michealaai` is running against the production INTERNAL_API_KEY.
- [ ] **Step 2:** From `/web` UI, kick off a real run. Observe in production:
  - `agent_runs` row claimed by orchestrator within ~5s (Phase 8.2 below — verify in Supabase Studio).
  - Trace events flow into Redis channel `agent-run:{id}`.
  - SSE in `/web` updates the timeline live.
  - `action_packages` row created on completion, viewable in `/app/action-packages/{id}`.
- [ ] **Step 3:** Walk every "Known unknowns" row in `devdocs/CAPABILITY_PACK_INTEGRATION.md` and mark its rightmost-column gate green/red.

### Task 8.2 — Update spec-to-reality mapping

- [ ] **Step 1:** Update `devdocs/CAPABILITY_PACK_INTEGRATION.md`'s "Known unknowns" table — flip statuses from `unknown` to `verified` (or document any divergence).
- [ ] **Step 2:** Update `devdocs/HANDOFF_PROMPT.md` Section 7 G row from "spec done; e2e verification owed" → "**verification done**".

### Task 8.3 — Commit

```bash
git add devdocs/CAPABILITY_PACK_INTEGRATION.md devdocs/HANDOFF_PROMPT.md
git commit -m "docs(g): Sprint G verification — e2e flow live in production"
```

---

## Phase 9: Final state-of-the-repo + v1.0.0 tag

### Task 9.1 — Update `devdocs/CURRENT_STATE.md`

- [ ] **Step 1:** Bump §7 API surface table to reflect the final route count (will be 36 + ~12 for Phase 3 = ~48 routes).
- [ ] **Step 2:** Update §10 "Done" with Sprints C, D, E, F, G, agent-SEO. Clear "Next" of items now done.
- [ ] **Step 3:** Update §9 timeline.

### Task 9.2 — Update `devdocs/HANDOFF_PROMPT.md`

- [ ] **Step 1:** Section 1 "Verified state" — production-deployed, all gates green, public URL.
- [ ] **Step 2:** Section 7 — every sprint marked done.
- [ ] **Step 3:** Add a Section 20 "What's beyond v1" listing the Out-of-Scope items at the top of this plan (CI, Sentry, status page, FedRAMP, etc.) so the next session knows what to consider.

### Task 9.3 — v1.0.0 git tag

- [ ] **Step 1:** Confirm working tree clean.
- [ ] **Step 2:** Annotated tag:

```bash
git tag -a v1.0.0 -m "v1.0.0 — public launch

GovCon Bid Desk capability pack, deployed to Vultr VX1 + Vercel + Supabase.
Sprints A through G complete. Agent-callable via /api/v1/tools/<name> with
gck_… keys, MCP server published. Magic-link auth via Resend SMTP. Eval
harness covering 4 fixtures × 5 LLM skills. Cross-repo Sprint G verified
end-to-end with /root/michealaai."
```

- [ ] **Step 3:** (If user OKs) `git push origin main --follow-tags`.

### Task 9.4 — Final commit

```bash
git add devdocs/CURRENT_STATE.md devdocs/HANDOFF_PROMPT.md
git commit -m "docs: v1.0.0 launch — final state-of-repo update"
git tag -a v1.0.0 -m "..."
```

---

## Self-Review

**Spec coverage:** every "deferred" item from the previous session's ending summary has a phase:

| Deferred item | Plan phase |
|---|---|
| Sprint A verification (hermes REPL) | 0.3 |
| Sprint C Phase 7 polish | 1 |
| Sprint C Phase 8 remainder (api keys / public mirror / rate limit / MCP / docs polish) | 3 |
| Sprint D (VX1 deploy) | 7 |
| Sprint E (USASpending) | 4 |
| Sprint F (eval harness) | 5 |
| Sprint G end-to-end verification | 8 |
| SSE upgrade in RunTimeline | 2 |
| Browser walk-through | 0.2 |
| Live API smoke test | 0.1 |

Plus advisor-flagged additions: production email delivery (Phase 6), schema-migration ASK-FIRST gating (Tasks 3.1, 4.1), parallel execution graph (top of plan).

**Placeholder scan:** No "TBD", "TODO", "implement later", "similar to Task N", or "fill in details". Code blocks are concrete; text decisions cite specific files / line anchors. Phase 4.4 and 3.5 reference "8 more tools mirroring the pattern" with the explicit note that the pattern is already established in `api/routes/tools.py` (Sprint B's committed code) — that's a live, readable reference, not a placeholder.

**Type consistency:** `gck_…` prefix used uniformly. `api_keys` table column names match between SQL, repo, schema, and routes. `AgentActor` discriminated cleanly between internal and per-user paths. `ToolResponse` envelope shape mirrors Sprint B's. `INTERNAL_API_KEY` vs `gck_…` clearly separated in the auth dep.

**Risks consciously accepted:**
- **Schema migrations require synchronous user ack.** This breaks the "auto mode aggressive execution" pattern from earlier sessions; explicitly called out in Tasks 3.1 and 4.1.
- **Phase 0 user-driven validation tasks** (browser walk + Hermes REPL). Without these, plans on broken foundations. Worth the 25 minutes.
- **Phase 6 (email) requires Supabase Dashboard access** outside the code repo. Documented but not automated.
- **Phase 7 deploy depends on infra not in this repo's reach** (VX1 provisioning, DNS, Vercel project settings). Step-by-step but not scriptable.
- **Phase 8 cross-repo verification** is gated by `/root/michealaai`'s state — can't be forced from this side.
- **Eval costs real Anthropic tokens** — explicit budget caveat in Task 5.3.
- **Per-tool API-key scopes are deferred** — every key gets `tools:*`. Future-work tag in the manifest.
- **Native MCP transport (HTTP/SSE) deferred** — stdio only in v1.

**Out-of-scope items consciously excluded** (CI / GitHub Actions, Sentry, status page, customer support tooling, FedRAMP/CMMC, internationalization, optimistic mutations, password fallback) — surfaced at the top of the plan so the user is not surprised at v1.0.0 tag time.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-10-launch-runway.md`. Recommended execution: **inline** (`superpowers:executing-plans`) for Phases 0–6 since each phase shares a small file set and the validation gates are natural review points; **switch to subagent-driven** for Phase 7 (deploy) where each step is an external operation against infra and the parallel-task isolation discipline pays off; **inline again** for Phases 8–9.

Critical path: 0 → 1 → 2 → 3 → 6 → 7 → 8 → 9, with 4 + 5 parallelizable into 1's slot. Realistic single-engineer time-to-launch: **5–7 working days** assuming Supabase + Vultr + Vercel + Resend accounts are already set up and `/root/michealaai` is ready for Phase 8.
