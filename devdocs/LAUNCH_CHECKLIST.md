# Launch Checklist — what needs to happen for v1.0.0

> **Companion to** `devdocs/CURRENT_STATE.md` (state of the repo) and
> `docs/superpowers/plans/2026-05-10-finish-it-all.md` (the executable plan).
> This file is the operational shopping list — exact commands, exact
> credentials needed, ordered by dependency. Read top to bottom; everything
> is sequenced so each step's prerequisites are satisfied by an earlier
> step (or marked `[USER]` if it depends on you).

---

## 0 · Snapshot — where we are (2026-05-10)

| Layer | Status |
|---|---|
| Backend | 53 routes · 11 skills · 186 tests · ruff/mypy clean |
| Schema | All 10 migrations applied to remote Supabase (incl. drift placeholders) |
| `/web` | Auth-hardened (`requireUser` helper) · ApprovalGate persisted server-side · SSE memoize/dedupe shipped |
| `/landing` | SEO + a11y baseline shipped; brand strings aligned with `LANDING_BRIEF.md` |
| Eval | Goldens bootstrapped (byte-exact, deterministic per PRD v1.2.6); `make eval` is the regression gate |
| MCP | `mcp-server-samrail` package wraps `/api/v1/tools` |
| Infra | VX1 live at `api.samrail.com` (TLS via certbot · systemd units running · §5.14 timers staged, awaiting `EMAIL_DRY_RUN=false` flip) |
| Email Channel A (auth) | ✅ Resend SMTP wired in Supabase Studio · domain `samrail.com` verified · sender `noreply@samrail.com` |
| Email Channel B (§5.14 weekly opportunity) | **shipped** — migration + auto-picker + send job + unsubscribe + curator override + 13 tests; behind `EMAIL_DRY_RUN=true` until prod-flip step (§4 below) |

---

## 1 · §5.14 Weekly Opportunity Email — SHIPPED

PRD §5.14 (Weekly Opportunity Email) is **implemented and merged**. Behind
`EMAIL_DRY_RUN=true` (the safe default) the send paths claim log slots
and render emails but never call Resend — flipping to false is gated by
the `api/config.py` `model_validator` which refuses to start unless
`RESEND_API_KEY`, `EMAIL_UNSUBSCRIBE_SECRET`, and `EMAIL_LEGAL_FOOTER_ADDRESS`
are all populated.

What landed (commits `685a8b5`, `1910631`, `3a916a4`):

| Component | File |
|---|---|
| Schema | `supabase/migrations/20260510130000_weekly_opportunity_email.sql` |
| Config + production guard | `api/config.py` (14 env vars + `model_validator`) |
| HMAC token service | `api/services/unsubscribe_token.py` |
| Resend HTTP client | `api/services/email_sender.py` |
| Repositories | `api/repositories/weekly_opportunity_{pick,email_log}.py` |
| Safety filters | `api/jobs/weekly_opportunity_safety.py` |
| Auto-picker | `api/jobs/auto_pick_weekly_opportunity.py` |
| Send job | `api/jobs/weekly_opportunity_email.py` |
| Email rendering | `api/email/render.py` |
| Routes | `api/routes/email_subscriptions.py` (3 routes) |
| Tests | `api/tests/test_weekly_opportunity_email.py` (13 tests) |
| systemd timers | `infra/systemd/govcapture-cron-{auto-pick,weekly}.{service,timer}` |
| Curator override | `scripts/pick_weekly_opportunity.py` |

What still needs to happen for §5.14 to actually send mail in production:

1. `[USER]` sign up for Resend, verify your sending domain (SPF + DKIM + DMARC)
2. `[USER]` set `RESEND_API_KEY`, `EMAIL_UNSUBSCRIBE_SECRET` (`openssl rand -hex 32`), and `EMAIL_LEGAL_FOOTER_ADDRESS` on VX1 `.env`
3. `[USER]` set `RESEND_FROM_EMAIL=SamRail <noreply@samrail.com>` (the default is the Resend sandbox sender, which only delivers to the account owner)
4. `[USER]` smoke-test with `EMAIL_DRY_RUN=true` first; review log rows in `weekly_opportunity_email_log` (status=`dry_run`)
5. `[USER]` flip `EMAIL_DRY_RUN=false` and trigger a manual run via `POST /internal/cron/weekly-opportunity-email` from inside the VX1 with the bearer
6. `[USER]` enable both timers: `sudo systemctl enable --now govcapture-cron-auto-pick.timer govcapture-cron-weekly.timer`

---

## 2 · Order of operations

Each row is a phase. Dependencies are explicit. `[USER]` rows need credentials/access I don't have. `[ENG]` rows I can execute autonomously the moment the prerequisite clears.

```
Phase 5 [USER]   Resend SMTP for Channel A magic-link (Studio config + DNS)
        +        §1 production gates above (Channel B — same Resend account
        +        if you want one bill, or a second sending key)
   ↓
Phase 6 [USER]   Vultr VX1 production deploy (now also runs the §5.14 timers
        +        once they're enabled in Step 6 of §1 above)
   ↓
Phase 7 [USER+ENG]  Sprint G cross-repo verification (or SSE-stub-only fallback)
   ↓
Phase 8 [ENG]       Eval goldens — already byte-exact + free (PRD v1.2.6)
   ↓
Phase 9 [ENG]    v1.0.0 tag + final state docs (gated on all above)
```

Phases 5/6 are the slowest because each needs ≥1 third-party account + DNS propagation. Plan to do them on the same day; DNS records for both can propagate while other work continues. With §5.14 already merged, Phase 5 now covers BOTH email channels (auth via SMTP + weekly opportunity via Resend HTTP).

---

## 3 · Phase 5 — Resend SMTP for Channel A magic-link

**Why:** Supabase default SMTP throttles to 4 emails/hour project-wide. Public launch needs a real provider.

### 5.1 Resend account [USER]

1. Sign up at https://resend.com
2. Add domain (e.g., `samrail.com` or `mail.samrail.com`)
3. Add SPF + DKIM × 3 + (optional) DMARC records at your DNS provider — Resend dashboard tells you the exact records
4. Wait for verification (≤ 30 min)
5. Generate an API key under **API Keys** → scope: **Sending access only**

### 5.2 Smoke test from Resend dashboard [USER]

Send a test email to your own inbox via the Resend dashboard. Confirm:
- Arrives within 60 s
- Lands in inbox (not spam)
- From-address shows `noreply@samrail.com`

### 5.3 Configure Supabase Auth SMTP [USER]

In Supabase Studio → **Authentication** → **Email Templates** → **SMTP Settings**, enable Custom SMTP and fill:

| Field | Value |
|---|---|
| Sender email | `noreply@samrail.com` |
| Sender name | `SamRail` |
| Host | `smtp.resend.com` |
| Port | `465` (SSL) |
| Username | `resend` |
| Password | `<Resend API key from 5.1>` |

Save.

### 5.4 Smoke test prod magic-link [USER]

From a clean browser (no session), request a magic link via your local `/web` against the linked Supabase project. Verify:
- Email arrives < 60 s from `noreply@samrail.com`
- Lands in inbox on Gmail (test) and Outlook (test)
- Clicking the link signs you in to `/app`
- Resend dashboard → Logs shows a `delivered` event

### 5.5 Done [ENG]

I update `devdocs/CURRENT_STATE.md` §10 with "Resend SMTP wired YYYY-MM-DD" and commit. No more code changes for Channel A.

---

## 4 · Phase 6 — VX1 production deploy

**Authoritative spec:** `infra/RUNBOOK.md` §§0–8. This section is a checklist; when in doubt the runbook wins.

### 6.1 Provision the box [USER]

1. Vultr → New Instance → **VX1**, **Ubuntu 24.04 LTS**, ≥ 16 vCPU / 64 GB
2. Upload SSH public key
3. Capture the public IP
4. Decide three domains (note them in a scratch file):
   - `api.samrail.com` — FastAPI behind nginx
   - `app.samrail.com` (or `samrail.com` direct) — `/web`
   - `samrail.com` (or `marketing.samrail.com`) — `/landing`

### 6.2 Bootstrap [USER]

```bash
ssh root@<VX1-IP>
git clone https://github.com/caterpillarC15/govcon.git /tmp/govcon
sudo bash /tmp/govcon/infra/bootstrap.sh
```

Expected: 7 numbered steps complete; `redis-cli ping` → `PONG`; ufw shows ports 22/80/443 open.

### 6.3 Clone repo + drop `.env` [USER]

```bash
sudo -u govcapture git clone https://github.com/caterpillarC15/govcon.git /opt/govcapture
INTERNAL_KEY=$(openssl rand -hex 32)   # mirror to /root/michealaai later
sudo -u govcapture install -m 0600 /dev/null /opt/govcapture/.env
sudo -u govcapture editor /opt/govcapture/.env
```

Paste from `.env.production.example` and fill:

```
# PRD v1.2.6: every skill is deterministic. Anthropic, model selection,
# and budget caps live with Michaela in /root/michealaai. This repo's
# .env carries Supabase + Resend + Redis + INTERNAL_API_KEY only.
SUPABASE_URL             — https://vvyxjdoenjujkxwbnzyl.supabase.co
SUPABASE_SERVICE_ROLE_KEY — sb_secret_…
SUPABASE_ANON_KEY        — sb_publishable_…
SUPABASE_STORAGE_BUCKET  — govcapture-attachments
INTERNAL_API_KEY         — $INTERNAL_KEY  (the openssl rand value)
REDIS_URL                — redis://localhost:6379/0
CORS_ALLOWED_ORIGINS     — https://app.samrail.com,https://samrail.com
NEXT_PUBLIC_API_BASE     — https://api.samrail.com   (for parity; only /web reads this)

# §5.14 weekly opportunity email — keep EMAIL_DRY_RUN=true for first deploy.
RESEND_API_KEY           — re_…  (sending-scope key)
RESEND_FROM_EMAIL        — SamRail <noreply@samrail.com>
EMAIL_PUBLIC_BASE_URL    — https://api.samrail.com
EMAIL_UNSUBSCRIBE_SECRET — $(openssl rand -hex 32)  (DIFFERENT from any dev value)
EMAIL_LEGAL_FOOTER_ADDRESS — "Acme Inc, 123 Main St, …"   (CAN-SPAM physical address)
EMAIL_DRY_RUN            — true  (flip to false only after smoke test)
EMAIL_AUTO_PICK_MIN_SCORE — 60
EMAIL_AUTO_PICK_MAX_CANDIDATES — 20
EMAIL_REQUIRE_DOUBLE_OPT_IN — false
```

### 6.4 Install deps + start systemd [USER]

```bash
sudo -u govcapture -H bash -lc 'cd /opt/govcapture && ~/.local/bin/uv sync'
sudo systemctl enable --now govcapture-api.service
sudo systemctl status govcapture-api --no-pager
curl http://127.0.0.1:8000/healthz
```

Expected: status `active (running)`; healthz returns 200 with supabase + redis green.

### 6.5 Wire nginx + TLS [USER]

```bash
# DNS first — A record api.samrail.com → VX1 IP. Wait for propagation.
dig +short api.samrail.com   # from your laptop, should resolve to VX1 IP

sudo cp /opt/govcapture/infra/nginx/govcapture.conf /etc/nginx/sites-available/
sudo sed -i 's|api.your-domain.example|api.samrail.com|g' /etc/nginx/sites-available/govcapture.conf
sudo ln -sf /etc/nginx/sites-available/govcapture.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d api.samrail.com --redirect --agree-tos -m you@samrail.com -n
```

### 6.6 Smoke test from outside [USER]

```bash
# From your laptop, NOT the box:
curl -s https://api.samrail.com/healthz
curl -s https://api.samrail.com/.well-known/agent.json | jq .
ssh root@<VX1-IP> 'sudo journalctl -u govcapture-api -n 50' | grep -i error || echo "no errors"
ssh root@<VX1-IP> 'sudo certbot certificates'   # cert valid > 30 days
```

### 6.7 Vercel — point `/landing` + `/web` at prod API [USER]

In each Vercel project → Settings → Environment Variables (Production scope):

```
NEXT_PUBLIC_API_BASE        https://api.samrail.com
NEXT_PUBLIC_SUPABASE_URL    https://vvyxjdoenjujkxwbnzyl.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY  sb_publishable_…
```

Trigger redeploy.

### 6.8 Done [ENG]

I update `devdocs/CURRENT_STATE.md` and `devdocs/HANDOFF_PROMPT.md` with the prod URL + verified-state line. Commit + push.

---

## 5 · Phase 7 — Sprint G cross-repo verification (or SSE-stub fallback)

Two flavors. Pick one — both verify the SSE pipeline works end-to-end.

### 7-stub · Standalone verification [USER+ENG]  ⏱ 5 min

Validates that prod's nginx + gunicorn streams SSE correctly, without `/root/michealaai`.

```bash
# 1. Sign in to https://app.samrail.com/login
# 2. Submit a goal at /app/goal — note the run-uuid in the URL
# 3. From your laptop, against your dev API (or prod with SSH tunnel to Redis):
make sse-stub RUN_ID=<run-uuid>   DELAY_MS=500
# 4. In another browser tab on /app/runs/<run-uuid>, watch the timeline populate (~10 s)
```

Verifies: 8/8 trace event types render; ApprovalGate gates the action package; SSE proxy doesn't disconnect under nginx.

### 7-real · Cross-repo end-to-end [USER+ENG]  ⏱ 1–2 days

Real verification with the orchestrator.

1. **`[USER]`** Mirror `INTERNAL_API_KEY` from VX1 `.env` into `/root/michealaai`'s env.
2. **`[USER]`** Confirm `/root/michealaai` is on a commit that implements the pickup contract documented in `devdocs/CAPABILITY_PACK_INTEGRATION.md`.
3. **`[USER]`** Trigger a real run from prod `/web` (login → profile → goal). Note the run-uuid.
4. **`[USER]`** Watch `/root/michealaai` logs: orchestrator should claim within ≤ 5 s.
5. **`[USER]`** Watch the `/app/runs/<run-uuid>` SSE timeline populate from real events.
6. **`[ENG]`** I verify in Supabase Studio:
   - `agent_runs` row reaches `status=complete`
   - `action_packages` row created with caller's `owner_profile_id`
   - All run events visible in `run_events` audit table
7. **`[ENG]`** I update `devdocs/CAPABILITY_PACK_INTEGRATION.md` "Known unknowns" → "verified" + commit.

### Decision

If `/root/michealaai` is ready: do **7-real**.
If not: ship v1.0.0 on **7-stub** alone. Add a "Known limitation" line in `CURRENT_STATE.md` noting the orchestrator e2e is owed in v1.0.x.

---

## 6 · Phase 8 — Eval goldens (already bootstrapped, byte-exact)

PRD v1.2.6 made every skill deterministic, so `make eval` is now a
**byte-exact** regression gate against goldens already committed under
`fixtures/<slug>/goldens/`. No LLM call, no Anthropic key, no budget.
The harness PASSes today; treat it like the test suite.

### 8.1 Daily-use [ENG]

```bash
make eval         # diff committed goldens vs current skill output
```

Run on every PR that touches `api/skills/`, `schemas/*.json`, or any
fixture under `fixtures/`. Failure means a skill's behavior drifted —
either the change is intentional (and the golden needs re-bootstrapping
in 8.2) or it's a regression (fix the skill).

### 8.2 Re-bootstrap when behavior changes intentionally [ENG]

```bash
make eval-bootstrap            # rewrites every golden from current skill output
git diff fixtures/*/goldens/   # hand-review what changed before committing
git add fixtures/*/goldens/
git commit -m "feat(eval): re-bootstrap goldens — <what changed and why>"
```

Hand-review IS the gate. A drifted golden is only correct if the human
agrees the new behavior is the intended one.

---

## 7 · Phase 9 — v1.0.0 tag

**Prerequisites:** Phases 5, 6, 7 (stub or real), 8 all done.

### 9.1 Final all-suite verification [ENG]

```bash
uv run pytest api/tests/ -q                          # ≥ 186 passed
uv run ruff check api && uv run mypy api             # both clean
make fixtures-validate && make eval                  # both green
npm -w landing run lint && npm -w landing run build  # clean
npm -w web run lint && npm -w web run typecheck && npm -w web run build  # clean
curl -s https://api.samrail.com/healthz            # 200
supabase migration list                              # local + remote synced
git status --short                                   # clean
```

### 9.2 Release notes commit + tag [ENG]

I author the v1.0.0 release-notes commit (PRD changelog + CURRENT_STATE refresh), create the annotated tag, and push:

```bash
git tag -a v1.0.0 -m "SamRail v1.0.0 — first public release"
git push origin main --follow-tags
```

### 9.3 Cross-repo announce [USER]

Drop a `CHANGELOG` entry in `/root/michealaai` noting v1.0.0 is the integration target.

---

## 8 · Credentials shopping list

Single list of everything you need to procure before resuming. Most are free.

| # | Credential | Where | Cost | Used in |
|---|---|---|---|---|
| 1 | ~~Real `ANTHROPIC_API_KEY`~~ — **dropped at PRD v1.2.6**; pack carries no LLM credential | — | — | — |
| 2 | Vultr account + VX1 instance | my.vultr.com | ~$96/mo for VX1 | Phase 6 |
| 3 | A domain you control | (any registrar) | ~$10/yr | Phase 5/6 |
| 4 | DNS record write access | (your registrar) | free | Phase 5/6 |
| 5 | Resend account + verified domain | resend.com | free tier covers magic-link | Phase 5 |
| 6 | Resend API key (sending scope) | resend.com → API Keys | free | Phase 5 |
| 7 | Supabase Studio access | already have | free | Phase 5 |
| 8 | Vercel project access for `/web` + `/landing` | already have | free | Phase 6.7 |
| 9 | CAN-SPAM legal mailing address | your lawyer or company | free | §5.14 (`EMAIL_LEGAL_FOOTER_ADDRESS`) |
| 10 | (if 7-real) `/root/michealaai` ready | your other repo | — | Phase 7 |

---

## 9 · §5.14 production-flip gates

§5.14 is shipped behind `EMAIL_DRY_RUN=true`. Production sending starts when:

- `RESEND_API_KEY` set on VX1 — sending-scope key from a verified-domain Resend account
- `EMAIL_UNSUBSCRIBE_SECRET` set on VX1 — `openssl rand -hex 32`, DIFFERENT from any dev value
- `EMAIL_LEGAL_FOOTER_ADDRESS` set on VX1 — CAN-SPAM physical mailing address
- `RESEND_FROM_EMAIL` points at a verified domain — NOT `onboarding@resend.dev` (sandbox only delivers to the Resend account owner)
- Smoke-test sequence:
  1. With `EMAIL_DRY_RUN=true`, trigger `POST /internal/cron/auto-pick-weekly-opportunity` — verify a `weekly_opportunity_picks` row appears with `picker_audit.pick.opportunity_id` populated
  2. Trigger `POST /internal/cron/weekly-opportunity-email` — verify `weekly_opportunity_email_log` rows appear with `status='dry_run'`
  3. Flip `EMAIL_DRY_RUN=false`, restart `govcapture-api.service`
  4. Send to your own inbox first: pick yourself as the sole eligible subscriber (`update waitlist_signups set unsubscribed_at = now() where email != 'you@…'`), trigger send, verify Gmail/Outlook delivery + List-Unsubscribe header + footer address
  5. Re-enable other subscribers (clear the temporary unsubscribed_at), enable the systemd timers:
     `sudo systemctl enable --now govcapture-cron-auto-pick.timer govcapture-cron-weekly.timer`

---

## 10 · Things explicitly OUT of scope for v1.0.0

Same as `docs/superpowers/plans/2026-05-10-finish-it-all.md`:

- CI/GitHub Actions
- Sentry/Grafana/structured logging
- FedRAMP/FISMA/CMMC
- i18n / dark mode / optimistic UI / password fallback auth
- shadcn/ui or any component-library introduction
- Native MCP HTTP/SSE transport (stdio only in v1)
- Per-tool API-key scopes (every key gets `tools:*`)
- Resolving the 2 remote-drift placeholder migrations into vendored equivalents (post-v1 schema squash)
- Native `hermes_plugin_govcapture/` Python plugin (MCP bridge fills the role for v1)

---

## 11 · How to resume — re-engagement script

When any blocker clears, drop me a one-liner. Suggested phrasing:

| Blocker cleared | Tell me |
|---|---|
| Skill behavior intentionally changed | "Re-bootstrap goldens" — I run `make eval-bootstrap`, you hand-review the diff, we commit |
| Resend SMTP configured in Studio | "Verify Phase 5 done" — I run a magic-link smoke test |
| VX1 reachable + .env in place | "VX1 at <IP>, domain <domain>" — I walk through 6.4–6.8 |
| `/root/michealaai` orchestrator ready | "michealaai is on commit <sha>" — I run Phase 7-real |
| §5.14 ready to flip out of dry-run | "Resend keys are in VX1 .env" — I run the §9 smoke-test sequence |
| All four above | "Tag v1.0.0" — I run §7.1 verification + tag + push |

---

## 12 · Doc maintenance

Update this file (a) when a phase completes (mark done + commit), (b) when a new ship-blocker is discovered, (c) when scope decisions change. Keep it as the single answer to "what is v1.0.0 waiting on?".
