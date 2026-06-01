# Raspberry Pi deployment

This project is intended to run on Raspberry Pi behind Caddy.

Deployment target:

- Install path: `/opt/mathgen`
- Service name: `mathgen.service`
- Internal bind: `127.0.0.1:8020`
- Public domain: `math.dcout.site`
- Reverse proxy: Caddy
- SQLite DB: `/opt/mathgen/data/mathgen.sqlite3`
- Environment file: `/etc/mathgen/mathgen.env`

Do not overwrite an existing `/etc/caddy/Caddyfile`. Add only the site block
from `deploy/Caddyfile.math.dcout.site.example`.

## Prepare files

Copy or clone the project onto the Raspberry Pi, then run from the project root:

```bash
bash deploy/install_pi.sh
```

The script creates `/opt/mathgen`, installs Python requirements into
`/opt/mathgen/.venv`, creates data directories, and copies `.env.example` to
`/etc/mathgen/mathgen.env` if it does not already exist.

Edit the environment file:

```bash
sudo nano /etc/mathgen/mathgen.env
sudo chmod 600 /etc/mathgen/mathgen.env
```

Required production values:

```env
MATHGEN_ENVIRONMENT=production
MATHGEN_DATABASE_URL=sqlite:////opt/mathgen/data/mathgen.sqlite3
GEMINI_API_KEYS=
GEMINI_MODEL_DEFAULT=gemini-2.5-flash-lite
MAX_PROBLEMS_PER_GENERATION=10
VALIDATION_TIMEOUT_SECONDS=3
```

Store real API keys only in the environment file. Do not put secrets in Git,
README files, shell history, screenshots, logs, or issue comments.

## systemd

Review `deploy/mathgen.service.example` before installing. Set `User=` and
`Group=` to the actual deployment user on the Raspberry Pi.

```bash
sudo cp /opt/mathgen/deploy/mathgen.service.example /etc/systemd/system/mathgen.service
sudo systemctl daemon-reload
sudo systemctl enable --now mathgen
systemctl status mathgen --no-pager
journalctl -u mathgen -n 100 --no-pager
```

The service runs:

```bash
/opt/mathgen/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8020
```

## Caddy

DNS for `math.dcout.site` must point to the Raspberry Pi before HTTPS can work.
Caddy can handle HTTPS automatically after DNS is correct.

Add this block to `/etc/caddy/Caddyfile`:

```caddy
math.dcout.site {
    reverse_proxy 127.0.0.1:8020
}
```

Validate and reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
systemctl status caddy --no-pager
```

## Health checks

```bash
curl http://127.0.0.1:8020/health
curl -I https://math.dcout.site
curl https://math.dcout.site/health
systemctl status mathgen --no-pager
journalctl -u mathgen -n 100 --no-pager
```

## Security notes

- Keep `/etc/mathgen/mathgen.env` at `chmod 600`.
- Never expose Gemini keys in API responses, logs, templates, docs, or commits.
- Initial admin workflows are for local/personal use. Add authentication before
  exposing privileged features as a public service.
- Do not crawl or store copyrighted textbook content.
- Keep `MAX_PROBLEMS_PER_GENERATION` low on Raspberry Pi. The default is 10.
- Keep `VALIDATION_TIMEOUT_SECONDS` small. The default is 3 seconds.
