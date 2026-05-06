#!/usr/bin/env bash
set -euo pipefail

# Raspberry Pi arrival-phase script draft.
# Default mode is dry-run. Set BACKUP_DRY_RUN=false only after SSH, rsync,
# Minecraft RCON, and NAS target paths are verified.
#
# Intended scheduler policy:
# - Run every BACKUP_INTERVAL_DAYS days at BACKUP_TIME, normally 03:30.
# - If players are online at 03:30, wait.
# - After all players leave, wait 10 minutes and recheck.
# - If players stay online until BACKUP_SKIP_CUTOFF, skip that day's backup.

PROJECT_ROOT="${PROJECT_ROOT:-/home/user/Raspberry_Pi}"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

MINECRAFT_SERVER_DIR="${MINECRAFT_SERVER_DIR:-$PROJECT_ROOT/04_minecraft_server}"
LOCAL_BACKUP_DIR="${LOCAL_BACKUP_DIR:-$PROJECT_ROOT/03_backup_to_nas/backups}"
NAS_BACKUP_TARGET="${NAS_BACKUP_TARGET:-user@192.168.0.20:/volume1/minecraft_backups/raspberry_pi}"
BACKUP_KEEP_COUNT="${BACKUP_KEEP_COUNT:-5}"
BACKUP_TIME="${BACKUP_TIME:-03:30}"
BACKUP_INTERVAL_DAYS="${BACKUP_INTERVAL_DAYS:-3}"
BACKUP_SKIP_CUTOFF="${BACKUP_SKIP_CUTOFF:-23:59}"
PLAYER_RECHECK_DELAY_SECONDS="${PLAYER_RECHECK_DELAY_SECONDS:-600}"
BACKUP_DRY_RUN="${BACKUP_DRY_RUN:-true}"
RCON_CLI="${RCON_CLI:-mcrcon}"

mkdir -p "$LOCAL_BACKUP_DIR"

timestamp="$(date '+%Y-%m-%d_%H%M%S')"
archive="$LOCAL_BACKUP_DIR/minecraft_backup_$timestamp.tar.gz"
manifest="$archive.manifest"
sha_file="$archive.sha256"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

run_or_print() {
  if [ "$BACKUP_DRY_RUN" = "true" ]; then
    printf '[dry-run] %q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

player_count() {
  # TODO: replace with RCON `list` parsing after Paper and RCON are enabled.
  # Return 0 for draft mode so the dry-run path is testable before the Pi arrives.
  printf '0\n'
}

save_all() {
  if command -v "$RCON_CLI" >/dev/null 2>&1; then
    run_or_print "$RCON_CLI" -H "${MINECRAFT_RCON_HOST:-127.0.0.1}" -P "${MINECRAFT_RCON_PORT:-25575}" -p "${MINECRAFT_RCON_PASSWORD:-}" "save-all flush"
  else
    log "mcrcon not installed; save-all is documented but skipped in draft mode"
  fi
}

past_cutoff() {
  local now_hm
  now_hm="$(date '+%H:%M')"
  [[ "$now_hm" > "$BACKUP_SKIP_CUTOFF" ]]
}

wait_for_empty_server() {
  local count
  count="$(player_count)"

  if [ "$count" = "0" ]; then
    log "no players online at scheduled backup time $BACKUP_TIME"
    return 0
  fi

  log "players online at scheduled backup time $BACKUP_TIME. waiting until everyone leaves."

  while true; do
    if past_cutoff; then
      log "players stayed online until cutoff $BACKUP_SKIP_CUTOFF. backup skipped for today."
      return 1
    fi

    sleep "$PLAYER_RECHECK_DELAY_SECONDS"
    count="$(player_count)"

    if [ "$count" != "0" ]; then
      log "players still online. waiting."
      continue
    fi

    log "server is empty. wait 10 minutes and recheck before backup."
    sleep "$PLAYER_RECHECK_DELAY_SECONDS"
    count="$(player_count)"

    if [ "$count" = "0" ]; then
      log "server is still empty after 10 minutes."
      return 0
    fi

    log "players rejoined during the 10 minute wait. waiting again."
  done
}

if ! wait_for_empty_server; then
  exit 0
fi

save_all

log "creating archive: $archive"
run_or_print tar \
  --exclude='.git' \
  --exclude='.gradle' \
  --exclude='.kotlin' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='build' \
  --exclude='app/build' \
  --exclude='logs' \
  --exclude='backups' \
  --exclude='.env' \
  --exclude='local.properties' \
  --exclude='ngrok.yml' \
  --exclude='*.db' \
  --exclude='*.apk' \
  --exclude='*.aab' \
  --exclude='*.jks' \
  --exclude='*.keystore' \
  --exclude='*.hprof' \
  -czf "$archive" \
  -C "$PROJECT_ROOT" \
  01_web_dashboard_fastapi 02_autorun_monitor_recovery 03_backup_to_nas 04_minecraft_server 05_raspberrypi_setup_test 06_security_external_access ai

if [ "$BACKUP_DRY_RUN" = "false" ]; then
  size_bytes="$(stat -c '%s' "$archive")"
  sha256sum "$archive" > "$sha_file"
  {
    printf 'created_at=%s\n' "$(date -Iseconds)"
    printf 'archive=%s\n' "$archive"
    printf 'size_bytes=%s\n' "$size_bytes"
    printf 'sha256_file=%s\n' "$sha_file"
  } > "$manifest"

  sha256sum -c "$sha_file"
fi

log "rsync to NAS target: $NAS_BACKUP_TARGET"
run_or_print rsync -avh --progress "$archive" "$sha_file" "$manifest" "$NAS_BACKUP_TARGET/"

log "keep latest $BACKUP_KEEP_COUNT local archives"
if [ "$BACKUP_DRY_RUN" = "false" ]; then
  find "$LOCAL_BACKUP_DIR" -maxdepth 1 -name 'minecraft_backup_*.tar.gz' -type f -printf '%T@ %p\n' |
    sort -rn |
    awk -v keep="$BACKUP_KEEP_COUNT" 'NR > keep {print $2}' |
    xargs -r rm -f
fi

log "NAS retention is handled by Synology-side command or scheduled cleanup after rsync is verified."
