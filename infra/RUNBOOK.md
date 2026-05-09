# Vultr VX1 Deployment Runbook

Native (no Docker) deploy of the FastAPI backend per PRD §7.6.

| Component | Where it runs |
|---|---|
| FastAPI (gunicorn + UvicornWorker × 4) | systemd unit `govcapture-api.service`, listens on `127.0.0.1:8000` |
| Postgres 16 | system `postgresql.service` |
| Redis | system `redis-server.service` |
| nginx (TLS terminator + reverse proxy) | system `nginx.service` |
| Daily backups | systemd timer `govcapture-backup.timer` → `pg_dump` + parsed tarball |

## 0. Prerequisites

- Vultr VX1 provisioned with **Ubuntu 24.04 LTS**
- Root SSH access (or a sudoer)
- A domain you control, e.g. `api.govcapture.example`

## 1. First-time provisioning

```bash
ssh root@<box-ip>
git clone https://github.com/caterpillarC15/govcon.git /tmp/govcon
sudo bash /tmp/govcon/infra/bootstrap.sh
```

`bootstrap.sh` is idempotent. It installs apt packages, configures `ufw`,
creates the `govcapture` user + working dirs, sets up Postgres + Redis,
installs systemd units, and prints the next-step checklist.

## 2. Set the Postgres password

```bash
sudo -u postgres psql -c "ALTER USER govcon WITH PASSWORD 'CHOOSE_A_STRONG_ONE';"
```

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
# paste the contents of .env.production.example, then fill in real values
```

## 5. Install deps + migrate + start

```bash
sudo -u govcapture -H bash -lc 'cd /opt/govcapture && ~/.local/bin/uv sync'
sudo -u govcapture -H bash -lc 'cd /opt/govcapture && ~/.local/bin/uv run alembic -c api/alembic.ini upgrade head'
sudo systemctl enable --now govcapture-api.service
sudo systemctl status govcapture-api --no-pager
```

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

`deploy.sh` does `git reset --hard origin/main` + `uv sync --frozen` +
`alembic upgrade head`. The systemd restart picks up the new code.

## 9. Operations

### Logs
```bash
sudo journalctl -u govcapture-api -f                # API
sudo journalctl -u govcapture-backup -n 200         # last backup run
sudo tail -F /var/log/nginx/access.log              # nginx
sudo tail -F /var/log/postgresql/postgresql-16-main.log
```

### Backups
- Local: `/var/backups/govcapture/govcon-*.sql.gz` and `parsed-*.tar.gz`
- Daily at 03:30 UTC via `govcapture-backup.timer`
- Manual run: `sudo systemctl start govcapture-backup`
- Off-box: set `OFFSITE_RSYNC_DEST` in `/etc/default/govcapture-backup` and
  reboot the timer (defaults to local-only)

### Restore from a backup
```bash
sudo systemctl stop govcapture-api
sudo -u postgres psql -c "DROP DATABASE govcon;"
sudo -u postgres createdb -O govcon govcon
gunzip -c /var/backups/govcapture/govcon-YYYYMMDD...sql.gz | sudo -u postgres psql govcon
sudo systemctl start govcapture-api
```

### Resource usage
```bash
htop                                                # quick
sudo systemctl status govcapture-api postgresql redis-server nginx --no-pager
df -h /var/lib /var/backups
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
sudo -u govcapture -H bash -lc '~/.local/bin/uv run alembic -c api/alembic.ini downgrade <prev-revision>'   # if a migration was bad
sudo systemctl restart govcapture-api
```

## 11. Common gotchas

| Symptom | Likely cause | Fix |
|---|---|---|
| `502 Bad Gateway` from nginx | API unit not running | `sudo systemctl status govcapture-api`; check journalctl |
| `connection refused` on Postgres | password mismatch | Compare `.env` `DATABASE_URL` vs the role's actual password |
| TLS cert renewal failed | port 80 blocked or DNS changed | `sudo certbot renew --dry-run` to surface the real error |
| Disk filling up | parsed-doc retention not enforced | Run `find /var/lib/govcapture/raw -mtime +30 -delete` (PRD §17 Q6) |
| Backup timer never fires | timer not enabled | `sudo systemctl enable --now govcapture-backup.timer` |
