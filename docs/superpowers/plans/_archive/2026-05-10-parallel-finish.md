# Parallel finish to v1.0.0

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for the ENG tracks.

**Goal:** ship v1.0.0 with `samrail.com` as the canonical domain, magic-link working end-to-end on prod, weekly opportunity email going out from Resend, FastAPI live on VX1, and cross-repo orchestration verified — by running independent tracks in parallel rather than serially.

**Status assumed:**

- Local dev fully working (dev-skip login, Supabase migrations applied, 206 tests green)
- DNS for `samrail.com` either done or in progress
- Resend domain `samrail.com` either verified or in progress
- Vercel landing at `govcon-rouge.vercel.app`, /web at `govcon-web-lac.vercel.app`
- `actions.ts` was just upgraded with smart origin fallback (commit on disk; covers the localhost-baked-into-build case at runtime)

**Bug context that landed this plan:**

- Email magic-link was going to `localhost` from the deployed `/web`. Code-side fix shipped (request-header fallback when env is localhost; throw on Vercel if still localhost). Vercel still needs `NEXT_PUBLIC_APP_URL` set + a redeploy to bake the right value into the build.

---

## Tracks (parallelizable)

```
Track 1 [USER, ~10 min]   Vercel env vars + redeploy (fixes localhost magic-link)
Track 2 [USER, ~5 min]    Supabase Studio Auth + SMTP config
Track 3 [ENG, done]       Template patches with samrail.com (this commit)
Track 4 [USER, 4-8 hrs]   VX1 production deploy
Track 5 [USER+ENG, 1-2d]  Sprint G cross-repo verification
Track 6 [ENG, gated]      v1.0.0 tag

Critical path: 1 → 2 → 4 → 6
Independent:   3, 5
```

Tracks 1+2 should fire today (10 min total + DNS wait). Track 4 is the long one. Track 5 runs in parallel with Track 4 if `/root/michealaai` is ready.

---

## Track 1 — Vercel env vars + redeploy (`~10 min` USER)

**Why first:** the email-to-localhost bug. The code-side fallback in `web/src/app/login/actions.ts` now reads request headers if `NEXT_PUBLIC_APP_URL` is localhost, but the cleanest fix is just setting the env var on Vercel.

### 1.1 Landing project (`govcon-rouge`)

Settings → Environment Variables → Production scope. Should have **only these 3** (delete anything else):

```
NEXT_PUBLIC_SITE_URL=https://samrail.com
NEXT_PUBLIC_APP_URL=https://app.samrail.com
NEXT_PUBLIC_API_BASE=                                ← empty until VX1 ships
```

### 1.2 Web project (`govcon-web-lac`)

Same dashboard, that project → Settings → Environment Variables → Production scope:

```
NEXT_PUBLIC_SUPABASE_URL=https://vvyxjdoenjujkxwbnzyl.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_u5ma_JhhAmWuC7RrunIMDA_ZtR62rUP
NEXT_PUBLIC_SITE_URL=https://samrail.com
NEXT_PUBLIC_APP_URL=https://app.samrail.com
NEXT_PUBLIC_API_BASE=                                ← empty until VX1 ships
```

### 1.3 NEVER set on Vercel (any project)

| Variable | Why not |
|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | Bypasses RLS, server-only — VX1 only |
| `INTERNAL_API_KEY` | Server auth secret — VX1 only |
| `RESEND_API_KEY` + `EMAIL_*` | Server-only — VX1 only |
| `ALLOW_DEV_LOGIN` / `DEV_USER_*` | Would render the dev-login button in prod |

If you previously dumped your full `.env` into Vercel, **delete every variable not listed in §1.1 / §1.2.**

### 1.4 Redeploy both — disable build cache

Per project: **Deployments → most recent → ⋯ menu → Redeploy → uncheck "Use existing build cache" → Redeploy.**

Wait ~2 min per project. `NEXT_PUBLIC_*` are inlined at build time; without a fresh build, the old localhost values remain.

### 1.5 Verify

```bash
# Landing's "Sign in" should now point at app.samrail.com (or your web project URL):
curl -s https://samrail.com/ | grep -oE 'href="[^"]*login[^"]*"' | head -3

# Or while DNS is propagating, check the auto-URL:
curl -s https://govcon-rouge.vercel.app/ | grep -oE 'href="[^"]*login[^"]*"' | head -3
```

Should NOT contain `localhost` or `samrail.com`.

---

## Track 2 — Supabase Studio Auth + SMTP (`~5 min` USER, parallel with Track 1)

### 2.1 Auth → URL Configuration

Supabase Studio → your project → **Authentication → URL Configuration**.

| Field | Value |
|---|---|
| Site URL | `https://app.samrail.com` |
| Additional Redirect URLs | `https://app.samrail.com/**` <br> `https://app.samrail.com/auth/callback` <br> `https://samrail.com/**` <br> (keep) `http://localhost:3001/**` |

Save. Without these, Supabase rejects the magic-link `redirectTo` parameter for the new domain — that's a separate failure mode from the bug Track 1 fixed.

### 2.2 Auth → Email Templates → SMTP Settings

Toggle **Custom SMTP** ON, fill:

| Field | Value |
|---|---|
| Sender email | `noreply@samrail.com` (after Resend domain verifies) <br> OR `onboarding@resend.dev` (sandbox; only delivers to Resend account owner) |
| Sender name | `SamRail` |
| Host | `smtp.resend.com` |
| Port | `465` |
| Username | `resend` |
| Password | `$RESEND_API_KEY (from your local .env)` |

Save.

If Resend domain isn't verified yet (i.e., you only see SPF/DKIM records pending), use the sandbox sender for now. After verification flips green at https://resend.com/domains, swap the sender email to `noreply@samrail.com`.

### 2.3 Smoke test

After Track 1 redeploy + Track 2 saves:

1. Sign out of `https://app.samrail.com`
2. Request a magic link to your real email
3. Confirm:
   - Email arrives within 60s from `noreply@samrail.com`
   - Link in email points at `https://app.samrail.com/auth/callback?code=…` (NOT localhost, NOT vercel.app)
   - Clicking lands you in `/app`
   - Resend dashboard → Logs shows "delivered"

If link is still localhost: Track 1 redeploy didn't happen with cache disabled; redo §1.4.
If Supabase rejects the redirect: §2.1 Site URL or Redirect URLs missing the new domain.

---

## Track 3 — Template patches (DONE — this commit)

What this commit lands:

- `devdocs/LAUNCH_CHECKLIST.md` — every `<your-domain>` and `<verified-domain>` placeholder swapped to `samrail.com`
- `devdocs/HERMES_LINK.md` — `<your-domain>` → `samrail.com`
- `.env.production.example`, `infra/RUNBOOK.md`, `infra/nginx/govcapture.conf`, `devdocs/SETUP.md` — already swapped (user did this earlier)

What's intentionally LEFT as placeholders:
- `PRD.md` — spec doc, domain-agnostic. Keeps `<your-domain>` / `samrail.com` in §5.14 email format examples.

After this commit, every operational doc is `samrail.com`-ready. Phase 4 (VX1) commands are paste-ready instead of needing find-and-replace.

---

## Track 4 — VX1 production deploy (`4-8 hours contiguous` USER)

**Don't start this late in the day.** DNS propagation for `api.samrail.com` adds non-deterministic wait.

Full step-by-step in `infra/RUNBOOK.md`. Compressed sequence:

### 4.1 Provision

- Vultr → New Instance → **VX1**, Ubuntu 24.04 LTS
- SSH key uploaded; capture the public IP
- DNS now (so it propagates while you bootstrap):

  | Type | Name | Value |
  |---|---|---|
  | `A` | `api` | `<VX1 public IP>` |

### 4.2 Bootstrap

```bash
ssh root@<VX1-IP>
git clone https://github.com/caterpillarC15/govcon.git /tmp/govcon
sudo bash /tmp/govcon/infra/bootstrap.sh
```

Expected: green output on 7 numbered steps. Idempotent.

### 4.3 Clone repo + drop `.env`

```bash
sudo -u govcapture git clone https://github.com/caterpillarC15/govcon.git /opt/govcapture

# Generate prod secrets (different from dev):
INTERNAL_KEY=$(openssl rand -hex 32)
EMAIL_SECRET=$(openssl rand -hex 32)
echo "INTERNAL_API_KEY=$INTERNAL_KEY"
echo "EMAIL_UNSUBSCRIBE_SECRET=$EMAIL_SECRET"

sudo -u govcapture install -m 0600 /dev/null /opt/govcapture/.env
sudo -u govcapture editor /opt/govcapture/.env
```

Paste from `.env.production.example` (already samrail.com-shaped — see Track 3) and fill in:

```
SUPABASE_URL=https://vvyxjdoenjujkxwbnzyl.supabase.co
SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY    # from your local .env
SUPABASE_ANON_KEY=sb_publishable_u5ma_JhhAmWuC7RrunIMDA_ZtR62rUP
SUPABASE_STORAGE_BUCKET=govcapture-attachments
INTERNAL_API_KEY=<the openssl output above>
REDIS_URL=redis://localhost:6379/0
CORS_ALLOWED_ORIGINS=https://samrail.com,https://app.samrail.com
RESEND_API_KEY=$RESEND_API_KEY (from your local .env)
RESEND_FROM_EMAIL=SamRail <noreply@samrail.com>
EMAIL_PUBLIC_BASE_URL=https://api.samrail.com
EMAIL_UNSUBSCRIBE_SECRET=<the openssl output above>
EMAIL_LEGAL_FOOTER_ADDRESS=SamRail · <real CAN-SPAM mailing address> · United States
EMAIL_DRY_RUN=true                              ← keep true for first deploy
EMAIL_REQUIRE_DOUBLE_OPT_IN=false
EMAIL_AUTO_PICK_ENABLED=true
EMAIL_AUTO_PICK_MIN_SCORE=60
EMAIL_AUTO_PICK_MAX_CANDIDATES=20
EMAIL_NAICS_ALLOWLIST=
EMAIL_USE_FIXTURES_FOR_AUTO_PICK=false
```

`SAM_API_KEY` empty is fine (falls back to seeded fixtures).

NEVER set on VX1: `ALLOW_DEV_LOGIN`, `DEV_USER_*`, `ANTHROPIC_API_KEY`, `LLM_*`, `RUN_BUDGET_*`, `HERMES_*`, `DEMO_*` — all dropped at PRD v1.2.6 or were dev-only.

### 4.4 Install + start systemd

```bash
sudo -u govcapture -H bash -lc 'cd /opt/govcapture && ~/.local/bin/uv sync'
sudo systemctl enable --now govcapture-api.service
sudo systemctl status govcapture-api --no-pager
curl http://127.0.0.1:8000/healthz   # {"status":"ok",...}
```

If healthz returns 503 with a config error, check the boot guard: `EMAIL_DRY_RUN=false` requires `RESEND_API_KEY`/`EMAIL_UNSUBSCRIBE_SECRET`/`EMAIL_LEGAL_FOOTER_ADDRESS` all set. Easy fix: keep `EMAIL_DRY_RUN=true` (your current value).

### 4.5 nginx + TLS

```bash
# DNS verification first:
dig +short api.samrail.com    # must resolve to your VX1 IP

# Then on the box:
sudo cp /opt/govcapture/infra/nginx/govcapture.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/govcapture.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d api.samrail.com --redirect --agree-tos -m you@samrail.com -n
```

### 4.6 Smoke test from outside

```bash
# From your laptop:
curl -s https://api.samrail.com/healthz
curl -s https://api.samrail.com/.well-known/agent.json | jq .
ssh root@<VX1-IP> 'sudo journalctl -u govcapture-api -n 50' | grep -i error || echo "no errors"
ssh root@<VX1-IP> 'sudo certbot certificates'   # cert valid > 30 days
```

### 4.7 Update Vercel projects

Now that the API is live, set `NEXT_PUBLIC_API_BASE=https://api.samrail.com` on **both** Vercel projects (landing + web) and redeploy each (cache disabled).

### 4.8 §5.14 production-flip

ONLY after §4.6 verifies and Resend domain is verified:

```bash
ssh root@<VX1-IP>
sudo -u govcapture editor /opt/govcapture/.env
# Change: EMAIL_DRY_RUN=true → false

sudo systemctl restart govcapture-api.service

# Smoke test (from anywhere with the INTERNAL_API_KEY):
curl -X POST https://api.samrail.com/internal/cron/auto-pick-weekly-opportunity \
  -H "Authorization: Bearer <INTERNAL_API_KEY>"

curl -X POST https://api.samrail.com/internal/cron/weekly-opportunity-email \
  -H "Authorization: Bearer <INTERNAL_API_KEY>"

# If both succeed, enable the timers:
sudo systemctl enable --now govcapture-cron-auto-pick.timer
sudo systemctl enable --now govcapture-cron-weekly.timer
sudo systemctl list-timers | grep govcapture
```

### Track 4 verification gate

- [ ] `curl https://api.samrail.com/healthz` → 200 from outside the box
- [ ] `journalctl -u govcapture-api -n 50` clean
- [ ] `certbot certificates` shows cert valid > 30 days
- [ ] Both Vercel projects redeployed with `NEXT_PUBLIC_API_BASE=https://api.samrail.com`
- [ ] Smoke: prod /web waitlist signup → row in Supabase `waitlist_signups`

---

## Track 5 — Sprint G cross-repo verification (`1-2 days` USER+ENG, parallel with Track 4)

This requires `/root/michealaai` cooperation; can run in parallel with Track 4 if the orchestrator side is ready.

### 5.1 Update michealaai's `DATA-SOURCES.md`

Cross-repo work — can't be done from this repo. Per `devdocs/CAPABILITY_PACK_INTEGRATION.md` "Three Supabase projects" section, that file currently mislabels the GovCon DB. Add a row distinguishing:

- `ktygrvbpugqhfyibzirr` — Lance's competitive-intel reads (agencies, contractors, contracts, psc_win_patterns)
- `vvyxjdoenjujkxwbnzyl` — `agent_runs` pickup + writebacks (this pack's project)

Without this fix, Michaela polls the wrong project and never claims our agent_runs rows.

### 5.2 Mirror `INTERNAL_API_KEY`

The same string used on VX1's `/opt/govcapture/.env` must be in `/root/michealaai`'s env. The pack's `require_internal_actor` returns 401 on mismatch.

### 5.3 Verify

After §5.1+§5.2 and Track 4 done:

1. From prod `https://app.samrail.com/login`, sign in
2. Submit a goal at `/app/goal` — note the run-uuid in the URL
3. In `/root/michealaai`, watch logs — orchestrator should claim within ~5s
4. In browser, `/app/runs/<uuid>` SSE timeline should populate live
5. Check Supabase Studio: `action_packages` row created with caller's `owner_profile_id`

### 5.4 If `/root/michealaai` isn't ready

Use `make sse-stub RUN_ID=<uuid>` to publish a synthetic 20-event trace to Redis. Verifies the SSE pipeline (Redis → FastAPI → /web EventSource) without the orchestrator. Document Sprint G real-verification as v1.0.x owed.

---

## Track 6 — v1.0.0 tag (`~5 min` ENG, gated)

Gated on Tracks 1, 2, 4 (and Track 5 if not deferred).

### 6.1 Final all-suite gate

```bash
uv run pytest api/tests/ -q                          # ≥ 206 passed
uv run ruff check api && uv run mypy api             # both clean
make eval && make fixtures-validate                  # both clean
npm -w landing run build && npm -w web run build     # both clean
curl -s https://api.samrail.com/healthz              # 200
supabase migration list                              # local + remote synced
```

### 6.2 Release-notes commit

Append to `PRD.md` changelog:

```markdown
## v1.0.0 — 2026-MM-DD

First public release. Schema synced, VX1 prod live at api.samrail.com,
landing + web on Vercel pointed at samrail.com / app.samrail.com,
cross-repo verified (or stubbed) with /root/michealaai, eval gate live
(byte-exact deterministic), production email via Resend SMTP from
noreply@samrail.com.

Stack frozen at this tag:
- 11 deterministic skills, 58+ routes, 206+ tests, ruff/mypy clean
- §5.14 weekly opportunity email live
- Hosting: Vultr VX1 (FastAPI + nginx + Redis) + Vercel × 2 + Supabase
- Bench: Michaela + 6 workers in /root/michealaai (separate repo)
```

Update `devdocs/CURRENT_STATE.md` §10 — move "Next" items to "Done"
where applicable; add a §9 timeline row for the release.

### 6.3 Commit + tag + push

```bash
git add PRD.md devdocs/CURRENT_STATE.md devdocs/HANDOFF_PROMPT.md
git commit -m "docs(release): v1.0.0 — first public release

See PRD changelog and CURRENT_STATE §10 for state at this tag."

git tag -a v1.0.0 -m "SamRail v1.0.0 — first public release.

Production at https://samrail.com (landing) +
https://app.samrail.com (/web) + https://api.samrail.com (FastAPI).
See PRD.md and devdocs/CURRENT_STATE.md for state at tag time."

git push origin main --follow-tags
```

### 6.4 Cross-repo signal

In `/root/michealaai`, drop a CHANGELOG entry pinning v1.0.0 as the
integration target.

---

## Re-engagement script

| Trigger | Track |
|---|---|
| "Vercel redeployed; sign-in works on samrail.com" | Track 1 done; move to Track 4 prep |
| "Studio Auth + SMTP saved; test magic link delivered" | Track 2 done |
| "VX1 at <IP>; bootstrap done" | Track 4 §4.3 starts here |
| "API healthz 200 from outside" | Track 4 §4.7 (Vercel API_BASE update) |
| "EMAIL_DRY_RUN=false; first real send delivered" | Track 4 §4.8 done |
| "michealaai claimed run <uuid>; e2e green" | Track 5 done |
| "Tag v1.0.0" | Track 6 starts |

---

## Continuous verification gates

These hold at every commit on every track:

```bash
uv run pytest api/tests/ -q       # ≥ 206 passed
uv run ruff check api             # All checks passed
uv run mypy api                   # 0 errors
make eval                         # PASSes against committed goldens
make fixtures-validate            # 4/4 OK
git status --short                # clean (intended changes only)
```
