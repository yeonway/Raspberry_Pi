#!/bin/bash

set -e

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$BASE_DIR/config/.env"

if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

PORT="${DASHBOARD_PORT:-8000}"
DOMAIN="${NGROK_DOMAIN:-}"
AUTHTOKEN="${NGROK_AUTHTOKEN:-}"

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok is not installed."
  echo "Install ngrok first, then run this script again."
  exit 1
fi

if [ -n "$AUTHTOKEN" ] && [ "$AUTHTOKEN" != "PUT_NGROK_AUTHTOKEN_HERE" ]; then
  ngrok config add-authtoken "$AUTHTOKEN"
fi

if [ -n "$DOMAIN" ]; then
  echo "Starting ngrok with domain: $DOMAIN"
  ngrok http --domain="$DOMAIN" "$PORT"
else
  echo "Starting ngrok on dashboard port: $PORT"
  ngrok http "$PORT"
fi
