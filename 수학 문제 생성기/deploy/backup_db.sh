#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-/opt/mathgen/data/mathgen.sqlite3}"
BACKUP_DIR="${2:-/opt/mathgen/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [ ! -f "${DB_PATH}" ]; then
  echo "Database not found: ${DB_PATH}" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"
sqlite3 "${DB_PATH}" ".backup '${BACKUP_DIR}/mathgen-${STAMP}.sqlite3'"
echo "${BACKUP_DIR}/mathgen-${STAMP}.sqlite3"
