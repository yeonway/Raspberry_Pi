# Raspberry Pi deployment

This document is a deployment guide for `insta-dm-lite`. It does not require
editing existing Raspberry Pi Caddy or systemd files directly from Codex.
Review and merge the examples manually on the server.

## Target layout

- App directory: `/opt/insta-dm-lite`
- Service user: `instadm`
- Env file: `/etc/insta-dm-lite/insta-dm-lite.env`
- SQLite DB: `/opt/insta-dm-lite/data/app.db`
- App logs: `/var/log/insta-dm-lite`
- Local FastAPI port: `127.0.0.1:8015`
- HTTPS reverse proxy: Caddy

FastAPI must listen only on localhost. Caddy is the only public HTTPS entry.

## 1. Prepare the server

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip rsync sqlite3 curl caddy
```

Create or update the app from the project directory:

```bash
sudo bash scripts/install_pi.sh
```

The install script copies the project to `/opt/insta-dm-lite`, creates the
`instadm` service user if needed, installs Python dependencies, creates the env
and log directories, installs the systemd service file, and enables the service.
It does not modify `/etc/caddy/Caddyfile`.

## 2. Configure secrets

Edit only the server env file:

```bash
sudo nano /etc/insta-dm-lite/insta-dm-lite.env
sudo chown root:instadm /etc/insta-dm-lite/insta-dm-lite.env
sudo chmod 0640 /etc/insta-dm-lite/insta-dm-lite.env
```

Use real values only in this file. Do not commit `.env`, access tokens, API
secrets, PortOne keys, Facebook app secrets, or `TOKEN_ENCRYPTION_KEY`.
Generate `TOKEN_ENCRYPTION_KEY` once and keep it stable:

```bash
python - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
```

Minimum production values normally include:

```env
APP_ENV=production
APP_SECRET_KEY=
DATABASE_URL=sqlite:///data/app.db
META_GRAPH_VERSION=v25.0
META_WEBHOOK_VERIFY_TOKEN=
META_WEBHOOK_VERIFY_SIGNATURE=true
PORTONE_STORE_ID=
PORTONE_CHANNEL_KEY=
PORTONE_API_SECRET=
PORTONE_WEBHOOK_SECRET=
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_REDIRECT_URI=https://example.com/connections/facebook/callback
TOKEN_ENCRYPTION_KEY=
```

Keep `TOKEN_ENCRYPTION_KEY` stable. Changing it makes stored Page Access Tokens
unreadable until customers reconnect.

## 3. Start systemd service

The service example runs one uvicorn worker. Keep a single queue worker while
this MVP uses SQLite.

```bash
sudo systemctl daemon-reload
sudo systemctl enable insta-dm-lite.service
sudo systemctl start insta-dm-lite.service
sudo systemctl status insta-dm-lite.service --no-pager
```

Useful logs:

```bash
journalctl -u insta-dm-lite.service -n 100 --no-pager
sudo ls -la /var/log/insta-dm-lite
```

Local health check:

```bash
bash scripts/healthcheck.sh
curl -i http://127.0.0.1:8015/health
```

Expected body:

```json
{"ok":true}
```

## 4. Configure Caddy

Use `deploy/Caddyfile.example` as a reference. Replace `instadm.dcout.site`
with the real domain, then manually merge only that host block into
`/etc/caddy/Caddyfile` or a Caddy import file according to the existing server
layout. Do not edit or remove unrelated existing hosts such as `dcout.site`,
`files.dcout.site`, or `files.sexyminup.site`.

Example:

```caddy
instadm.dcout.site {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8015
}
```

Webhook paths such as `/webhooks/meta` and `/billing/portone/webhook` pass
through the same reverse proxy. No special rewrite is required.

Validate before reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

Public checks:

```bash
curl -I https://instadm.dcout.site/health
curl https://instadm.dcout.site/health
```

FastAPI should continue to bind to localhost behind Caddy:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8015 --forwarded-allow-ips=127.0.0.1
```

## 5. SQLite backup

Run an on-demand backup:

```bash
sudo -u instadm bash /opt/insta-dm-lite/scripts/backup_db.sh
```

Override paths if needed:

```bash
sudo -u instadm DB_PATH=/opt/insta-dm-lite/data/app.db \
  BACKUP_DIR=/opt/insta-dm-lite/backups \
  KEEP_DAYS=14 \
  bash /opt/insta-dm-lite/scripts/backup_db.sh
```

Example daily cron entry:

```cron
15 3 * * * instadm /bin/bash /opt/insta-dm-lite/scripts/backup_db.sh >> /var/log/insta-dm-lite/backup.log 2>&1
```

Keep backups readable only by the service user or administrators.

## 6. File permissions

Recommended checks:

```bash
sudo chown -R instadm:instadm /opt/insta-dm-lite
sudo chown root:instadm /etc/insta-dm-lite/insta-dm-lite.env
sudo chmod 0640 /etc/insta-dm-lite/insta-dm-lite.env
sudo chmod 0750 /opt/insta-dm-lite/data /var/log/insta-dm-lite
```

Do not expose `.env`, SQLite DB files, or backups through Caddy.

## 7. Rollback

Before replacing the app directory, create a tar backup that excludes secrets
and DB files:

```bash
cd /opt
sudo tar --exclude="insta-dm-lite/.env" \
  --exclude="insta-dm-lite/.venv" \
  --exclude="insta-dm-lite/data/*.db" \
  -czf "/opt/insta-dm-lite-backup-$(date +%Y%m%d-%H%M%S).tar.gz" \
  insta-dm-lite
```

Rollback service files by restoring the previous app directory, then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart insta-dm-lite.service
```
