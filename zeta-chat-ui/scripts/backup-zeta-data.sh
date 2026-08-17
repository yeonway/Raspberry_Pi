#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${CHAT_LOG_DIR:-/var/lib/zeta-chat-ui/data}"
BACKUP_DIR="${ZETA_BACKUP_DIR:-/var/backups/zeta-chat-ui}"
KEEP_DAYS="${ZETA_BACKUP_KEEP_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="${BACKUP_DIR}/zeta-data-${STAMP}.tar.gz"

if [ ! -d "${DATA_DIR}" ]; then
  echo "Data directory does not exist: ${DATA_DIR}" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"
tar -C "$(dirname "${DATA_DIR}")" -czf "${ARCHIVE}" "$(basename "${DATA_DIR}")"
find "${BACKUP_DIR}" -type f -name 'zeta-data-*.tar.gz' -mtime +"${KEEP_DAYS}" -delete

echo "${ARCHIVE}"
