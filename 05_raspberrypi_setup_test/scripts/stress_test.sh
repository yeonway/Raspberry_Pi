#!/bin/bash
set -u

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$LOG_DIR"

DURATION_MIN="${1:-15}"
DURATION_SEC=$((DURATION_MIN * 60))
NOW="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/stress_test_$NOW.log"
TEMP_LOG="$LOG_DIR/stress_temperature_$NOW.log"
DISK_TEST_FILE="$LOG_DIR/disk_write_test_$NOW.bin"
PIDS=""

log() {
  echo "$1" | tee -a "$LOG_FILE"
}

get_temp() {
  if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd measure_temp 2>/dev/null | cut -d= -f2
  elif [ -f /sys/class/thermal/thermal_zone0/temp ]; then
    awk '{printf "%.1f°C", $1/1000}' /sys/class/thermal/thermal_zone0/temp
  else
    echo "unknown"
  fi
}

get_throttled() {
  if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd get_throttled 2>/dev/null | cut -d= -f2
  else
    echo "unknown"
  fi
}

watch_temperature() {
  echo "time,temp,throttled" >> "$TEMP_LOG"
  while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S'),$(get_temp),$(get_throttled)" >> "$TEMP_LOG"
    sleep 5
  done
}

log "Raspberry Pi Stress Test"
log "time: $(date '+%Y-%m-%d %H:%M:%S')"
log "duration: ${DURATION_MIN} minutes"
log "log_file: $LOG_FILE"
log "temperature_log: $TEMP_LOG"

log ""
log "Before test:"
log "temp=$(get_temp)"
log "throttled=$(get_throttled)"

watch_temperature &
WATCH_PID=$!

cleanup() {
  kill "$WATCH_PID" >/dev/null 2>&1 || true
  rm -f "$DISK_TEST_FILE" >/dev/null 2>&1 || true
}
trap cleanup EXIT

log ""
log "Disk write quick test started"
if dd if=/dev/zero of="$DISK_TEST_FILE" bs=1M count=256 conv=fsync 2>&1 | tee -a "$LOG_FILE"; then
  log "Disk write quick test success"
else
  log "Disk write quick test failed"
fi
rm -f "$DISK_TEST_FILE" >/dev/null 2>&1 || true

log ""
if command -v stress-ng >/dev/null 2>&1; then
  log "stress-ng found. CPU/RAM stress started."
  stress-ng --cpu 4 --vm 1 --vm-bytes 512M --timeout "${DURATION_SEC}s" --metrics-brief 2>&1 | tee -a "$LOG_FILE"
else
  log "stress-ng not found. Install it later with: sudo apt install -y stress-ng"
  log "Fallback CPU stress started."
  END_TIME=$((SECONDS + DURATION_SEC))
  while [ $SECONDS -lt $END_TIME ]; do
    for i in 1 2 3 4; do
      sha256sum /dev/zero >/dev/null 2>&1 &
      PIDS="$PIDS $!"
    done
    sleep 10
    kill $PIDS >/dev/null 2>&1 || true
    PIDS=""
  done
fi

log ""
log "After test:"
log "temp=$(get_temp)"
log "throttled=$(get_throttled)"

log ""
log "Recent kernel warning/error lines:"
dmesg 2>/dev/null | grep -Ei "nvme|pcie|usb|under-voltage|voltage|thrott|reset|error|fail" | tail -n 120 | tee -a "$LOG_FILE"

log ""
log "Stress test finished."
log "Check logs:"
log "$LOG_FILE"
log "$TEMP_LOG"
