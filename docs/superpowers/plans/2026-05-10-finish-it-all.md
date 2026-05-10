# Finish-It-All Implementation Plan — every outstanding item to v1.0.0

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) or superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the GovCon Bid Desk pack from its current state (16 commits this session, web build clean, 183 tests passing, Phase 4 auth migration in working tree, lucide-react ESM fix verified live) to **v1.0.0 publicly launchable**: working tree clean, all schema migrations applied, ApprovalGate persisted server-side, SSE polished, production email delivering, VX1 deployed, cross-repo flow verified end-to-end, eval goldens bootstrapped, annotated v1.0.0 tag pushed.

**Architecture:**
- **Each phase opens with a "what's already done" survey** so the executor doesn't redo committed work. Many phases that *would* exist in a greenfield plan are skipped because the user has already shipped them in parallel.
- **Schema-touching tasks pause for explicit user ack** before `supabase db push` (handoff §17.3).
- **Phase 0 commits the in-flight working-tree work first** — clean baseline before structured changes.
- **Phases 5–9 are external/deployment-shaped** — they require Supabase Studio access, VX1 host access, DNS, Vercel env, `/root/michealaai` coordination, and real Anthropic tokens. The plan is precise about *what* needs to happen but the executor must have those credentials in hand.

**Tech Stack:** Python 3.12 · FastAPI · supabase-py AsyncClient · pytest-asyncio · uv · Anthropic SDK · Next 15 · React 19 · Tailwind 4 · `@supabase/ssr` 0.10 · Redis · Vultr VX1 + nginx + systemd · Vercel · Supabase.

**Out of scope** (acknowledge but don't plan):
- CI/GitHub Actions wiring (post-v1)
- Sentry / structured logging / Grafana
- FedRAMP / FISMA / CMMC compliance
- i18n, dark mode, optimistic UI, password fallback
- shadcn/ui or any component library introduction
- Native MCP HTTP/SSE transport (stdio only in v1)
- Per-tool API-key scopes (every key gets `tools:*` in v1)

**Verification gates (must hold at end of every phase):**
- `uv run pytest api/tests/ -q` — all green; suite size ≥ 183.
- `uv run ruff check api` — clean.
- `uv run mypy api` — 0 errors.
- `npm --prefix web run typecheck` — clean.
- `npm --prefix web run lint` — clean.
- `npm --prefix web run build` — clean.
- `npm --prefix landing run typecheck && lint && build` — clean.
- `git status --short` — only intended changes.

**Final verification gates (entire plan complete):**
- All gates above hold continuously.
- Schema migrations `b334c20` + `ec7eb5f` + new approval migration are applied (`supabase migration list` shows them).
- A live curl using a `gck_…` key calls `/api/v1/tools/parse-goal` against the production VX1 URL and gets a valid envelope.
- Magic-link signup arrives via the production email provider (NOT Supabase's default SMTP).
- `/app/action-packages/[id]` approval state survives refresh (DB-persisted).
- A real `agent_runs` row created via `POST /agent-runs` in `/web` is claimed by `/root/michealaai`'s orchestrator within ~5 seconds and produces a viewable `action_packages` row in the UI.
- `make eval` passes against committed goldens for ≥4 fixtures × ≥3 LLM skills.
- `git tag v1.0.0` exists at HEAD.
- `git push origin main --follow-tags` has shipped the tag.

---

## What's already done — DO NOT REPLAN

The session has shipped 16 commits ending at `a03591f`. Specifically:

| Item | Status | Commit / location |
|---|---|---|
| Sprint B HTTP /tools/<name> parity | ✅ shipped | (earlier session) |
| Sprint A Hermes plugin scaffolding | ✅ shipped | `3e3baf4` (verification owed) |
| Sprint G coordination spec | ✅ shipped | `952b1cc` |
| Sprint C Phase 7.1+7.2 (skeletons + error boundaries) | ✅ shipped | `5628129` |
| Sprint C Phase 7.4 (SSE upgrade — polling → EventSource via same-origin proxy) | ✅ shipped | `94120d5` |
| Sprint F (eval scaffolding — runner+differs+Makefile) | ✅ shipped | `b420fd5` |
| Sprint E + Phase 4.2-4.5 (query_usaspending + competitor_history) | ✅ shipped | `3b19e39` |
| Phase 3.1 + 4.1 schema migrations (api_keys + competitor_history) | ✅ committed (NOT yet applied — see Phase 4 below) | `b334c20` + `ec7eb5f` |
| Phase 3.2-3.6 (api keys + /api/v1/tools mirror + rate limit + fail-open) | ✅ shipped | `3c9a7de` + `a63bf30` |
| Phase 3.7 (`/app/keys` UI) | ✅ shipped | `1b239c6` |
| Phase 3.8 (`mcp-server-govcapture` package) | ✅ shipped | `966fa96` |
| Phase 3.9 (robots + JSON-LD) | ✅ shipped | `e8e2500` |
| query_usaspending real-API fix (award_type_codes) | ✅ shipped | `5ff99cb` + `310febb` |
| lucide-react ESM resolution fix (`transpilePackages`) | ✅ shipped | `a03591f` |
| **Frontend cleanup Phase 1 (brand alignment)** | ✅ shipped | `3c37ffb` |
| **Frontend cleanup Phase 2 (delete AppConsole)** | ✅ shipped | `a51330e` |
| **Frontend cleanup Phase 5 (workspace + tsconfig)** | ✅ shipped | `aa98b8f` |
| **Frontend cleanup Phase 6 (SEO + a11y)** | ✅ shipped | `4e95d74` |
| **Frontend cleanup Phase 8 (agents truth-fix + cleanup sweep)** | ✅ shipped | `c74a0ef` |

**Phase 4 (auth hardening: getSession → getUser via requireUser helper)** is functionally complete in the working tree — 9 files modified, helper at `web/src/lib/supabase/auth.ts`, typecheck + lint + build all clean. **Phase 0 below commits it.**

---

## Phase 0: Commit the in-flight Phase 4 auth migration

**Validation gate:** `npm --prefix web run typecheck && lint && build` clean (already true per the recheck).

**Why first:** The working tree is dirty with completed work. Subsequent phases need a clean baseline so each phase produces one logical commit.

### Task 0.1: Snapshot the in-flight files

- [ ] **Step 1: Confirm typecheck/lint/build still clean**

```bash
npm --prefix /Volumes/CS_Stuff/govcon/web run typecheck
npm --prefix /Volumes/CS_Stuff/govcon/web run lint
npm --prefix /Volumes/CS_Stuff/govcon/web run build
npm --prefix /Volumes/CS_Stuff/govcon/landing run typecheck
npm --prefix /Volumes/CS_Stuff/govcon/landing run build
uv run pytest /Volumes/CS_Stuff/govcon/api/tests/ -q
```

Expected: all clean.

- [ ] **Step 2: List the staging set**

The Phase 4 auth migration touches:
- `web/src/lib/supabase/auth.ts` (NEW — the `requireUser` helper)
- `web/src/middleware.ts` (uses `getUser()` not `getSession()`)
- `web/src/app/api/run-stream/[id]/route.ts` (auth-aware proxy)
- `web/src/app/app/page.tsx`
- `web/src/app/app/keys/page.tsx`
- `web/src/app/app/goal/page.tsx`
- `web/src/app/app/runs/[id]/page.tsx`
- `web/src/app/app/profile/page.tsx`
- `web/src/app/app/profile/[id]/page.tsx`
- `web/src/app/app/opportunities/[id]/page.tsx`
- `web/src/app/app/action-packages/[id]/page.tsx`

Plus three doc updates that landed alongside (these may be from a different mental thread; if so, split):
- `devdocs/CAPABILITY_PACK_INTEGRATION.md`
- `tasks/CONTRACTS.md`
- `tasks/INTERFERENCE_MAP.md`
- `tasks/README.md`

### Task 0.2: Commit auth changes

- [ ] **Step 1: Stage the auth files**

```bash
cd /Volumes/CS_Stuff/govcon
git add \
  web/src/lib/supabase/auth.ts \
  web/src/middleware.ts \
  web/src/app/api/run-stream/\[id\]/route.ts \
  web/src/app/app/page.tsx \
  web/src/app/app/keys/page.tsx \
  web/src/app/app/goal/page.tsx \
  web/src/app/app/runs/\[id\]/page.tsx \
  web/src/app/app/profile/page.tsx \
  web/src/app/app/profile/\[id\]/page.tsx \
  web/src/app/app/opportunities/\[id\]/page.tsx \
  web/src/app/app/action-packages/\[id\]/page.tsx
```

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(web): auth hardening — getSession()→getUser() via requireUser

Per Supabase SSR docs, getSession() locally decodes the JWT — an
expired or forged token passes silently. getUser() makes a network
round-trip to /auth/v1/user and is the only path that actually
validates identity on the server.

New helper at web/src/lib/supabase/auth.ts: requireUser() wraps
getUser() (with redirect to /login on failure), then reads the
session locally for the bearer token. Every server component / route
handler that calls FastAPI now goes through this helper instead of
duplicating getSession() patterns.

Files migrated (9): /app, /app/keys, /app/goal, /app/runs/[id],
/app/profile, /app/profile/[id], /app/opportunities/[id],
/app/action-packages/[id], plus the SSE proxy at
/api/run-stream/[id]. Middleware also switched to getUser().

Closes the auth-validation half of the frontend cleanup plan
(Phase 4: Critical C4, High H3 + H4, Medium M6).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 0.3: Surface and commit the doc updates

- [ ] **Step 1: Inspect what changed in each doc**

```bash
git diff devdocs/CAPABILITY_PACK_INTEGRATION.md tasks/CONTRACTS.md \
        tasks/INTERFERENCE_MAP.md tasks/README.md
```

If the diff is small and consistent (e.g., all four are tracking the same Phase 4 + 11-tool message), commit as one. If they diverge in subject, split.

- [ ] **Step 2: Commit (single commit if cohesive)**

```bash
git add devdocs/CAPABILITY_PACK_INTEGRATION.md tasks/CONTRACTS.md \
        tasks/INTERFERENCE_MAP.md tasks/README.md
git commit -m "docs: track auth-hardening + 11-tool surface across reference docs"
```

### Task 0.4: Verify clean tree

- [ ] **Step 1:** `git status --short` returns nothing.
- [ ] **Step 2:** `git log --oneline -5` shows the new auth commit at HEAD.

---

## Phase 1: ApprovalGate server-side persistence (cleanup-plan Phase 3)

**Validation gate:** Phase 0 working tree clean. Action package routes still respond per Phase 0.1 smoke.

**Why:** Today the `/app/action-packages/[id]/ApprovalGate` is local-state only — `useState(approved=false)`. Refresh wipes it. The orchestrator can't gate downstream actions (e.g., emailing a contracting officer) without a server-side `approved_at` signal.

### Task 1.1 — `action_packages` approval columns ⚠️ ASK FIRST

- [ ] **Step 1: Surface to user.** Print this proposal:

> "About to add two columns to `action_packages`: `approved_at TIMESTAMPTZ NULL` and `approved_by UUID NULL REFERENCES auth.users(id) ON DELETE SET NULL`. RLS on the table is unchanged (still scoped via `owner_profile_id`). OK to proceed?"

Wait for explicit yes. Do NOT proceed without ack.

- [ ] **Step 2: Author migration**

```bash
TS=20260510140000  # or now-ish UTC; must be after 20260510120100
cat > /Volumes/CS_Stuff/govcon/supabase/migrations/${TS}_add_action_package_approval.sql <<'EOF'
-- supabase/migrations/20260510140000_add_action_package_approval.sql
--
-- Real approval persistence for action packages. Today's UI uses
-- client-only state — refresh wipes the approved/checked state. The
-- orchestrator can't gate downstream actions (outreach, submission)
-- without a server-side approved_at signal. Adding two columns:
--
--   approved_at  — timestamp of approval; null = not approved
--   approved_by  — Supabase auth user who approved (FK to auth.users)
--
-- The pair is set together in a single PATCH; never one without the
-- other. RLS unchanged (owner_profile_id scoping covers reads/writes).

ALTER TABLE public.action_packages
  ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS approved_by UUID NULL
    REFERENCES auth.users(id) ON DELETE SET NULL;

COMMENT ON COLUMN public.action_packages.approved_at IS
  'Timestamp when an authorized user approved the package. Null = not yet approved.';
COMMENT ON COLUMN public.action_packages.approved_by IS
  'Supabase auth user who approved. Set together with approved_at.';
EOF
```

- [ ] **Step 3: Apply (after user ack)**

The migration is committed but NOT auto-applied. The user runs:

```bash
supabase db push
```

against the linked project. Confirm via:

```bash
supabase migration list
# expect 20260510140000_add_action_package_approval present + applied
```

### Task 1.2 — Update schema sources + codegen

- [ ] **Step 1: Update `schemas/action-package.schema.json`**

Add to `properties` and `additionalProperties: false`:

```json
"approved_at": { "type": ["string", "null"], "format": "date-time" },
"approved_by": { "type": ["string", "null"], "format": "uuid" }
```

NOT in `required` (nullable until approval).

- [ ] **Step 2: Regenerate Pydantic** — but FIRST address the known `make schemas` non-idempotency bug (see Phase 3 below). For now, hand-edit `api/schemas/action_package.py` to add the two fields:

```python
approved_at: AwareDatetime | None = None
approved_by: UUID | None = None
```

(The hand-edit is reversible once Phase 3 lands; for v1, edit-in-place is faster than fixing the codegen first.)

### Task 1.3 — `POST /action-packages/{id}/approve` route

**Files:**
- Modify: `api/routes/action_packages.py`
- Modify: `api/repositories/action_package.py` (add `approve(...)` method)

- [ ] **Step 1: Repo method**

Append to `api/repositories/action_package.py`:

```python
async def approve(
    self, package_id: uuid.UUID, owner_id: uuid.UUID, auth_user_id: uuid.UUID
) -> dict[str, Any] | None:
    """Mark approved. Owner-scoped: returns None if package not owned."""
    resp = await (
        self._client.table("action_packages")
        .update({
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": str(auth_user_id),
        })
        .eq("id", str(package_id))
        .eq("owner_profile_id", str(owner_id))
        .is_("approved_at", "null")  # idempotent: don't re-stamp
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None
```

- [ ] **Step 2: Route**

In `api/routes/action_packages.py`:

```python
@router.post("/{package_id}/approve", response_model=ActionPackage)
async def approve_action_package(
    package_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    repo: ActionPackageRepository = Depends(get_action_package_repo),
) -> ActionPackage:
    row = await repo.approve(package_id, user.id, user.id)
    if row is None:
        # Either not found, not owned, or already approved.
        # Re-fetch to disambiguate so the client gets a useful response.
        existing = await repo.get_owned(package_id, user.id)
        if existing is None:
            raise HTTPException(404, "Action package not found")
        return ActionPackage.model_validate(existing)  # already approved → idempotent return
    return ActionPackage.model_validate(row)
```

- [ ] **Step 3: Tests**

In `api/tests/test_routes.py` or a new `test_action_package_approve.py`:

```python
async def test_approve_sets_approved_at(client) -> None:
    pkg = await _create_action_package(client)  # helper assumed
    r = await client.post(f"/action-packages/{pkg['id']}/approve")
    assert r.status_code == 200
    assert r.json()["approved_at"] is not None
    assert r.json()["approved_by"] == str(TEST_USER_ID)


async def test_approve_idempotent(client) -> None:
    pkg = await _create_action_package(client)
    r1 = await client.post(f"/action-packages/{pkg['id']}/approve")
    first_at = r1.json()["approved_at"]
    r2 = await client.post(f"/action-packages/{pkg['id']}/approve")
    # Same approved_at; second call doesn't re-stamp.
    assert r2.json()["approved_at"] == first_at


async def test_approve_404_unknown(client) -> None:
    r = await client.post(f"/action-packages/{uuid.uuid4()}/approve")
    assert r.status_code == 404
```

Add to `api/tests/conftest.py::_TABLE_DEFAULTS["action_packages"]`:

```python
"approved_at": None,
"approved_by": None,
```

And ensure FakeSupabase `_Query.is_("col", "null")` already supports this filter (it does, per the api_keys migration).

### Task 1.4 — Frontend: `<ApprovalGate>` calls the route

**Files:**
- Modify: `web/src/lib/api.ts` (add `approveActionPackage`)
- Modify: `web/src/lib/types.ts` (`ActionPackage` gets `approved_at?`, `approved_by?`)
- Modify: `web/src/app/app/action-packages/[id]/ApprovalGate.tsx`
- Modify: `web/src/app/app/action-packages/[id]/page.tsx` (pass `initialApproved` prop)

- [ ] **Step 1: API client**

```ts
// types.ts additions
export type ActionPackage = {
  // ... existing fields
  approved_at?: string | null
  approved_by?: string | null
}

// api.ts additions inside `export const api = {...}`:
approveActionPackage: (token: string, id: string) =>
  request<ActionPackage>(`/action-packages/${id}/approve`, token, { method: 'POST' }),
```

- [ ] **Step 2: Page passes server-known approval state**

In `web/src/app/app/action-packages/[id]/page.tsx`, replace the `<ApprovalGate items={pkg.approval_required} />` line with:

```tsx
<ApprovalGate
  items={pkg.approval_required}
  packageId={pkg.id}
  initialApproved={pkg.approved_at != null}
/>
```

- [ ] **Step 3: ApprovalGate calls the API**

Rewrite `ApprovalGate.tsx` to:

```tsx
'use client'

import { useState } from 'react'
import { CheckCircle2, Loader2 } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { api, ApiError } from '@/lib/api'

export function ApprovalGate({
  items,
  packageId,
  initialApproved,
}: {
  items: string[]
  packageId: string
  initialApproved: boolean
}) {
  const supabase = createClient()
  const [checked, setChecked] = useState<Record<number, boolean>>({})
  const [approved, setApproved] = useState(initialApproved)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const allChecked = items.length > 0 && items.every((_, i) => checked[i])

  if (approved) {
    return (
      <div className="flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
        <CheckCircle2 size={16} aria-hidden />
        Approval recorded. The orchestrator can now read approved_at to gate downstream actions.
      </div>
    )
  }

  async function submit() {
    setBusy(true)
    setError('')
    try {
      const session = (await supabase.auth.getSession()).data.session
      if (!session) {
        setError('Session expired. Sign in again.')
        return
      }
      await api.approveActionPackage(session.access_token, packageId)
      setApproved(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Approve failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3">
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i}>
            <label className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3 text-sm">
              <input
                type="checkbox"
                checked={!!checked[i]}
                onChange={(e) => setChecked((c) => ({ ...c, [i]: e.target.checked }))}
                className="mt-1"
              />
              <span>{item}</span>
            </label>
          </li>
        ))}
      </ul>
      <button
        type="button"
        disabled={!allChecked || busy}
        onClick={() => void submit()}
        className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-blue-900 px-4 text-sm font-medium text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {busy ? <Loader2 size={15} className="animate-spin" aria-hidden /> : null}
        Approve & continue
      </button>
      {error ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
```

### Task 1.5 — Verify + commit

- [ ] All Phase 1 verification gates green (pytest +3 new tests; 183 → 186; web typecheck/lint/build clean).
- [ ] Manual browser check: approve a package, refresh, observe approval persists.
- [ ] Commit:

```bash
git add supabase/migrations/20260510140000_add_action_package_approval.sql \
        schemas/action-package.schema.json api/schemas/action_package.py \
        api/repositories/action_package.py api/routes/action_packages.py \
        api/tests/conftest.py api/tests/test_routes.py \
        web/src/lib/api.ts web/src/lib/types.ts \
        web/src/app/app/action-packages/\[id\]/page.tsx \
        web/src/app/app/action-packages/\[id\]/ApprovalGate.tsx
git commit -m "feat(approval): persist ActionPackage approval to action_packages.approved_at

Migration ASK-FIRST gate cleared. Adds approved_at + approved_by columns
to action_packages; new POST /action-packages/{id}/approve route
(JWT + owner-scoped, idempotent on already-approved). Frontend
ApprovalGate now calls it; initialApproved prop seeded from the row's
approved_at so refresh preserves state. Closes cleanup plan Phase 3
(Critical C2)."
```

---

## Phase 2: SSE polish (cleanup-plan Phase 7)

**Validation gate:** Phase 0 + 1 clean. RunTimeline behaves correctly under React Strict Mode (no double-open EventSources).

**Files:** Single file — `web/src/app/app/runs/[id]/RunTimeline.tsx`.

### Task 2.1 — Memoize Supabase client

- [ ] **Step 1:** Add `useMemo`:

```tsx
import { useMemo } from 'react'
// ...
const supabase = useMemo(() => createClient(), [])
```

This prevents a new client (and thus a new EventSource) per render.

### Task 2.2 — `partial` status icon

- [ ] **Step 1:** Add `AlertCircle` import + branch in `StatusBadge`:

```tsx
import { AlertCircle, CheckCircle2, Clock, Loader2, XCircle } from 'lucide-react'
// ...
function StatusBadge({ status }: { status: RunStatus }) {
  if (status === 'complete') return <CheckCircle2 size={28} className="text-emerald-600" aria-hidden />
  if (status === 'partial')  return <AlertCircle  size={28} className="text-amber-600"   aria-hidden />
  if (status === 'failed')   return <XCircle      size={28} className="text-rose-600"    aria-hidden />
  if (status === 'running')  return <Loader2      size={28} className="animate-spin text-blue-700" aria-hidden />
  return <Clock size={28} className="text-slate-500" aria-hidden />
}
```

### Task 2.3 — Drop "Live stream disconnected — retrying" pseudo-error

EventSource auto-reconnects; the message has lied to the user when no actual disconnect happened (Strict Mode double-effect). Drop it; let the absence of new events be the only signal.

- [ ] **Step 1:** Remove the `setError('Live stream disconnected — retrying.')` call inside `es.onerror`. Replace with a no-op and a comment:

```tsx
es.onerror = () => {
  // Browser auto-reconnects EventSources by default. Explicitly
  // surfacing "disconnected" was lying under React Strict Mode where
  // the effect runs twice and the first es.close() fires onerror on
  // the now-stale instance. Quiet by design.
}
```

### Task 2.4 — Dedupe on event identity

A subtle bug: in Strict Mode the dev-only double-effect can append the same event twice if the orchestrator publishes during the brief overlap. Add a per-event identity guard:

- [ ] **Step 1:** When appending, dedupe on `step_id` + `type` (or `ts` if no step_id):

```tsx
setRun((prev) => {
  const key = `${parsed.step_id ?? parsed.ts ?? ''}:${parsed.type}`
  if (key && prev.steps.some((s) => `${s.step_id ?? s.ts ?? ''}:${s.type}` === key)) {
    return prev
  }
  return { ...prev, steps: [...prev.steps, parsed] }
})
```

### Task 2.5 — Verify + commit

- [ ] typecheck + lint + build clean.
- [ ] Manual: open `/app/runs/[some-id]` in dev, watch DevTools Network — only ONE `/api/run-stream/[id]` connection should be open (not two).
- [ ] Commit:

```bash
git add web/src/app/app/runs/\[id\]/RunTimeline.tsx
git commit -m "fix(runs): SSE polish — memoize client, partial-status icon, no false retry, dedup steps

Closes cleanup plan Phase 7 (M1 + M2 + M3 + M4)."
```

---

## Phase 3: Fix `make schemas` non-idempotency (pre-existing tech debt)

**Validation gate:** Hand-written `api/schemas/{api_key,tool_requests,competitor_history,api_key}.py` exist (they should — Phase 0 left them).

**Why:** The Phase 4.2-4.5 implementer surfaced this. `make schemas` deletes hand-written modules (api_key.py, tool_requests.py) because the target does `rm -rf api/schemas` before running codegen, then only regenerates files that have a JSON Schema source. Two consequences:

1. Hand-rolled `tool_requests.py` and `api_key.py` get blown away on every `make schemas`. Surfaced as "data loss" pattern; we've been working around it by not running `make schemas`.
2. Four generated files (`fixture_manifest.py`, `opportunity.py`, `profile.py`, `waitlist.py`) drift between runs without input changes — codegen output isn't stable.

### Task 3.1 — Inspect current Makefile target

- [ ] **Step 1:**

```bash
grep -n -A 12 "^schemas:" /Volumes/CS_Stuff/govcon/Makefile
```

Read what `schemas:` does today.

### Task 3.2 — Restructure target

The fix: separate "generated" from "hand-written" by directory, OR scope the cleanup to only generated paths.

- [ ] **Step 1: Pick approach.** Recommended: split `api/schemas/` into:
  - `api/schemas/_generated/` — codegen target writes here, blown away on each run.
  - `api/schemas/` (hand-written modules stay here).
  - Re-export from `api/schemas/__init__.py` so callers don't change imports.

This is invasive (every `from api.schemas.<gen> import` becomes `from api.schemas._generated.<gen> import`). Alternative simpler fix:

  - **Switch the Makefile target from `rm -rf` to a per-file removal scoped only to known generated files.**

```make
# Hand-written modules that codegen MUST preserve:
HAND_WRITTEN_SCHEMAS = api/schemas/__init__.py api/schemas/api_key.py \
                      api/schemas/tool_requests.py api/schemas/competitor_history.py

GENERATED_SCHEMAS = $(filter-out $(HAND_WRITTEN_SCHEMAS), $(wildcard api/schemas/*.py))

.PHONY: schemas
schemas:
	rm -f $(GENERATED_SCHEMAS)
	# ... existing codegen invocation ...
```

(Pseudocode — read the existing target and adapt the variable list to whatever is actually hand-written.)

### Task 3.3 — Stabilize codegen output

For the four files that drift between runs without input changes (fixture_manifest, opportunity, profile, waitlist):

- [ ] **Step 1:** Diff a fresh run against a previous run:

```bash
make schemas
git diff api/schemas/
```

Look for sources of nondeterminism: dict ordering, timestamps, randomly-generated comments, line-ending differences.

- [ ] **Step 2:** Pin codegen flags. `datamodel-code-generator` accepts `--use-default --target-python-version 3.12 --output-model-type pydantic_v2.BaseModel` — verify the existing invocation has stable flags.

- [ ] **Step 3:** If drift persists, file as a known issue and document a "before regenerating, expect noise diff in these 4 files" warning in the Makefile target's docstring.

### Task 3.4 — Verify + commit

- [ ] **Step 1:** Run `make schemas` twice in a row. Second run produces zero `git diff`.
- [ ] **Step 2:** Confirm hand-written files still exist after `make schemas`.
- [ ] **Step 3:**

```bash
git add Makefile  # plus any schema regenerations from cleanup
git commit -m "fix(makefile): scope schema codegen cleanup to generated-only files

Pre-existing bug surfaced by the launch-runway sprint: \`make schemas\`
deleted hand-written api_key.py + tool_requests.py + competitor_history.py
because the target did \`rm -rf api/schemas\` before regen. Restricted
the deletion to a list of known-generated files."
```

---

## Phase 4: Apply pending Supabase migrations

**Validation gate:** All earlier phases clean. User has Supabase project access.

**Why:** Three migrations are committed but NOT applied. The new routes (Phase 3.2-3.6 api keys, Phase 4.2-4.5 competitor_history, Phase 1's approval) cannot exercise real data without `supabase db push`.

### Task 4.1 — Surface migration plan to user

- [ ] **Step 1:** Print the list:

```bash
ls /Volumes/CS_Stuff/govcon/supabase/migrations/2026051*
```

Expected:
- `20260510120000_add_api_keys.sql`
- `20260510120100_add_competitor_history.sql`
- `20260510140000_add_action_package_approval.sql` (from Phase 1)

- [ ] **Step 2:** Confirm `supabase` CLI is logged in and linked:

```bash
supabase status   # shows linked project
```

- [ ] **Step 3:** Ask the user: "About to apply 3 migrations to the linked Supabase project. Proceed?"

Wait for explicit yes.

### Task 4.2 — Apply

- [ ] **Step 1:**

```bash
cd /Volumes/CS_Stuff/govcon
supabase db push
```

Expected: 3 migrations applied. Watch for errors (e.g., FK violations if `auth.users` integration isn't right — fall back to `profiles(id)` if needed per Phase 1 contingency).

- [ ] **Step 2: Verify**

```bash
supabase migration list
```

Should show all three as Applied.

### Task 4.3 — Smoke-test the live routes

- [ ] **Step 1:** From local dev with a real Supabase JWT, mint an API key:

```bash
JWT=...   # from /web/login flow
curl -X POST http://localhost:8000/api/keys \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke"}'
# expect: {"id":"...", "plaintext_key":"gck_...", ...}
```

- [ ] **Step 2:** Use the gck_ key against /api/v1/tools:

```bash
GCK=gck_...
curl -X POST http://localhost:8000/api/v1/tools/rank-opportunities \
  -H "Authorization: Bearer $GCK" \
  -H "Content-Type: application/json" \
  -d '{"scored":[{"opportunity_id":"a","decision":"pursue","total_score":75,"due_date":"2026-06-01"}]}'
# expect: {"data":{"ranked":[...]}, "metrics":null}
```

- [ ] **Step 3:** Approve a real action package via the UI; verify Supabase Studio shows `approved_at` populated.

### Task 4.4 — No commit (operational step)

This phase doesn't produce a code commit. Update the verified-state markers:

- [ ] **Step 1:**

```bash
git add devdocs/HANDOFF_PROMPT.md  # if you update Section 1 to mark migrations applied
git commit -m "docs(state): migrations applied — api_keys, competitor_history, approval"
```

---

## Phase 5: Production magic-link email delivery

**Validation gate:** A real production magic link delivers within 30s and doesn't land in spam.

**Why:** Supabase's default SMTP throttles to 4 emails/hour project-wide. Public launch needs a real provider.

### Task 5.1 — Pick provider

Recommended: **Resend** (3,000/mo free tier, low friction).

Alternatives: Postmark (premium deliverability), SES (cheap if AWS native).

### Task 5.2 — Configure (Supabase Studio, not code)

- [ ] **Step 1:** Sign up for Resend, get an API key.
- [ ] **Step 2:** Add a domain (e.g., `mail.govcapture.example`); verify SPF/DKIM/DMARC DNS.
- [ ] **Step 3:** In Supabase Studio → Authentication → Email Templates → SMTP Settings:
  - Host: `smtp.resend.com`
  - Port: `465` (TLS)
  - Username: `resend`
  - Password: `<resend api key>`
  - Sender email: `noreply@mail.govcapture.example`
  - Sender name: `GovCapture`

### Task 5.3 — Customize template

- [ ] **Step 1:** Edit the Magic Link email template in Supabase Studio. Replace stock copy with brand-aligned text matching `/login`.

### Task 5.4 — Verify deliverability

- [ ] **Step 1:** From production (or a Resend-configured dev), request a magic link to a real Gmail / Outlook / Yahoo account. Confirm:
  - Arrives within 30s.
  - Doesn't land in spam (especially Outlook).
  - Link works (single-use, 5min TTL).

- [ ] **Step 2:** Stress-test: 5 requests in a minute should all deliver (Supabase default would block this at 4).

### Task 5.5 — Document

- [ ] **Step 1:** Update `.env.production.example` with a comment:

```
# Email delivery: SMTP configured in Supabase Studio → Auth → SMTP Settings.
# Provider: Resend. Sender: noreply@mail.govcapture.example.
# Secret lives in Supabase, not in this env file.
```

- [ ] **Step 2:**

```bash
git add .env.production.example
git commit -m "docs(infra): production magic-link email delivery via Resend"
```

---

## Phase 6: VX1 production deploy

**Validation gate:** All earlier phases clean. User has Vultr account, DNS access, Vercel access.

### Task 6.1 — Provision

- [ ] **Step 1:** Vultr VX1 (16 vCPU / 64 GB / 960 GB / Ubuntu 24.04). Root SSH key.
- [ ] **Step 2:** SSH in. `hostnamectl set-hostname api-prod-1`.

### Task 6.2 — Bootstrap

- [ ] **Step 1:** `bash <(curl -s ...path-to-bootstrap.sh)` or scp + run `infra/bootstrap.sh`. Idempotent: installs apt deps, ufw, redis, govcapture user, systemd unit.
- [ ] **Step 2:** `redis-cli ping` → `PONG`.

### Task 6.3 — Code + sync

- [ ] **Step 1:** Clone to `/opt/govcapture` (deploy key for private repo).
- [ ] **Step 2:** `uv sync` as the `govcapture` user.

### Task 6.4 — `.env`

- [ ] **Step 1:** Drop production `.env` (chmod 600, owned by govcapture):

```
ANTHROPIC_API_KEY=sk-ant-...
SAM_API_KEY=                # optional
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
SUPABASE_ANON_KEY=sb_publishable_...
SUPABASE_STORAGE_BUCKET=govcapture-attachments
INTERNAL_API_KEY=<long random — mirror to /root/michealaai>
REDIS_URL=redis://localhost:6379/0
LLM_DEV_MODEL=claude-haiku-4-5-20251001
LLM_SYNTH_MODEL=claude-sonnet-4-6
RUN_BUDGET_USD=0.50
RUN_BUDGET_STEPS=40
RUN_BUDGET_SECONDS=360
CORS_ALLOWED_ORIGINS=https://app.govcapture.example,https://govcapture.example
```

### Task 6.5 — systemd + nginx + certbot

- [ ] **Step 1:** `systemctl enable --now govcapture-api.service`. Check `systemctl status`.
- [ ] **Step 2:** `curl 127.0.0.1:8000/healthz` → 200.
- [ ] **Step 3:** Configure nginx at `/etc/nginx/sites-available/govcapture` (SSE-friendly: `proxy_buffering off`, long timeouts).
- [ ] **Step 4:** `certbot --nginx -d api.govcapture.example`.
- [ ] **Step 5:** `systemctl reload nginx`.

### Task 6.6 — DNS

- [ ] **Step 1:** A record `api.govcapture.example` → VX1 IP.
- [ ] **Step 2:** `dig +short api.govcapture.example` from a remote host returns the right IP.

### Task 6.7 — Production smoke

- [ ] **Step 1:** From outside the box:

```bash
curl https://api.govcapture.example/healthz
curl https://api.govcapture.example/.well-known/agent.json
curl -X POST https://api.govcapture.example/tools/rank-opportunities \
  -H "X-Internal-API-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scored":[{"opportunity_id":"a","decision":"pursue","total_score":75,"due_date":"2026-06-01"}]}'
```

All return 200 with valid bodies.

- [ ] **Step 2:** `journalctl -u govcapture-api -n 50` — no tracebacks.

### Task 6.8 — Vercel

- [ ] **Step 1:** Vercel project → Environment Variables:
  - `NEXT_PUBLIC_API_BASE = https://api.govcapture.example`
  - `NEXT_PUBLIC_SUPABASE_URL` (already set)
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY` (already set)

- [ ] **Step 2:** Trigger redeploy.
- [ ] **Step 3:** Visit production URL → end-to-end:
  - Sign in (Phase 5 SMTP delivers magic link)
  - Land on /app
  - Mint API key at /app/keys
  - Copy the gck_, curl `/api/v1/tools/parse-goal` from your local terminal — works.

### Task 6.9 — Document

- [ ] **Step 1:** Update `infra/RUNBOOK.md` with any lessons from rollout.
- [ ] **Step 2:**

```bash
git add infra/RUNBOOK.md
git commit -m "docs(deploy): VX1 deploy notes"
```

---

## Phase 7: Cross-repo Sprint G end-to-end verification

**Validation gate:** Phase 6 deploy live. `/root/michealaai` is on a known commit that implements the pickup contract from `devdocs/CAPABILITY_PACK_INTEGRATION.md` Sprint G section.

### Task 7.1 — Coordinate with `/root/michealaai`

- [ ] **Step 1:** Confirm orchestrator is running against the production INTERNAL_API_KEY (the same secret as VX1).
- [ ] **Step 2:** Confirm the orchestrator's pickup-loop interval and trace-event schema match `devdocs/CAPABILITY_PACK_INTEGRATION.md` §"Pickup contract" + §"Trace event format".

### Task 7.2 — Trigger a real run

- [ ] **Step 1:** From production `/web` UI:
  - Sign in
  - Create a profile
  - Click "Start a run" → goal entry → submit
  - Land on `/app/runs/{id}`

- [ ] **Step 2:** Observe in real time:
  - `agent_runs` row claimed (`status='running'`) within ~5s.
  - Trace events flow into Redis channel `agent-run:{id}`.
  - SSE in `/web` updates the timeline live (no polling fallback).
  - On completion: `action_packages` row created; UI shows the package; approval gate works (Phase 1).

- [ ] **Step 3:** Hit each "Known unknowns" row in CAPABILITY_PACK_INTEGRATION.md — flip status to verified or document divergence.

### Task 7.3 — Update spec docs

- [ ] **Step 1:** Update `devdocs/CAPABILITY_PACK_INTEGRATION.md` "Known unknowns" table — flip `unknown` → `verified` per row.
- [ ] **Step 2:** Update `devdocs/HANDOFF_PROMPT.md` Section 7 row G from "spec done" → "**verification done**".

### Task 7.4 — Commit

```bash
git add devdocs/CAPABILITY_PACK_INTEGRATION.md devdocs/HANDOFF_PROMPT.md
git commit -m "docs(g): Sprint G verification — e2e flow live in production"
```

---

## Phase 8: Eval goldens bootstrap

**Validation gate:** Real `ANTHROPIC_API_KEY` in `.env` (not the placeholder).

**Why:** `eval/runner/runner.py` is wired but the goldens directory is empty. Running `make eval` against no goldens succeeds vacuously.

### Task 8.1 — Add `eval_inputs` blocks to each fixture manifest

For each fixture (`strong-pursue`, `maybe-needs-partner`, `reject`, `adversarial-image-pdf`):

- [ ] **Step 1:** Edit `fixtures/<slug>/manifest.json`. Add an `eval_inputs` block describing per-skill inputs:

```json
{
  "slug": "strong-pursue",
  "opportunity": { /* existing */ },
  "eval_inputs": {
    "parse_goal": {
      "goal": "Find FedRAMP cyber RFPs in the next 30 days",
      "company_profile": {"naics_codes": ["541512"]}
    },
    "score_fit": {
      "company_profile": { /* */ },
      "requirements": [ /* synthesized from this fixture */ ]
    },
    "extract_requirements": {
      "pdf_path": "attachments/main.pdf"
    },
    "detect_risks": { /* */ },
    "generate_action_package": { /* mode: full */ }
  }
}
```

Skip skills that don't apply to a given fixture.

### Task 8.2 — Bootstrap goldens

- [ ] **Step 1:** Cost ceiling: budget ~$0.40 max for full bootstrap.

- [ ] **Step 2:**

```bash
cd /Volumes/CS_Stuff/govcon
make eval-bootstrap
```

This calls real Anthropic for every (fixture × skill) declared. Watch the cost meter.

- [ ] **Step 3:** Hand-review the produced JSON files at `eval/goldens/<slug>/<skill>.json`. If a "reject" fixture got "pursue" decision, the skill or prompt is broken — fix BEFORE accepting golden.

### Task 8.3 — Lock as regression gate

- [ ] **Step 1:** Run `make eval` (without --bootstrap). Should pass (output matches golden within tolerance).

- [ ] **Step 2:** Sanity-check tolerance: deliberately mutate a constant in one skill, re-run `make eval`, observe failure. Revert.

### Task 8.4 — Commit

```bash
git add fixtures/*/manifest.json eval/goldens/
git commit -m "feat(eval): bootstrap goldens for 4 fixtures × 5 LLM skills"
```

---

## Phase 9: v1.0.0 tag + final state docs

**Validation gate:** All earlier phases done. Working tree clean.

### Task 9.1 — Update CURRENT_STATE.md

- [ ] **Step 1:** Bump §7 API surface to reflect the final route count (~54 with the new approve route).
- [ ] **Step 2:** §10 "Done" — add Phase 1 (approval persistence), Phase 2 (SSE polish), Phase 4 (migrations applied), Phase 5 (Resend SMTP), Phase 6 (VX1 deployed), Phase 7 (Sprint G verified), Phase 8 (eval goldens). "Next" — clear out completed items.
- [ ] **Step 3:** §9 timeline — add 2026-05-10 launch-runway + finish-it-all entries.

### Task 9.2 — Update HANDOFF_PROMPT.md

- [ ] **Step 1:** Section 1 — production state (URL, route count, all gates).
- [ ] **Step 2:** Section 7 — every sprint marked done.
- [ ] **Step 3:** Add a Section 20 "Beyond v1" listing the Out-of-Scope items so the next session knows what to consider.

### Task 9.3 — Annotated v1.0.0 tag

- [ ] **Step 1:** Working tree clean.
- [ ] **Step 2:**

```bash
git tag -a v1.0.0 -m "v1.0.0 — public launch

GovCon Bid Desk capability pack, deployed to Vultr VX1 + Vercel + Supabase.
Sprints A through G complete. Agent-callable via /api/v1/tools/<name>
with gck_… keys, MCP server published. Magic-link auth via Resend SMTP.
Eval harness covering 4 fixtures × 5 LLM skills. Cross-repo Sprint G
verified end-to-end with /root/michealaai. ApprovalGate persisted
server-side via action_packages.approved_at."
```

### Task 9.4 — Push

- [ ] **Step 1:** Working tree clean.
- [ ] **Step 2:**

```bash
git push origin main --follow-tags
```

Verify on GitHub: tag `v1.0.0` visible.

---

## Self-Review

**Spec coverage:** every truly-outstanding item from the previous plans + session has a phase here. Items already shipped are in the "What's already done" table at the top, NOT replanned.

**Placeholder scan:** No "TBD", "TODO", "implement later", "similar to Task N", "fill in details". Where flexibility is required (e.g., Phase 3.2's two approaches to the schemas codegen split), I name both options and pick a recommendation.

**Type consistency:**
- `requireUser()` → `{ user, token }` shape used in Phase 0's commit message + Phase 1's API client.
- `approved_at`, `approved_by` consistent across migration SQL, JSON schema, Pydantic model, repo method, route, frontend types, ApprovalGate component.
- `gck_…` key prefix consistent.

**Risks consciously accepted:**
- Phase 1 ASK-FIRST gate slows the auto-mode flow but is required.
- Phase 3 (Makefile fix) is non-trivial and could touch many files; reasonable to defer if Phase 4 needs to ship first (in that case, hand-editing schemas is acceptable for v1).
- Phase 5 (email) needs Resend account + DNS access — out-of-band setup blocks the agent.
- Phase 6 (deploy) needs Vultr + DNS + Vercel access — same.
- Phase 7 needs `/root/michealaai` ready — same.
- Phase 8 costs real Anthropic tokens — explicit budget caveat.

**Out-of-scope items deliberately excluded** are listed at the top of the plan.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-10-finish-it-all.md`. Two execution options:

**1. Inline (recommended for Phases 0–3, 8, 9)** — same-session execution via `superpowers:executing-plans`. The first three phases share a small file set and the natural review points are the per-phase commits.

**2. Subagent-driven (recommended for Phase 6)** — deploy is a sequence of external operations (provision, DNS, certbot) where each step is its own context; subagent isolation prevents leakage.

**Phases 4, 5, 7** are operational, not implementable by an agent without external account access — the plan describes them precisely; the executor with credentials performs them.

**Critical path:** 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9. Phases 1, 2, 3, 8 can be reordered if convenient (each ships as a standalone PR); 4 must follow 1 (or 1's migration won't apply); 5 must precede 6 (you don't want to deploy with broken email); 7 needs 6 deployed; 9 must be last.

**Realistic single-engineer ETA:** 3–5 working days. Most of the time is in Phase 6 (deploy) + Phase 7 (cross-repo coordination); Phases 0–3 are mostly in-session refactors.
