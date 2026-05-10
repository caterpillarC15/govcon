# What's left to ship

Local dev is working (dev-skip login + Supabase migrations applied + 206 tests green). This doc is **only** the remaining work to get to a tagged `v1.0.0`. Already-done stuff (clone, install, env files, Supabase, migrations) is intentionally NOT here — see `git log` if you need that history.

**Order matters** — phases are listed in dependency order. Skip down to whichever blocker is currently active.

---

## Status snapshot

| Phase | Status |
|---|---|
| Local dev (FastAPI + landing + /web + Redis + dev-skip login) | ✅ done |
| Supabase migrations applied | ✅ done |
| Bench rename, doc cleanup, schema sync | ✅ done |
| Deploy `/web` to Vercel as 2nd project | ✅ done — `app.samrail.com` |
| Wire env vars on both Vercel projects | ✅ done |
| Resend SMTP in Supabase Studio (Channel A) | ✅ done — `noreply@samrail.com`, domain verified |
| FastAPI co-located on `ssh govcon` (Vultr 16 vCPU box) | ⏳ unit installed, fixing crashloop on first start |
| Caddy block for `api.samrail.com` | ⏳ pending service-up |
| DNS A record `api.samrail.com` → `207.246.90.84` (Vercel) | ⏳ user action |
| **§5.14 production-flip** (`EMAIL_DRY_RUN=false`) | ⏳ flip + enable timers (gated on healthz green + advisor) |
| Sprint G cross-repo verification with `/root/michealaai` | ⏳ DATA-SOURCES.md patch + INTERNAL_API_KEY mirror |
| **v1.0.0 tag** | ⏳ (gated on §5.14 flip + Sprint G verify) |

> **2026-05-10 note:** Earlier rows in this table previously claimed "VX1 production
> deploy ✅ live — api.samrail.com". That was aspirational — the box was never
> bootstrapped, `api.samrail.com` had no DNS record, and `/opt/govcapture/.env`
> didn't exist. The deploy is now in-flight via `infra/deploy-onebox.sh`,
> co-locating FastAPI on the same box that runs hermes-agent + michealaai.

---

## 1. Deploy `/web` to Vercel as a second project

Right now only `landing` is deployed (at `https://govcon-rouge.vercel.app`). The "Sign in" button has nowhere good to point because `/web` doesn't exist on Vercel yet.

**Steps:**

1. Vercel dashboard → **Add New** → **Project**
2. Import the same `caterpillarC15/govcon` repo (Vercel will warn about duplicate import — confirm "Continue")
3. **Project Name:** `govcon-web` (or similar — controls auto-URL)
4. **Framework Preset:** Next.js
5. **Root Directory:** click **Edit** → set to `web`
6. Don't set env vars yet — Phase 2 covers that
7. Click **Deploy**

After ~2 min you'll have a URL like `https://govcon-web-xxxxx.vercel.app`. **Note the exact URL — you'll need it in Phase 2.**

---

## 2. Wire env vars on both Vercel projects

`NEXT_PUBLIC_*` env vars are baked at **build time**. Setting them and not redeploying = no effect.

### Landing project (`govcon-rouge`)

Settings → Environment Variables → Production scope. Should ONLY have these 3 (delete anything else):

```
NEXT_PUBLIC_SITE_URL=https://samrail.com
NEXT_PUBLIC_APP_URL=https://app.samrail.com
NEXT_PUBLIC_API_BASE=                                       ← empty until Phase 5 (VX1)
```

### Web project (`govcon-web-xxxxx`)

Same place, on the new project. Should have:

```
NEXT_PUBLIC_SUPABASE_URL=https://vvyxjdoenjujkxwbnzyl.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_u5ma_JhhAmWuC7RrunIMDA_ZtR62rUP
NEXT_PUBLIC_SITE_URL=https://samrail.com
NEXT_PUBLIC_APP_URL=https://app.samrail.com
NEXT_PUBLIC_API_BASE=                                       ← empty until Phase 5
```

### Both projects: redeploy

Per project: **Deployments → most recent → ⋯ menu → Redeploy → uncheck "Use existing build cache" → Redeploy.**

### Supabase Auth URL configuration

Supabase Studio → **Authentication** → **URL Configuration**:

```
Site URL: https://app.samrail.com
Redirect URLs:
  https://app.samrail.com/auth/callback
  https://<current-web-vercel-domain>/auth/callback  # temporary, until app.samrail.com is live
  http://localhost:3001/auth/callback
```

If `Site URL` or the deployed `/web` `NEXT_PUBLIC_APP_URL` is still localhost,
the email link will verify through Supabase and then dump the browser onto
localhost. Fix these values before testing magic links.

### NEVER set on Vercel (any project)

| ❌ | Why |
|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | Bypasses RLS — VX1 only |
| `INTERNAL_API_KEY` | Server-only auth secret — VX1 only |
| `RESEND_API_KEY`, `EMAIL_*` | Server-only — VX1 only |
| `ALLOW_DEV_LOGIN`, `DEV_USER_*` | Would render the dev-login button in production |

### Verify

```bash
curl -s https://govcon-rouge.vercel.app/ | grep -oE 'href="[^"]*login[^"]*"' | head -3
```

Should return `https://govcon-web-xxxxx.vercel.app/login` — not localhost, not the `samrail.com` fallback.

---

## 3. Resend SMTP for Supabase Auth (Channel A magic-links)

Supabase's default SMTP throttles to **4 emails/hour** project-wide. That's not viable for real users. Swap to Resend.

**Already done** in your `.env`: `RESEND_API_KEY=re_33wJTrVV_…` exists. You just need to wire it into Supabase Studio.

**Steps:**

1. Supabase Studio → your project → **Authentication** → **Email Templates** → **SMTP Settings**
2. Toggle **Enable Custom SMTP** ON
3. Fill:
   - Sender email: `onboarding@resend.dev` (sandbox sender — only delivers to the Resend account-owner inbox until you verify a domain)
   - Sender name: `SamRail`
   - Host: `smtp.resend.com`
   - Port: `465`
   - Username: `resend`
   - Password: your Resend API key with sending access
4. Save

### Verify `samrail.com` (required for sending to non-account-owner addresses)

Sandbox sender (`onboarding@resend.dev`) only delivers to the Resend account owner. For real subscribers you need a verified domain.

1. https://resend.com/domains → **Add domain**
2. Enter `samrail.com`
3. Add the SPF + DKIM × 3 + (optional) DMARC DNS records Resend shows you
4. Wait for verification (~10 min)
5. Update Studio SMTP sender email to `noreply@samrail.com`
6. Update `.env` (and prod `.env` later) `RESEND_FROM_EMAIL=SamRail <noreply@samrail.com>`

### Test

Sign out of `/web`, request a magic link, confirm:
- Email arrives within 60s from `noreply@samrail.com` (or `onboarding@resend.dev` in sandbox)
- Link works (lands in `/app` after click)
- Resend dashboard → **Logs** shows a "delivered" event

---

## 4. §5.14 production-flip (`EMAIL_DRY_RUN=false`)

Right now the weekly opportunity email job claims log slots and renders content but **never calls Resend** — `EMAIL_DRY_RUN=true` is the default. To actually send, you need to flip this AFTER Phase 5 (VX1 deploy) so the cron route runs in prod.

**Don't do this until VX1 is up and Resend domain is verified.** Then:

1. SSH into VX1, edit `/opt/govcapture/.env`, change `EMAIL_DRY_RUN=true` → `false`
2. Restart: `sudo systemctl restart govcapture-api.service`
3. The boot guard in `api/config.py` will refuse start if any of `RESEND_API_KEY`, `EMAIL_UNSUBSCRIBE_SECRET`, `EMAIL_LEGAL_FOOTER_ADDRESS` are empty — make sure all three are set.
4. Smoke test: trigger the cron route manually and verify a real email arrives:

```bash
curl -X POST https://api.samrail.com/internal/cron/auto-pick-weekly-opportunity \
  -H "Authorization: Bearer $INTERNAL_API_KEY"
# Expect: {"week_key": "...", "picked_opportunity_id": "...", ...}

curl -X POST https://api.samrail.com/internal/cron/weekly-opportunity-email \
  -H "Authorization: Bearer $INTERNAL_API_KEY"
# Expect: {"sent": N, "skipped_already_sent": 0, "failed": 0, ...}
```

5. Enable the systemd timers so it runs weekly:

```bash
sudo systemctl enable --now govcapture-cron-auto-pick.timer    # Sun 22:00 UTC
sudo systemctl enable --now govcapture-cron-weekly.timer       # Mon 14:00 UTC
```

---

## 5. VX1 production deploy

The FastAPI backend lives on a Vultr VX1 (16 vCPU, Ubuntu 24.04). Full step-by-step in `infra/RUNBOOK.md`. Compressed version:

### Provision

- Vultr → New Instance → **VX1**, Ubuntu 24.04 LTS, ~$96/mo
- Upload SSH key, get the public IP
- API hostname: `api.samrail.com`

### Bootstrap

```bash
ssh root@<VX1-IP>
git clone https://github.com/caterpillarC15/govcon.git /tmp/govcon
sudo bash /tmp/govcon/infra/bootstrap.sh
# Idempotent: installs apt deps, ufw, redis, govcapture user, systemd unit
```

### Clone + .env

```bash
sudo -u govcapture git clone https://github.com/caterpillarC15/govcon.git /opt/govcapture

# Generate a fresh INTERNAL_API_KEY for prod (different from dev)
INTERNAL_KEY=$(openssl rand -hex 32)

sudo -u govcapture install -m 0600 /dev/null /opt/govcapture/.env
sudo -u govcapture editor /opt/govcapture/.env
# Paste from .env.production.example, fill in real values:
#   - SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY (same as dev)
#   - INTERNAL_API_KEY=$INTERNAL_KEY
#   - RESEND_API_KEY (same as dev)
#   - EMAIL_LEGAL_FOOTER_ADDRESS (real CAN-SPAM address now)
#   - EMAIL_UNSUBSCRIBE_SECRET (FRESH, not the dev value: openssl rand -hex 32)
#   - CORS_ALLOWED_ORIGINS=https://samrail.com,https://app.samrail.com
#   - Keep EMAIL_DRY_RUN=true for first deploy
```

### Install + start

```bash
sudo -u govcapture -H bash -lc 'cd /opt/govcapture && ~/.local/bin/uv sync'
sudo systemctl enable --now govcapture-api.service
sudo systemctl status govcapture-api --no-pager
curl http://127.0.0.1:8000/healthz
# Expect: {"status":"ok",...}
```

### nginx + TLS

DNS first — point an A record at the VX1 IP for your API hostname, wait for propagation:

```bash
dig +short api.samrail.com      # should resolve to VX1 IP
```

Then on the box:

```bash
sudo cp /opt/govcapture/infra/nginx/govcapture.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/govcapture.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d api.samrail.com --redirect --agree-tos -m you@samrail.com -n
```

### Verify from outside the box

```bash
curl -s https://api.samrail.com/healthz
# Expect: {"status":"ok","supabase":"ok","redis":"ok"}
```

### Update Vercel projects

Now that the API is live, set `NEXT_PUBLIC_API_BASE=https://api.samrail.com` on **both** Vercel projects (landing + web) and redeploy each.

---

## 6. Sprint G cross-repo verification with `/root/michealaai`

**Cross-repo work — can't be done from this repo.** Coordinated with the orchestrator side.

Per `devdocs/CAPABILITY_PACK_INTEGRATION.md`, Michaela's pickup loop polls `agent_runs` rows from this pack's Supabase, claims them, drives the run, writes back artifacts, and emits trace events to Redis.

Two things owed by `/root/michealaai`:

1. **Update `/root/michealaai/DATA-SOURCES.md`** to distinguish the two GovCon projects:
   - `ktygrvbpugqhfyibzirr` — Lance's competitive-intel reads (agencies, contractors, contracts)
   - `vvyxjdoenjujkxwbnzyl` — `agent_runs` pickup + writebacks (this pack's project)

   Without this, Michaela polls the wrong project and never sees our runs.

2. **Mirror `INTERNAL_API_KEY`** between `/opt/govcapture/.env` (VX1) and `/root/michealaai`'s env. Same string both sides — the pack's writeback routes 401 on mismatch.

### Verification gate (when both sides ready)

1. Sign in to prod `/web`, submit a goal
2. Note run-uuid in URL
3. Watch `/root/michealaai` logs — should claim within ~5s
4. Watch `/web/app/runs/<uuid>` — SSE timeline populates
5. Check Studio: `action_packages` row appears with caller's `owner_profile_id`

If `/root/michealaai` isn't ready, the SSE stub gets you most of the way:

```bash
make sse-stub RUN_ID=<run-uuid>      # Mon-Fri tooling, replays 20 events through Redis
```

---

## 7. Custom domain

Use `samrail.com` for the public surfaces:

| Surface | Custom domain |
|---|---|
| Landing | `samrail.com` (apex) or `www.samrail.com` |
| `/web` | `app.samrail.com` |
| API (VX1) | `api.samrail.com` |

Steps:

1. Vercel landing project → Settings → Domains → add `samrail.com` → follow DNS instructions
2. Vercel web project → same, add `app.samrail.com`
3. Update env vars on both Vercel projects to use the real domain
4. Update VX1 `.env`: `CORS_ALLOWED_ORIGINS=https://samrail.com,https://app.samrail.com`
5. Update Resend `RESEND_FROM_EMAIL` to `noreply@samrail.com`, verify domain at resend.com/domains
6. Redeploy everything

No code change required — env-only swap.

---

## 8. v1.0.0 tag

Once 1–6 above are done:

```bash
# Final all-suite gate
uv run pytest api/tests/ -q                          # ≥ 206 passed
uv run ruff check api && uv run mypy api             # both clean
make eval && make fixtures-validate                  # both clean
npm -w landing run build && npm -w web run build     # both clean
curl -s https://api.samrail.com/healthz              # 200 from outside the box

# Tag + push
git tag -a v1.0.0 -m "SamRail v1.0.0 — first public release"
git push origin main --follow-tags
```

That's it.

---

## When you're stuck

| Stuck on | Where to look |
|---|---|
| Vercel env vars | This doc §2 |
| Supabase Studio | This doc §3 (or Supabase docs) |
| VX1 deploy details | `infra/RUNBOOK.md` |
| Sprint G coordination | `devdocs/CAPABILITY_PACK_INTEGRATION.md` |
| Local-dev issue | Working directory: `git log` recent commits, `git diff` your tree, run `uv run pytest api/tests/ -q` |
| What's actually shipped vs not | `devdocs/CURRENT_STATE.md` |

---

## TL;DR — exact next 3 commands

```bash
# 1. Vercel dashboard, click Add New → Project, import repo, Root Dir = web, Deploy
# 2. Once deployed, set the env vars per §2 on BOTH projects
# 3. After redeploy, run:
curl -s https://govcon-rouge.vercel.app/ | grep -oE 'href="[^"]*login[^"]*"' | head -3
# Should NOT contain "localhost". If it doesn't, Phase 1+2 done — move to Phase 3.
```
