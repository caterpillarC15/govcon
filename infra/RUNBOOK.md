# Vultr VX1 Deployment Runbook (v1.2.3)

Native (no Docker) deploy of the FastAPI backend per PRD §7.6. Postgres and
object storage live in Supabase (PRD v1.2.3 §7.5); the VX1 hosts the app,
agent runtime, SSE pub/sub, and TLS terminator.

| Component | Where it runs |
|---|---|
| FastAPI (gunicorn + UvicornWorker × 4) | systemd unit `govcapture-api.service`, listens on `127.0.0.1:8000` |
| Hermes runtime | subprocess of FastAPI (same `govcapture` user) |
| Redis | system `redis-server.service` — SSE pub/sub bridge (PRD §7.5) |
| nginx (TLS terminator + reverse proxy) | system `nginx.service` |
| **Supabase Postgres** (external) | DATABASE_URL → Direct Connection (port 5432) |
| **Supabase Storage** (external) | bucket `govcapture-attachments` |

## 0. Prerequisites

- Vultr VX1 provisioned with **Ubuntu 24.04 LTS**
- Root SSH access (or a sudoer)
- A domain you control, e.g. `api.govcapture.example`
- A Supabase project (create at https://supabase.com — Free tier is enough for MVP)

## 1. Create the Supabase project (one time)

1. https://supabase.com → New project. Region close to VX1.
2. **Settings → Database → Connection string → Direct connection** (port `5432`).
   Capture the URL — replace `[YOUR-PASSWORD]` with the password you set.
3. **Settings → API** — capture `URL`, `anon public` key, and `service_role` key.
4. **Storage → New bucket** → `govcapture-attachments` (private, no public read).
5. Optional but recommended: under **Storage → Policies**, add a retention rule
   on the `raw/` prefix matching PRD §17 Q6 (30-day purge of original PDFs).

> Use the **Direct Connection** URL (port 5432), NOT the pgBouncer pooler at
> 6543 — asyncpg uses prepared statements which transaction-mode pooling rejects.

## 2. Provision the box

```bash
ssh root@<box-ip>
git clone https://github.com/caterpillarC15/govcon.git /tmp/govcon
sudo bash /tmp/govcon/infra/bootstrap.sh
```

`bootstrap.sh` is idempotent. It installs apt packages, configures `ufw`,
creates the `govcapture` user, sets up Redis, installs the API systemd unit,
and prints the next-step checklist. **It does not install Postgres anymore**
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
# Paste from .env.example, then fill in:
#   DATABASE_URL                — Supabase Direct Connection URL (port 5432, with SSL)
#   SUPABASE_URL                — https://<ref>.supabase.co
#   SUPABASE_SERVICE_ROLE_KEY   — server-only; bypasses RLS
#   SUPABASE_ANON_KEY           — safe for the web client
#   SUPABASE_STORAGE_BUCKET     — govcapture-attachments
#   ANTHROPIC_API_KEY           — sk-ant-...
```

## 5. Install deps + migrate Supabase + start

Apply DDL from the repo with the Supabase CLI (linked project), **before** or **alongside**
starting the API:

```bash
# From your laptop (repo linked via supabase link): push migrations to remote Postgres.
cd /path/to/govcon && supabase db push

# On the box: sync Python deps and start the unit.
sudo -u govcapture -H bash -lc 'cd /opt/govcapture && ~/.local/bin/uv sync'
sudo systemctl enable --now govcapture-api.service
sudo systemctl status govcapture-api --no-pager
```

Migrations live under `supabase/migrations/*.sql`. The FastAPI app connects with
`DATABASE_URL` (Direct connection, port 5432); SSL is handled in `api/db/__init__.py`.

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

The FastAPI CORS allowlist already accepts `*.vercel.app` (see `api/main.py`),
so the prod landing can hit the API immediately.

## 8. Subsequent deploys

```bash
sudo -u govcapture -H bash -lc '/opt/govcapture/infra/deploy.sh'
sudo systemctl restart govcapture-api
sudo systemctl status govcapture-api --no-pager
```

`deploy.sh` does `git reset --hard origin/main` + `uv sync --frozen`.
Run `supabase db push` when migration files changed, **before** `sudo systemctl restart govcapture-api`.

## 9. Operations

### Logs
```bash
sudo journalctl -u govcapture-api -f                # API
sudo tail -F /var/log/nginx/access.log              # nginx
# Supabase Postgres logs: dashboard → Project → Logs → Postgres
# Supabase Storage logs:  dashboard → Project → Logs → Storage
```

### Backups

**Supabase handles Postgres backups** — Pro tier has point-in-time restore;
Free tier has 7-day rolling. No on-box pg_dump cron anymore.

**Storage backups** are out of scope for v1.2.3 (the bucket is the system of
record for raw PDFs; parsed text is regeneratable from the chunks in
`api/skills/parse_pdf`). If you want belt-and-suspenders, use Supabase's
Storage replication or an `aws s3 sync` against the S3-compatible endpoint.

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
# Pick a known-good commit and reset to it.
cd /opt/govcapture
sudo -u govcapture git fetch origin
sudo -u govcapture git reset --hard <good-commit-sha>
sudo -u govcapture -H bash -lc '~/.local/bin/uv sync --frozen'
# If a Supabase migration was bad: revert via dashboard SQL or a new corrective migration; then db push.
sudo systemctl restart govcapture-api
```

## 11. Common gotchas

| Symptom | Likely cause | Fix |
|---|---|---|
| `502 Bad Gateway` from nginx | API unit not running | `sudo systemctl status govcapture-api`; check journalctl |
| asyncpg `prepared statement does not exist` errors | DATABASE_URL pointing at the Supabase pooler (port 6543) | Switch to the Direct Connection URL (port 5432). |
| `connection refused` from asyncpg | DATABASE_URL malformed or password wrong | Re-copy from Supabase dashboard; verify the literal `[YOUR-PASSWORD]` placeholder was replaced. |
| asyncpg complains about SSL | Custom DATABASE_URL with a non-localhost hostname; the engine adds `ssl=require` automatically. If your provider uses a self-signed cert, set `ssl=verify-ca` or `ssl=disable` in `api/db/__init__.py` per their docs. |
| TLS cert renewal failed | port 80 blocked or DNS changed | `sudo certbot renew --dry-run` to surface the real error |
| `SUPABASE_SERVICE_ROLE_KEY is not configured` from `api/storage.py` | `.env` missing the var | Add it; the FastAPI service-role mediates Storage access |
