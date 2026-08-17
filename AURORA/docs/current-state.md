# Current State

Last checked: 2026-07-08

## Runtime

- Public URL: `https://zeta.dcout.site`
- Raspberry Pi path: `/home/user/Raspberry_Pi/zeta-chat-ui`
- systemd service: `zeta-chat-ui.service`
- Next.js listen address: `127.0.0.1:3033`
- Reverse proxy: Caddy

## AI Provider

- Production uses a local-provider loopback from the Raspberry Pi.
- If the model server runs on the Windows PC, keep a reverse SSH tunnel open.
- Current production provider: LM Studio.
- Current production model env: `LM_STUDIO_MODEL=gemma-4-e4b-uncensored-hauhaucs-aggressive`.
- Current LM Studio provider URL from the Pi: `http://127.0.0.1:1234/v1`.
- LM Studio tunnel script: `scripts/lmstudio-reverse-tunnel.ps1`
- Ollama is still configured as a fallback option with `OLLAMA_MODEL=qwen2.5:7b` and `OLLAMA_BASE_URL=http://127.0.0.1:11434`.
- Ollama tunnel script: `scripts/ollama-reverse-tunnel.ps1`

## Verification Baseline

Run locally before deploying code changes:

```powershell
npm run lint
npm run build
```

Run on or against the Raspberry Pi after deploy/config changes:

```bash
systemctl is-active zeta-chat-ui.service
curl -I http://127.0.0.1:3033/
curl -I https://zeta.dcout.site/
curl http://127.0.0.1:3033/api/models
sudo caddy validate --config /etc/caddy/Caddyfile
```

## Notes

- `data/` contains runtime chat logs, account state, prompt edits, chatbot edits, and memory files. Preserve it during deploys and do not commit it as source.
- The app can run with generated defaults when `data/` is absent in a fresh checkout.
