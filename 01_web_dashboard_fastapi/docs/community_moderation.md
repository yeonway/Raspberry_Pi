# DCOUT Community Local Moderation

DCOUT Community can call a local OpenAI-compatible llama.cpp server for Qwen2.5-0.5B-Instruct moderation. The FastAPI app only sends the submitted post/comment text to the local endpoint and stores the moderation input hash, flags, action, model name, and latency. It does not store the model response text in `community_moderation_logs`.

## Environment

Add real values to `.env`; do not commit `.env`.

```env
COMMUNITY_MODERATION_ENABLED=true
COMMUNITY_MODERATION_PROVIDER=llamacpp
COMMUNITY_MODERATION_BASE_URL=http://127.0.0.1:8088
COMMUNITY_MODERATION_MODEL=qwen2.5-0.5b-instruct
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

## llama.cpp Server Example

This is a documentation example only. Do not commit model files, and adjust paths for the Raspberry Pi.

```ini
[Unit]
Description=Qwen Moderation llama.cpp Server
After=network-online.target

[Service]
User=user
WorkingDirectory=/home/user/models
ExecStart=/home/user/llama.cpp/build/bin/llama-server \
  -m /home/user/models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --host 127.0.0.1 \
  --port 8088 \
  -c 1024 \
  -ngl 0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Policy

The model is a helper, not the final authority. A flagged post or comment is not permanently deleted automatically. The app marks it as `pending_review` or `auto_hidden`, logs the decision, and leaves final action to an administrator.
