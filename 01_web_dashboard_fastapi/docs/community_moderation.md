# DCOUT Community Local Moderation

DCOUT Community can call a local OpenAI-compatible llama.cpp server for Qwen2.5-0.5B-Instruct moderation. The FastAPI app sends submitted post/comment text to `127.0.0.1` and stores only the moderation input hash, flags, final action, model name, and latency in `community_moderation_logs`.

The model is a helper, not the final authority. A flagged post or comment is not permanently deleted automatically. The app marks it as `pending_review` or `auto_hidden`, logs the decision, and leaves final action to an administrator.

## 1. Download Qwen GGUF Model

Use the Q4_K_M GGUF model from Hugging Face:

- Repo: `Qwen/Qwen2.5-0.5B-Instruct-GGUF`
- File: `qwen2.5-0.5b-instruct-q4_k_m.gguf`
- Default path: `/home/user/models/qwen2.5-0.5b/qwen2.5-0.5b-instruct-q4_k_m.gguf`

```bash
cd /home/user/Raspberry_Pi/01_web_dashboard_fastapi
source .venv/bin/activate

pip install -r requirements.txt
python3 scripts/download_qwen_moderation_model.py
```

Optional:

```bash
python3 scripts/download_qwen_moderation_model.py --local-dir /home/user/models/qwen2.5-0.5b
python3 scripts/download_qwen_moderation_model.py --force
```

Model files are intentionally ignored by git. Do not store GGUF files inside the repository.

## 2. Prepare llama.cpp / llama-server

Build or install `llama-server` separately. The startup script checks these locations in order:

1. `LLAMA_SERVER_BIN`
2. `/home/user/llama.cpp/build/bin/llama-server`
3. `/usr/local/bin/llama-server`
4. `llama-server` from `PATH`

Manual run:

```bash
cd /home/user/Raspberry_Pi/01_web_dashboard_fastapi
source .venv/bin/activate

bash scripts/start_qwen_moderation_server.sh
```

The script runs:

```bash
llama-server \
  -m /home/user/models/qwen2.5-0.5b/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --host 127.0.0.1 \
  --port 8088 \
  -c 1024 \
  -ngl 0
```

Moderation only needs one-character classification output, so the default context is small and GPU offload is disabled.

## 3. Register systemd Service

The repository includes an example unit only. It is not installed automatically.

```bash
cd /home/user/Raspberry_Pi/01_web_dashboard_fastapi
sudo cp docs/qwen-moderation.service.example /etc/systemd/system/qwen-moderation.service
sudo systemctl daemon-reload
sudo systemctl enable --now qwen-moderation
sudo systemctl status qwen-moderation --no-pager
```

## 4. Configure `.env`

Add real values to `/home/user/Raspberry_Pi/01_web_dashboard_fastapi/.env`; do not commit `.env`.

```env
COMMUNITY_MODERATION_ENABLED=true
COMMUNITY_MODERATION_PROVIDER=llamacpp
COMMUNITY_MODERATION_BASE_URL=http://127.0.0.1:8088
COMMUNITY_MODERATION_MODEL=qwen2.5-0.5b-instruct
COMMUNITY_MODERATION_MODEL_PATH=/home/user/models/qwen2.5-0.5b/qwen2.5-0.5b-instruct-q4_k_m.gguf
COMMUNITY_MODERATION_TIMEOUT_SECONDS=5
COMMUNITY_MODERATION_FAIL_MODE=pending_review
COMMUNITY_MODERATION_AUTO_HIDE=true
COMMUNITY_MODERATION_MAX_CHARS=1200
```

Fail modes:

- `allow`: if the model call fails, rule-based filtering decides.
- `pending_review`: if the model call fails, the item waits for admin review.
- `auto_hide`: if the model call fails, the item is temporarily hidden.

`pending_review` is the recommended default.

## 5. Restart FastAPI

```bash
sudo systemctl restart news-dashboard
sudo systemctl status news-dashboard --no-pager
```

## 6. Check Moderation Connection

With `qwen-moderation` running:

```bash
cd /home/user/Raspberry_Pi/01_web_dashboard_fastapi
source .venv/bin/activate

python3 scripts/check_qwen_moderation.py
```

Expected:

```text
Qwen moderation server OK
response=0
latency_ms=123
```

## 7. Check Community Routes

```bash
curl -I http://127.0.0.1:8013/community
curl -I http://127.0.0.1:8013/admin/community
```

Then create a normal test post from `/community/write`. If the model server is down, `COMMUNITY_MODERATION_FAIL_MODE` controls whether the post is allowed, pending review, or hidden.

## 8. Troubleshooting

```bash
sudo systemctl status qwen-moderation --no-pager
sudo journalctl -u qwen-moderation -n 100 --no-pager
sudo systemctl status news-dashboard --no-pager
sudo journalctl -u news-dashboard -n 100 --no-pager
curl http://127.0.0.1:8088/v1/models
```

Common checks:

- Confirm the GGUF file exists at `COMMUNITY_MODERATION_MODEL_PATH`.
- Confirm `llama-server` is executable.
- Confirm port `8088` is not already in use.
- Confirm `.env` is loaded by `news-dashboard`.
