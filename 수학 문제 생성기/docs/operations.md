# Operations

## Service control

```bash
sudo systemctl start mathgen
sudo systemctl stop mathgen
sudo systemctl restart mathgen
systemctl status mathgen --no-pager
journalctl -u mathgen -f
journalctl -u mathgen -n 100 --no-pager
```

The app should listen on `127.0.0.1:8020`.

## Deployment verification

```bash
curl http://127.0.0.1:8020/health
curl -I https://math.dcout.site
curl https://math.dcout.site/health
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Also check the local web and API surface after a deploy:

```bash
curl http://127.0.0.1:8020/api/subjects
curl http://127.0.0.1:8020/api/problem-formats
curl http://127.0.0.1:8020/api/ai/status
```

## DB backup

Default DB path:

```bash
/opt/mathgen/data/mathgen.sqlite3
```

Run:

```bash
bash /opt/mathgen/deploy/backup_db.sh
```

Or specify paths:

```bash
bash /opt/mathgen/deploy/backup_db.sh /opt/mathgen/data/mathgen.sqlite3 /opt/mathgen/backups
```

Copy backups off the Raspberry Pi regularly.

## Gemini key rotation

Edit:

```bash
sudo nano /etc/mathgen/mathgen.env
sudo chmod 600 /etc/mathgen/mathgen.env
sudo systemctl restart mathgen
```

Use comma-separated keys:

```env
GEMINI_API_KEYS=
```

Put the real comma-separated Gemini keys only in the target host environment
file.

The API never returns key secrets. Check only counts:

```bash
curl http://127.0.0.1:8020/api/ai/status
```

## Caddy changes

Do not replace the full Caddyfile. Add the `math.dcout.site` block and validate:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## Incident checklist

1. Check the app service:

```bash
systemctl status mathgen --no-pager
journalctl -u mathgen -n 100 --no-pager
```

2. Check local health:

```bash
curl http://127.0.0.1:8020/health
```

3. Check Caddy:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
systemctl status caddy --no-pager
journalctl -u caddy -n 100 --no-pager
```

4. Check public health:

```bash
curl -I https://math.dcout.site
curl https://math.dcout.site/health
```

5. Check disk usage and DB:

```bash
df -h
ls -lh /opt/mathgen/data/
```

6. If needed, restore from the latest backup after stopping the service.

## Low-load operating defaults

- Keep generated batches at 5 to 10 problems.
- Keep `MAX_PROBLEMS_PER_GENERATION=10` unless the Pi has spare capacity.
- Keep `VALIDATION_TIMEOUT_SECONDS=3` or lower for public traffic.
- Prefer cached SVG/table rendering over regenerating assets.
- Add a queue before enabling large batch generation.
