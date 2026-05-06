#!/bin/bash

cd "$(dirname "$0")"

JAVA_RAM_MIN="1G"
JAVA_RAM_MAX="4G"

exec java \
  -Xms$JAVA_RAM_MIN \
  -Xmx$JAVA_RAM_MAX \
  -XX:+UseG1GC \
  -XX:+ParallelRefProcEnabled \
  -XX:MaxGCPauseMillis=200 \
  -XX:+UnlockExperimentalVMOptions \
  -XX:+DisableExplicitGC \
  -XX:+AlwaysPreTouch \
  -jar paper.jar nogui
