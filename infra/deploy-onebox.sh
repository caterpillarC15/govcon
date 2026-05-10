#!/usr/bin/env bash
# infra/deploy-onebox.sh — one-shot deploy for co-locating the FastAPI backend
# on an existing Ubuntu 24.04 box that ALREADY runs Caddy (e.g. the same Vultr
# VX1 that hosts hermes-agent + michealaai). This script does NOT install nginx
# or certbot or reset ufw — it leaves your existing Caddy + firewall alone and
# adds a single api.samrail.com site block to the Caddyfile.
#
# Idempotent. Safe to re-run. Defaults to EMAIL_DRY_RUN=true on first deploy.
#
# Required env (caller passes via SSH):
#   PROD_INTERNAL_API_KEY        Fresh INTERNAL_API_KEY (different from dev)
#   PROD_EMAIL_UNSUBSCRIBE_SECRET Fresh EMAIL_UNSUBSCRIBE_SECRET
#   SUPABASE_URL                  Same as dev — Supabase project URL
#   SUPABASE_SERVICE_ROLE_KEY     Same as dev — service role key
#   SUPABASE_ANON_KEY             Same as dev — anon/publishable key
#   RESEND_API_KEY                Same as dev — Resend send key
#
# Optional env (sensible defaults if omitted):
#   API_HOSTNAME=api.samrail.com
#   APP_HOSTNAME=app.samrail.com
#   LANDING_HOSTNAME=samrail.com
#   EMAIL_DRY_RUN=true            ALWAYS true on first deploy; flip later
#   REPO_URL=https://github.com/caterpillarC15/govcon.git
#   REPO_BRANCH=main
#   MICHEALAAI_DIR=/root/michealaai
#
# Usage from your laptop:
#   ssh govcon \
#     PROD_INTERNAL_API_KEY=<hex> \
#     PROD_EMAIL_UNSUBSCRIBE_SECRET=<hex> \
#     SUPABASE_URL=... \
#     SUPABASE_SERVICE_ROLE_KEY=... \
#     SUPABASE_ANON_KEY=... \
#     RESEND_API_KEY=... \
#     bash /opt/govcapture/infra/deploy-onebox.sh
#
# (Or scp this file up first, then run.)

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root" >&2
  exit 1
fi

REQUIRED=(PROD_INTERNAL_API_KEY PROD_EMAIL_UNSUBSCRIBE_SECRET SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY SUPABASE_ANON_KEY RESEND_API_KEY)
for v in "${REQUIRED[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "ERROR: required env var $v is unset" >&2
    exit 2
  fi
done

API_HOSTNAME="${API_HOSTNAME:-api.samrail.com}"
APP_HOSTNAME="${APP_HOSTNAME:-app.samrail.com}"
LANDING_HOSTNAME="${LANDING_HOSTNAME:-samrail.com}"
EMAIL_DRY_RUN="${EMAIL_DRY_RUN:-true}"
REPO_URL="${REPO_URL:-https://github.com/caterpillarC15/govcon.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
MICHEALAAI_DIR="${MICHEALAAI_DIR:-/root/michealaai}"
APP_USER="govcapture"
REPO_DIR="/opt/govcapture"

echo "==> [1/12] apt deps (no nginx, no certbot — Caddy already does TLS)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  ca-certificates curl gnupg git \
  build-essential pkg-config \
  python3.12 python3.12-venv python3.12-dev \
  redis-server

echo "==> [2/12] redis enabled"
systemctl enable --now redis-server >/dev/null
redis-cli ping >/dev/null && echo "    redis: PONG"

echo "==> [3/12] create system user ${APP_USER}"
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "${APP_USER}"
  echo "    created"
else
  echo "    already exists"
fi

echo "==> [4/12] /opt/govcapture working dir"
install -d -o "${APP_USER}" -g "${APP_USER}" -m 0755 "${REPO_DIR}"

echo "==> [5/12] install uv for ${APP_USER}"
sudo -u "${APP_USER}" -H bash -c '
  if [ ! -x "$HOME/.local/bin/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
  fi
  $HOME/.local/bin/uv --version
'

echo "==> [6/12] clone or update repo into ${REPO_DIR}"
if [ -d "${REPO_DIR}/.git" ]; then
  sudo -u "${APP_USER}" -H bash -c "cd ${REPO_DIR} && git fetch --quiet origin && git reset --hard origin/${REPO_BRANCH}"
  echo "    pulled to $(sudo -u ${APP_USER} -H bash -c "cd ${REPO_DIR} && git rev-parse --short HEAD")"
else
  sudo -u "${APP_USER}" -H bash -c "cd ${REPO_DIR} && git clone --branch ${REPO_BRANCH} --quiet ${REPO_URL} ."
  echo "    cloned to $(sudo -u ${APP_USER} -H bash -c "cd ${REPO_DIR} && git rev-parse --short HEAD")"
fi

echo "==> [7/12] uv sync (install Python deps)"
sudo -u "${APP_USER}" -H bash -c "cd ${REPO_DIR} && \$HOME/.local/bin/uv sync --quiet"

echo "==> [8/12] write ${REPO_DIR}/.env (mode 0600, EMAIL_DRY_RUN=${EMAIL_DRY_RUN})"
ENV_FILE="${REPO_DIR}/.env"
install -m 0600 -o "${APP_USER}" -g "${APP_USER}" /dev/null "${ENV_FILE}"
cat > "${ENV_FILE}" <<EOF
SAM_API_KEY=
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
SUPABASE_STORAGE_BUCKET=govcapture-attachments
INTERNAL_API_KEY=${PROD_INTERNAL_API_KEY}
REDIS_URL=redis://localhost:6379/0
CORS_ALLOWED_ORIGINS=https://${LANDING_HOSTNAME},https://${APP_HOSTNAME}
RESEND_API_KEY=${RESEND_API_KEY}
RESEND_FROM_EMAIL=SamRail <noreply@${LANDING_HOSTNAME}>
RESEND_REPLY_TO=thisisaayushbaniya@gmail.com
EMAIL_PUBLIC_BASE_URL=https://${API_HOSTNAME}
EMAIL_UNSUBSCRIBE_SECRET=${PROD_EMAIL_UNSUBSCRIBE_SECRET}
EMAIL_LEGAL_FOOTER_ADDRESS=SamRail · c/o Antler · Austin, TX · United States
EMAIL_DRY_RUN=${EMAIL_DRY_RUN}
EMAIL_REQUIRE_DOUBLE_OPT_IN=false
EMAIL_AUTO_PICK_ENABLED=true
EMAIL_AUTO_PICK_MIN_SCORE=60
EMAIL_AUTO_PICK_MAX_CANDIDATES=20
EMAIL_NAICS_ALLOWLIST=
EMAIL_USE_FIXTURES_FOR_AUTO_PICK=false
EOF
chown "${APP_USER}:${APP_USER}" "${ENV_FILE}"
chmod 0600 "${ENV_FILE}"

echo "==> [9/12] install systemd units (api + 2 cron timers)"
install -m 0644 "${REPO_DIR}/infra/systemd/govcapture-api.service"             /etc/systemd/system/
install -m 0644 "${REPO_DIR}/infra/systemd/govcapture-cron-auto-pick.service"  /etc/systemd/system/
install -m 0644 "${REPO_DIR}/infra/systemd/govcapture-cron-auto-pick.timer"    /etc/systemd/system/
install -m 0644 "${REPO_DIR}/infra/systemd/govcapture-cron-weekly.service"     /etc/systemd/system/
install -m 0644 "${REPO_DIR}/infra/systemd/govcapture-cron-weekly.timer"       /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now govcapture-api.service
sleep 3
systemctl is-active --quiet govcapture-api.service && echo "    govcapture-api: active" || { systemctl status govcapture-api --no-pager; exit 3; }

echo "==> [10/12] healthz on 127.0.0.1:8000"
HEALTH=$(curl -fsS --max-time 10 http://127.0.0.1:8000/healthz || echo FAIL)
echo "    ${HEALTH}"
[[ "${HEALTH}" == FAIL ]] && exit 4

echo "==> [11/12] add ${API_HOSTNAME} site block to Caddyfile"
CADDYFILE=/etc/caddy/Caddyfile
if ! grep -q "^${API_HOSTNAME} {" "${CADDYFILE}"; then
  cp "${CADDYFILE}" "${CADDYFILE}.bak.$(date +%Y%m%d%H%M%S)"
  cat >> "${CADDYFILE}" <<EOF

${API_HOSTNAME} {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8000 {
        header_up X-Forwarded-Proto {scheme}
        header_up X-Forwarded-Host {host}
    }
}
EOF
  echo "    appended Caddy block (cert auto-issues once DNS resolves)"
  caddy validate --config "${CADDYFILE}" --adapter caddyfile >/dev/null && echo "    caddy validate: ok"
  systemctl reload caddy
else
  echo "    already present, skipping"
fi

echo "==> [12/12] mirror INTERNAL_API_KEY into ${MICHEALAAI_DIR}/.env (Sprint G)"
if [ -f "${MICHEALAAI_DIR}/.env" ]; then
  cp "${MICHEALAAI_DIR}/.env" "${MICHEALAAI_DIR}/.env.bak.$(date +%Y%m%dT%H%M%SZ)"
  if grep -q '^INTERNAL_API_KEY=' "${MICHEALAAI_DIR}/.env"; then
    sed -i "s|^INTERNAL_API_KEY=.*|INTERNAL_API_KEY=${PROD_INTERNAL_API_KEY}|" "${MICHEALAAI_DIR}/.env"
  else
    echo "INTERNAL_API_KEY=${PROD_INTERNAL_API_KEY}" >> "${MICHEALAAI_DIR}/.env"
  fi
  echo "    INTERNAL_API_KEY mirrored"
else
  echo "    WARN: ${MICHEALAAI_DIR}/.env not found — skipping mirror"
fi

echo
echo "================================================================"
echo "  Deploy complete. Next steps:"
echo
echo "  1. Add DNS A record at Vercel:"
echo "       Name:  api"
echo "       Value: $(hostname -I | awk '{print $1}')"
echo "       TTL:   default"
echo
echo "  2. Wait ~2 min for DNS, then verify from outside:"
echo "       curl https://${API_HOSTNAME}/healthz"
echo
echo "  3. Once green, smoke-test the cron routes (still EMAIL_DRY_RUN=true):"
echo "       curl -X POST -H 'Authorization: Bearer \$INTERNAL_API_KEY' \\"
echo "         https://${API_HOSTNAME}/internal/cron/auto-pick-weekly-opportunity"
echo
echo "  4. When ready to actually send: edit ${ENV_FILE},"
echo "     change EMAIL_DRY_RUN=true → false, then:"
echo "       systemctl restart govcapture-api"
echo "       systemctl enable --now govcapture-cron-auto-pick.timer"
echo "       systemctl enable --now govcapture-cron-weekly.timer"
echo "================================================================"
