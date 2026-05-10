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
| Eval | 15 fixture × skill `eval_inputs` authored; goldens NOT yet bootstrapped |
| MCP | `mcp-server-govcapture` package wraps `/api/v1/tools` |
| Infra | `bootstrap.sh`/`deploy.sh`/systemd/nginx authored + bash-syntax-clean; never executed in prod |
| Email Channel A (auth) | Supabase default SMTP (4/hr cap); needs swap to Resend SMTP |
| Email Channel B (§5.14 weekly opportunity) | PRD-spec'd; **zero code yet** |

---

## 1 · Decision required up front

**Is PRD §5.14 (Weekly Opportunity Email) in scope for v1.0.0, or v1.1.0?**

PRD §5.14 introduces:
- 3 new Supabase migrations (`waitlist_signups` columns + `weekly_opportunity_picks` + `weekly_opportunity_email_log`)
- A Resend HTTP client + HMAC unsubscribe token system
- An LLM auto-picker job (uses `score_fit` against a synthetic SMB profile)
- A curator override script (`scripts/pick_weekly_opportunity.py`)
- A Monday send job + systemd timer (`govcapture-cron-auto-pick.timer`)
- A `/unsubscribe` HTTP route
- 14 new env vars (already drafted in `.env.production.example`)

**Effort:** ~3–5 working days of clean implementation.

| Path | What ships in v1.0.0 | What ships in v1.1.0 |
|---|---|---|
| **A — §5.14 IN v1.0.0** | Pack + auth + magic-link + ApprovalGate + Weekly Opportunity Email end-to-end | (incremental polish) |
| **B — §5.14 OUT of v1.0.0** | Pack + auth + magic-link + ApprovalGate (no outbound marketing email) | §5.14 weekly opportunity email |

**Recommendation:** Path B unless the weekly opportunity email is what makes v1.0.0 demoable to first customers. Path B gets to a tag faster; §5.14 then ships as v1.1.0 within a week.

The rest of this doc assumes **Path B**. A `§5.14 addendum` section at the end shows the additional steps if you pick Path A.

---

## 2 · Order of operations (Path B)

Each row is a phase. Dependencies are explicit. `[USER]` rows need credentials/access I don't have. `[ENG]` rows I can execute autonomously the moment the prerequisite clears.

```
Phase 5 [USER]   Resend SMTP for Channel A magic-link (Studio config + DNS)
   ↓
Phase 6 [USER]   Vultr VX1 production deploy
   ↓
Phase 7 [USER+ENG]  Sprint G cross-repo verification (or SSE-stub-only fallback)
   ↓
Phase 8 [USER+ENG]  Eval goldens bootstrap (real ANTHROPIC_API_KEY + ~$0.50)
   ↓
Phase 9 [ENG]    v1.0.0 tag + final state docs (gated on all above)
```

Phases 5/6 are the slowest because each needs ≥1 third-party account + DNS propagation. Plan to do them on the same day; DNS records for both can propagate while other work continues.

---

## 3 · Phase 5 — Resend SMTP for Channel A magic-link

**Why:** Supabase default SMTP throttles to 4 emails/hour project-wide. Public launch needs a real provider.

### 5.1 Resend account [USER]

1. Sign up at https://resend.com
2. Add domain (e.g., `<your-domain>` or `mail.<your-domain>`)
3. Add SPF + DKIM × 3 + (optional) DMARC records at your DNS provider — Resend dashboard tells you the exact records
4. Wait for verification (≤ 30 min)
5. Generate an API key under **API Keys** → scope: **Sending access only**

### 5.2 Smoke test from Resend dashboard [USER]

Send a test email to your own inbox via the Resend dashboard. Confirm:
- Arrives within 60 s
- Lands in inbox (not spam)
- From-address shows `noreply@<your-domain>`

### 5.3 Configure Supabase Auth SMTP [USER]

In Supabase Studio → **Authentication** → **Email Templates** → **SMTP Settings**, enable Custom SMTP and fill:

| Field | Value |
|---|---|
| Sender email | `noreply@<your-domain>` |
| Sender name | `GovCon Bid Desk` |
| Host | `smtp.resend.com` |
| Port | `465` (SSL) |
| Username | `resend` |
| Password | `<Resend API key from 5.1>` |

Save.

### 5.4 Smoke test prod magic-link [USER]

From a clean browser (no session), request a magic link via your local `/web` against the linked Supabase project. Verify:
- Email arrives < 60 s from `noreply@<your-domain>`
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
   - `api.<your-domain>` — FastAPI behind nginx
   - `app.<your-domain>` (or `<your-domain>` direct) — `/web`
   - `<your-domain>` (or `marketing.<your-domain>`) — `/landing`

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
ANTHROPIC_API_KEY        — sk-ant-api…(real)
SUPABASE_URL             — https://vvyxjdoenjujkxwbnzyl.supabase.co
SUPABASE_SERVICE_ROLE_KEY — sb_secret_…
SUPABASE_ANON_KEY        — sb_publishable_…
SUPABASE_STORAGE_BUCKET  — govcapture-attachments
INTERNAL_API_KEY         — $INTERNAL_KEY  (the openssl rand value)
REDIS_URL                — redis://localhost:6379/0
CORS_ALLOWED_ORIGINS     — https://app.<your-domain>,https://<your-domain>
LLM_DEV_MODEL            — claude-haiku-4-5-20251001
LLM_SYNTH_MODEL          — claude-sonnet-4-6
RUN_BUDGET_USD           — 0.50
RUN_BUDGET_STEPS         — 40
RUN_BUDGET_SECONDS       — 360
NEXT_PUBLIC_API_BASE     — https://api.<your-domain>   (for parity; only /web reads this)
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
# DNS first — A record api.<your-domain> → VX1 IP. Wait for propagation.
dig +short api.<your-domain>   # from your laptop, should resolve to VX1 IP

sudo cp /opt/govcapture/infra/nginx/govcapture.conf /etc/nginx/sites-available/
sudo sed -i 's|api.your-domain.example|api.<your-domain>|g' /etc/nginx/sites-available/govcapture.conf
sudo ln -sf /etc/nginx/sites-available/govcapture.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d api.<your-domain> --redirect --agree-tos -m you@<your-domain> -n
```

### 6.6 Smoke test from outside [USER]

```bash
# From your laptop, NOT the box:
curl -s https://api.<your-domain>/healthz
curl -s https://api.<your-domain>/.well-known/agent.json | jq .
ssh root@<VX1-IP> 'sudo journalctl -u govcapture-api -n 50' | grep -i error || echo "no errors"
ssh root@<VX1-IP> 'sudo certbot certificates'   # cert valid > 30 days
```

### 6.7 Vercel — point `/landing` + `/web` at prod API [USER]

In each Vercel project → Settings → Environment Variables (Production scope):

```
NEXT_PUBLIC_API_BASE        https://api.<your-domain>
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
# 1. Sign in to https://app.<your-domain>/login
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

## 6 · Phase 8 — Eval goldens bootstrap

**Cost:** ~$0.40–$0.60 in Sonnet tokens (12 actual LLM calls; `score_fit` short-circuits on `reject` fixture without an LLM call). Inputs already authored — `make eval-bootstrap` is one command.

### 8.1 Replace placeholder Anthropic key [USER]

Edit `/Volumes/CS_Stuff/govcon/.env`:

```diff
- ANTHROPIC_API_KEY=sk-ant-test-placeholder
+ ANTHROPIC_API_KEY=sk-ant-api…<real key from console.anthropic.com>
```

### 8.2 Bootstrap goldens [ENG, ack budget first]

```bash
make eval-bootstrap                      # 12 LLM calls, ~$0.50
```

Writes `fixtures/<slug>/goldens/<skill>.json` per (fixture × skill) declared.

### 8.3 Hand-review every golden [USER+ENG]

I open each generated file and check:

| Skill | Golden must show |
|---|---|
| `parse_goal` (×3 fixtures) | keywords + naics_hints align with goal |
| `score_fit` strong-pursue | `decision=strong_pursue`, `total_score ≥ 85`, blockers empty |
| `score_fit` maybe | `decision=maybe`, `total_score 55–69`, suggests partner |
| `score_fit` reject | `decision=reject`, `total_score=0`, blockers populated (§11.1 short-circuit) |
| `detect_risks` | severities follow PRD §5.8 taxonomy |
| `generate_action_package` strong-pursue | `mode=full`, `human_approval_required[]` populated |
| `generate_action_package` reject | `mode=reject_summary`, no submit material |
| `extract_requirements` adversarial | output includes `unparseable=true` marker |

If any golden is wrong, we DO NOT commit it — fix the skill or the input first.

### 8.4 Lock as regression gate [ENG]

```bash
make eval                                 # passes against committed goldens
# deliberately mutate api/skills/score_fit/skill.py constant
make eval                                 # fails (gate is real)
git checkout api/skills/score_fit/skill.py
make eval                                 # passes again
```

Commit goldens.

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
curl -s https://api.<your-domain>/healthz            # 200
supabase migration list                              # local + remote synced
git status --short                                   # clean
```

### 9.2 Release notes commit + tag [ENG]

I author the v1.0.0 release-notes commit (PRD changelog + CURRENT_STATE refresh), create the annotated tag, and push:

```bash
git tag -a v1.0.0 -m "GovCon Bid Desk v1.0.0 — first public release"
git push origin main --follow-tags
```

### 9.3 Cross-repo announce [USER]

Drop a `CHANGELOG` entry in `/root/michealaai` noting v1.0.0 is the integration target.

---

## 8 · Credentials shopping list

Single list of everything you need to procure before resuming. Most are free.

| # | Credential | Where | Cost | Used in |
|---|---|---|---|---|
| 1 | Real `ANTHROPIC_API_KEY` | console.anthropic.com | pay-as-you-go (~$0.50 for eval bootstrap) | Phase 8 |
| 2 | Vultr account + VX1 instance | my.vultr.com | ~$96/mo for VX1 | Phase 6 |
| 3 | A domain you control | (any registrar) | ~$10/yr | Phase 5/6 |
| 4 | DNS record write access | (your registrar) | free | Phase 5/6 |
| 5 | Resend account + verified domain | resend.com | free tier covers magic-link | Phase 5 |
| 6 | Resend API key (sending scope) | resend.com → API Keys | free | Phase 5 |
| 7 | Supabase Studio access | already have | free | Phase 5 |
| 8 | Vercel project access for `/web` + `/landing` | already have | free | Phase 6.7 |
| 9 | (if Path A) CAN-SPAM legal mailing address | your lawyer or company | free | §5.14 |
| 10 | (if 7-real) `/root/michealaai` ready | your other repo | — | Phase 7 |

---

## 9 · Path A addendum — if §5.14 is in v1.0.0 scope

Adds Phase 5.5 between Phase 5 and Phase 6. Estimated +3–5 days.

### 5.5a · Implement §5.14 weekly opportunity email [ENG]

I do these in order, with TDD per finish-it-all conventions. Each is its own commit.

1. **Migration** — `supabase/migrations/<ts>_add_weekly_opportunity_email.sql`
   - Adds to `waitlist_signups`: `weekly_opportunity_enabled BOOLEAN DEFAULT TRUE`, `unsubscribed_at TIMESTAMPTZ`, `unsubscribed_reason TEXT`, `bounced_at TIMESTAMPTZ`, `complained_at TIMESTAMPTZ`, `confirmed_at TIMESTAMPTZ`, `last_emailed_at TIMESTAMPTZ`
   - Creates `weekly_opportunity_picks (week_key UNIQUE, opportunity_id, source, picker_audit JSONB, picked_at)`
   - Creates `weekly_opportunity_email_log (id, email, week_key, email_type, status, resend_message_id, sent_at, UNIQUE(email, week_key, email_type))`
   - RLS on all three; service role for the email job
2. **Config** — extend `api/config.py` with the 14 new env vars from `.env.production.example`; add the production refuse-to-start guard (`EMAIL_DRY_RUN=false` + any of `RESEND_API_KEY`/`EMAIL_UNSUBSCRIBE_SECRET`/`EMAIL_LEGAL_FOOTER_ADDRESS` empty → fail at boot)
3. **HMAC unsubscribe** — `api/services/unsubscribe_token.py` with `mint(email)` + `verify(token, email) -> bool` using `EMAIL_UNSUBSCRIBE_SECRET`
4. **Resend HTTP client** — `api/services/resend_client.py` with one function: `send(to, subject, html, text, headers={List-Unsubscribe})`. Honors `EMAIL_DRY_RUN`
5. **Curator override** — `scripts/pick_weekly_opportunity.py --week <key> --opportunity-id <uuid> [--allow-fixture]`
6. **Auto-picker** — `api/jobs/auto_pick_weekly_opportunity.py` — pulls last-7-days candidates, applies safety filters (`no narrow set-asides`, `deadline ≥ 14 days`, `no clearance/CUI keywords`, `US performance`), ranks survivors via `score_fit` against synthetic SMB profile, picks above `EMAIL_AUTO_PICK_MIN_SCORE`
7. **Send job** — `api/jobs/send_weekly_opportunity.py` — claims a slot atomically (`INSERT … ON CONFLICT DO NOTHING RETURNING id`), then `UPDATE … status='sent'` after Resend success
8. **Unsubscribe route** — `GET /unsubscribe?email=…&token=…` → verifies HMAC → marks `unsubscribed_at` → confirmation page
9. **systemd timers** — `infra/systemd/govcapture-cron-auto-pick.{service,timer}` (Sun 22:00 UTC), `govcapture-cron-send.{service,timer}` (Mon 14:00 UTC)
10. **Tests** — happy path, dry-run path, idempotency (same week_key won't double-send), unsubscribe-token tampering, safety-filter rejections
11. **Docs** — bump PRD changelog v1.2.5 → v1.2.6; update CURRENT_STATE §10

### 5.5b · Production gates [USER]

Before flipping `EMAIL_DRY_RUN=true → false`:

- `RESEND_API_KEY` set on VX1
- `EMAIL_UNSUBSCRIBE_SECRET` set on VX1 (different value from any dev secret)
- `EMAIL_LEGAL_FOOTER_ADDRESS` set on VX1 (CAN-SPAM physical address)
- `RESEND_FROM_EMAIL` points at a verified domain (NOT `onboarding@resend.dev` — that only delivers to the Resend account owner)
- A verified-domain test send to your own inbox via the dry-run-disabled job lands cleanly

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
| Real Anthropic key in `.env` | "Run eval bootstrap" |
| Resend SMTP configured in Studio | "Verify Phase 5 done" — I run a magic-link smoke test |
| VX1 reachable + .env in place | "VX1 at <IP>, domain <domain>" — I walk through 6.4–6.8 |
| `/root/michealaai` orchestrator ready | "michealaai is on commit <sha>" — I run Phase 7-real |
| §5.14 decision made | "Path A" or "Path B" — I start the corresponding phase |
| All four above | "Tag v1.0.0" — I run §9.1 verification + tag + push |

---

## 12 · Doc maintenance

Update this file (a) when a phase completes (mark done + commit), (b) when a new ship-blocker is discovered, (c) when scope decisions change. Keep it as the single answer to "what is v1.0.0 waiting on?".
