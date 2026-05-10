#!/usr/bin/env bash
# infra/deploy.sh — pull main, sync deps, restart the API.
#
# Schema changes are applied with Supabase CLI from a linked workstation or CI:
#   supabase db push
# The VX1 box does not run Alembic or Supabase migrations automatically.
#
# Run as the `govcapture` user on the box, from inside /opt/govcapture:
#   sudo -u govcapture -H bash -lc '/opt/govcapture/infra/deploy.sh'
#
# Or the convenience wrapper from the runbook:
#   sudo systemctl restart govcapture-api   # after this script completes
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/govcapture}"
BRANCH="${BRANCH:-main}"

cd "${REPO_DIR}"

echo "==> [1/3] git pull origin ${BRANCH}"
git fetch --quiet origin "${BRANCH}"
git reset --hard "origin/${BRANCH}"

echo "==> [2/3] uv sync"
"${HOME}/.local/bin/uv" sync --frozen

echo "==> [3/3] done (run supabase db push separately before restart if migrations changed)"
echo "    Run as root: sudo systemctl restart govcapture-api"
