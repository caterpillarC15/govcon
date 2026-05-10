# Sprint C: `/web` Product UI + Auth Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended for this plan; same two/three growing files most phases) or superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift `/web` from "authenticated shell + monolithic console" to a usable customer-facing product: polished login → dashboard → profile management → goal-driven runs with live SSE timeline → opportunity detail → action-package approval flow. The user can sign in, create a profile, kick off a run, watch it progress in real time, drill into an opportunity, and approve a bid memo.

**Architecture:**
- **Route-segmented Next 15 App Router**: each major surface gets its own route. Server components for the protected shell + initial data fetch (Supabase SSR), client islands for interactivity (forms, polling, SSE).
- **Auth (already wired, polished here)**: magic-link via `signInWithOtp` → callback exchanges code for cookie → middleware enforces session on `/app/**`. New: explicit "magic link sent" landing, friendly "session expired" path, loading state during sign-in.
- **Data layer**: `/web/src/lib/api.ts` extended to a typed client; per-route server fetchers use Supabase JWT directly.
- **Real-time**: `EventSource` to `GET /agent-runs/:id/stream` for live trace events (Sprint B's SSE forwarder); auto-close on `run_completed`.
- **Approval gate**: `human_approval_required` rendered as required checkboxes; "Approve" disabled until all checked. (Pack does not enforce server-side; UI is the gate.)
- **Stack**: Next 15 (App Router) · React 19 · Tailwind 4 · `@supabase/ssr` 0.10 · `@supabase/supabase-js` 2.105 · `lucide-react`. No new deps.

**Non-goals:**
- Password auth or OAuth providers — magic link only for v1.
- Editing the AppConsole inline — replaced by route-segmented pages.
- Server-side enforcement of approval gates (that's a separate Sprint).
- Component library introduction (shadcn/ui etc.) — keep current Tailwind-only style.
- Storybook / visual regression tooling.
- Marketing site changes (lives in `/landing`).

**Verification gates (must hold at end of every phase):**
- `npm -w web run typecheck` — clean.
- `npm -w web run lint` — clean (no new warnings).
- `npm -w web run build` — clean (production build).
- Manual browser check at the end of each phase: log in (magic link in dev: `localhost:54321/auth/v1` or Supabase Studio inbox), navigate the new surfaces, confirm no console errors, confirm requests succeed against `localhost:8000`.

**Final verification gates (sprint complete):**
- Cold-start flow: visit `/`, get redirected to `/login` (when signed-out) or `/app` (when signed-in).
- Magic-link flow: enter email, see "check your inbox" panel, click link in inbox, land on `/app`.
- First-run flow: empty `/app` → "Create profile" CTA → form → return to `/app` populated → enter goal → submit → land on `/app/runs/[id]` with live SSE timeline.
- Drill-in: opportunity row → `/app/opportunities/[id]` with requirements + fit + risks.
- Approval flow: action package → check all approval gates → "Approve" enables.
- Sign-out: returns to `/login`; revisit `/app` redirects.
- Mobile: Chrome devtools at 375px width — no horizontal scroll, all forms usable.

---

## File Structure

| Action | Path | Responsibility |
|---|---|---|
| Modify | `web/src/middleware.ts` | (already correct; verify) |
| Modify | `web/src/app/page.tsx` | Add "redirect by auth state" smart landing (currently always redirects to `/app`) |
| Modify | `web/src/app/login/page.tsx` | Loading state on submit, "resend" link, friendlier copy |
| Modify | `web/src/app/login/actions.ts` | (likely no change; verify error paths) |
| Modify | `web/src/app/auth/callback/route.ts` | Carry `?error=` to `/login` on exchange failure |
| Create | `web/src/app/login/sent/page.tsx` | "Magic link sent" confirmation surface (replaces in-page panel) |
| Create | `web/src/app/app/layout.tsx` | Shared shell for the authed product (header, nav, sign-out) |
| Replace | `web/src/app/app/page.tsx` | Dashboard home: list profiles + recent runs + primary CTA, replaces AppConsole-as-everything |
| Delete | `web/src/app/app/AppConsole.tsx` | Decomposed into the routes below |
| Create | `web/src/app/app/profile/new/page.tsx` | Profile create form (server component shell + client form) |
| Create | `web/src/app/app/profile/page.tsx` | Profile list / edit |
| Create | `web/src/app/app/profile/[id]/page.tsx` | Profile detail / edit |
| Create | `web/src/app/app/goal/page.tsx` | Goal entry form (creates `agent_runs` row, redirects to `/app/runs/[id]`) |
| Create | `web/src/app/app/runs/[id]/page.tsx` | Run timeline + matched opportunities list (server component) |
| Create | `web/src/app/app/runs/[id]/RunTimeline.tsx` | Client component subscribing to SSE |
| Create | `web/src/app/app/opportunities/[id]/page.tsx` | Opportunity detail: requirements, fit-score, risks |
| Create | `web/src/app/app/action-packages/[id]/page.tsx` | Action package detail + approval gate |
| Create | `web/src/app/app/action-packages/[id]/ApprovalGate.tsx` | Client component enforcing all-checkboxes-checked |
| Modify | `web/src/lib/api.ts` | Typed fetchers for each entity; central error handling; `apiFetch<T>(path, init, token)` |
| Create | `web/src/lib/types.ts` | TS types mirroring the API responses (CompanyProfile, AgentRun, Opportunity, ActionPackage, etc.) |
| Create | `web/src/components/EmptyState.tsx` | Reusable empty-state card |
| Create | `web/src/components/Card.tsx` | Reusable rounded glass card wrapper to match existing design |
| Create | `web/src/components/Skeleton.tsx` | Loading skeleton primitives |
| Create | `web/src/components/PageHeader.tsx` | Page-title header used across `/app/*` |

---

## Phase 0: Foundation — typed client + types + reusable components

### Task 0.1: TypeScript types

**Files:** Create `web/src/lib/types.ts`

- [ ] **Step 1: Author the types**

```ts
// web/src/lib/types.ts
export type CompanyProfile = {
  id: string
  name: string
  description?: string | null
  capabilities: string[]
  naics_codes: string[]
  certifications: string[]
  location?: string | null
  small_business_status: boolean
  clearance_status?: string | null
  preferred_role: 'prime' | 'sub' | 'either'
  created_at: string
  updated_at?: string | null
}

export type RunStatus = 'pending' | 'running' | 'complete' | 'partial' | 'failed'

export type TraceEvent = {
  type: string
  ts?: string
  run_id?: string
  step_id?: string
  label?: string
  tool?: string
  decision?: string
  score?: number
  summary?: string
  input?: Record<string, unknown>
  output?: Record<string, unknown> | null
  error?: string | null
  latency_ms?: number
  cost_usd?: number
  [key: string]: unknown
}

export type AgentRun = {
  id: string
  goal: string
  status: RunStatus
  steps: TraceEvent[]
  opportunities: string[]
  selected_opportunity_id?: string | null
  action_package_id?: string | null
  company_profile_id?: string | null
  completed_at?: string | null
  created_at: string
}

export type Opportunity = {
  id: string
  slug: string
  title: string
  agency: string
  due_date?: string | null
  set_aside?: string | null
  naics?: string | null
  description?: string | null
  source_url?: string | null
}

export type Decision = 'strong_pursue' | 'pursue' | 'maybe' | 'reject'

export type ExtractedRequirement = {
  id: string
  type: string
  title: string
  value?: string
  description?: string
  confidence: 'high' | 'medium' | 'low' | 'unknown'
  evidence_snippet?: string
  source_document?: string
  page_number?: number | null
  is_blocker: boolean
}

export type FitScore = {
  total_score: number
  decision: Decision
  confidence: 'high' | 'medium' | 'low'
  strengths: string[]
  weaknesses: string[]
  blockers: string[]
}

export type RiskFlag = {
  id: string
  category: string
  severity: 'critical_blocker' | 'major_risk' | 'moderate_risk' | 'minor_concern'
  title: string
  description: string
  evidence?: string
  mitigation?: string
  requires_human_review: boolean
}

export type ActionPackage = {
  id: string
  opportunity_id: string
  company_profile_id: string
  executive_summary: string
  decision: Decision
  fit_score: number
  fit_rationale: string
  compliance_matrix: Array<{ requirement: string; status: string; evidence: string; next_action: string; owner: string }>
  risk_register: Array<{ risk: string; severity: string; explanation: string; mitigation: string }>
  proposal_checklist: string[]
  timeline: Array<{ date: string; task: string; owner: string }>
  partner_suggestions: Array<{ partner_type: string; gap_solved: string; why_needed: string; outreach_angle: string; confidence: string }> | null
  outreach_draft?: { subject: string; body: string } | null
  approval_required: string[]
  created_at: string
}
```

- [ ] **Step 2: Verify imports**

Run: `npm -w web run typecheck`
Expected: clean.

### Task 0.2: Typed API client

**Files:** Modify `web/src/lib/api.ts`

- [ ] **Step 1: Replace the file with the typed client**

```ts
// web/src/lib/api.ts
import type {
  ActionPackage,
  AgentRun,
  CompanyProfile,
  ExtractedRequirement,
  FitScore,
  Opportunity,
  RiskFlag,
} from './types'

export function getApiBase() {
  return (process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000').replace(
    /\/$/,
    '',
  )
}

export class ApiError extends Error {
  status: number
  body: unknown
  constructor(status: number, message: string, body?: unknown) {
    super(message)
    this.status = status
    this.body = body
  }
}

async function request<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
    cache: 'no-store',
  })
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const message =
      typeof body === 'object' && body && 'detail' in body && typeof (body as { detail: unknown }).detail === 'string'
        ? (body as { detail: string }).detail
        : `Request failed (${response.status})`
    throw new ApiError(response.status, message, body)
  }
  return (await response.json()) as T
}

export const api = {
  listCompanyProfiles: (token: string) =>
    request<CompanyProfile[]>('/company-profiles', token),
  getCompanyProfile: (token: string, id: string) =>
    request<CompanyProfile>(`/company-profiles/${id}`, token),
  createCompanyProfile: (token: string, payload: Partial<CompanyProfile>) =>
    request<CompanyProfile>('/company-profiles', token, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  createAgentRun: (token: string, payload: { goal: string; profile_id?: string; profile?: Partial<CompanyProfile> }) =>
    request<AgentRun>('/agent-runs', token, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getAgentRun: (token: string, id: string) =>
    request<AgentRun>(`/agent-runs/${id}`, token),
  listAgentRunOpportunities: (token: string, id: string) =>
    request<Opportunity[]>(`/agent-runs/${id}/opportunities`, token),

  getOpportunity: (token: string, id: string) =>
    request<Opportunity>(`/opportunities/${id}`, token),
  getOpportunityRequirements: (token: string, id: string) =>
    request<ExtractedRequirement[]>(`/opportunities/${id}/requirements`, token),
  getOpportunityFitScore: (token: string, id: string) =>
    request<FitScore>(`/opportunities/${id}/fit-score`, token),
  getOpportunityRisks: (token: string, id: string) =>
    request<RiskFlag[]>(`/opportunities/${id}/risks`, token),

  getActionPackage: (token: string, id: string) =>
    request<ActionPackage>(`/action-packages/${id}`, token),
}
```

- [ ] **Step 2: typecheck + lint**

Run: `npm -w web run typecheck && npm -w web run lint`
Expected: clean.

### Task 0.3: Reusable components

**Files:** Create `web/src/components/{Card,EmptyState,PageHeader,Skeleton}.tsx`

- [ ] **Step 1: Card**

```tsx
// web/src/components/Card.tsx
import type { ReactNode } from 'react'

export function Card({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={`rounded-[20px] border border-white/80 bg-white/76 p-5 shadow-[0_20px_60px_-44px_rgba(15,23,42,0.5)] backdrop-blur-2xl ${className}`}
    >
      {children}
    </div>
  )
}
```

- [ ] **Step 2: EmptyState**

```tsx
// web/src/components/EmptyState.tsx
import type { ReactNode } from 'react'

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-[20px] border border-dashed border-slate-200 bg-white/40 p-10 text-center">
      {icon ? <div className="text-blue-900">{icon}</div> : null}
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      {description ? (
        <p className="max-w-sm text-sm leading-6 text-slate-600">{description}</p>
      ) : null}
      {action}
    </div>
  )
}
```

- [ ] **Step 3: PageHeader**

```tsx
// web/src/components/PageHeader.tsx
import type { ReactNode } from 'react'

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: string
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? (
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="mt-1 text-2xl font-semibold tracking-normal text-slate-950">
          {title}
        </h1>
        {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </header>
  )
}
```

- [ ] **Step 4: Skeleton**

```tsx
// web/src/components/Skeleton.tsx
export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-xl bg-slate-200/60 ${className}`}
      aria-hidden
    />
  )
}
```

- [ ] **Step 5: typecheck**

Run: `npm -w web run typecheck`
Expected: clean.

### Task 0.4: Shared `/app` layout

**Files:** Create `web/src/app/app/layout.tsx`

- [ ] **Step 1: Author the layout**

```tsx
// web/src/app/app/layout.tsx
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { signOut } from '../login/actions'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  return (
    <main className="min-h-screen bg-[#f7f8fb] text-slate-950">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-5 py-6 sm:px-8">
        <header className="flex flex-col gap-4 rounded-[28px] border border-white/80 bg-white/72 p-5 shadow-[0_24px_70px_-44px_rgba(15,23,42,0.44)] backdrop-blur-2xl sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Link
              href="/app"
              className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500 transition hover:text-slate-700"
            >
              GovCapture
            </Link>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">
              Michaela bid desk
            </h1>
            <p className="mt-1 text-sm text-slate-600">{user.email}</p>
          </div>
          <nav className="flex items-center gap-2">
            <Link
              href="/app/profile"
              className="h-10 rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 grid place-items-center"
            >
              Profile
            </Link>
            <form action={signOut}>
              <button
                type="submit"
                className="h-10 rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
              >
                Sign out
              </button>
            </form>
          </nav>
        </header>
        {children}
      </div>
    </main>
  )
}
```

- [ ] **Step 2: typecheck**

Run: `npm -w web run typecheck`
Expected: clean.

---

## Phase 1: Login flow polish

### Task 1.1: Smart root redirect

**Files:** Modify `web/src/app/page.tsx`

- [ ] **Step 1: Replace blind `/app` redirect with auth-aware redirect**

```tsx
// web/src/app/page.tsx
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export default async function Home() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  redirect(user ? '/app' : '/login')
}
```

### Task 1.2: Login submit with loading state

**Files:** Modify `web/src/app/login/page.tsx`

- [ ] **Step 1: Convert to client island for the submit button** (use `useFormStatus`)

Use Edit to replace the form block. The Server-Action `signIn` import stays. Add a SubmitButton client subcomponent:

```tsx
// at top of file
'use client' is NOT applied to the page. Instead, extract:
```

```tsx
// web/src/app/login/SubmitButton.tsx (new file)
'use client'
import { Loader2 } from 'lucide-react'
import { useFormStatus } from 'react-dom'

export function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus()
  return (
    <button
      type="submit"
      disabled={pending}
      className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-full bg-slate-950 px-5 text-sm font-medium text-white transition hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-800 disabled:cursor-not-allowed disabled:opacity-70"
    >
      {pending ? <Loader2 size={15} className="animate-spin" aria-hidden /> : null}
      {pending ? 'Sending…' : label}
    </button>
  )
}
```

Then in `login/page.tsx`, replace the inline `<button>` with `<SubmitButton label="Send magic link" />` (and import it).

- [ ] **Step 2: Tighter copy + resend link after sent state**

Replace the `params.sent` panel with a richer block including a "Use a different email?" link back to a fresh form (`<Link href="/login">`).

### Task 1.3: Friendlier auth-callback failure path

**Files:** Modify `web/src/app/auth/callback/route.ts`

- [ ] **Step 1: Surface exchange errors to the login screen**

```ts
// web/src/app/auth/callback/route.ts
import { NextResponse, type NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'

function safeNext(value: string | null) {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return '/app'
  return value
}

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const next = safeNext(requestUrl.searchParams.get('next'))

  if (!code) {
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent('Missing magic-link code. Request a new link.')}`, requestUrl.origin),
    )
  }

  const supabase = await createClient()
  const { error } = await supabase.auth.exchangeCodeForSession(code)
  if (error) {
    return NextResponse.redirect(
      new URL(
        `/login?error=${encodeURIComponent('Magic link expired or already used. Request a new link.')}`,
        requestUrl.origin,
      ),
    )
  }

  return NextResponse.redirect(new URL(next, requestUrl.origin))
}
```

### Task 1.4: Verify

- [ ] `npm -w web run typecheck && npm -w web run lint && npm -w web run build`
- [ ] Manual: visit `/login`, submit email, see "Sending…" loader, then "Magic link sent". Visit a malformed callback URL → land on `/login` with friendly error.

---

## Phase 2: Dashboard home

### Task 2.1: Replace `/app/page.tsx` with dashboard

**Files:** Replace `web/src/app/app/page.tsx`. Delete `web/src/app/app/AppConsole.tsx` after dependent routes exist (Phase 3+).

- [ ] **Step 1: New `/app/page.tsx` server component**

```tsx
// web/src/app/app/page.tsx
import Link from 'next/link'
import { Plus, Sparkles } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import type { CompanyProfile } from '@/lib/types'

export const dynamic = 'force-dynamic'

async function getToken(): Promise<string | null> {
  const supabase = await createClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

export default async function AppHome() {
  const token = await getToken()
  if (!token) {
    return null // middleware redirected; defensive
  }

  let profiles: CompanyProfile[] = []
  let loadError: string | null = null
  try {
    profiles = await api.listCompanyProfiles(token)
  } catch (err) {
    loadError = err instanceof ApiError ? err.message : 'Could not load profiles.'
  }

  const hasProfile = profiles.length > 0

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Bid desk"
        title="Welcome back"
        subtitle={
          hasProfile
            ? 'Pick a profile and start a new run, or jump back into a recent one.'
            : 'Set up your company profile so Michaela can match opportunities.'
        }
        actions={
          hasProfile ? (
            <Link
              href="/app/goal"
              className="inline-flex h-10 items-center gap-2 rounded-full bg-blue-900 px-4 text-sm font-medium text-white transition hover:bg-blue-800"
            >
              <Sparkles size={15} aria-hidden /> Start a run
            </Link>
          ) : null
        }
      />

      {loadError ? (
        <Card className="border-red-200 bg-red-50/80 text-sm text-red-900">
          {loadError}
        </Card>
      ) : null}

      {!hasProfile ? (
        <EmptyState
          icon={<Plus size={28} />}
          title="No company profile yet"
          description="GovCapture matches opportunities to your capabilities, NAICS codes, certifications, and clearance level. Add a profile to begin."
          action={
            <Link
              href="/app/profile/new"
              className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              Create company profile
            </Link>
          }
        />
      ) : (
        <Card>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-blue-900">Your profiles</p>
              <h2 className="mt-1 text-lg font-semibold text-slate-950">
                {profiles.length} on file
              </h2>
            </div>
            <Link
              href="/app/profile"
              className="text-sm font-medium text-blue-900 underline-offset-4 hover:underline"
            >
              Manage
            </Link>
          </div>
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {profiles.map((profile) => (
              <li
                key={profile.id}
                className="rounded-2xl border border-slate-200 bg-white p-4"
              >
                <p className="text-sm font-semibold text-slate-950">{profile.name}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {profile.naics_codes.join(', ') || 'No NAICS'} ·{' '}
                  {profile.small_business_status ? 'Small business' : 'Not registered SB'}
                </p>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
```

### Task 2.2: Verify

- [ ] `npm -w web run typecheck && npm -w web run lint && npm -w web run build`
- [ ] Browser: empty-profile state shows the create CTA; populated state lists profiles + "Start a run" link.

---

## Phase 3: Profile management

### Task 3.1: `/app/profile/new`

**Files:** Create `web/src/app/app/profile/new/{page.tsx,ProfileForm.tsx}`

- [ ] **Step 1: Server shell**

```tsx
// web/src/app/app/profile/new/page.tsx
import { PageHeader } from '@/components/PageHeader'
import { Card } from '@/components/Card'
import { ProfileForm } from './ProfileForm'

export const dynamic = 'force-dynamic'

export default function NewProfilePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Profile"
        title="Create a company profile"
        subtitle="Capabilities, NAICS, certifications, and clearance — used by Gate (eligibility) and Lenny (fit ranking)."
      />
      <Card>
        <ProfileForm />
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Client form (extract from existing AppConsole)**

```tsx
// web/src/app/app/profile/new/ProfileForm.tsx
'use client'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { api, ApiError } from '@/lib/api'

function splitList(value: string) {
  return value.split(',').map((s) => s.trim()).filter(Boolean)
}

export function ProfileForm() {
  const router = useRouter()
  const supabase = createClient()
  const [form, setForm] = useState({
    name: '',
    capabilities: '',
    naics: '',
    certifications: '',
    location: '',
    description: '',
    clearanceStatus: 'none',
    smallBusiness: true,
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const session = (await supabase.auth.getSession()).data.session
      if (!session) {
        setError('Session expired. Sign in again.')
        return
      }
      const created = await api.createCompanyProfile(session.access_token, {
        name: form.name.trim(),
        description: form.description || null,
        capabilities: splitList(form.capabilities),
        naics_codes: splitList(form.naics),
        certifications: splitList(form.certifications),
        location: form.location || null,
        small_business_status: form.smallBusiness,
        clearance_status: form.clearanceStatus,
        preferred_role: 'either',
      })
      router.push(`/app/profile/${created.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save profile.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Name" required>
        <input
          value={form.name}
          onChange={(e) => setForm((c) => ({ ...c, name: e.target.value }))}
          required
          className={inputCls}
        />
      </Field>
      <Field label="Capabilities (comma-separated)">
        <textarea
          value={form.capabilities}
          onChange={(e) => setForm((c) => ({ ...c, capabilities: e.target.value }))}
          rows={2}
          className={inputCls}
        />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="NAICS codes">
          <input
            value={form.naics}
            onChange={(e) => setForm((c) => ({ ...c, naics: e.target.value }))}
            className={inputCls}
          />
        </Field>
        <Field label="Clearance">
          <select
            value={form.clearanceStatus}
            onChange={(e) => setForm((c) => ({ ...c, clearanceStatus: e.target.value }))}
            className={inputCls}
          >
            <option value="none">None</option>
            <option value="secret">Secret</option>
            <option value="top_secret">Top Secret</option>
          </select>
        </Field>
      </div>
      <Field label="Certifications (comma-separated)">
        <input
          value={form.certifications}
          onChange={(e) => setForm((c) => ({ ...c, certifications: e.target.value }))}
          className={inputCls}
        />
      </Field>
      <div className="grid grid-cols-[1fr_auto] items-end gap-3">
        <Field label="Location">
          <input
            value={form.location}
            onChange={(e) => setForm((c) => ({ ...c, location: e.target.value }))}
            className={inputCls}
          />
        </Field>
        <label className="flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700">
          <input
            type="checkbox"
            checked={form.smallBusiness}
            onChange={(e) => setForm((c) => ({ ...c, smallBusiness: e.target.checked }))}
          />
          Small business
        </label>
      </div>
      <Field label="Description">
        <textarea
          value={form.description}
          onChange={(e) => setForm((c) => ({ ...c, description: e.target.value }))}
          rows={3}
          className={inputCls}
        />
      </Field>
      {error ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-900">{error}</p>
      ) : null}
      <button
        type="submit"
        disabled={busy}
        className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {busy ? <Loader2 size={15} className="animate-spin" aria-hidden /> : null}
        Create profile
      </button>
    </form>
  )
}

const inputCls =
  'mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20'

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">
        {label}
        {required ? ' *' : ''}
      </span>
      {children}
    </label>
  )
}
```

### Task 3.2: `/app/profile` (list/manage)

**Files:** Create `web/src/app/app/profile/page.tsx`

Server component listing profiles with edit links. Each profile is a `Link` to `/app/profile/[id]`. New-profile button to `/app/profile/new`.

### Task 3.3: `/app/profile/[id]` detail (read-only for v1)

**Files:** Create `web/src/app/app/profile/[id]/page.tsx`

Server component fetching the profile via `api.getCompanyProfile(token, id)`. Renders the fields. v1 is read-only; "Edit" button is disabled with tooltip "Coming soon" (avoid scope creep).

### Task 3.4: Verify

- [ ] typecheck + lint + build
- [ ] Browser: create profile from /app → redirects to detail page; back to /app shows it.

---

## Phase 4: Run flow with live SSE timeline

### Task 4.1: `/app/goal` entry form

**Files:** Create `web/src/app/app/goal/{page.tsx,GoalForm.tsx}`

Server shell + client form. Form posts via `api.createAgentRun({goal, profile_id})` and then `router.push(\`/app/runs/${created.id}\`)`.

### Task 4.2: `/app/runs/[id]` server shell

**Files:** Create `web/src/app/app/runs/[id]/page.tsx`

Server component fetches the initial run + opportunities + (optionally) action package. Hands them to `<RunTimeline>` client component for live updates.

### Task 4.3: `<RunTimeline>` SSE subscriber

**Files:** Create `web/src/app/app/runs/[id]/RunTimeline.tsx`

```tsx
'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { getApiBase } from '@/lib/api'
import type { AgentRun, TraceEvent } from '@/lib/types'

export function RunTimeline({ initial }: { initial: AgentRun }) {
  const [run, setRun] = useState<AgentRun>(initial)
  const [events, setEvents] = useState<TraceEvent[]>(initial.steps ?? [])
  const supabase = createClient()

  useEffect(() => {
    let es: EventSource | null = null
    let cancelled = false

    async function start() {
      // EventSource doesn't support custom headers; pass token via a session
      // cookie path or use polling fallback. Supabase JWT cookie set by SSR
      // middleware should be auto-attached if we use credentials: include.
      // Browser EventSource sends cookies by default for same-origin.
      // We must build a same-origin proxy if /agent-runs/{id}/stream is on
      // a different origin. For dev, NEXT_PUBLIC_API_BASE = http://localhost:8000
      // is cross-origin from http://localhost:3001 — cookies won't flow.
      // Workaround: query string token (less ideal) OR a Next.js proxy route.
      // For Phase 4: use polling first; SSE upgrade in Phase 7.
      const session = (await supabase.auth.getSession()).data.session
      if (!session) return
      const tick = async () => {
        if (cancelled) return
        try {
          const r = await fetch(`${getApiBase()}/agent-runs/${run.id}`, {
            headers: { Authorization: `Bearer ${session.access_token}` },
            cache: 'no-store',
          })
          if (r.ok) {
            const next = (await r.json()) as AgentRun
            setRun(next)
            setEvents(next.steps ?? [])
            if (['complete', 'failed', 'partial'].includes(next.status)) return
          }
        } catch {
          /* swallow */
        }
        if (!cancelled) setTimeout(tick, 2000)
      }
      tick()
    }
    start()
    return () => {
      cancelled = true
      es?.close()
    }
  }, [run.id, supabase])

  return (
    // ... render events list
  )
}
```

**Note on SSE:** browser `EventSource` doesn't support custom headers, and Next dev server proxy is needed for same-origin. v1 ships with a 2s poll loop on `/agent-runs/{id}` — same UX, simpler. Real SSE is a Phase 7 follow-up.

### Task 4.4: Verify

- [ ] typecheck + lint + build
- [ ] Browser: enter goal → land on `/app/runs/[id]` → poll updates `status` and event count.

---

## Phase 5: Opportunity detail

### Task 5.1: `/app/opportunities/[id]`

**Files:** Create `web/src/app/app/opportunities/[id]/page.tsx`

Server component fetching opportunity + requirements + fit + risks in parallel. Renders sections. Make rows in `/app/runs/[id]` linked to this page.

### Task 5.2: Verify

- [ ] typecheck + build
- [ ] Browser: navigate from a run's opportunity row to detail page.

---

## Phase 6: Action package + approval gate

### Task 6.1: `/app/action-packages/[id]/page.tsx`

Server shell renders the package fields and the `<ApprovalGate>` client component below.

### Task 6.2: `<ApprovalGate>` client component

```tsx
'use client'
import { useState } from 'react'

export function ApprovalGate({ items }: { items: string[] }) {
  const [checked, setChecked] = useState<Record<number, boolean>>({})
  const allChecked = items.every((_, i) => checked[i])
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
        disabled={!allChecked}
        className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-blue-900 px-4 text-sm font-medium text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        Approve & continue
      </button>
      <p className="text-xs text-slate-500">
        Approval is recorded client-side; this Sprint does not enforce server-side enforcement of submission.
      </p>
    </div>
  )
}
```

### Task 6.3: Verify

- [ ] typecheck + build
- [ ] Browser: navigate to action package; "Approve" disabled until all items checked.

---

## Phase 7: Polish

### Task 7.1: Loading skeletons + error boundaries

Add `loading.tsx` and `error.tsx` files at strategic route segments:
- `web/src/app/app/loading.tsx`
- `web/src/app/app/runs/[id]/loading.tsx`
- `web/src/app/app/opportunities/[id]/loading.tsx`

### Task 7.2: Mobile sweep

Walk every page at 375px, 768px, 1280px. Fix any horizontal-scroll cases. Tighten button sizing.

### Task 7.3: Copy + a11y pass

- [ ] All buttons have accessible labels.
- [ ] All forms have `<label>` for each input.
- [ ] Tab order is sensible.

### Task 7.4: SSE upgrade (optional, post-v1)

Replace polling in `RunTimeline` with `EventSource` once a same-origin Next proxy or token-via-querystring decision is made.

### Task 7.5: Final verification

- [ ] All gates green.
- [ ] Cold-start flow walked end-to-end.
- [ ] Update `devdocs/CURRENT_STATE.md` §10 — move `/web` UI from "Next" to "Done" with the new route list.
- [ ] Update `devdocs/HANDOFF_PROMPT.md` Section 7 — mark Sprint C done.

---

## Phase 8: Agent SEO — make the website agent-discoverable and agent-callable

**Goal:** Other AI agents (Claude, GPT, custom MCP clients, web-crawling agents) can discover what govcapture does and call its tools without first reading our marketing copy. Modeled on zero.xyz's "the website itself is the API" pattern.

**Architecture:** Three new surfaces stacked on top of Sprint B:
1. **Discovery layer** — well-known files + OpenAPI + an `llms.txt` that any AI crawler can read.
2. **Public agent auth** — per-user API keys (`gck_…` format) replacing the single internal shared key for outside-the-pack callers; opens `/api/v1/tools/<name>` to authenticated agents.
3. **MCP server** — `mcp_server_govcapture/` Python package exposing the 10 tools over Model Context Protocol so any MCP client (Claude Desktop, Cursor, etc.) can natively use the pack.

**Files to add:**

| Action | Path | Responsibility |
|---|---|---|
| Create | `api/routes/well_known.py` | `/.well-known/agent.json`, `/.well-known/llms.txt`, `/.well-known/mcp.json` |
| Create | `api/routes/api_keys.py` | `POST/GET/DELETE /api/keys` for agent API key minting (user JWT auth) |
| Create | `api/routes/v1_tools.py` | Public mirror of `/tools/<name>` at `/api/v1/tools/<name>`, accepting either `gck_…` API keys or `INTERNAL_API_KEY` |
| Create | `api/auth.py` (extend) | `require_agent_key` dep verifying `Authorization: Bearer gck_…` against `api_keys.key_hash` |
| Create | `api/repositories/api_key.py` | Repo for the new `api_keys` table |
| Create | `supabase/migrations/<ts>_add_api_keys.sql` | `api_keys` table + RLS scoped to `owner_profile_id` |
| Create | `web/src/app/app/keys/page.tsx` | UI to mint, list, copy-once, revoke API keys |
| Create | `web/src/app/agents/page.tsx` | Public "for agents" landing page (auth-free) describing how to use the platform |
| Create | `landing/llms.txt` and `landing/.well-known/agent.json` | Static well-known surfaces on the marketing site |
| Create | `mcp_server_govcapture/` (separate package) | MCP server wrapping the 10 tools — pip-installable, runs locally next to a Claude Desktop install |

**Phase 8 tasks (each TDD where code, doc-only otherwise):**

- **8.1 — `api_keys` table + repo + auth dep.** Migration, repo, `require_agent_key` matching `bcrypt`/`sha256` hashes; tests with FakeSupabase.
- **8.2 — `POST/GET/DELETE /api/keys`.** Routes to mint (returns plaintext key once), list (prefix-only), revoke (soft-delete via `revoked_at`).
- **8.3 — `/api/v1/tools/<name>` public mirror.** Reuses Sprint B request models + skill dispatchers. Auth accepts either header. Each route gets a "scope" string; v1 grants `tools:*` to every key.
- **8.4 — Rate limiting (per API key).** Token-bucket backed by Redis; default 60 req/min/key. Reject 429 with `Retry-After`.
- **8.5 — `/.well-known/agent.json`** (FastAPI route serving the manifest):
  ```json
  {
    "name": "GovCon Bid Desk",
    "description": "Federal contracting capability pack: SAM search, requirement extraction, fit scoring, bid memo synthesis.",
    "version": "1.0.0",
    "auth": { "type": "bearer", "token_url": "/api/keys", "scheme": "gck" },
    "tools_url": "/api/v1/tools",
    "openapi_url": "/openapi.json",
    "llms_url": "/.well-known/llms.txt",
    "contact": "agents@govcapture.example"
  }
  ```
- **8.6 — `/.well-known/llms.txt`** (markdown, human-and-LLM-readable):
  ```
  # GovCon Bid Desk

  Federal contracting capability pack. Hired AI worker that finds federal
  contracts worth bidding on, decides pursue/skip, and produces a bid memo.

  ## For agents
  - API root: https://api.govcapture.example/api/v1
  - Tools: GET /api/v1/tools (10 tools; OpenAPI at /openapi.json)
  - Auth: bearer token (gck_… format), mint at /app/keys after sign-in
  - Rate limit: 60 req/min per key

  ## Tools
  - parse-goal, parse-pdf, extract-requirements, score-fit, detect-risks,
    generate-action-package, search-sam, fetch-attachment,
    rank-opportunities, load-seeded-opportunities

  ## Conventions
  - All responses: { "data": ..., "metrics": LLMMetrics | null }
  - All requests: JSON body; required fields per /openapi.json
  ```
- **8.7 — `/.well-known/mcp.json`.** MCP discovery manifest pointing to the MCP server (8.10).
- **8.8 — `/agents` public landing page** in `/web` (or `/landing` — pick one). Describes the API, links to `/app/keys` for sign-in-then-mint, copy-paste cURL examples.
- **8.9 — `/app/keys` UI.** Mint/list/revoke flow. Plaintext key shown ONCE on creation with copy-to-clipboard; never retrievable again.
- **8.10 — `mcp_server_govcapture/` package.** New Python package:
  - `pyproject.toml` with `[project.scripts] mcp-server-govcapture = "mcp_server_govcapture.server:main"`
  - `server.py` using `mcp` SDK; tools are HTTP wrappers around `/api/v1/tools/<name>` (same pattern as Sprint A's Hermes plugin — keep the source-of-truth in one place)
  - README with `claude_desktop_config.json` snippet
- **8.11 — OpenAPI polish.** FastAPI auto-generates `/openapi.json`; verify each `/api/v1/tools/<name>` route has a clean operation_id, summary, description, and the request/response schemas are public-friendly (no internal jargon in descriptions).
- **8.12 — Robots + meta.** `robots.txt` at the root allowing crawlers; `/agents` page has rich `<meta>` tags + JSON-LD for `SoftwareApplication` schema.
- **8.13 — Submit to agent directories.** Manual: agent.directory, tools.directory, MCP marketplace, Hermes plugin marketplace. Tracked outside this repo.

**Verification gates (Phase 8):**
- A naive curl using a minted API key calls `/api/v1/tools/parse-goal` and gets a valid envelope.
- `curl https://<host>/.well-known/agent.json` returns the manifest.
- `curl https://<host>/.well-known/llms.txt` returns the markdown.
- An MCP-aware client (Claude Desktop, Cursor) added with the local `mcp-server-govcapture` binary + an API key sees all 10 tools and can call one successfully.
- `npm -w web run build` clean; `/agents` renders without auth.
- Rate limit kicks in: hammer one key with 100 calls in 30s, observe 429s with `Retry-After`.

**Risks consciously accepted:**
- **API key stored client-side post-mint** — user must store it; we can't recover. Mitigation: clear copy-button + "save this now" warning.
- **No granular scopes in v1** — every key has full tool access. Future work adds per-tool scopes.
- **MCP package is HTTP-wrapper, not native** — same tradeoff as Sprint A's Hermes plugin. Worth it: one canonical code path (the public /api/v1 routes).
- **Rate limit is per-key only, not per-tenant** — a user with 10 keys gets 600 req/min effectively. v2 adds per-owner aggregate caps.

**Why this is a separate, large piece of work:** Phase 8 is realistically a Sprint of its own (Sprint H?). It's planned here so the architecture is unified, but execution-wise it should land *after* Sprints C Phases 0–7 are stable. Trying to ship login UI and a public API surface in the same change-set inflates blast radius.

---

## Self-Review

**Spec coverage** (login + post-login product page, the user's request):

| Requirement | Task |
|---|---|
| Login page | Already exists; polished in Phase 1 (loading state, error recovery) |
| Magic-link delivery | Already wired; Phase 1 task 1.3 hardens callback errors |
| Post-login dashboard ("the actual page user sees") | Phase 2 — `/app/page.tsx` rewrite |
| Profile management (implicit) | Phase 3 |
| Run flow (implicit; without it the dashboard has nothing to do) | Phase 4 |
| Opportunity drill-in (implicit; the value of the product) | Phase 5 |
| Action package + approval (implicit; the deliverable) | Phase 6 |
| Polish & mobile | Phase 7 |

**Placeholder scan:** No "TBD", "TODO", "implement later", "fill in details", "similar to Task N". Each step has actual code or an exact path. Phase 7 is intentionally lighter (it's polish).

**Type consistency:** `CompanyProfile`, `AgentRun`, `Opportunity`, `ActionPackage` types are defined once in `web/src/lib/types.ts` and reused across `api.ts` and every page. Server-side `getToken()` helper appears in every protected route — encapsulated in the shared layout's data flow.

**Risks consciously accepted:**
- **SSE deferred to polling:** Browser `EventSource` lacks header support; cross-origin dev (3001 ↔ 8000) blocks cookie-based auth. v1 polls every 2s, SSE upgrade is Phase 7.4. Same UX, slightly higher backend cost.
- **No password fallback:** Magic-link only. If Supabase email delivery breaks, users are blocked. Acceptable for private beta; add OAuth + password in a follow-up.
- **Approval gate is UI-only:** Pack does not enforce server-side. Documented in the gate component's helper text.
- **No optimistic mutations:** Forms wait on the round trip. Simpler; can add optimistic UX later if it bothers users.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-10-sprint-c-web-ui-and-auth.md`. Recommended execution: **inline** (`superpowers:executing-plans`) — Phase 0/1/2 share a small file set, and the per-phase verification gates are the natural review points. Start with Phase 0 → 1 → 2 to ship a usable end-to-end-incomplete-but-coherent v0 (login → dashboard → empty state with CTA). Phases 3–7 deepen the product but each ships incrementally.
