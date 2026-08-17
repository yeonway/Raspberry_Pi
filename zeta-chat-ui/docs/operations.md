# Operations

## Runtime Data

Keep mutable app data outside the git checkout in production.

Recommended Raspberry Pi layout:

```bash
sudo mkdir -p /var/lib/zeta-chat-ui/data
sudo chown -R user:user /var/lib/zeta-chat-ui
```

Set the service environment:

```text
CHAT_LOG_DIR=/var/lib/zeta-chat-ui/data
PROMPT_CONFIG_PATH=/var/lib/zeta-chat-ui/data/response-prompts.txt
```

If existing data lives inside the checkout, migrate it while the service is stopped:

```bash
sudo systemctl stop zeta-chat-ui.service
mkdir -p /var/lib/zeta-chat-ui
rsync -a /home/user/Raspberry_Pi/zeta-chat-ui/data/ /var/lib/zeta-chat-ui/data/
sudo systemctl start zeta-chat-ui.service
```

## Backups

Create a daily archive of the data directory:

```bash
CHAT_LOG_DIR=/var/lib/zeta-chat-ui/data \
ZETA_BACKUP_DIR=/var/backups/zeta-chat-ui \
/home/user/Raspberry_Pi/zeta-chat-ui/scripts/backup-zeta-data.sh
```

Example cron entry:

```cron
15 4 * * * CHAT_LOG_DIR=/var/lib/zeta-chat-ui/data ZETA_BACKUP_DIR=/var/backups/zeta-chat-ui /home/user/Raspberry_Pi/zeta-chat-ui/scripts/backup-zeta-data.sh >/var/log/zeta-chat-ui-backup.log 2>&1
```

## LM Studio Tunnel

The current topology starts the reverse SSH tunnel from the Windows PC running LM Studio. The script already reconnects in a loop:

```powershell
scripts\lmstudio-reverse-tunnel.ps1
```

For unattended Windows operation, install it as a scheduled task:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-lmstudio-tunnel-task.ps1
```

If the tunnel direction is changed so the Raspberry Pi initiates the connection to a host with SSH access, use a systemd-managed `autossh` service instead. Do not store SSH passwords in service files.
