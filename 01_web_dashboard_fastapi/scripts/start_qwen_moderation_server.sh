#!/usr/bin/env bash
set -euo pipefail

# Moderation classification only needs short responses. Keep context small and
# CPU-only by default so it can run predictably on Raspberry Pi.

MODEL_PATH="${COMMUNITY_MODERATION_MODEL_PATH:-/home/user/models/qwen2.5-0.5b/qwen2.5-0.5b-instruct-q4_k_m.gguf}"
HOST="${COMMUNITY_MODERATION_HOST:-127.0.0.1}"
PORT="${COMMUNITY_MODERATION_PORT:-8088}"
CTX_SIZE="${COMMUNITY_MODERATION_CONTEXT:-1024}"
GPU_LAYERS="${COMMUNITY_MODERATION_GPU_LAYERS:-0}"

if [[ -n "${LLAMA_SERVER_BIN:-}" ]]; then
  LLAMA_SERVER="${LLAMA_SERVER_BIN}"
elif [[ -x "/home/user/llama.cpp/build/bin/llama-server" ]]; then
  LLAMA_SERVER="/home/user/llama.cpp/build/bin/llama-server"
elif [[ -x "/usr/local/bin/llama-server" ]]; then
  LLAMA_SERVER="/usr/local/bin/llama-server"
else
  LLAMA_SERVER="$(command -v llama-server || true)"
fi

if [[ -z "${LLAMA_SERVER}" ]]; then
  echo "ERROR: llama-server not found. Set LLAMA_SERVER_BIN or install llama.cpp." >&2
  exit 1
fi

if [[ ! -f "${MODEL_PATH}" ]]; then
  echo "ERROR: model file not found: ${MODEL_PATH}" >&2
  echo "Run: python3 scripts/download_qwen_moderation_model.py" >&2
  exit 1
fi

echo "Starting Qwen moderation server"
echo "llama-server=${LLAMA_SERVER}"
echo "model=${MODEL_PATH}"
echo "listen=http://${HOST}:${PORT}"

exec "${LLAMA_SERVER}" \
  -m "${MODEL_PATH}" \
  --host "${HOST}" \
  --port "${PORT}" \
  -c "${CTX_SIZE}" \
  -ngl "${GPU_LAYERS}"
