#!/bin/bash
set -u

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$LOG_DIR"

INTERVAL="${1:-5}"
NOW="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/temperature_watch_$NOW.log"

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

get_clock() {
  if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd measure_clock arm 2>/dev/null | cut -d= -f2
  else
    echo "unknown"
  fi
}

echo "Temperature watch started"
echo "interval: ${INTERVAL}s"
echo "log_file: $LOG_FILE"
echo "Press Ctrl+C to stop"
echo "time,temp,throttled,cpu_clock" | tee -a "$LOG_FILE"

while true; do
  LINE="$(date '+%Y-%m-%d %H:%M:%S'),$(get_temp),$(get_throttled),$(get_clock)"
  echo "$LINE" | tee -a "$LOG_FILE"
  sleep "$INTERVAL"
done
