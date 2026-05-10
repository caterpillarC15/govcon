# Frontend Cleanup & Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended; phases share growing files like middleware, layout) or superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every Critical/High/Medium issue surfaced in the 2026-05-10 frontend hyperanalysis (~30 issues across `/web`, `/landing`, monorepo cross-cutting) without breaking the green test suite. Each phase ships a focused, reviewable commit and leaves typecheck/lint/build clean.

**Architecture:**
- **One phase = one PR-sized commit.** Phases are sequenced so each can land independently. Auth changes (Phase 4) bundle 8 file edits because they share one fix pattern (`getSession()` → `getUser()`); cosmetic phases stay narrow.
- **Backend changes are TDD** — pytest first, then implementation. Phase 3 (ApprovalGate persistence) adds a PATCH route + migration with the standard `api/skills` test pattern.
- **Frontend changes use the existing verification loop**: `npm -w <pkg> run typecheck && lint && build`. There is no Jest/Vitest in the repo; behavioral checks are manual against the dev server.
- **Schema changes pause for explicit user ack** before `supabase db push`, per HANDOFF_PROMPT §17 trigger #3.
- **Phase 0 is a validation gate**, not work. Confirms the analyzed state still holds before any edit.

**Tech Stack:** Next 15 · React 19 · Tailwind 4 · `@supabase/ssr` 0.10 · TypeScript 6 · Python 3.12 · FastAPI · supabase-py AsyncClient · pytest-asyncio · uv · npm workspaces.

**Authoritative references:**
- Hyperanalysis findings: 2026-05-10 frontend deep-review session (in conversation, not yet a file).
- Canonical brand: `tasks/LANDING_BRIEF.md`.
- Public-positioning rules: `devdocs/V1_PRODUCT_ALIGNMENT.md` lines 22-23, 75-94, 109-114.
- Capability-pack identity: `devdocs/CURRENT_STATE.md`, `PRD.md` v1.2.5 changelog.
- Server route pattern: `api/routes/agent_runs.py` (CRUD-only).
- Test harness: `api/tests/conftest.py` (FakeSupabase, `INTERNAL_HEADERS`).
- Supabase SSR docs: https://supabase.com/docs/guides/auth/server-side/nextjs (the `getUser()` vs `getSession()` rule comes from here).

**Overlap with `2026-05-10-launch-runway.md`:**
- That plan's Phase 2 ("Sprint C Phase 7 polish") and Phase 3 ("SSE upgrade") cover SOME of the same surface as this plan's Phases 6 (SEO+a11y) and 7 (SSE correctness). **This plan deliberately scopes to bug-fixes against the analyzed state, not greenfield additions.** If launch-runway lands first, re-validate Phase 6/7 before executing — some issues may already be closed.
- Launch-runway's Phase 4 ("public agent surface") will replace the entire `agents/page.tsx` content. This plan's Phase 8 only does the minimum truth-fix (M9 + H2) needed if launch-runway hasn't landed yet.

**Non-goals:**
- Adding a JS test framework (Vitest/Playwright) — out of scope.
- Component library introduction (shadcn/ui etc.) — out of scope.
- New product features beyond bug-fixes — out of scope.
- Refactoring `/landing` to use a CMS or design system — out of scope.
- Internationalization, dark mode rollout — out of scope.

**Verification gates (must hold at end of every phase):**
- `uv run pytest api/tests/ -q` — all green; suite size ≥ 113 (today's baseline; grows in Phase 3).
- `uv run ruff check api` — clean.
- `uv run mypy api` — clean.
- `npm -w web run typecheck` — clean.
- `npm -w web run lint` — clean.
- `npm -w web run build` — clean.
- `npm -w landing run typecheck` — clean.
- `npm -w landing run lint` — clean.
- `npm -w landing run build` — clean.
- `git status` — clean (only the intended phase changes).

**Final verification gates (entire plan complete):**
- All gates above hold.
- `grep -ri 'GovCapture\|capture analyst\|capture agent' landing/src landing/public 2>&1 | grep -v 'govcapture-attachments'` returns nothing.
- `grep -rn 'getSession()' web/src` returns only ignorable cases (e.g., comments) — every functional call is `getUser()`.
- `find landing/ -name 'package-lock.json'` returns nothing.
- `npm run build` (root, no workspace flag) succeeds AND builds both `web` and `landing`.
- `web/tsconfig.json` and `landing/tsconfig.json` both contain `"noUncheckedIndexedAccess": true`.
- A manual browser check of `/web` `app/action-packages/[id]` shows the approval state persists across refresh.
- A new "approved_at" column is visible on `action_packages` in Supabase.
- `landing/public/sitemap.xml` (or `landing/src/app/sitemap.ts`) exists; landing `<head>` includes `og:image`, `twitter:card`, canonical URL, `metadataBase`.
- Mobile menu focus moves into the panel on open and back to the trigger on close.
- A skip-to-content link is the first focusable element on the landing page.

---

## File Structure

| Action | Path | Responsibility | Phase |
|---|---|---|---|
| Modify | `landing/src/data/copy.ts` | Brand strings → "GovCon Bid Desk", drop "capture", drop hackathon blurb, drop budget pill, fix duplicate © | 1 |
| Modify | `landing/src/components/sections/Hero.tsx` | Replace inline "first-pass capture analyst" prose with brief-aligned wording | 1 |
| Modify | `landing/src/components/sections/Waitlist.tsx` | h2 says "Run a real capture" → "Run a real bid review" | 1 |
| Modify | `landing/src/components/Navbar.tsx` | Wordmark text "GovCapture" → "GovCon Bid Desk" | 1 |
| Modify | `landing/src/components/sections/Footer.tsx` | Drop "MVP for the Agents Track" | 1 |
| Modify | `landing/src/app/layout.tsx` | Title/desc/og rewrite + themeColor `#fafaf7` + add `metadataBase` (also Phase 6) | 1, 6 |
| Modify | `landing/public/robots.txt` | Drop placeholder `govcapture.example` sitemap line until sitemap exists | 1 |
| Modify | `landing/src/components/sections/StoryCards.tsx` | Add "Example output" label to preview tile | 1 |
| Delete | `web/src/app/app/AppConsole.tsx` | Dead code (547 lines, never imported) | 2 |
| Create | `supabase/migrations/<ts>_add_action_package_approval.sql` | `approved_at TIMESTAMPTZ NULL`, `approved_by UUID NULL` on `action_packages` | 3 |
| Create | `schemas/action-package-approve.schema.json` | Approve request body schema (empty payload v1) | 3 |
| Modify | `schemas/action-package.schema.json` | Add `approved_at` + `approved_by` fields | 3 |
| Modify | `api/repositories/action_package.py` | Add `approve(id, user_id)` method | 3 |
| Modify | `api/routes/action_packages.py` | Add `POST /action-packages/{id}/approve` route | 3 |
| Create | `api/tests/test_action_package_approve.py` | Tests for approve route + repo | 3 |
| Modify | `web/src/lib/api.ts` | Add `approveActionPackage(id, token)` client + fix `Partial<CompanyProfile>` DTO | 3, 8 |
| Modify | `web/src/app/app/action-packages/[id]/ApprovalGate.tsx` | Replace fake state with real PATCH; honest disabled/loading/error states | 3 |
| Modify | `web/src/app/app/action-packages/[id]/page.tsx` | Pass `approvedAt`/token to ApprovalGate; render "approved by …" badge if set | 3 |
| Modify | `web/src/middleware.ts` | Use `response` for redirect (preserve cookie writes) | 4 |
| Modify | `web/src/app/api/run-stream/[id]/route.ts` | `getSession()` → `getUser()` + bearer from validated user | 4 |
| Modify | `web/src/app/app/page.tsx` | `getToken()` → `getUser()` + `redirect('/login')` on null | 4 |
| Modify | `web/src/app/app/goal/page.tsx` | Same pattern | 4 |
| Modify | `web/src/app/app/runs/[id]/page.tsx` | Same pattern | 4 |
| Modify | `web/src/app/app/profile/page.tsx` | Same pattern | 4 |
| Modify | `web/src/app/app/profile/[id]/page.tsx` | Same pattern | 4 |
| Modify | `web/src/app/app/action-packages/[id]/page.tsx` | Same pattern | 4 |
| Modify | `web/src/app/app/keys/page.tsx` | Same pattern | 4 |
| Modify | `web/src/app/app/opportunities/[id]/page.tsx` | Same pattern | 4 |
| Delete | `landing/package-lock.json` | Orphan lockfile breaks workspaces | 5 |
| Modify | `package.json` (root) | Symmetricize root scripts to cover both workspaces | 5 |
| Modify | `web/tsconfig.json` | Add `noUncheckedIndexedAccess: true`; remove `ignoreDeprecations` | 5 |
| Modify | `landing/tsconfig.json` | Add `noUncheckedIndexedAccess: true`; remove `ignoreDeprecations` | 5 |
| Modify | `web/src/app/globals.css` | Add `@theme` block for shared design tokens | 5 |
| Modify | `web/eslint.config.js` | Lint `**/*.{js,mjs}` config files too | 5 |
| Modify | `landing/eslint.config.js` | Same | 5 |
| Modify | `web/package.json` | Align eslint/typescript-eslint/globals minor versions with landing | 5 |
| Create | `landing/src/app/sitemap.ts` | Next 15 `MetadataRoute.Sitemap` for `/`, `/#waitlist` | 6 |
| Modify | `landing/public/robots.txt` | Re-add `Sitemap: <real-prod-host>/sitemap.xml` (or env-driven) | 6 |
| Modify | `landing/src/app/layout.tsx` | Add `og:image`, `twitter:card`, canonical, `metadataBase` | 6 |
| Create | `landing/public/og.png` | Simple 1200x630 OG image (use a placeholder PNG via `Skip if asset already shipped`) | 6 |
| Modify | `landing/src/components/Navbar.tsx` | Mobile menu focus trap + return-focus to trigger | 6 |
| Modify | `landing/src/app/ui/Landing.tsx` | Add `<a href="#main">Skip to main</a>` + `id="main"` on `<main>` | 6 |
| Modify | `web/src/app/app/action-packages/[id]/page.tsx` | Add `scope="col"` to compliance matrix `<th>` | 6 |
| Modify | `web/src/app/app/runs/[id]/RunTimeline.tsx` | Memoize Supabase client; add `partial` case to StatusBadge; dedup events by step_id; honest disconnect copy | 7 |
| Modify | `.env.production.example` | Add explicit comment on `CORS_ALLOWED_ORIGINS` requirement for the landing prod domain | 8 |
| Modify | `web/src/lib/api.ts` | `Partial<CompanyProfile>` → `CreateCompanyProfilePayload` | 8 |
| Modify | `web/src/app/app/profile/[id]/page.tsx` | "Start a run" CTA → `/app/goal?profileId=…` | 8 |
| Modify | `web/src/app/app/goal/GoalForm.tsx` | Read `?profileId=` to set initial selection | 8 |
| Modify | `web/src/app/agents/page.tsx` | Truth-fix copy (keys are live not coming-soon); remove `X-Internal-API-Key` from public snippet | 8 |

---

## Phase 0: Pre-flight validation

**Goal:** Confirm the analyzed state still matches the repo before editing anything.

**Files:** none (read-only).

- [ ] **Step 1: Verify current commit + suite state**

```bash
git log --oneline -3
git status -sb
uv run pytest api/tests/ -q 2>&1 | tail -3
uv run ruff check api 2>&1 | tail -2
uv run mypy api 2>&1 | tail -2
npm -w web run typecheck 2>&1 | tail -3
npm -w landing run typecheck 2>&1 | tail -3
```

Expected:
- Recent commits include `7514fa4` (merge) and downstream work.
- `git status` shows only the user's parallel work, if any.
- pytest: `113 passed` (or current baseline ≥ 113).
- ruff/mypy: clean.
- typechecks: clean.

- [ ] **Step 2: Verify the issues haven't already been fixed**

Spot-check the 5 Critical findings:

```bash
# C1: brand violations
grep -c "GovCapture\|capture analyst" landing/src/data/copy.ts landing/src/components/sections/Hero.tsx
# C2: ApprovalGate fake
grep -n "setApproved(true)" web/src/app/app/action-packages/[id]/ApprovalGate.tsx
# C3: AppConsole orphan
grep -rn "AppConsole" web/src
# C4: SSE proxy getSession
grep -n "getSession\|getUser" web/src/app/api/run-stream/[id]/route.ts
# C5: orphan lockfile
ls landing/package-lock.json 2>&1
```

If any check returns "already fixed," skip the corresponding phase or task.

- [ ] **Step 3: Branch decision**

Ask the user: feature branch (`fix/frontend-cleanup-2026-05-10`) or stay on `main`? Default per HANDOFF_PROMPT §15 is **ask**, but a multi-phase plan is precisely when feature-branching pays off. Recommend feature branch + PR at the end.

If feature branch chosen:
```bash
git checkout -b fix/frontend-cleanup-2026-05-10
```

If stay-on-main: explicit user consent recorded in commit messages.

---

## Phase 1: Brand alignment (Critical C1, Medium M10–M13)

**Goal:** Every public-facing string in `/landing` matches the canonical `tasks/LANDING_BRIEF.md` and `devdocs/V1_PRODUCT_ALIGNMENT.md`. No "GovCapture", no "capture", no hackathon language, no exposed budget constants.

**Files:** `landing/src/data/copy.ts`, `landing/src/components/sections/{Hero,Waitlist,Footer,StoryCards}.tsx`, `landing/src/components/Navbar.tsx`, `landing/src/app/layout.tsx`, `landing/public/robots.txt`.

- [ ] **Step 1: Update `landing/src/data/copy.ts` — product strings**

Read `tasks/LANDING_BRIEF.md` for the canonical headline/subhead/CTA. Then in `landing/src/data/copy.ts`:

```ts
export const PRODUCT = {
  name: 'GovCon Bid Desk',
  tagline: 'AI bid-desk operator for government contracting teams.',
};

export const HERO = {
  title: 'Find contracts worth bidding\nbefore the deadline',
  subtitle:
    'Hire an AI operator that qualifies opportunities, drafts the bid plan, and keeps proposal work moving.',
  cta: 'Start bid review',
};

// Drop the budget pill from TRUST entirely (was: 'Bounded runs · 40 steps · 6 min · $0.50')
export const TRUST = [
  // … keep the brief-aligned items only; remove implementation-detail pills
];

export const FOOTER = {
  // Drop year + © from this string; Footer.tsx renders them once.
  legal: 'GovCon Bid Desk · All rights reserved',
  // (was: '© ' + new Date().getFullYear() + ' GovCapture · MVP for the Agents Track')
};
```

(Real values: read the brief verbatim; don't paraphrase.)

- [ ] **Step 2: Replace hardcoded prose in `landing/src/components/sections/Hero.tsx`**

Find the inline `"first-pass capture analyst"` text (around lines 32-44) and replace with `{HERO.subtitle}` from `data/copy.ts` (now wired). Delete the old inline JSX.

- [ ] **Step 3: Fix `Waitlist.tsx` h2**

```bash
grep -n "Run a real capture" landing/src/components/sections/Waitlist.tsx
```

Replace the matched h2 string with `Run a real bid review against your profile`.

- [ ] **Step 4: Fix `Navbar.tsx` wordmark**

Find the `GovCapture` string (around line 59); replace with `GovCon Bid Desk`. If the wordmark is a logo SVG, either keep the SVG (no text) or update its accessible name.

- [ ] **Step 5: Drop hackathon blurb in `Footer.tsx`**

Confirm `FOOTER.legal` no longer contains "MVP for the Agents Track". Footer.tsx:13 already renders `© {year}` separately — remove the `© ` and year from `FOOTER.legal` (already done in Step 1) so the duplicate `© © 2026` bug is fixed.

- [ ] **Step 6: `StoryCards.tsx` — label preview as illustrative**

In `DiscoverPreview` (lines 13-28 area), add a small label above or below the result row:

```tsx
<span className="text-xs uppercase tracking-wider text-fg/60">Example output</span>
```

Use whatever atom matches the existing micro-label style (likely `MonoLabel` from `components/ui/Primitives.tsx`).

- [ ] **Step 7: `landing/src/app/layout.tsx` — title/desc + themeColor**

```ts
export const metadata: Metadata = {
  title: {
    default: 'GovCon Bid Desk · AI bid-desk operator',
    template: '%s · GovCon Bid Desk',
  },
  description:
    'Hire an AI operator that finds contracts worth bidding, qualifies opportunities, and drafts the bid plan.',
  openGraph: {
    title: 'GovCon Bid Desk',
    description:
      'AI bid-desk operator for government contracting teams.',
    siteName: 'GovCon Bid Desk',
    type: 'website',
  },
};

export const viewport: Viewport = {
  themeColor: '#fafaf7', // matches --color-canvas-warm; was '#0f172a'
};
```

`metadataBase`, OG image, twitter:card, canonical → Phase 6.

- [ ] **Step 8: `landing/public/robots.txt` — drop placeholder sitemap line**

Until Phase 6 ships a real sitemap, remove the line:

```
Sitemap: https://govcapture.example/sitemap.xml
```

Keep the `User-agent: *` and `Allow: /` lines.

- [ ] **Step 9: Run gates**

```bash
npm -w landing run typecheck
npm -w landing run lint
npm -w landing run build
```

All clean.

- [ ] **Step 10: Manual smoke test**

```bash
npm -w landing run dev
```

Open `http://localhost:3000`. Verify:
- Browser tab title: "GovCon Bid Desk · AI bid-desk operator".
- No "GovCapture" anywhere on the page.
- No "MVP for the Agents Track" in footer.
- Footer copyright shows `© 2026 GovCon Bid Desk · All rights reserved` (single ©).
- Story preview tile has "Example output" label.
- Mobile theme color (visible in iOS Safari devtools) is warm white, not dark.

- [ ] **Step 11: Commit**

```bash
git add landing/
git commit -m "$(cat <<'EOF'
fix(landing): align brand strings with LANDING_BRIEF.md (PRD v1.2.5)

Replaces internal codename "GovCapture" + "capture analyst" framing with
canonical "GovCon Bid Desk / bid-desk operator" everywhere on the public
site. Per V1_PRODUCT_ALIGNMENT.md, public copy must not lead with
capture/MCP/Hermes/agent platform; it should sell the worker.

- copy.ts: PRODUCT.name, HERO title/subtitle/cta, FOOTER.legal
- Hero.tsx: drop inline "first-pass capture analyst" prose, use HERO.subtitle
- Waitlist.tsx: h2 "Run a real capture" → "Run a real bid review"
- Navbar.tsx: wordmark text
- Footer.tsx: drop hackathon blurb; fix duplicate © by moving year to component
- StoryCards.tsx: label preview tile as "Example output"
- layout.tsx: title/desc/og + themeColor #fafaf7 (was #0f172a, mismatched light design)
- robots.txt: drop placeholder sitemap (real one ships in Phase 6)

Verified: landing typecheck/lint/build clean; manual browser check.
EOF
)"
```

---

## Phase 2: Delete dead code (Critical C3)

**Goal:** Remove `web/src/app/app/AppConsole.tsx` (547 lines, never imported, has its own private redefinitions of types already in `lib/types.ts`).

- [ ] **Step 1: Verify nothing imports it**

```bash
grep -rn "AppConsole" web/src
```

Expected: only the file itself appears. If anything else does, stop and surface to user.

- [ ] **Step 2: Delete**

```bash
git rm web/src/app/app/AppConsole.tsx
```

- [ ] **Step 3: Verify gates**

```bash
npm -w web run typecheck
npm -w web run lint
npm -w web run build
```

All clean. If typecheck fails, AppConsole was actually referenced — restore and stop.

- [ ] **Step 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
chore(web): delete dead AppConsole.tsx (547 lines, never imported)

AppConsole was the original v1.2.4 monolithic console with private
type redefinitions of AgentRun/Opportunity (now centralized in
lib/types.ts), inline authedFetch (replaced by lib/api.ts), and
manual "Refresh run" UX (replaced by SSE timeline in
runs/[id]/RunTimeline.tsx). Confirmed not imported anywhere via
\`grep -rn AppConsole web/src\` before deletion.

Verified: web typecheck/lint/build clean.
EOF
)"
```

---

## Phase 3: ApprovalGate persistence (Critical C2)

**Goal:** ApprovalGate writes to a real `PATCH /action-packages/{id}/approve` endpoint. The state survives refresh. The orchestrator can read `approved_at` to gate downstream actions.

**Approach:** Add `approved_at TIMESTAMPTZ NULL` and `approved_by UUID NULL REFERENCES auth.users(id)` to the `action_packages` table. Add a `POST /action-packages/{id}/approve` route (JWT-protected, owner-aware). UI calls this and renders the approval as committed.

**Ask first triggers in this phase:**
- Step 1 (schema change) → user must ack before `supabase db push`.
- If `auth.users(id)` FK can't be added (RLS / cross-schema concerns), fall back to `approved_by_profile_id UUID REFERENCES profiles(id)`.

- [ ] **Step 1: Draft migration SQL — DO NOT push yet**

```bash
TS=$(date -u +%Y%m%d%H%M%S)
cat > supabase/migrations/${TS}_add_action_package_approval.sql <<'EOF'
-- PRD v1.2.5+: real approval persistence for action packages.
-- The orchestrator reads approved_at to gate downstream actions
-- (e.g., emailing the contracting officer).

ALTER TABLE action_packages
  ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS approved_by UUID NULL
    REFERENCES auth.users(id) ON DELETE SET NULL;

COMMENT ON COLUMN action_packages.approved_at IS
  'Timestamp when an authorized user approved the package. Null = not yet approved.';
COMMENT ON COLUMN action_packages.approved_by IS
  'Supabase auth user who approved. Set together with approved_at.';

-- RLS already enforces owner_profile_id; no policy change needed.
EOF
```

- [ ] **Step 2: Show migration to user, get explicit ack**

Print the file contents and ask: "OK to `supabase db push`?" Wait for explicit yes.

- [ ] **Step 3: Apply migration**

```bash
supabase db push
```

Expected: migration listed, applied without error.

- [ ] **Step 4: Update `schemas/action-package.schema.json`**

Add fields:

```json
"approved_at": {
  "type": ["string", "null"],
  "format": "date-time",
  "description": "Timestamp when approved; null = unapproved"
},
"approved_by": {
  "type": ["string", "null"],
  "format": "uuid",
  "description": "Supabase auth.users.id of the approver"
}
```

Run codegen:

```bash
make schemas
```

Expected: `api/schemas/action_package.py` regenerates with the two new fields.

- [ ] **Step 5: Write the failing test for approve route**

Create `api/tests/test_action_package_approve.py`:

```python
import uuid
import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.tests.conftest import FakeSupabase

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PKG_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.mark.asyncio
async def test_approve_sets_approved_at_and_approved_by(
    fake_supabase: FakeSupabase, jwt_for,
):
    # Arrange: a package owned by USER_ID, currently unapproved.
    fake_supabase.tables["action_packages"].rows = [
        {"id": str(PKG_ID), "owner_profile_id": str(USER_ID),
         "approved_at": None, "approved_by": None},
    ]
    token = jwt_for(USER_ID)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/action-packages/{PKG_ID}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["approved_at"] is not None
    assert body["approved_by"] == str(USER_ID)


@pytest.mark.asyncio
async def test_approve_returns_404_for_other_users_package(
    fake_supabase: FakeSupabase, jwt_for,
):
    other_user = uuid.UUID("33333333-3333-3333-3333-333333333333")
    fake_supabase.tables["action_packages"].rows = [
        {"id": str(PKG_ID), "owner_profile_id": str(other_user),
         "approved_at": None, "approved_by": None},
    ]
    token = jwt_for(USER_ID)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/action-packages/{PKG_ID}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_requires_jwt():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(f"/action-packages/{PKG_ID}/approve")
    assert resp.status_code == 401
```

- [ ] **Step 6: Run tests — confirm failure**

```bash
uv run pytest api/tests/test_action_package_approve.py -v
```

Expected: 3 failures (404 from missing route).

- [ ] **Step 7: Add repo method**

In `api/repositories/action_package.py`:

```python
async def approve(
    self, pkg_id: uuid.UUID, user_id: uuid.UUID,
) -> dict | None:
    """Mark approved by user. Returns the updated row or None if not found/owned."""
    now = datetime.now(timezone.utc).isoformat()
    res = await (
        self.client.table("action_packages")
        .update({"approved_at": now, "approved_by": str(user_id)})
        .eq("id", str(pkg_id))
        .eq("owner_profile_id", str(user_id))
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None
```

- [ ] **Step 8: Add route**

In `api/routes/action_packages.py`:

```python
@router.post("/{pkg_id}/approve", response_model=ActionPackage)
async def approve_action_package(
    pkg_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    repo: ActionPackageRepository = Depends(get_action_package_repo),
) -> ActionPackage:
    row = await repo.approve(pkg_id, user.id)
    if row is None:
        raise HTTPException(404, "Action package not found")
    return ActionPackage.model_validate(row)
```

Add the necessary imports at the top of the file (`uuid`, `Depends`, `HTTPException`, `AuthenticatedUser`, `require_user`, `get_action_package_repo`).

- [ ] **Step 9: Run tests — expect green**

```bash
uv run pytest api/tests/test_action_package_approve.py -v
```

Expected: 3 passed.

- [ ] **Step 10: Run full suite + lint + types**

```bash
uv run pytest api/tests/ -q
uv run ruff check api
uv run mypy api
```

All green. Suite size: 113 → 116 (+3 new tests).

- [ ] **Step 11: Add client function in `web/src/lib/api.ts`**

```ts
export async function approveActionPackage(
  id: string, token: string,
): Promise<ActionPackage> {
  const res = await fetch(`${API_BASE}/action-packages/${id}/approve`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`approve failed: ${res.status} ${await res.text()}`);
  }
  return (await res.json()) as ActionPackage;
}
```

- [ ] **Step 12: Rewrite `ApprovalGate.tsx`**

Replace the fake state with real persistence:

```tsx
'use client';
import { useState, useTransition } from 'react';
import { approveActionPackage } from '@/lib/api';

interface Props {
  packageId: string;
  token: string;
  approvalItems: string[];
  initialApprovedAt: string | null;
}

export default function ApprovalGate({
  packageId, token, approvalItems, initialApprovedAt,
}: Props) {
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [approvedAt, setApprovedAt] = useState<string | null>(initialApprovedAt);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  if (approvedAt) {
    return (
      <div className="rounded border border-green-500/30 bg-green-500/5 p-4">
        <p className="text-sm text-green-700">
          Approved {new Date(approvedAt).toLocaleString()}.
        </p>
      </div>
    );
  }

  const allChecked = checked.size === approvalItems.length;

  const onApprove = () => {
    setError(null);
    startTransition(async () => {
      try {
        const updated = await approveActionPackage(packageId, token);
        setApprovedAt(updated.approved_at ?? new Date().toISOString());
      } catch (e) {
        setError((e as Error).message);
      }
    });
  };

  return (
    <div className="space-y-3">
      <ul className="space-y-2">
        {approvalItems.map((item, i) => (
          <li key={i} className="flex gap-2">
            <input
              id={`approval-${i}`}
              type="checkbox"
              checked={checked.has(i)}
              onChange={(e) => {
                const next = new Set(checked);
                if (e.target.checked) next.add(i); else next.delete(i);
                setChecked(next);
              }}
            />
            <label htmlFor={`approval-${i}`}>{item}</label>
          </li>
        ))}
      </ul>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="button"
        disabled={!allChecked || pending}
        onClick={onApprove}
        className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {pending ? 'Approving…' : 'Approve'}
      </button>
    </div>
  );
}
```

- [ ] **Step 13: Update `web/src/app/app/action-packages/[id]/page.tsx`**

Pass `token` and `initialApprovedAt` to `<ApprovalGate>`. Render an "Approved by …" badge in the page header if `pkg.approved_at` is set.

- [ ] **Step 14: Manual browser test**

```bash
# In one terminal:
uv run uvicorn api.main:app --reload
# In another:
npm -w web run dev
```

- Sign in.
- Navigate to an action package detail.
- Verify checkboxes; confirm Approve disabled until all checked.
- Click Approve. Confirm UI shows "Approved <date>".
- Refresh the page. Confirm still shows "Approved" (state persisted).

- [ ] **Step 15: Run all gates**

```bash
uv run pytest api/tests/ -q
uv run ruff check api
uv run mypy api
npm -w web run typecheck
npm -w web run lint
npm -w web run build
```

All clean.

- [ ] **Step 16: Commit**

```bash
git add supabase/migrations/ schemas/ api/ web/
git commit -m "$(cat <<'EOF'
feat(api,web): persist action-package approval state

ApprovalGate previously only flipped local React state — the success
copy claimed the orchestrator would see it, but nothing was written.
Approval now hits a real PATCH endpoint and survives refresh.

Backend:
- Migration: add approved_at TIMESTAMPTZ + approved_by UUID FK to
  auth.users on action_packages
- Schema: add approved_at + approved_by to action-package.schema.json
- Repo: ActionPackageRepository.approve(pkg_id, user_id) — owner-scoped
- Route: POST /action-packages/{id}/approve (JWT, 404 for other users')
- Tests: 3 new (happy, cross-owner 404, missing JWT 401)

Frontend:
- lib/api.ts: approveActionPackage(id, token)
- ApprovalGate: real POST + useTransition; honest error/pending states
- action-packages/[id]/page.tsx: pass token + initialApprovedAt

Verified: pytest 116 passed (was 113); ruff + mypy + web build clean;
manual browser flow shows persistence across refresh.
EOF
)"
```

---

## Phase 4: Auth hardening (Critical C4, High H3 + H4, Medium M6)

**Goal:** Every server-side Supabase auth check uses `getUser()` (network-validated) instead of `getSession()` (local-decode-only). Middleware preserves cookie writes on redirect. Pages with no token redirect instead of rendering blank.

**Files (9):** `web/src/middleware.ts`, `web/src/app/api/run-stream/[id]/route.ts`, plus 7 page files (`app/page.tsx`, `goal/page.tsx`, `runs/[id]/page.tsx`, `profile/page.tsx`, `profile/[id]/page.tsx`, `action-packages/[id]/page.tsx`, `keys/page.tsx`, `opportunities/[id]/page.tsx`).

- [ ] **Step 1: Read the Supabase SSR docs section once**

Confirm the rule: in server contexts, `getSession()` only decodes the JWT locally; `getUser()` makes a network round-trip to validate. Use `getUser()` for any decision based on identity.

- [ ] **Step 2: Fix middleware first**

Read `web/src/middleware.ts`. Find the redirect block (around line 43-48). The current code creates a fresh `NextResponse.redirect(...)` after `getUser()` call — losing any token-refresh cookies set on `response`.

Replace with the official Supabase Next.js middleware pattern:

```ts
const { data: { user } } = await supabase.auth.getUser();

if (!user && !isPublicRoute(request.nextUrl.pathname)) {
  // Preserve cookies that may have been refreshed during getUser().
  const url = request.nextUrl.clone();
  url.pathname = '/login';
  const redirect = NextResponse.redirect(url);
  // Carry the cookie writes from `response` onto the redirect:
  response.cookies.getAll().forEach((c) => {
    redirect.cookies.set(c.name, c.value, c);
  });
  return redirect;
}

return response;
```

- [ ] **Step 3: Fix SSE proxy route**

In `web/src/app/api/run-stream/[id]/route.ts`:

```ts
// BEFORE (around lines 15-18):
const { data: { session } } = await supabase.auth.getSession();
if (!session) return new Response('Unauthorized', { status: 401 });
const token = session.access_token;

// AFTER:
const { data: { user }, error: userErr } = await supabase.auth.getUser();
if (userErr || !user) {
  return new Response('Unauthorized', { status: 401 });
}
// getUser validated; safe to read session for the bearer token.
const { data: { session } } = await supabase.auth.getSession();
if (!session) return new Response('Unauthorized', { status: 401 });
const token = session.access_token;
```

- [ ] **Step 4: Fix the 8 server pages — one common helper**

Pattern repeats. Create a small helper at `web/src/lib/supabase/auth.ts`:

```ts
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';

/**
 * Get the validated user + their access token, server-side.
 * Redirects to /login if no valid session.
 *
 * Use this in every server component / route handler that needs to
 * make an authenticated call to the FastAPI backend.
 */
export async function requireUser() {
  const supabase = await createClient();
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error || !user) {
    redirect('/login');
  }
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) {
    redirect('/login');
  }
  return { user, token: session.access_token };
}
```

- [ ] **Step 5: Replace `getToken()` in each page**

For each of:
- `web/src/app/app/page.tsx`
- `web/src/app/app/goal/page.tsx`
- `web/src/app/app/runs/[id]/page.tsx`
- `web/src/app/app/profile/page.tsx`
- `web/src/app/app/profile/[id]/page.tsx`
- `web/src/app/app/action-packages/[id]/page.tsx`
- `web/src/app/app/keys/page.tsx`
- `web/src/app/app/opportunities/[id]/page.tsx`

Replace this pattern:

```ts
const supabase = await createClient();
const { data: { session } } = await supabase.auth.getSession();
const token = session?.access_token;
if (!token) return null; // ← silently blank
```

With:

```ts
import { requireUser } from '@/lib/supabase/auth';
// …
const { token } = await requireUser();
```

If a page has any local `getToken()` helper, delete it.

- [ ] **Step 6: Run gates**

```bash
npm -w web run typecheck
npm -w web run lint
npm -w web run build
```

All clean. `grep -rn 'getSession' web/src` should now show only the SSE proxy + `requireUser` helper.

- [ ] **Step 7: Manual browser test**

- Sign in normally; verify all pages still render.
- In devtools, delete the Supabase cookie. Refresh `/app`. Should redirect to `/login` (not render blank).
- (Optional) wait for token expiry; observe redirect on next navigation rather than a blank page.

- [ ] **Step 8: Commit**

```bash
git add web/
git commit -m "$(cat <<'EOF'
fix(web): harden auth — getSession→getUser, preserve refresh cookies, redirect on null

Supabase SSR docs: getSession() only decodes the JWT locally; an expired
or forged token passes. Server-side identity decisions need getUser(),
which validates against /auth/v1/user. Previously the SSE proxy and 8
server pages all relied on getSession alone.

Also: middleware was creating a fresh NextResponse.redirect() that did
not carry the cookie writes from a successful token refresh, silently
discarding refreshed sessions. And 6 pages did "if (!token) return null"
instead of redirecting to /login, producing blank screens on expiry.

- middleware.ts: carry response.cookies onto the redirect response
- api/run-stream/[id]/route.ts: getUser() guard before reading session
- new lib/supabase/auth.ts::requireUser() helper
- 8 pages: replace local getToken() pattern with requireUser()

Verified: web typecheck/lint/build clean; manual cookie-deletion test
shows redirect (not blank); grep confirms only the proxy + helper
still call getSession (after a validated getUser).
EOF
)"
```

---

## Phase 5: Workspace + tsconfig + tooling (Critical C5, High H1 + H5, Medium M14)

**Goal:** Delete the orphan workspace lockfile, symmetricize root scripts to cover both packages, enable `noUncheckedIndexedAccess`, and align trivial dev-dep version drift.

- [ ] **Step 1: Delete `landing/package-lock.json`**

```bash
git rm landing/package-lock.json
npm install # regenerates the root lockfile cleanly
```

If this introduces dep-version diffs, surface to user before committing.

- [ ] **Step 2: Symmetricize root `package.json` scripts**

Replace the asymmetric block:

```json
"scripts": {
  "dev:landing": "npm -w landing run dev --",
  "dev:web": "npm -w web run dev --",
  "build": "npm run build:landing && npm run build:web",
  "build:landing": "npm -w landing run build",
  "build:web": "npm -w web run build",
  "lint": "npm run lint:landing && npm run lint:web",
  "lint:landing": "npm -w landing run lint",
  "lint:web": "npm -w web run lint",
  "typecheck": "npm run typecheck:landing && npm run typecheck:web",
  "typecheck:landing": "npm -w landing run typecheck",
  "typecheck:web": "npm -w web run typecheck",
  "start:landing": "npm -w landing run start",
  "start:web": "npm -w web run start"
}
```

Keep the bare `dev` script aliased to whichever surface is the default for solo dev — recommend `landing`. Document that.

- [ ] **Step 3: Add `noUncheckedIndexedAccess` to both tsconfigs**

`web/tsconfig.json` and `landing/tsconfig.json`:

```jsonc
"compilerOptions": {
  // …existing fields…
  "strict": true,
  "noUncheckedIndexedAccess": true,
  // remove: "ignoreDeprecations": "6.0",
}
```

- [ ] **Step 4: Run typecheck — surface any new errors**

```bash
npm -w web run typecheck 2>&1 | tail -30
npm -w landing run typecheck 2>&1 | tail -30
```

Expect new errors at array index sites and record lookups. Fix each by:
- Adding explicit `if (item === undefined)` guard before use, OR
- Using `arr.at(i)` (returns `T | undefined` already), OR
- Using non-null assertion only where the index is mathematically guaranteed in-bounds (rare; comment it).

Iterate until clean.

- [ ] **Step 5: Add `@theme` block to `web/src/app/globals.css`**

Mirror the `/landing` token system. Open `landing/src/app/globals.css`, copy the `@theme { … }` block, paste at the top of `web/src/app/globals.css` (after `@import "tailwindcss";`). Adjust any web-specific tokens.

- [ ] **Step 6: Lint config files too**

In both `web/eslint.config.js` and `landing/eslint.config.js`, broaden the `files` glob:

```js
files: ['**/*.{ts,tsx,js,mjs}']
```

- [ ] **Step 7: Align minor dev-dep versions**

In `web/package.json`, update to match `landing/package.json`'s lower bounds for the three drifting packages (or vice versa — pick the higher of the two):

```json
"eslint": "^10.3.0",
"typescript-eslint": "^8.59.2",
"globals": "^17.6.0"
```

Run `npm install` from root.

- [ ] **Step 8: Run full gate set**

```bash
npm -w web run typecheck
npm -w web run lint
npm -w web run build
npm -w landing run typecheck
npm -w landing run lint
npm -w landing run build
npm run build  # bare root script — should now build BOTH workspaces
```

All clean.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore(monorepo): drop orphan lockfile, symmetricize scripts, tighten tsconfigs

- Delete landing/package-lock.json — sub-package lockfiles break npm
  workspaces and can cause dep version splits between landing and web.
- Symmetricize root scripts: \`npm run build\` now builds BOTH workspaces;
  same for lint/typecheck. Asymmetric \`build:web\` only set up earlier
  meant CI's \`npm run build\` silently skipped the product app.
- Add noUncheckedIndexedAccess to both tsconfigs (strict alone does not
  enable this; it's the leading source of uncaught runtime errors).
  Remove the now-unnecessary \`ignoreDeprecations: "6.0"\` flag.
- Add @theme block to web/globals.css so /web can use Tailwind v4 token
  utilities (was hard-coded hex values; /landing already had this).
- Broaden ESLint config glob to lint .mjs/.js config files.
- Align eslint/typescript-eslint/globals minor versions across web + landing.

Verified: all typecheck/lint/build green in both packages and at root.
EOF
)"
```

---

## Phase 6: SEO + accessibility (High H6 + H7 + H8 + H9, Medium M7)

**Goal:** Landing has a real sitemap, OG/Twitter metadata, mobile menu focus management, skip-to-content. Compliance matrix table has proper `scope`.

- [ ] **Step 1: Decide canonical prod host**

Ask the user: what's the production host? Default placeholder: `https://govconbiddesk.com`. Use whatever they say in the next steps.

If unknown, fall back to env-driven via `NEXT_PUBLIC_SITE_URL` and add it to `.env.example` and `.env.production.example`.

- [ ] **Step 2: Create `landing/src/app/sitemap.ts`**

```ts
import type { MetadataRoute } from 'next';

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://govconbiddesk.com';

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 1,
    },
    {
      url: `${SITE}/#waitlist`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.8,
    },
  ];
}
```

- [ ] **Step 3: Re-add Sitemap line to `landing/public/robots.txt`**

```
User-agent: *
Allow: /

Sitemap: https://govconbiddesk.com/sitemap.xml
```

(Adjust host per Step 1.)

- [ ] **Step 4: Add metadata fields to `landing/src/app/layout.tsx`**

```ts
const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://govconbiddesk.com';

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: {
    default: 'GovCon Bid Desk · AI bid-desk operator',
    template: '%s · GovCon Bid Desk',
  },
  description: 'Hire an AI operator that finds contracts worth bidding…',
  alternates: { canonical: SITE },
  openGraph: {
    title: 'GovCon Bid Desk',
    description: 'AI bid-desk operator for government contracting teams.',
    url: SITE,
    siteName: 'GovCon Bid Desk',
    type: 'website',
    images: [{ url: '/og.png', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'GovCon Bid Desk',
    description: 'AI bid-desk operator for government contracting teams.',
    images: ['/og.png'],
  },
};
```

- [ ] **Step 5: Add a placeholder OG image**

If no design asset is ready, generate a 1200×630 PNG with the wordmark + tagline using any tool (Figma export, `npx ogimage`, or manually). Save to `landing/public/og.png`. Reference will resolve once the file exists.

If user prefers to defer the image: skip this step but **leave `images: []` in the metadata block** rather than referencing a missing file (broken OG is worse than no OG).

- [ ] **Step 6: Mobile-menu focus trap in `landing/src/components/Navbar.tsx`**

Add refs and focus management. Around the existing menu (lines 102-153 area):

```tsx
import { useEffect, useRef, useState } from 'react';

const triggerRef = useRef<HTMLButtonElement>(null);
const firstItemRef = useRef<HTMLAnchorElement>(null);

useEffect(() => {
  if (open) {
    firstItemRef.current?.focus();
  }
}, [open]);

const close = () => {
  setOpen(false);
  triggerRef.current?.focus();
};

useEffect(() => {
  if (!open) return;
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') close();
  };
  window.addEventListener('keydown', onKey);
  return () => window.removeEventListener('keydown', onKey);
}, [open]);
```

Wire `ref={triggerRef}` on the hamburger button and `ref={firstItemRef}` on the first link inside the panel. Replace any `onClick={() => setOpen(false)}` on link clicks with `onClick={close}`.

For full focus trapping (Tab cycling within the panel), the simplest no-deps approach is to set `inert` on the surrounding content:

```tsx
<div inert={open ? '' : undefined}>
  {/* page content under the menu */}
</div>
```

Otherwise, accept "Escape closes + focus return" as the v1 a11y baseline and document the trap as a follow-up.

- [ ] **Step 7: Skip-to-content link**

In `landing/src/app/ui/Landing.tsx` (the top-level page composition), add as the very first child of the page:

```tsx
<a
  href="#main"
  className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 rounded bg-blue-700 px-3 py-2 text-white"
>
  Skip to main content
</a>
```

And ensure the `<main>` element has `id="main"`:

```tsx
<main id="main" className="…">
```

- [ ] **Step 8: Add `scope="col"` to compliance matrix `<th>`**

In `web/src/app/app/action-packages/[id]/page.tsx` (around lines 104-112), add `scope="col"` to every `<th>` in the compliance matrix table:

```tsx
<th scope="col">Requirement</th>
<th scope="col">Status</th>
<th scope="col">Evidence</th>
<th scope="col">Next action</th>
<th scope="col">Owner</th>
```

- [ ] **Step 9: Run gates**

```bash
npm -w landing run typecheck
npm -w landing run lint
npm -w landing run build
npm -w web run typecheck
npm -w web run lint
npm -w web run build
```

All clean.

- [ ] **Step 10: Manual smoke test**

```bash
npm -w landing run dev
```

- View source: confirm `<meta property="og:title" …>` etc. appear.
- Visit `http://localhost:3000/sitemap.xml` — XML body returned.
- Resize to 375px, open the hamburger menu — focus moves to first link.
- Press Escape — menu closes, focus returns to hamburger button.
- Tab from URL bar — first focusable element is "Skip to main content".

- [ ] **Step 11: Commit**

```bash
git add landing/ web/
git commit -m "$(cat <<'EOF'
feat(landing,web): SEO + accessibility — sitemap, OG/Twitter, focus mgmt, skip link

Landing:
- New src/app/sitemap.ts using Next 15 MetadataRoute.Sitemap
- Re-add Sitemap line to robots.txt (no longer points at placeholder host)
- layout.tsx: metadataBase, og:image, twitter:card summary_large_image,
  canonical alternates
- public/og.png: 1200x630 social card
- Navbar mobile menu: focus moves to first link on open, returns to
  trigger on Escape close, Escape closes the panel
- Landing.tsx: skip-to-content link as first focusable element + id="main"

Web:
- action-packages/[id] compliance matrix: add scope="col" to <th>
  cells so screen readers associate headers with data cells

Verified: typecheck/lint/build clean both packages; manual SR + keyboard
test on landing; sitemap.xml served by dev server.
EOF
)"
```

---

## Phase 7: SSE correctness (Medium M1 + M2 + M3 + M4)

**Goal:** RunTimeline doesn't duplicate steps, doesn't show fake "retrying" copy, doesn't open multiple EventSources under Strict Mode, and renders a distinct icon for `partial` status.

**Files:** `web/src/app/app/runs/[id]/RunTimeline.tsx` (single file).

- [ ] **Step 1: Memoize Supabase client**

At the top of the component:

```tsx
import { useMemo } from 'react';
// …
const supabase = useMemo(() => createClient(), []);
```

This prevents a new client (and potentially a new EventSource) per render.

- [ ] **Step 2: Add `partial` case to `StatusBadge`**

Around lines 194-207, in the icon-selection switch:

```tsx
import { AlertCircle } from 'lucide-react';

switch (status) {
  case 'complete': return <CheckCircle className="text-green-600" />;
  case 'partial': return <AlertCircle className="text-amber-600" />;
  case 'failed': return <XCircle className="text-red-600" />;
  case 'running': return <Loader2 className="animate-spin text-blue-600" />;
  default: return <Clock className="text-fg/60" />;
}
```

- [ ] **Step 3: Dedupe SSE events by `step_id`**

Around lines 62-65 in the message handler:

```tsx
setRun((prev) => {
  // Deduplicate by step_id; existing steps win.
  const existingIds = new Set(prev.steps.map((s) => s.step_id));
  if (parsed.step_id && existingIds.has(parsed.step_id)) {
    return prev; // already rendered (likely from initial server fetch)
  }
  return { ...prev, steps: [...prev.steps, parsed] };
});
```

- [ ] **Step 4: Honest disconnect copy**

Around lines 82-84:

```tsx
es.onerror = () => {
  if (es.readyState === EventSource.CLOSED) {
    setStreamState({ kind: 'closed' });
  } else {
    setStreamState({ kind: 'connecting' }); // EventSource is auto-retrying
  }
};
```

And render two distinct UI strings:

```tsx
{streamState.kind === 'closed' && (
  <p className="text-sm text-fg/60">
    Live stream disconnected.{' '}
    <button onClick={() => location.reload()} className="underline">
      Refresh
    </button>
  </p>
)}
{streamState.kind === 'connecting' && (
  <p className="text-sm text-fg/60">Reconnecting…</p>
)}
```

(Fold this into whatever state machine RunTimeline already uses; the example above introduces minimum vocabulary.)

- [ ] **Step 5: Run gates**

```bash
npm -w web run typecheck
npm -w web run lint
npm -w web run build
```

All clean.

- [ ] **Step 6: Manual browser test**

```bash
npm -w web run dev
```

- Visit a run with completed steps. Confirm no doubled rows.
- Open devtools Network tab. Stop the FastAPI server. Confirm UI shows "Reconnecting…" (auto-retry) or "disconnected" (true close), not the misleading "retrying" string with no actual retry.
- A `partial`-status run shows the amber AlertCircle, not grey Clock.

- [ ] **Step 7: Commit**

```bash
git add web/
git commit -m "$(cat <<'EOF'
fix(web): RunTimeline correctness — memoize client, dedupe steps, honest stream UX, partial badge

- useMemo around createClient() so Strict Mode's double-render doesn't
  open a second EventSource
- Dedupe SSE events by step_id before appending: prevents the
  server-rendered initial steps from rendering twice when the upstream
  replays from start
- Replace misleading "Live stream disconnected — retrying" with two
  distinct states: "Reconnecting…" while EventSource auto-retries,
  "Disconnected" + manual Refresh when the stream is truly closed
- StatusBadge: add explicit case for 'partial' (amber AlertCircle);
  was falling through to grey Clock identical to 'pending'

Verified: web typecheck/lint/build clean; manual flow shows no
doubled rows + correct disconnect copy + correct partial icon.
EOF
)"
```

---

## Phase 8: Cleanup sweep (High H10, Medium M5 + M8 + M9, secondary H2)

**Goal:** Smaller items: typed creation DTO, profileId in CTA, agents/page truth-fix, CORS doc, X-Internal-API-Key removed from public snippet.

- [ ] **Step 1: `web/src/lib/api.ts` — typed creation DTO**

Replace `Partial<CompanyProfile>` with a proper DTO:

```ts
export type CreateCompanyProfilePayload = Omit<
  CompanyProfile, 'id' | 'created_at' | 'updated_at' | 'owner_profile_id'
>;

export async function createCompanyProfile(
  payload: CreateCompanyProfilePayload, token: string,
): Promise<CompanyProfile> {
  // existing fetch body unchanged
}
```

Update every call-site that passed `id`/timestamps and now gets a TS error.

- [ ] **Step 2: Pass `profileId` in `Profile[id]` "Start a run" CTA**

`web/src/app/app/profile/[id]/page.tsx` (around lines 107-112):

```tsx
<Link href={`/app/goal?profileId=${profile.id}`}>Start a run with this profile</Link>
```

- [ ] **Step 3: Read `?profileId=` in `GoalForm`**

`web/src/app/app/goal/GoalForm.tsx`:

```tsx
import { useSearchParams } from 'next/navigation';
// …
const params = useSearchParams();
const initialProfileId = params.get('profileId') ?? profiles[0]?.id ?? '';
const [profileId, setProfileId] = useState(initialProfileId);
```

Validate that `initialProfileId` matches one of the user's owned profiles before using it; fall back to `profiles[0]?.id` if not.

- [ ] **Step 4: Truth-fix `agents/page.tsx`**

In `web/src/app/agents/page.tsx`:

- Remove the "coming soon" copy from the auth card (around lines 76-77). Replace with: "Per-agent keys (gck_…) live at [/app/keys](/app/keys). Internal callers may continue using `X-Internal-API-Key` server-to-server."
- Remove the `X-Internal-API-Key: $INTERNAL_API_KEY` curl snippet (around line 111). Replace with a `gck_…` example, OR move the internal-key snippet to a server-rendered admin doc that requires auth.

Cross-reference `2026-05-10-launch-runway.md` Phase 4 — if the public agent surface there is about to fully replace this page, this step is a stop-gap for the interim.

- [ ] **Step 5: CORS docs in `.env.production.example`**

Confirm the comment block above `CORS_ALLOWED_ORIGINS` calls out: "Must include the production landing host (e.g. `https://govconbiddesk.com`); empty CORS will cause every POST /waitlist to fail silently in the browser."

If the comment isn't already there post-Phase 5, add it.

- [ ] **Step 6: Run gates**

```bash
uv run pytest api/tests/ -q
uv run ruff check api
uv run mypy api
npm -w web run typecheck
npm -w web run lint
npm -w web run build
```

All clean.

- [ ] **Step 7: Manual browser test**

- Visit `/app/profile/<id>` → click "Start a run with this profile" → confirm `/app/goal?profileId=<id>` URL and the dropdown pre-selects that profile.
- Visit `/agents` → confirm copy reflects keys are live, no `$INTERNAL_API_KEY` in any code block.

- [ ] **Step 8: Commit**

```bash
git add web/ .env.production.example
git commit -m "$(cat <<'EOF'
chore(web): cleanup sweep — typed DTO, profileId CTA, agents truth, CORS docs

- lib/api.ts: CreateCompanyProfilePayload (Omit id/timestamps/owner) so
  callers get compile-time errors when passing server-generated fields,
  not just 422 at runtime.
- profile/[id]: "Start a run" CTA now passes ?profileId=… so GoalForm
  pre-selects the profile the user was viewing instead of profiles[0].
- goal/GoalForm: read ?profileId from useSearchParams; validate against
  owned profiles before using.
- agents/page.tsx: copy says keys are live (they are, via /app/keys);
  drop the $INTERNAL_API_KEY snippet from the public product page —
  internal key is server-only per PRD v1.2.5.
- .env.production.example: explicit comment on CORS_ALLOWED_ORIGINS
  requirement so /waitlist doesn't silently fail in prod.

Verified: pytest 116, ruff/mypy/web build clean; manual smoke test on
profile→goal flow and agents copy.
EOF
)"
```

---

## Self-Review

### Spec coverage

Walking the hyperanalysis findings against the plan:

| Finding | Severity | Phase | Step |
|---|---|---|---|
| C1 brand alignment | Critical | 1 | 1-10 |
| C2 ApprovalGate fake | Critical | 3 | 1-16 |
| C3 AppConsole dead | Critical | 2 | 1-4 |
| C4 SSE proxy getSession | Critical | 4 | 3 |
| C5 orphan lockfile | Critical | 5 | 1 |
| H1 root scripts asymmetric | High | 5 | 2 |
| H2 X-Internal-API-Key in agents/page | High | 8 | 4 |
| H3 8 pages getSession | High | 4 | 4-5 |
| H4 middleware redirect cookies | High | 4 | 2 |
| H5 noUncheckedIndexedAccess | High | 5 | 3-4 |
| H6 missing sitemap | High | 6 | 2-3 |
| H7 missing OG/Twitter/canonical/metadataBase | High | 6 | 4-5 |
| H8 mobile menu focus trap | High | 6 | 6 |
| H9 skip-to-content | High | 6 | 7 |
| H10 CORS prod docs | High | 8 | 5 |
| M1 StatusBadge partial | Medium | 7 | 2 |
| M2 SSE event dedup | Medium | 7 | 3 |
| M3 SSE retry copy | Medium | 7 | 4 |
| M4 memoize Supabase | Medium | 7 | 1 |
| M5 createCompanyProfile DTO | Medium | 8 | 1 |
| M6 redirect not return null | Medium | 4 | 4-5 (covered by `requireUser` helper) |
| M7 scope="col" | Medium | 6 | 8 |
| M8 profileId in CTA | Medium | 8 | 2-3 |
| M9 agents coming-soon copy | Medium | 8 | 4 |
| M10 HERO.subtitle dead | Medium | 1 | 1-2 (re-wired, no longer dead) |
| M11 Story preview "Example" | Medium | 1 | 6 |
| M12 themeColor mismatch | Medium | 1 | 7 |
| M13 duplicate © | Medium | 1 | 1 |
| M14 web @theme block | Medium | 5 | 5 |

All 29 issues covered. Two items I deliberately did not break out:
- M14's "ignoreDeprecations" → handled inline in Phase 5 Step 3.
- "ESLint configs exclude config files" (a Medium not in the original 30-numbered list) → Phase 5 Step 6.

### Placeholder scan

No "TODO", "implement later", or "fill in details" left in the plan. Every code block contains the actual code an engineer would type. The one judgment-call left to execution is the production hostname (Phase 6 Step 1) — explicitly flagged as "ask the user," not a placeholder.

### Type consistency

- `requireUser()` returns `{ user, token }` — referenced consistently in Phase 4 Steps 4-5.
- `CreateCompanyProfilePayload` — defined Phase 8 Step 1, no other phase references it (no inconsistency).
- `approveActionPackage(id, token)` — defined Phase 3 Step 11, called Phase 3 Step 12.
- Pydantic `ActionPackage` model — extended in Phase 3 Step 4 (`approved_at`, `approved_by`); rendered Phase 3 Step 13.

No mismatches found.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-10-frontend-cleanup-fixes.md`. Two execution options:**

**1. Subagent-Driven (recommended for cosmetic phases 1, 5, 6, 8)** — Each phase dispatched to a fresh subagent. Two-stage review per phase. Best for parallelizing independent visual/cleanup work.

**2. Inline Execution (recommended for behavioral phases 2, 3, 4, 7)** — Single session, executing-plans skill. Best for phases that share files or need iterative manual browser testing (Phases 3 + 4 + 7 all touch `/web` runtime behavior).

Hybrid is fine: do Phase 1 + 5 + 6 + 8 via subagents in parallel, then 2 → 3 → 4 → 7 inline so manual browser checks are coherent.

**Which approach?**
