#!/bin/bash
set -u

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$LOG_DIR"

NOW="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/system_check_$NOW.log"

log() {
  echo "$1" | tee -a "$LOG_FILE"
}

run() {
  log ""
  log "===== $1 ====="
  shift
  "$@" 2>&1 | tee -a "$LOG_FILE"
}

log "Raspberry Pi System Check"
log "time: $(date '+%Y-%m-%d %H:%M:%S')"
log "log_file: $LOG_FILE"

run "OS" uname -a

if [ -f /etc/os-release ]; then
  run "OS Release" cat /etc/os-release
fi

run "Uptime" uptime
run "CPU Info" lscpu
run "Memory" free -h
run "Disk Usage" df -h
run "Block Devices" lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL
run "Root Mount" findmnt /

if command -v vcgencmd >/dev/null 2>&1; then
  run "Temperature" vcgencmd measure_temp
  run "Throttled / Power Status" vcgencmd get_throttled
  run "CPU Clock" vcgencmd measure_clock arm
  run "Core Voltage" vcgencmd measure_volts core
else
  log ""
  log "===== vcgencmd ====="
  log "vcgencmd not found. This is normal on non-Raspberry Pi systems."
fi

if command -v java >/dev/null 2>&1; then
  log ""
  log "===== Java Version ====="
  java -version 2>&1 | tee -a "$LOG_FILE"

  JAVA_VERSION_TEXT="$(java -version 2>&1 | head -n 1)"
  if echo "$JAVA_VERSION_TEXT" | grep -q '"25'; then
    log "Java 25 check: OK"
  else
    log "Java 25 check: CHECK NEEDED - Paper 26.1+ 사용 전 Java 25 필요"
  fi
else
  log ""
  log "===== Java Version ====="
  log "java not found. Install/check Java 25 before running Paper."
fi

if command -v nvme >/dev/null 2>&1; then
  run "NVMe List" nvme list
else
  log ""
  log "===== NVMe List ====="
  log "nvme command not found. Install nvme-cli later if detailed NVMe info is needed."
fi

log ""
log "===== Kernel Errors Related to NVMe/PCIe/USB/Power ====="
dmesg 2>/dev/null | grep -Ei "nvme|pcie|usb|under-voltage|voltage|thrott|reset|error|fail" | tail -n 120 | tee -a "$LOG_FILE"

log ""
log "System check finished."
log "Saved to: $LOG_FILE"
