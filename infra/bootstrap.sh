#!/usr/bin/env bash
# infra/bootstrap.sh — one-shot provisioning for a Vultr VX1 (Ubuntu 24.04).
#
# Per PRD §7.6 — provisions the box reproducibly with:
#   - apt updates + unattended security upgrades
#   - postgresql-16, redis-server, nginx, certbot, ufw
#   - python3.12 + uv (no Docker)
#   - non-root system user `govcapture`
#   - working dirs under /opt/govcapture and /var/lib/govcapture
#   - daily pg_dump + parsed-document tarball via systemd timer
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
DATA_DIR="/var/lib/govcapture"
BACKUP_DIR="/var/backups/govcapture"
APP_USER="govcapture"

echo "==> [1/9] apt update + base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  ca-certificates curl gnupg ufw fail2ban \
  build-essential pkg-config \
  python3.12 python3.12-venv python3.12-dev \
  postgresql-16 postgresql-client-16 \
  redis-server \
  nginx certbot python3-certbot-nginx \
  unattended-upgrades \
  rsync git

echo "==> [2/9] enable unattended security upgrades"
cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

echo "==> [3/9] firewall — allow 22/80/443, deny everything else"
ufw --force reset >/dev/null
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow 22/tcp >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

echo "==> [4/9] non-root user ${APP_USER}"
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "${APP_USER}"
fi

echo "==> [5/9] working dirs"
install -d -o "${APP_USER}" -g "${APP_USER}" -m 0755 "${REPO_DIR}"
install -d -o "${APP_USER}" -g "${APP_USER}" -m 0755 "${DATA_DIR}"
install -d -o "${APP_USER}" -g "${APP_USER}" -m 0755 "${DATA_DIR}/raw"
install -d -o "${APP_USER}" -g "${APP_USER}" -m 0755 "${DATA_DIR}/parsed"
install -d -o postgres -g postgres -m 0750 "${BACKUP_DIR}"

echo "==> [6/9] uv (Python package manager) for ${APP_USER}"
sudo -u "${APP_USER}" -H bash -c '
  if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
'

echo "==> [7/9] postgres role + db (idempotent)"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='govcon'" | grep -q 1 \
  || sudo -u postgres createuser govcon
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='govcon'" | grep -q 1 \
  || sudo -u postgres createdb -O govcon govcon
echo "    Postgres role 'govcon' + db 'govcon' present."
echo "    Set a password now: sudo -u postgres psql -c \"ALTER USER govcon WITH PASSWORD '...';\""

echo "==> [8/9] redis — enable + start"
systemctl enable --now redis-server >/dev/null
systemctl enable --now postgresql >/dev/null

echo "==> [9/9] systemd units (api, backup) installed but not started"
install -m 0644 "$(dirname "$0")/systemd/govcapture-api.service"   /etc/systemd/system/
install -m 0644 "$(dirname "$0")/systemd/govcapture-backup.service" /etc/systemd/system/
install -m 0644 "$(dirname "$0")/systemd/govcapture-backup.timer"   /etc/systemd/system/
install -m 0755 "$(dirname "$0")/backup.sh" /usr/local/bin/govcapture-backup
systemctl daemon-reload
systemctl enable govcapture-backup.timer >/dev/null

cat <<EOF

================================================================
Bootstrap complete.

Next (see infra/RUNBOOK.md for full detail):

  1. Set the postgres password for the 'govcon' role:
       sudo -u postgres psql -c "ALTER USER govcon WITH PASSWORD '...';"

  2. Clone the repo into ${REPO_DIR}:
       sudo -u ${APP_USER} git clone https://github.com/caterpillarC15/govcon.git ${REPO_DIR}

  3. Drop a production .env into ${REPO_DIR}/.env (see .env.production.example):
       sudo -u ${APP_USER} editor ${REPO_DIR}/.env

  4. Install deps + run migrations + start the API:
       sudo -u ${APP_USER} bash -lc 'cd ${REPO_DIR} && \$HOME/.local/bin/uv sync'
       sudo -u ${APP_USER} bash -lc 'cd ${REPO_DIR} && \$HOME/.local/bin/uv run alembic -c api/alembic.ini upgrade head'
       sudo systemctl enable --now govcapture-api.service

  5. Wire nginx + TLS (after DNS points to this box):
       sudo cp infra/nginx/govcapture.conf /etc/nginx/sites-available/govcapture.conf
       sudo ln -sf /etc/nginx/sites-available/govcapture.conf /etc/nginx/sites-enabled/
       sudo rm -f /etc/nginx/sites-enabled/default
       sudo nginx -t && sudo systemctl reload nginx
       sudo certbot --nginx -d api.your-domain.example

  6. Verify:
       curl https://api.your-domain.example/healthz
       sudo systemctl status govcapture-api govcapture-backup.timer
================================================================
EOF
