#!/usr/bin/env bash
set -euo pipefail

APP_NAME="insta-dm-lite"
APP_USER="${APP_USER:-instadm}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
APP_DIR="${APP_DIR:-/opt/$APP_NAME}"
ENV_DIR="${ENV_DIR:-/etc/$APP_NAME}"
ENV_FILE="$ENV_DIR/$APP_NAME.env"
LOG_DIR="${LOG_DIR:-/var/log/$APP_NAME}"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "--help" ]]; then
    cat <<HELP
Usage: sudo bash scripts/install_pi.sh

Installs the FastAPI app files, Python dependencies, env directory, log directory,
and systemd service. It does not modify /etc/caddy/Caddyfile.

Environment overrides:
  APP_USER=instadm APP_DIR=/opt/insta-dm-lite LOG_DIR=/var/log/insta-dm-lite
HELP
    exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run with sudo: sudo bash scripts/install_pi.sh" >&2
    exit 1
fi

if ! id "$APP_USER" >/dev/null 2>&1; then
    useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

install -d -m 0750 -o "$APP_USER" -g "$APP_GROUP" "$APP_DIR"
install -d -m 0750 -o "$APP_USER" -g "$APP_GROUP" "$APP_DIR/data"
install -d -m 0750 -o "$APP_USER" -g "$APP_GROUP" "$LOG_DIR"
install -d -m 0750 -o root -g "$APP_GROUP" "$ENV_DIR"

rsync -a --delete \
    --exclude ".env" \
    --exclude ".venv" \
    --exclude "__pycache__" \
    --exclude ".pytest_cache" \
    --exclude "data/*.db" \
    --exclude "data/*.sqlite" \
    --exclude "logs" \
    "$SOURCE_DIR/" "$APP_DIR/"

chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
    install -m 0640 -o root -g "$APP_GROUP" "$SOURCE_DIR/.env.example" "$ENV_FILE"
    echo "Created $ENV_FILE from .env.example. Fill real secrets before starting."
else
    chmod 0640 "$ENV_FILE"
    chown root:"$APP_GROUP" "$ENV_FILE"
fi

if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
    sudo -u "$APP_USER" python3 -m venv "$APP_DIR/.venv"
fi

sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

install -m 0644 -o root -g root "$SOURCE_DIR/deploy/$APP_NAME.service" "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable "$APP_NAME.service"

echo "Installed $APP_NAME."
echo "Edit $ENV_FILE, then run:"
echo "  sudo systemctl start $APP_NAME.service"
echo "  sudo systemctl status $APP_NAME.service --no-pager"
echo "Caddy is not modified. See docs/deploy_pi.md and deploy/Caddyfile.example."
