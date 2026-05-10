# GovCon Bid Desk — full setup guide

The "I cloned this, now what?" doc. Reads top-to-bottom in ~10 minutes;
following it gets you a fully running stack (FastAPI + landing + /web +
Supabase + Redis) on your laptop in under 15 minutes.

For ongoing day-to-day use, jump to **§7 (Run locally)**.
For deployment, see `devdocs/LAUNCH_CHECKLIST.md` + `infra/RUNBOOK.md`.

---

## 0 · TL;DR (already-set-up path)

If your `.env` and `web/.env.local` are already populated and Supabase
migrations are already applied:

```bash
# Terminal 1 — Redis (only needed for SSE timeline)
make services-up

# Terminal 2 — FastAPI
uv run uvicorn api.main:app --reload --port 8000

# Terminal 3 — both Next apps in parallel
npm run dev
```

Open `http://localhost:3001/login` → click the amber **Sign in as dev**
button → land in `/app`. Done.

If anything errors, jump to **§9 Troubleshooting**.

---

## 1 · The product in one paragraph

GovCon Bid Desk is a **capability pack** — shared tools, a data layer,
an HTTP API, a marketing landing, and an authenticated product UI — that
AI agents (especially Michaela in `/root/michealaai`) call to find
federal contracts worth bidding, decide pursue/maybe/reject, and
produce action packages. This repo owns mechanics + contracts + the UI;
Michaela's bench owns judgment + LLM cost. Per PRD v1.2.6, every skill
in this repo is **deterministic** — no Anthropic SDK lives here anymore.

---

## 2 · Prerequisites

Install once on your machine.

| Tool | Version | macOS install | Linux install |
|---|---|---|---|
| **Node.js** | ≥ 20.x | `brew install node` | `nvm install 20` |
| **Python** | 3.12 | `brew install python@3.12` | `apt install python3.12` |
| **uv** (Python pkg mgr) | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | same |
| **Redis** | ≥ 7 | `brew install redis` | `apt install redis-server` |
| **Supabase CLI** | latest | `brew install supabase/tap/supabase` | [docs](https://supabase.com/docs/guides/local-development/cli/getting-started) |
| **git** | any modern | likely already installed | likely already installed |

**Optional but useful:**
- `gh` (GitHub CLI) — `brew install gh`
- `httpie` or `curl` — for API smoke tests

Verify everything's on your PATH:

```bash
node --version    # ≥ v20
uv --version
redis-cli --version
supabase --version
```

---

## 3 · Clone + dependencies

```bash
# Clone
git clone https://github.com/caterpillarC15/govcon.git
cd govcon

# Python dependencies (FastAPI, supabase-py, etc.)
uv sync

# Node dependencies (workspaces: landing + web + mcp_server_govcapture)
npm install
```

`uv sync` reads `pyproject.toml` + `uv.lock` and creates `.venv/`.
`npm install` reads root `package.json` (workspaces declared) and
installs deps for both Next apps.

**Don't run `npm install` inside `landing/` or `web/` directly** — the
workspace setup at root handles them in one shot.

---

## 4 · Environment files

Three env files matter. The first two are gitignored (local secrets);
the third is committed as a template for the production VX1 deploy.

### 4.1 — `.env` (root, gitignored)

This is what FastAPI reads. Copy from the template, fill in real values:

```bash
cp .env.example .env
$EDITOR .env
```

Required fields (the file's comments explain each):

| Variable | What |
|---|---|
| `SUPABASE_URL` | Your project URL — `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only; bypasses RLS. Get from Supabase Studio → Settings → API |
| `SUPABASE_ANON_KEY` | The publishable key (`sb_publishable_…`) |
| `SUPABASE_STORAGE_BUCKET` | `govcapture-attachments` (default; bucket must exist) |
| `INTERNAL_API_KEY` | Long random string. Generate: `openssl rand -hex 32` |
| `REDIS_URL` | `redis://localhost:6379/0` for local |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001,http://localhost:5173` |

Optional / dev-convenience:

| Variable | What |
|---|---|
| `SAM_API_KEY` | Live SAM.gov; empty = seeded fixtures only |
| `ALLOW_DEV_LOGIN=true` | Renders the amber "Sign in as dev" button on /web/login (skip email) |
| `DEV_USER_EMAIL` / `DEV_USER_PASSWORD` | Defaults `dev@local.test` / `devonly-not-for-prod` |

§5.14 weekly opportunity email (set whatever you like in dev — keep
`EMAIL_DRY_RUN=true`):

| Variable | What |
|---|---|
| `RESEND_API_KEY` | Your Resend API key. Sign up at resend.com — sandbox sender works |
| `RESEND_FROM_EMAIL` | `GovCapture <onboarding@resend.dev>` (sandbox sender) |
| `EMAIL_PUBLIC_BASE_URL` | `http://localhost:8000` |
| `EMAIL_UNSUBSCRIBE_SECRET` | `openssl rand -hex 32` |
| `EMAIL_LEGAL_FOOTER_ADDRESS` | Required for prod, can be a placeholder in dev |
| `EMAIL_DRY_RUN=true` | Keep this in dev. False sends real email. |

**What's NOT in `.env`** (PRD v1.2.6 dropped these):
`ANTHROPIC_API_KEY`, `LLM_DEV_MODEL`, `LLM_SYNTH_MODEL`, `RUN_BUDGET_*`,
`HERMES_HOME`, `HERMES_MODEL`, `DEMO_*`. If you copied an old `.env`,
delete those lines — they're ignored but confusing.

### 4.2 — `web/.env.local` (gitignored)

Next.js reads `.env.local` from each app's root, **not** the repo root.
So `/web` needs its own copy of the env vars.

Easiest: copy your root `.env` into `web/.env.local` verbatim.

```bash
cp .env web/.env.local
```

Re-copy whenever you update `.env`. (You can also symlink, but most
operating systems handle the copy fine.)

The `/web` app reads:
- All `NEXT_PUBLIC_*` (browser-safe)
- `SUPABASE_SERVICE_ROLE_KEY` (server-only, used by `signInAsDev`
  action's admin client)
- `ALLOW_DEV_LOGIN` / `DEV_USER_EMAIL` / `DEV_USER_PASSWORD`
  (server-only)

### 4.3 — `.env.production.example` (committed template)

Don't edit this for local dev. It's the template for what to put in
`/opt/govcapture/.env` on the VX1 production box. See **§10 Deployment**
when you're ready to ship.

---

## 5 · Supabase setup (one-time)

If you're joining a project that already has Supabase set up, you just
need:
1. The project URL + anon key + service-role key (from whoever owns it)
2. To `supabase link` so migrations work

Skip to **§5.3** if you already have Studio access.

### 5.1 — Create a Supabase project (only if starting fresh)

Go to https://supabase.com → **New project**. Pick a region close to you.
Wait ~2 minutes for provisioning.

In **Settings → API**, capture:
- Project URL (e.g., `https://abc123xyz.supabase.co`)
- `anon` key — the publishable one
- `service_role` key — server-only, bypasses RLS

Add these to your `.env` (and `web/.env.local`).

### 5.2 — Create the storage bucket

In the project's dashboard, **Storage → New bucket** → name it
`govcapture-attachments`. **Set Public to OFF** (private). Do not
enable any RLS policies — the FastAPI uses the service-role key to
bypass RLS.

### 5.3 — Link the CLI to the project

```bash
supabase login         # one-time; opens browser for OAuth
supabase link --project-ref <your-project-ref>
```

Project ref is the subdomain of your Supabase URL — for
`https://abc123xyz.supabase.co` it's `abc123xyz`.

### 5.4 — Apply migrations

```bash
supabase db push
```

This applies every `supabase/migrations/*.sql` file in order. Currently
there are 11 migrations covering: core schema, Michaela layer, ownership
+ provenance, waitlist, api_keys, competitor_history, action_package
approval columns, and the §5.14 weekly opportunity email tables.

Verify:

```bash
supabase migration list
```

Every row should show **both** Local and Remote populated.

If two timestamps (`20260510021500`, `20260510024000`) appear with
empty SQL files locally, that's intentional — they're "drift
placeholders" for migrations that were applied to remote outside this
repo. See `devdocs/CURRENT_STATE.md` §10 schema-state table for the
full story.

### 5.5 — (Optional) swap to Resend SMTP

By default, Supabase Auth emails (magic-link, password reset) go through
Supabase's shared SMTP. **It throttles to 4 emails/hour project-wide** —
fine for solo dev but easy to hit during testing.

If you'd rather use the dev-login button (no email at all), skip this.
Otherwise, in Studio:

**Authentication → Email Templates → SMTP Settings** → enable Custom
SMTP and fill:

| Field | Value |
|---|---|
| Sender email | `noreply@<your-domain>` (or `onboarding@resend.dev` for sandbox) |
| Sender name | `GovCon Bid Desk` |
| Host | `smtp.resend.com` |
| Port | `465` |
| Username | `resend` |
| Password | `<your Resend API key>` |

Sandbox-sender mode (`onboarding@resend.dev`) only delivers to the
Resend account-owner email. Verify a domain at resend.com/domains for
real subscriber sends.

---

## 6 · Database is alive — let's verify

```bash
uv run python -c "
import asyncio
from api.db import get_client

async def main():
    client = await get_client()
    tables = ['profiles', 'opportunities', 'agent_runs', 'company_profiles',
              'api_keys', 'competitor_history', 'weekly_opportunity_picks',
              'weekly_opportunity_email_log']
    for t in tables:
        r = await client.table(t).select('*').limit(1).execute()
        print(f'{t}: ok')

asyncio.run(main())
"
```

Should print 8 lines of `ok`. If any fail, your migrations didn't fully
apply — re-run `supabase db push` and check `supabase migration list`.

---

## 7 · Run locally

Three terminals, ~30 seconds total.

### 7.1 — Redis

```bash
make services-up      # macOS: brew services start redis
                      # Linux: sudo systemctl start redis-server
redis-cli ping        # PONG
```

You can stop it later with `make services-down`. Required only for the
SSE pub/sub bridge (run-timeline page); the rest of the app works
without it.

### 7.2 — FastAPI

```bash
uv run uvicorn api.main:app --reload --port 8000
```

Output:
```
INFO:     Will watch for changes in these directories
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

Smoke test in another shell:

```bash
curl http://localhost:8000/healthz
# {"status":"ok","supabase":"ok","redis":"ok"}
```

### 7.3 — Both Next apps in parallel

```bash
npm run dev
```

The root `package.json` `dev` script launches **landing on :3000** and
**web on :3001** simultaneously. Both Next apps hot-reload on file
changes.

Output (interleaved, color-coded):
```
landing | ▲ Next.js 15.5.18  http://localhost:3000
web     | ▲ Next.js 15.5.18  http://localhost:3001
landing | ✓ Ready in 1.2s
web     | ✓ Ready in 1.4s
```

### 7.4 — Sign in (dev-skip)

Open `http://localhost:3001/login`.

Under the email magic-link form you'll see an amber dashed panel:

> **DEV ONLY**
> [ Sign in as dev (skip email) ]
> Idempotently creates `dev@local.test` via service-role + signs in
> with password. Gated by `ALLOW_DEV_LOGIN=true` in `.env`; will
> no-op in production.

Click it. ~1 second later you're at `/app`.

What happened:
1. Server action checked `ALLOW_DEV_LOGIN === 'true'` and the
   service-role key is present
2. Service-role admin client created the user
   `dev@local.test` (idempotent — second click does nothing new)
3. Anon-key client called `signInWithPassword` with the dev password
4. Session cookie set on the response
5. Redirect to `/app`

No email, no Supabase rate limit, no waiting.

### 7.5 — Visit the landing too

`http://localhost:3000/` — this is the marketing site. Click "Sign in"
top-right; should redirect to `http://localhost:3001/login` (the app).

If it redirects to `localhost:3000/login` instead, you're on a stale
build — check that `NEXT_PUBLIC_APP_URL=http://localhost:3001` is in
`.env` (and `web/.env.local`), then **stop and restart `npm run dev`**.
Server-component env reads happen at server-start; hot-reload doesn't
re-read env.

---

## 8 · Verify everything works (full gate sweep)

Run these commands periodically. They're the same gates CI would run:

```bash
# Backend
uv run pytest api/tests/ -q             # ≥ 206 passed
uv run ruff check api                   # All checks passed
uv run mypy api                         # Success: no issues
make eval                               # 15 PASSes (byte-exact regression gate)
make fixtures-validate                  # 4 fixtures OK

# Frontend
npm -w landing run lint                 # clean
npm -w landing run build                # clean
npm -w web run lint                     # clean
npm -w web run typecheck                # clean
npm -w web run build                    # clean

# Schemas (if you've edited /schemas/*.json)
make schemas                            # idempotent; second run produces no diff
```

If any fail, see **§9 Troubleshooting** or check the relevant doc:
- Schema issues: `tasks/CONTRACTS.md` §2
- Eval drift: re-bootstrap with `make eval-bootstrap` after hand-reviewing the diff
- Test failures: `api/tests/conftest.py` for the FakeSupabase shape

---

## 9 · Troubleshooting

### "Cannot find module './208.js'" (Next webpack runtime error)

Stale `.next/` build cache. Fix:

```bash
rm -rf landing/.next web/.next
npm run dev    # rebuilds clean
```

This happens after dependency changes or when switching branches with
divergent client-component graphs.

### Magic-link redirects to `localhost:3000` instead of `localhost:3001`

`NEXT_PUBLIC_APP_URL` either missing or stale. Fix:

```bash
grep NEXT_PUBLIC_APP_URL web/.env.local
# Must show: NEXT_PUBLIC_APP_URL=http://localhost:3001
```

If missing, add it. **Restart the Next dev server** — env vars used in
Server Components are read at server-start, not on file save.

### "Sign in as dev" button doesn't appear

```bash
grep ALLOW_DEV_LOGIN web/.env.local
# Must show: ALLOW_DEV_LOGIN=true
```

If missing, add to `web/.env.local`:
```
ALLOW_DEV_LOGIN=true
DEV_USER_EMAIL=dev@local.test
DEV_USER_PASSWORD=devonly-not-for-prod
```

Restart `npm run dev`.

### "Email rate limit exceeded" trying to sign in via magic link

Supabase shared SMTP is capped at 4/hour per project. Two fixes:

1. Use the **dev-skip button** instead (see §7.4)
2. Configure Resend SMTP in Supabase Studio (see §5.5)

### Port 3000 / 3001 / 8000 already in use

```bash
lsof -i :3001     # find the PID
kill <PID>
```

Or just use `pkill -f "next dev"` to nuke any stray Next processes.

### Redis not running, FastAPI healthz returns 5xx

```bash
redis-cli ping     # should be PONG
make services-up   # starts via brew or systemctl
```

If brew complains: `brew services list` and look for the redis line. If
it shows "stopped" or "error", restart with `brew services restart redis`.

### `supabase db push` says "remote-only migration not in local"

Two timestamps (`20260510021500`, `20260510024000`) were applied to
remote outside this repo and exist locally as empty placeholder files.
That's expected. If `supabase migration list` shows them on both sides,
ignore the warning. If they're missing locally, recreate the empty
placeholder files (see `supabase/migrations/` for naming).

### Tests pass but `make eval` fails

A skill's deterministic output drifted. Either:
- The change was intentional → re-bootstrap goldens:
  ```bash
  make eval-bootstrap
  git diff fixtures/*/goldens/   # hand-review
  git add fixtures/*/goldens/ && git commit
  ```
- The change was a bug → fix the skill, don't re-bootstrap.

### Stale `web/.env.local` after editing `.env`

Next.js reads its own `.env.local`, not the repo root's. If you've
edited `.env`, copy it over:

```bash
cp .env web/.env.local
```

Then **restart the Next dev server**.

---

## 10 · Deployment (forward-looking)

You don't need this for local dev. Pasted here so the picture is
complete. Full step-by-step lives in `devdocs/LAUNCH_CHECKLIST.md`.

### 10.1 — Frontend: Vercel × 2 projects

The repo has **two Next.js apps** (`landing/` and `web/`) — Vercel
builds one app per project, so you need two projects, both pointing at
the same git repo with different **Root Directory** settings.

| Project | Root Directory | Production URL example |
|---|---|---|
| **landing** (currently `govcon-rouge.vercel.app`) | `landing` | `https://govcon-rouge.vercel.app` |
| **web** (TODO) | `web` | `https://govcon-web-xxxxx.vercel.app` |

Env vars on each project (Production scope only — `NEXT_PUBLIC_*` prefix
required for browser exposure):

**Landing:**
```
NEXT_PUBLIC_SITE_URL=https://govcon-rouge.vercel.app
NEXT_PUBLIC_APP_URL=https://govcon-web-xxxxx.vercel.app
NEXT_PUBLIC_API_BASE=        (empty until VX1 ships)
```

**Web:**
```
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<sb_publishable_...>
NEXT_PUBLIC_SITE_URL=https://govcon-rouge.vercel.app
NEXT_PUBLIC_APP_URL=https://govcon-web-xxxxx.vercel.app
NEXT_PUBLIC_API_BASE=
```

**Never set on Vercel (any project):**
- `SUPABASE_SERVICE_ROLE_KEY` — server-only, belongs on VX1 only
- `INTERNAL_API_KEY` — server-only
- `RESEND_API_KEY` — server-only
- `EMAIL_*` — server-only
- `ALLOW_DEV_LOGIN` / `DEV_USER_*` — would render the dev-login button in production

After saving env vars, **redeploy** (Deployments → ⋯ → Redeploy →
uncheck "Use existing build cache"). `NEXT_PUBLIC_*` vars are baked at
build time.

### 10.2 — Backend: Vultr VX1

FastAPI + Redis + nginx on a Vultr VX1 (16 vCPU, Ubuntu 24.04). Full
runbook in `infra/RUNBOOK.md`. Quick path:

```bash
ssh root@<VX1-IP>
git clone https://github.com/caterpillarC15/govcon.git /tmp/govcon
sudo bash /tmp/govcon/infra/bootstrap.sh

sudo -u govcapture git clone https://github.com/caterpillarC15/govcon.git /opt/govcapture
sudo -u govcapture install -m 0600 /dev/null /opt/govcapture/.env
sudo -u govcapture editor /opt/govcapture/.env
# Paste from .env.production.example, fill in real values

sudo -u govcapture -H bash -lc 'cd /opt/govcapture && ~/.local/bin/uv sync'
sudo systemctl enable --now govcapture-api.service

# nginx + TLS
sudo cp infra/nginx/govcapture.conf /etc/nginx/sites-available/
sudo certbot --nginx -d api.<your-domain>
```

Then update both Vercel projects' `NEXT_PUBLIC_API_BASE` to
`https://api.<your-domain>` and redeploy.

### 10.3 — Custom domains (optional, recommended)

When you buy a real domain (e.g., `govcon.app`):

- **Landing project** → custom domain `govcon.app`
- **Web project** → custom domain `app.govcon.app`
- **VX1** → `api.govcon.app`

Update env vars to match (drop the `*.vercel.app` URLs). One-time
work; pays off in branding + email deliverability.

---

## 11 · Day-to-day workflows

| Want to | Do |
|---|---|
| Add a new skill | Create `api/skills/<name>/skill.py`, declare input/output schemas, write tests in `api/tests/test_<name>.py` |
| Add a new Supabase migration | `supabase migration new <name>`, edit, `supabase db push` |
| Update a Pydantic model | Edit `schemas/<name>.schema.json`, run `make schemas`, commit both |
| Pull updated dependencies | `uv sync && npm install` |
| Run one specific test | `uv run pytest api/tests/test_score_fit.py -v -k "test_short_circuit"` |
| Reset the dev DB (DESTRUCTIVE — local Supabase only, NOT remote) | `supabase db reset` |
| See what FastAPI routes exist | `uv run python -c "from api.main import app; [print(r.path) for r in app.routes if hasattr(r, 'path')]"` |
| Replay an SSE trace through /web | `make sse-stub RUN_ID=<uuid>` (after creating an `agent_runs` row from `/app/goal`) |

---

## 12 · Where to look (other docs)

| Topic | File |
|---|---|
| State of the repo right now | `devdocs/CURRENT_STATE.md` |
| Architecture (4 layers, Michaela ↔ pack relationship) | `devdocs/MICHAELA_SYSTEM_MODEL.md` |
| Cross-repo integration spec (Michaela ↔ this pack) | `devdocs/CAPABILITY_PACK_INTEGRATION.md` |
| Wiring this pack into a Hermes runtime | `devdocs/HERMES_LINK.md` |
| Production launch checklist | `devdocs/LAUNCH_CHECKLIST.md` |
| Strategic horizon (multi-pack future) | `devdocs/CAPABILITY_PACKS_CANVAS.md` |
| Today-shaped product alignment / voice | `devdocs/V1_PRODUCT_ALIGNMENT.md` |
| Continuation handoff (for fresh agent sessions) | `devdocs/HANDOFF_PROMPT.md` |
| API contracts (schemas, SSE events, env vars, routes) | `tasks/CONTRACTS.md` |
| Fixture content spec | `tasks/FIXTURES.md` |
| Landing copy brief | `tasks/LANDING_BRIEF.md` |
| Hermes dev-time testing | `HERMES.md` |
| VX1 deploy runbook | `infra/RUNBOOK.md` |
| Active plans | `docs/superpowers/plans/` |
| Archived plans | `docs/superpowers/plans/_archive/` |
| Product spec | `PRD.md` (current v1.2.6) |

---

## 13 · Common shortcuts

```bash
# Help target lists every Makefile target with descriptions
make help

# Re-generate Pydantic schemas from JSON Schema sources
make schemas

# Validate every fixture manifest
make fixtures-validate

# Apply Supabase migrations
make db-push

# Pull remote schema (cautious; check diff before commit)
make db-pull

# Stub SSE trace publisher for /web testing
make sse-stub RUN_ID=<uuid> [DELAY_MS=500]
```

---

## 14 · Getting unstuck

If after reading this you still can't get the stack running:

1. Check `devdocs/CURRENT_STATE.md` § 1 ("verified state") for the
   commands that were green at the last known-good commit.
2. `git log --oneline -20` — recent commits often have notes about what
   was changed and why.
3. `git status` and `git diff` — your working tree might have uncommitted
   changes that are breaking something.
4. Reset to a known-good commit and verify the gates: `git stash` your
   work, then run §8's gate sweep.

If a specific error is stumping you, search:

```bash
grep -rn "<exact error string>" devdocs/ tasks/ README.md infra/ --include="*.md"
```

Most errors that have happened to a previous contributor are documented
somewhere in those files.

---

**End of setup guide.** When this is your first run-through, expect
about 15 minutes total: 5 min on prereqs, 5 min on env + Supabase, 5
min on first dev sign-in. Subsequent runs are 30 seconds (just §0 TL;DR).
