#!/usr/bin/env bash
# infra/bootstrap.sh — one-shot provisioning for a Vultr VX1 (Ubuntu 24.04).
#
# Per PRD §7.6 (v1.2.3) — provisions the box reproducibly with:
#   - apt updates + unattended security upgrades
#   - redis-server, nginx, certbot, ufw
#   - python3.12 + uv (no Docker)
#   - non-root system user `govcapture`
#   - /opt/govcapture working dir
#
# Postgres lives in Supabase (PRD v1.2.3 §7.5) — no on-box pg install, no
# pg_dump cron, no /var/lib/govcapture data dir. Object storage lives in a
# Supabase bucket. Backups are managed by Supabase. The box keeps Redis (SSE
# pub/sub bridge), FastAPI (gunicorn under systemd), Hermes (subprocess of
# FastAPI), and nginx + certbot.
#
# Idempotent. Run as root: `sudo bash infra/bootstrap.sh`.
# After this completes, see infra/RUNBOOK.md for "First deploy".
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root (sudo bash infra/bootstrap.sh)" >&2
  exit 1
fi

if ! grep -q 'Ubuntu 24.04' /etc/os-release 2>/dev/null; then
  echo "WARN: /etc/os-release does not show Ubuntu 24.04. Proceeding anyway." >&2
fi

REPO_DIR="${REPO_DIR:-/opt/govcapture}"
APP_USER="govcapture"

echo "==> [1/7] apt update + base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  ca-certificates curl gnupg ufw fail2ban \
  build-essential pkg-config \
  python3.12 python3.12-venv python3.12-dev \
  redis-server \
  nginx certbot python3-certbot-nginx \
  unattended-upgrades \
  rsync git

echo "==> [2/7] enable unattended security upgrades"
cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

echo "==> [3/7] firewall — allow 22/80/443, deny everything else"
ufw --force reset >/dev/null
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow 22/tcp >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

echo "==> [4/7] non-root user ${APP_USER}"
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "${APP_USER}"
fi

echo "==> [5/7] /opt/govcapture working dir"
install -d -o "${APP_USER}" -g "${APP_USER}" -m 0755 "${REPO_DIR}"

echo "==> [6/7] uv (Python package manager) for ${APP_USER}"
sudo -u "${APP_USER}" -H bash -c '
  if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
'

echo "==> [7/7] redis + systemd unit (api installed, not started)"
systemctl enable --now redis-server >/dev/null
install -m 0644 "$(dirname "$0")/systemd/govcapture-api.service" /etc/systemd/system/
systemctl daemon-reload

cat <<EOF

================================================================
Bootstrap complete (v1.2.3 — Supabase Postgres + Storage, no on-box pg).

Next (see infra/RUNBOOK.md for full detail):

  1. Create a Supabase project at https://supabase.com and capture:
       - Direct Connection URL (Settings → Database, port 5432)
       - Service Role key (Settings → API; server-only, bypasses RLS)
       - Anon key (Settings → API; safe for the web client)
     Create a Storage bucket named 'govcapture-attachments' (private).

  2. Clone the repo into ${REPO_DIR}:
       sudo -u ${APP_USER} git clone https://github.com/caterpillarC15/govcon.git ${REPO_DIR}

  3. Drop a production .env into ${REPO_DIR}/.env with the Supabase values:
       sudo -u ${APP_USER} install -m 0600 /dev/null ${REPO_DIR}/.env
       sudo -u ${APP_USER} editor ${REPO_DIR}/.env
       # Use the Direct Connection URL (port 5432), NOT the pooler (6543).

  4. Install deps + apply Supabase migrations + start the API:
       sudo -u ${APP_USER} bash -lc 'cd ${REPO_DIR} && \$HOME/.local/bin/uv sync'
       On a machine linked to Supabase: cd repo && supabase db push
       sudo systemctl enable --now govcapture-api.service

  5. Wire nginx + TLS (after DNS points to this box):
       sudo cp infra/nginx/govcapture.conf /etc/nginx/sites-available/govcapture.conf
       sudo ln -sf /etc/nginx/sites-available/govcapture.conf /etc/nginx/sites-enabled/
       sudo rm -f /etc/nginx/sites-enabled/default
       sudo nginx -t && sudo systemctl reload nginx
       sudo certbot --nginx -d api.your-domain.example

  6. Verify:
       curl https://api.your-domain.example/healthz
       sudo systemctl status govcapture-api
================================================================
EOF
