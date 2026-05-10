# Vultr VX1 Deployment Runbook (v1.2.5)

Native (no Docker) deploy of the FastAPI backend per PRD §7.6. Supabase
manages Postgres and object storage (PRD v1.2.3 §7.5; PRD v1.2.4 dropped
the on-box ORM/Alembic toolchain). The VX1 hosts the capability-pack API,
Redis pub/sub, and the TLS terminator. Michaela/Hermes orchestration runs
separately and calls this API.

| Component | Where it runs |
|---|---|
| FastAPI (gunicorn + UvicornWorker × 4) | systemd unit `govcapture-api.service`, listens on `127.0.0.1:8000` |
| Redis | system `redis-server.service` — SSE pub/sub bridge (PRD §7.5) |
| nginx (TLS terminator + reverse proxy) | system `nginx.service` |
| **Supabase project** (external) | Postgres + Storage + Auth (GoTrue) |
| Michaela/Hermes runtime (external) | `/root/michealaai` or its deployment target; not started by this API unit |

## 0. Prerequisites

- Vultr VX1 provisioned with **Ubuntu 24.04 LTS**
- Root SSH access (or a sudoer)
- A domain you control: `api.samrail.com`
- A Supabase project (create at https://supabase.com — Free tier is enough for MVP)
- The Supabase CLI on your local machine (or on the box): https://supabase.com/docs/guides/local-development/cli/getting-started

## 1. Create the Supabase project (one time)

1. https://supabase.com → New project. Region close to VX1.
2. **Settings → API** — capture `URL`, `anon public` key, and `service_role` key.
3. **Storage → New bucket** → `govcapture-attachments` (private, no public read).
4. Optional but recommended: under **Storage → Policies**, add a retention rule
   on the `raw/` prefix matching PRD §17 Q6 (30-day purge of original PDFs).
5. **Apply schema.** From your machine:
   ```bash
   supabase login
   supabase link --project-ref <your-project-ref>
   supabase db push     # applies every supabase/migrations/*.sql in order
   ```
   The migrations create the core govbase schema, the Michaela MVP layer
   (`profiles`, `opportunity_matches`, `documents`, `document_chunks`,
   `run_events`), and the ownership / provenance columns.

## 2. Provision the box

```bash
ssh root@<box-ip>
git clone https://github.com/caterpillarC15/govcon.git /tmp/govcon
sudo bash /tmp/govcon/infra/bootstrap.sh
```

`bootstrap.sh` is idempotent. It installs apt packages, configures `ufw`,
creates the `govcapture` user, sets up Redis, installs the API systemd
unit, and prints the next-step checklist. **It does not install Postgres**
(Supabase replaces it).

## 3. Clone the repo to `/opt/govcapture`

```bash
sudo -u govcapture git clone https://github.com/caterpillarC15/govcon.git /opt/govcapture
```

If the repo is private, use a deploy key:

```bash
sudo -u govcapture ssh-keygen -t ed25519 -f ~govcapture/.ssh/id_deploy -N ''
sudo cat ~govcapture/.ssh/id_deploy.pub   # add to GitHub: Settings → Deploy keys (read-only)
sudo -u govcapture bash -lc 'GIT_SSH_COMMAND="ssh -i ~/.ssh/id_deploy" git clone git@github.com:caterpillarC15/govcon.git /opt/govcapture'
```

## 4. Drop a `.env`

```bash
sudo -u govcapture install -m 0600 /dev/null /opt/govcapture/.env
sudo -u govcapture editor /opt/govcapture/.env
# Paste from .env.production.example, then fill in:
#   ANTHROPIC_API_KEY           — sk-ant-...
#   SUPABASE_URL                — https://<ref>.supabase.co
#   SUPABASE_SERVICE_ROLE_KEY   — server-only; bypasses RLS for internal writes
#   SUPABASE_ANON_KEY           — used by the JWT verifier
#   SUPABASE_STORAGE_BUCKET     — govcapture-attachments
#   INTERNAL_API_KEY            — long random; mirror to Michaela for internal writebacks
#   CORS_ALLOWED_ORIGINS        — your prod web origins, comma-separated
```

## 5. Install deps + start

```bash
sudo -u govcapture -H bash -lc 'cd /opt/govcapture && ~/.local/bin/uv sync'
sudo systemctl enable --now govcapture-api.service
sudo systemctl status govcapture-api --no-pager
```

There is no `alembic upgrade head` step anymore. Schema lives in
`supabase/migrations/*.sql` and is applied via `supabase db push` from
whichever machine has the Supabase CLI installed (typically your laptop,
not the box).

Sanity check directly against gunicorn:

```bash
curl http://127.0.0.1:8000/healthz
```

## 6. Wire nginx + TLS

Point your domain's `A` record at the box, wait for DNS to propagate, then:

```bash
sudo cp /opt/govcapture/infra/nginx/samrail.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/samrail.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d api.samrail.com --redirect --agree-tos -m you@samrail.com -n
```

Verify:

```bash
curl https://api.samrail.com/healthz
```

## 7. Wire the landing → API

In Vercel project `landing`:
**Settings → Environment Variables** → add
`NEXT_PUBLIC_API_BASE = https://api.samrail.com` for **Production**.
Trigger a redeploy.

The FastAPI CORS allowlist is driven by `CORS_ALLOWED_ORIGINS` in the box's
`.env` plus the regex `*.vercel.app` baked into `api/main.py`, so the prod
landing can hit the API immediately.

## 8. Subsequent deploys

```bash
sudo -u govcapture -H bash -lc '/opt/govcapture/infra/deploy.sh'
sudo systemctl restart govcapture-api
sudo systemctl status govcapture-api --no-pager
```

`deploy.sh` does `git reset --hard origin/main` + `uv sync --frozen`. The
systemd restart picks up the new code. Schema changes are applied
**separately** from your laptop:

```bash
supabase db push     # any new files under supabase/migrations/
```

## 9. Operations

### Logs
```bash
sudo journalctl -u govcapture-api -f                # API
sudo tail -F /var/log/nginx/access.log              # nginx
# Supabase Postgres logs: dashboard → Project → Logs → Postgres
# Supabase Storage logs:  dashboard → Project → Logs → Storage
# Supabase Auth logs:     dashboard → Project → Logs → Auth
```

### Backups

**Supabase handles Postgres backups** — Pro tier has point-in-time restore;
Free tier has 7-day rolling. No on-box pg_dump cron.

**Storage backups** are out of scope for v1.2.5 (the bucket is the system of
record for raw PDFs; parsed text is regeneratable from `document_chunks`).
If you want belt-and-suspenders, use Supabase Storage replication or
`aws s3 sync` against the S3-compatible endpoint.

### Resource usage
```bash
htop                                                # quick
sudo systemctl status govcapture-api redis-server nginx --no-pager
df -h /var/lib /var/log
```

### Tune worker count
PRD §7.6 says 4–8 workers. Edit `infra/systemd/govcapture-api.service`,
change `--workers 4` to up to `--workers 8`, then:
```bash
sudo cp infra/systemd/govcapture-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart govcapture-api
```

## 10. Rollback

```bash
# Code rollback — pick a known-good commit and reset to it.
cd /opt/govcapture
sudo -u govcapture git fetch origin
sudo -u govcapture git reset --hard <good-commit-sha>
sudo -u govcapture -H bash -lc '~/.local/bin/uv sync --frozen'
sudo systemctl restart govcapture-api
```

Schema rollback is handled in Supabase: revert the offending migration in
`supabase/migrations/`, write the inverse migration, `supabase db push`.
**There is no `alembic downgrade` anymore.**

## 11. Weekly opportunity email (PRD §5.14, v1.2.6)

A standalone outbound channel: one curated federal opportunity per week to opted-in waitlist signups via Resend. **Implementation status: spec'd, not yet built.** The bullets below are the runbook devs follow when the work lands.

### Resend account + domain (one-time, manual)

1. Sign up at https://resend.com (free tier covers 3,000/month).
2. Add `samrail.com` at https://resend.com/domains. Copy the SPF (TXT) and DKIM (3 × CNAME) records into your DNS. Wait for verification (usually <10 min).
3. Create a sending API key at https://resend.com/api-keys with `send_emails` scope only. Capture the `re_…` value.
4. Until step 2 verifies, the Resend sandbox sender (`onboarding@resend.dev`) only delivers to the Resend account-owner inbox — fine for the first dev test, useless for production.

### Drop secrets into the box

Add to `/opt/govcapture/.env`:

```bash
RESEND_API_KEY=re_…
RESEND_FROM_EMAIL=SamRail <noreply@samrail.com>
EMAIL_PUBLIC_BASE_URL=https://api.samrail.com
EMAIL_UNSUBSCRIBE_SECRET=$(openssl rand -hex 32)
EMAIL_LEGAL_FOOTER_ADDRESS="Your Co · 123 Main St · Austin, TX 78701"
EMAIL_DRY_RUN=true
```

Keep `EMAIL_DRY_RUN=true` until the first verified-domain test send lands.

### Apply the schema migration

```bash
sudo -u govcapture -H bash -lc 'cd /opt/govcapture && supabase db push'
```

This runs `supabase/migrations/<timestamp>_add_email_preferences_and_logs.sql` which:
- Adds `weekly_opportunity_enabled`, `unsubscribed_at`, `unsubscribed_reason`, `bounced_at`, `complained_at`, `confirmed_at`, `last_emailed_at` to `waitlist_signups`.
- Creates `weekly_opportunity_picks` (one row per `week_key`).
- Creates `weekly_opportunity_email_log` (UNIQUE on `(email, week_key, email_type)` for idempotency).

### Install the systemd timers

Two units, decoupled so a failed pick never breaks the send:

```bash
sudo cp infra/systemd/govcapture-cron-auto-pick.service /etc/systemd/system/
sudo cp infra/systemd/govcapture-cron-auto-pick.timer  /etc/systemd/system/
sudo cp infra/systemd/govcapture-cron-weekly.service   /etc/systemd/system/
sudo cp infra/systemd/govcapture-cron-weekly.timer     /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now govcapture-cron-auto-pick.timer
sudo systemctl enable --now govcapture-cron-weekly.timer
```

Cadence:
- `govcapture-cron-auto-pick.timer` — Sunday 22:00 UTC. Picks the week's opportunity. Idempotent on `(week_key)`.
- `govcapture-cron-weekly.timer` — Monday 14:00 UTC. Sends to eligible recipients. Idempotent on `(email, week_key, email_type)`.

Both `curl` `127.0.0.1:8000/internal/cron/...` with `Authorization: Bearer ${INTERNAL_API_KEY}` from `/opt/govcapture/.env`. nginx returns 404 for `/internal/*` — these routes are loopback-only.

### Manual fire (dry-run safe)

```bash
# Pick this week manually (overrides the auto-picker):
sudo -u govcapture -H bash -lc 'cd /opt/govcapture && \
  uv run python scripts/pick_weekly_opportunity.py --week 2026-W19 --opportunity-id <uuid>'

# Trigger the auto-picker on demand:
curl -fsS -X POST -H "Authorization: Bearer $INTERNAL_API_KEY" \
  http://127.0.0.1:8000/internal/cron/auto-pick-weekly-opportunity

# Trigger the email send on demand (respects EMAIL_DRY_RUN):
curl -fsS -X POST -H "Authorization: Bearer $INTERNAL_API_KEY" \
  http://127.0.0.1:8000/internal/cron/weekly-opportunity-email

# Force a one-off dry-run regardless of env:
curl -fsS -X POST -H "Authorization: Bearer $INTERNAL_API_KEY" \
  'http://127.0.0.1:8000/internal/cron/weekly-opportunity-email?dry_run=true'
```

### Logs

```bash
sudo journalctl -u govcapture-cron-auto-pick -f
sudo journalctl -u govcapture-cron-weekly -f
sudo journalctl -u govcapture-api -f | grep weekly_opportunity_email
```

Per-attempt JSON logs hash recipient emails (SHA-256). Resend message IDs are kept; raw addresses, API keys, and token values never enter logs.

### Going live

1. Confirm a test send to your own verified inbox.
2. Inspect the rendered email — subject < 78 chars, footer address present, unsubscribe link returns the success page when clicked.
3. Edit `/opt/govcapture/.env`: `EMAIL_DRY_RUN=false`.
4. `sudo systemctl restart govcapture-api`.
5. Manually fire the cron with `?dry_run=true` to confirm settings load.
6. The next Monday 14:00 UTC sends for real.

### Rollback

`EMAIL_DRY_RUN=true` + `systemctl restart govcapture-api` halts all sends immediately. Already-claimed `weekly_opportunity_email_log` rows for the current week stay (preventing accidental re-sends if you toggle back).

## 12. Common gotchas

| Symptom | Likely cause | Fix |
|---|---|---|
| `502 Bad Gateway` from nginx | API unit not running | `sudo systemctl status govcapture-api`; check journalctl |
| `401 Unauthorized` on user routes | Missing or expired Supabase JWT | Have the caller refresh through `auth.signInWith…` and retry. Check `SUPABASE_ANON_KEY` matches the project. |
| `401 Unauthorized` on writeback routes | Missing `X-Internal-API-Key` header or wrong value | Michaela worker/tool calls must send `INTERNAL_API_KEY`. User JWTs cannot reach those routes by design. |
| `503 Supabase auth is not configured` | `SUPABASE_URL` empty | Drop a real value into `.env`, restart the unit. |
| `503 Internal API key is not configured` | `INTERNAL_API_KEY` empty | Generate a long random; mirror to the bench's environment. |
| `SUPABASE_SERVICE_ROLE_KEY is not configured` from `api/storage.py` | `.env` missing the var | Add it; the FastAPI service-role mediates Storage access |
| TLS cert renewal failed | port 80 blocked or DNS changed | `sudo certbot renew --dry-run` to surface the real error |
