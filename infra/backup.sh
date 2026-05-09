#!/usr/bin/env bash
# infra/backup.sh — installed to /usr/local/bin/govcapture-backup by bootstrap.sh
#
# Daily backup per PRD §7.6:
#   - pg_dump of the govcon database
#   - tarball of /var/lib/govcapture/parsed (extracted requirements survive
#     even if raw PDFs purge; see PRD §17 Q6 30-day raw retention)
#
# Retention: keeps the most recent 14 days locally. Off-box rsync is
# a separate concern — set OFFSITE_RSYNC_DEST to enable it.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/govcapture}"
DATA_DIR="${DATA_DIR:-/var/lib/govcapture}"
DB_NAME="${DB_NAME:-govcon}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
OFFSITE_RSYNC_DEST="${OFFSITE_RSYNC_DEST:-}"  # e.g. "user@host:/srv/govcapture-backups/"

mkdir -p "${BACKUP_DIR}"
chmod 0750 "${BACKUP_DIR}"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
db_out="${BACKUP_DIR}/govcon-${stamp}.sql.gz"
parsed_out="${BACKUP_DIR}/parsed-${stamp}.tar.gz"

echo "[$(date -u +%FT%TZ)] starting backup"

# Postgres dump (custom-format would also work; plain SQL is easier to inspect).
sudo -u postgres pg_dump --no-owner --clean --if-exists "${DB_NAME}" \
  | gzip -c > "${db_out}"
echo "  wrote ${db_out} ($(du -h "${db_out}" | cut -f1))"

# Parsed-document tarball. Skip if the dir doesn't exist yet (fresh box).
if [ -d "${DATA_DIR}/parsed" ]; then
  tar -czf "${parsed_out}" -C "${DATA_DIR}" parsed
  echo "  wrote ${parsed_out} ($(du -h "${parsed_out}" | cut -f1))"
else
  echo "  skipped parsed tarball (dir not present yet)"
fi

# Retention — drop anything older than RETENTION_DAYS.
find "${BACKUP_DIR}" -type f \( -name 'govcon-*.sql.gz' -o -name 'parsed-*.tar.gz' \) \
  -mtime "+${RETENTION_DAYS}" -print -delete

# Off-box rsync (optional). Failure here is non-fatal — local backup still wins.
if [ -n "${OFFSITE_RSYNC_DEST}" ]; then
  echo "  rsync → ${OFFSITE_RSYNC_DEST}"
  rsync -a --delete --partial "${BACKUP_DIR}/" "${OFFSITE_RSYNC_DEST}" || \
    echo "  WARN: off-box rsync failed; local backup is still in place."
fi

echo "[$(date -u +%FT%TZ)] backup done"
