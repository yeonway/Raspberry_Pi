#!/usr/bin/env bash
set -euo pipefail

# Deploy this Next.js project as the public zeta.dcout.site application.
# Run only from an administrator shell: sudo bash scripts/deploy-zeta-root.sh

if [[ ${EUID} -ne 0 ]]; then
  echo "Run with: sudo bash scripts/deploy-zeta-root.sh" >&2
  exit 1
fi

SOURCE_DIR="/home/user/Raspberry_Pi/AURORA"
RELEASE_ID="$(date +%Y%m%d-%H%M%S)"
DEPLOY_ROOT="/srv/zeta-next-ui"
RELEASE_DIR="${DEPLOY_ROOT}/releases/${RELEASE_ID}"
CURRENT_LINK="${DEPLOY_ROOT}/current"
DATA_DIR="/var/lib/zeta-next-ui/data"
BACKUP_DIR="/srv/deploy-backups/zeta-next-ui/${RELEASE_ID}"
CADDYFILE="/etc/caddy/Caddyfile"
UNIT_FILE="/etc/systemd/system/zeta-next-ui.service"

for command in caddy rsync systemctl; do
  command -v "${command}" >/dev/null || {
    echo "Required command is unavailable: ${command}" >&2
    exit 1
  }
done

[[ -f "${SOURCE_DIR}/package.json" ]] || {
  echo "Source project was not found: ${SOURCE_DIR}" >&2
  exit 1
}

echo "Building the source project..."
runuser -u user -- bash -lc "cd '${SOURCE_DIR}' && npm run build"

echo "Creating a reversible backup..."
install -d -m 0750 -o user -g user "${BACKUP_DIR}" "${RELEASE_DIR}" "${DATA_DIR}"
cp -a "${CADDYFILE}" "${BACKUP_DIR}/Caddyfile.before"
if [[ -f "${UNIT_FILE}" ]]; then
  cp -a "${UNIT_FILE}" "${BACKUP_DIR}/zeta-next-ui.service.before"
fi

echo "Publishing release ${RELEASE_ID}..."
rsync -a \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='.git' \
  --exclude='.deploy-backups' \
  --exclude='data' \
  "${SOURCE_DIR}/" "${RELEASE_DIR}/"

if [[ -d "${SOURCE_DIR}/data" && ! -e "${DATA_DIR}/.migrated-from-source" ]]; then
  rsync -a "${SOURCE_DIR}/data/" "${DATA_DIR}/"
  touch "${DATA_DIR}/.migrated-from-source"
fi
chown -R user:user "${DEPLOY_ROOT}" "${DATA_DIR}"
ln -sfn "${RELEASE_DIR}" "${CURRENT_LINK}"

cat > "${UNIT_FILE}" <<'UNIT'
[Unit]
Description=Zeta Next.js web UI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/srv/zeta-next-ui/current
Environment=NODE_ENV=production
EnvironmentFile=-/etc/zeta-chat-ui-origin.env
Environment=CHAT_LOG_DIR=/var/lib/zeta-next-ui/data
Environment=PROMPT_CONFIG_PATH=/var/lib/zeta-next-ui/data/response-prompts.txt
ExecStart=/usr/bin/npm run start -- --hostname 127.0.0.1 --port 3033
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

python3 - "${CADDYFILE}" <<'PYTHON'
from pathlib import Path
import sys

path = Path(sys.argv[1])
contents = path.read_text(encoding="utf-8")
old = '''    @backend path /api/* /health
    handle @backend {
        reverse_proxy 127.0.0.1:8039
    }

    handle {
        root * /srv/zeta-chat-ui/current/frontend/dist
        try_files {path} /index.html
        file_server
    }'''
new = '''    # zeta-next-ui managed deployment
    handle {
        reverse_proxy 127.0.0.1:3033
    }'''

if contents.count(old) != 1:
    raise SystemExit("The expected zeta.dcout.site block was not found; Caddyfile was left unchanged.")

path.write_text(contents.replace(old, new), encoding="utf-8")
PYTHON

if ! caddy validate --config "${CADDYFILE}" --adapter caddyfile; then
  cp -a "${BACKUP_DIR}/Caddyfile.before" "${CADDYFILE}"
  echo "Caddy validation failed; configuration restored." >&2
  exit 1
fi

systemctl daemon-reload
systemctl enable --now zeta-next-ui.service
systemctl restart zeta-next-ui.service

if ! curl --fail --silent --show-error --max-time 15 http://127.0.0.1:3033/ >/dev/null; then
  echo "The Next.js service did not pass its local health check." >&2
  exit 1
fi

if ! systemctl reload caddy; then
  cp -a "${BACKUP_DIR}/Caddyfile.before" "${CADDYFILE}"
  systemctl reload caddy
  echo "Caddy reload failed; the previous public configuration was restored." >&2
  exit 1
fi

curl --fail --silent --show-error --max-time 20 https://zeta.dcout.site/ >/dev/null
echo "Deployment complete. Backup: ${BACKUP_DIR}"
