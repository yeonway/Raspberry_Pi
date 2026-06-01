# Raspberry Pi deploy

Assumed target:

- Project path: `/home/user/Raspberry_Pi/10_useless_lab_site`
- Service name: `useless-lab.service`
- Port: `8011`
- Domain: `minigame.dcout.site`

## Deploy commands

```bash
cd /home/user/Raspberry_Pi/10_useless_lab_site
sudo cp deploy/useless-lab.service /etc/systemd/system/useless-lab.service
sudo systemctl daemon-reload
sudo systemctl enable --now useless-lab.service
systemctl status useless-lab.service --no-pager
curl -i http://127.0.0.1:8011/
sudo cp deploy/Caddyfile.minigame.dcout.site /etc/caddy/sites-enabled/minigame.dcout.site
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
curl -I https://minigame.dcout.site/
```

## Update commands

```bash
cd /home/user/Raspberry_Pi/10_useless_lab_site
sudo systemctl restart useless-lab.service
systemctl status useless-lab.service --no-pager
curl -i http://127.0.0.1:8011/
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
curl -I https://minigame.dcout.site/
```
