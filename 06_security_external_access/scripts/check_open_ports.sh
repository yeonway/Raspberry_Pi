#!/bin/bash

set -e

echo "[1] Hostname"
hostname

echo ""
echo "[2] IP addresses"
hostname -I || true

echo ""
echo "[3] Listening ports"
if command -v ss >/dev/null 2>&1; then
  ss -tulpen
else
  netstat -tulpen
fi

echo ""
echo "[4] UFW status"
if command -v ufw >/dev/null 2>&1; then
  sudo ufw status verbose
else
  echo "ufw not installed"
fi

echo ""
echo "[5] Important ports memo"
echo "8000  = FastAPI dashboard"
echo "25565 = Minecraft server"
echo "22    = SSH"
echo ""
echo "Check that only required ports are open."
