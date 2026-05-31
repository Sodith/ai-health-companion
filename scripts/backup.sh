#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  scripts/backup.sh
#  MySQL hot-backup for AI Health Companion
#
#  Usage:
#    chmod +x scripts/backup.sh
#    ./scripts/backup.sh                     # one-off backup
#    # or add to crontab (daily at 02:00):
#    # 0 2 * * * /home/ubuntu/ai-health-companion/scripts/backup.sh >> /var/log/ai-health-backup.log 2>&1
#
#  Backup files are written to  ./backups/  and rotated (keep last 7 days).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
CONTAINER="ai-health-mysql"
KEEP_DAYS=7

# Load env vars (DATABASE credentials)
if [[ -f "${PROJECT_DIR}/.env" ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "${PROJECT_DIR}/.env" | xargs)
fi

MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"
MYSQL_DATABASE="${MYSQL_DATABASE:-health_companion}"

if [[ -z "$MYSQL_ROOT_PASSWORD" ]]; then
  echo "[ERROR] MYSQL_ROOT_PASSWORD is not set. Aborting."
  exit 1
fi

# ── Run backup ────────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${MYSQL_DATABASE}_${TIMESTAMP}.sql.gz"

echo "[$(date -u +%FT%TZ)] Starting backup of database '${MYSQL_DATABASE}' → ${BACKUP_FILE}"

docker exec "$CONTAINER" \
  mysqldump \
    --single-transaction \
    --routines \
    --triggers \
    -u root \
    -p"${MYSQL_ROOT_PASSWORD}" \
    "${MYSQL_DATABASE}" \
  | gzip > "$BACKUP_FILE"

echo "[$(date -u +%FT%TZ)] Backup complete. Size: $(du -sh "$BACKUP_FILE" | cut -f1)"

# ── Rotate old backups ────────────────────────────────────────────────────────
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime "+${KEEP_DAYS}" -delete
echo "[$(date -u +%FT%TZ)] Old backups (>${KEEP_DAYS} days) removed."

