# Vultr VX1 Deployment Runbook (v1.2.4)

Native (no Docker) deploy of the FastAPI backend per PRD §7.6. Supabase
manages Postgres and object storage (PRD v1.2.3 §7.5; PRD v1.2.4 dropped
the on-box ORM/Alembic toolchain). The VX1 hosts the app, the agent
runtime, the SSE pub/sub, and the TLS terminator.

| Component | Where it runs |
|---|---|
| FastAPI (gunicorn + UvicornWorker × 4) | systemd unit `govcapture-api.service`, listens on `127.0.0.1:8000` |
| Hermes runtime (Michaela + bench) | subprocess of FastAPI (same `govcapture` user) |
| Redis | system `redis-server.service` — SSE pub/sub bridge (PRD §7.5) |
| nginx (TLS terminator + reverse proxy) | system `nginx.service` |
| **Supabase project** (external) | Postgres + Storage + Auth (GoTrue) |

## 0. Prerequisites

- Vultr VX1 provisioned with **Ubuntu 24.04 LTS**
- Root SSH access (or a sudoer)
- A domain you control, e.g. `api.govcapture.example`
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
#   INTERNAL_API_KEY            — long random; required for sub-agent writeback routes
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
sudo cp /opt/govcapture/infra/nginx/govcapture.conf /etc/nginx/sites-available/
sudo sed -i 's|api.your-domain.example|api.govcapture.example|g' /etc/nginx/sites-available/govcapture.conf
sudo ln -sf /etc/nginx/sites-available/govcapture.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d api.govcapture.example --redirect --agree-tos -m you@example.com -n
```

Verify:

```bash
curl https://api.govcapture.example/healthz
```

## 7. Wire the landing → API

In Vercel project `landing`:
**Settings → Environment Variables** → add
`NEXT_PUBLIC_API_BASE = https://api.govcapture.example` for **Production**.
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

**Storage backups** are out of scope for v1.2.4 (the bucket is the system of
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

## 11. Common gotchas

| Symptom | Likely cause | Fix |
|---|---|---|
| `502 Bad Gateway` from nginx | API unit not running | `sudo systemctl status govcapture-api`; check journalctl |
| `401 Unauthorized` on user routes | Missing or expired Supabase JWT | Have the caller refresh through `auth.signInWith…` and retry. Check `SUPABASE_ANON_KEY` matches the project. |
| `401 Unauthorized` on writeback routes | Missing `X-Internal-API-Key` header or wrong value | Sub-agent toolset must send `INTERNAL_API_KEY` from `.env`. User JWTs cannot reach those routes by design. |
| `503 Supabase auth is not configured` | `SUPABASE_URL` empty | Drop a real value into `.env`, restart the unit. |
| `503 Internal API key is not configured` | `INTERNAL_API_KEY` empty | Generate a long random; mirror to the bench's environment. |
| `SUPABASE_SERVICE_ROLE_KEY is not configured` from `api/storage.py` | `.env` missing the var | Add it; the FastAPI service-role mediates Storage access |
| TLS cert renewal failed | port 80 blocked or DNS changed | `sudo certbot renew --dry-run` to surface the real error |
