#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/mathgen"
ENV_DIR="/etc/mathgen"
SERVICE_NAME="mathgen.service"

echo "This script prepares mathgen-web directories and Python dependencies."
echo "Run from the extracted project root on the Raspberry Pi."
echo "It does not edit Caddyfile automatically."

sudo mkdir -p "${APP_DIR}"
sudo mkdir -p "${APP_DIR}/data"
sudo mkdir -p "${APP_DIR}/data/rendered"
sudo mkdir -p "${ENV_DIR}"

sudo rsync -a \
  --exclude ".venv" \
  --exclude ".env" \
  --exclude ".git" \
  --exclude ".codex_tmp" \
  ./ "${APP_DIR}/"

sudo chown -R "${USER}:${USER}" "${APP_DIR}"

cd "${APP_DIR}"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

if [ ! -f "${ENV_DIR}/mathgen.env" ]; then
  sudo cp .env.example "${ENV_DIR}/mathgen.env"
  sudo chmod 600 "${ENV_DIR}/mathgen.env"
  echo "Edit ${ENV_DIR}/mathgen.env and add real Gemini API keys before production use."
fi

echo
echo "Next manual steps:"
echo "1. Review deploy/mathgen.service.example and set User/Group for this host."
echo "2. sudo cp deploy/mathgen.service.example /etc/systemd/system/${SERVICE_NAME}"
echo "3. sudo systemctl daemon-reload"
echo "4. sudo systemctl enable --now ${SERVICE_NAME}"
echo "5. Add deploy/Caddyfile.math.dcout.site.example block to /etc/caddy/Caddyfile without overwriting existing sites."
echo "6. sudo caddy validate --config /etc/caddy/Caddyfile"
echo "7. sudo systemctl reload caddy"
echo "8. curl http://127.0.0.1:8020/health"
echo "9. curl https://math.dcout.site/health"
