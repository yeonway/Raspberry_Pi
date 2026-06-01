#!/usr/bin/env bash
set -euo pipefail

APP_NAME="insta-dm-lite"
APP_DIR="${APP_DIR:-/opt/$APP_NAME}"
DB_PATH="${DB_PATH:-$APP_DIR/data/app.db}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"

if [[ ! -f "$DB_PATH" ]]; then
    echo "Database not found: $DB_PATH" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"
chmod 0750 "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%d-%H%M%S)"
backup_file="$BACKUP_DIR/app-$timestamp.db"

sqlite3 "$DB_PATH" ".backup '$backup_file'"
gzip -f "$backup_file"
find "$BACKUP_DIR" -name "app-*.db.gz" -type f -mtime +"$KEEP_DAYS" -delete

echo "$backup_file.gz"
