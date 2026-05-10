#!/usr/bin/env bash
# infra/deploy.sh — pull main, sync deps, restart the API.
#
# Run as the `govcapture` user on the box, from inside /opt/govcapture:
#   sudo -u govcapture -H bash -lc '/opt/govcapture/infra/deploy.sh'
#
# Or the convenience wrapper from the runbook:
#   sudo systemctl restart govcapture-api   # after this script completes
#
# Schema changes are applied separately via the Supabase CLI:
#   supabase db push     # against the linked Supabase project
#
# (PRD v1.2.4 dropped Alembic; the data layer is Supabase PostgREST.)
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/govcapture}"
BRANCH="${BRANCH:-main}"

cd "${REPO_DIR}"

echo "==> [1/3] git pull origin ${BRANCH}"
git fetch --quiet origin "${BRANCH}"
git reset --hard "origin/${BRANCH}"

echo "==> [2/3] uv sync"
"${HOME}/.local/bin/uv" sync --frozen

echo "==> [3/3] reload systemd unit"
echo "    Run as root: sudo systemctl restart govcapture-api"
