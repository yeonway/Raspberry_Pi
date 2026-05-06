#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="/home/user/Raspberry_Pi/02_autorun_monitor_recovery/logs/watchdog.log"
CHECK_INTERVAL_SECONDS="${WATCHDOG_INTERVAL_SECONDS:-30}"
SERVICES=("dashboard.service" "minecraft.service")

mkdir -p "$(dirname "$LOG_FILE")"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}

log "watchdog started"

while true; do
  for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
      continue
    fi

    log "$service is not active. restart requested."
    if systemctl restart "$service"; then
      log "$service restart success"
    else
      log "$service restart failed"
    fi
  done

  sleep "$CHECK_INTERVAL_SECONDS"
done
