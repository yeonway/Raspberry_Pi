# Raspberry Pi deploy

Assumed target:

- Project path: `/home/user/Raspberry_Pi/09_personal_memo_site`
- Service name: `personal-memo.service`
- Port: `8009`

## Deploy commands

```bash
cd /home/user/Raspberry_Pi/09_personal_memo_site
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python - <<'PY'
from pathlib import Path
import secrets
p = Path(".env")
text = p.read_text()
text = text.replace("change-this-long-random-secret", secrets.token_urlsafe(48))
p.write_text(text)
PY
python scripts/create_admin.py
sudo cp deploy/personal-memo.service /etc/systemd/system/personal-memo.service
sudo systemctl daemon-reload
sudo systemctl enable --now personal-memo.service
systemctl status personal-memo.service --no-pager
curl -i http://127.0.0.1:8009/health
```
