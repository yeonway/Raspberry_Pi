# zeta-chat-ui

Purpose: Zeta-style AI character chat UI built with Next.js App Router, TypeScript, Tailwind CSS, and a server-side local AI API route.

## Local Run

```powershell
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

## Environment

Copy `.env.example` to `.env.local` when local overrides are needed.

```text
NEXT_PUBLIC_APP_NAME=Zeta
AI_PROVIDER=lmstudio
LM_STUDIO_BASE_URL=http://localhost:1234/v1
CHAT_PROVIDER_BASE_URL=
LM_STUDIO_MODEL=gemma-4-e4b-uncensored-hauhaucs-aggressive
LM_STUDIO_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=
OLLAMA_THINK=false
OLLAMA_NUM_CTX=4096
OLLAMA_NUM_GPU=99
OLLAMA_KEEP_ALIVE=10m
CHAT_MODEL_MAX_MESSAGES=12
CHAT_MAX_TOKENS=8192
CHAT_MAX_TOKENS_SHORT=192
CHAT_MAX_TOKENS_MEDIUM=512
CHAT_MAX_TOKENS_LONG=1200
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=
OPENAI_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
ADMIN_TOKEN=change-me
CHAT_LOG_DIR=./data
PROMPT_CONFIG_PATH=./data/response-prompts.txt
RATE_LIMIT_DISABLED=0
CHAT_RATE_LIMIT_MAX=30
CHAT_RATE_LIMIT_WINDOW_MS=60000
MEMORY_LLM_ENABLED=0
MEMORY_IDLE_UPDATE_MS=300000
MEMORY_SELECTIVE_RETRIEVAL=1
MEMORY_STATE_CACHE_TTL_MS=600000
MEMORY_STATE_CACHE_MAX=128
MEMORY_RECENCY_DECAY_LAMBDA=0.03
MEMORY_RAG_TOP_K=3
MEMORY_RECENT_EVENTS=4
MEMORY_CONTEXT_SUMMARY_CHARS=500
MEMORY_CONTEXT_ITEM_CHARS=500
MEMORY_CONTEXT_CHUNKS=3
MEMORY_CONTEXT_GRAPH_EDGES=12
MEMORY_CONTEXT_TIMEOUT_MS=150
MEMORY_DOCUMENT_TAIL_BYTES=262144
MEMORY_SEARCH_MAX_DOCUMENTS=400
MEMORY_COMPACT_TURN_INTERVAL=50
MEMORY_COMPACT_DOCUMENTS_MAX=1200
MEMORY_COMPACT_DOCUMENTS_KEEP=600
MEMORY_COMPACT_READ_BYTES=4194304
STREAM_TOKEN_DELAY_MS=0
```

`LM_STUDIO_BASE_URL` defaults to `http://localhost:1234/v1`. The browser calls `/api/chat`; only the Next.js server route talks to LM Studio, Ollama, or OpenAI.
`CHAT_PROVIDER_BASE_URL` is accepted as an alias for local providers. In Raspberry Pi deployment, `localhost` or `127.0.0.1` means the provider must run on the Raspberry Pi itself or be exposed to the Pi with a reverse tunnel such as `scripts/lmstudio-reverse-tunnel.ps1`; if LM Studio or Ollama runs on another machine, set `LM_STUDIO_BASE_URL` or `OLLAMA_BASE_URL` to that machine's reachable LAN URL.
`/admin`에서 `ADMIN_TOKEN`을 입력하면 서버에 저장된 최근 대화 로그를 볼 수 있습니다.

`/api/chat` streams by default with server-sent events. Set `stream:false` in the request body only when a legacy JSON `{ content }` response is needed. For LM Studio, set `AI_PROVIDER=lmstudio`, `LM_STUDIO_MODEL`, and optionally `LM_STUDIO_BASE_URL`. For Ollama, set `AI_PROVIDER=ollama`, `OLLAMA_MODEL`, and optionally `OLLAMA_BASE_URL`. `OLLAMA_THINK=false` disables Ollama thinking mode for models that support it. For OpenAI, set `AI_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL` / `OPENAI_BASE_URL`. For DeepSeek, choose `deepseek-v4-flash` in `/admin` and enter the DeepSeek API key there; the key is stored in server-side runtime data, not in source code.

## Memory

The server keeps full chat turns and also builds compact long-term memory under `CHAT_LOG_DIR/memory`.

- `turns.jsonl`: full user/assistant turns are preserved.
- `state.json`: rolling summary, user profile facts, reply preferences, relationship state, Zeta-style shared events, relationship graph edges, and long-conversation chunks.
- `relationship.json`: small relationship-state mirror for fast-changing intimacy, trust, mood, dynamic, open loops, and boundaries.
- `documents.jsonl`: searchable memory snippets used as lightweight local RAG.

Memory is enabled by default. `MEMORY_LLM_ENABLED=0` keeps raw turns and fallback summaries without an extra local-model memory-extraction call. Set `MEMORY_ENABLED=0` to disable all memory. `MEMORY_MODEL` can point to a smaller local model for summary/profile/preference/relationship/event extraction when `MEMORY_LLM_ENABLED=1`.

Memory is scoped to one chat only. The storage key is the chat ID, not the account, browser session, character, or selected model, so model changes do not reset memory for the same chat. Response generation stays fast because each answer immediately appends raw turns, while compact `state.json` updates are batched after `MEMORY_IDLE_UPDATE_MS` of chat inactivity. `MEMORY_SELECTIVE_RETRIEVAL=1` skips memory context for low-signal greetings/reactions and scans `documents.jsonl` only when the latest user message looks memory-relevant. Active chat state is cached in process memory for `MEMORY_STATE_CACHE_TTL_MS`, capped by `MEMORY_STATE_CACHE_MAX`. RAG ranking uses a lightweight BM25-style keyword score plus `MEMORY_RECENCY_DECAY_LAMBDA` so relevant recent memories win over stale low-value memories. `MEMORY_CONTEXT_TIMEOUT_MS` caps how long response generation waits for memory context before starting the provider request; set it to `0` to wait without a cap. `MEMORY_DOCUMENT_TAIL_BYTES` limits how much of `documents.jsonl` is scanned per request, and parsed documents are cached in process memory when the file has not changed. Every `MEMORY_COMPACT_TURN_INTERVAL` turns, oversized `documents.jsonl` files are compacted to recent snippets plus the current state snapshot; `turns.jsonl` remains the raw append-only turn log. Response length also controls provider token budget through `CHAT_MAX_TOKENS_SHORT`, `CHAT_MAX_TOKENS_MEDIUM`, and `CHAT_MAX_TOKENS_LONG`, capped by `CHAT_MAX_TOKENS`. Tune `CHAT_MODEL_MAX_MESSAGES`, `CHAT_MAX_TOKENS_*`, `MEMORY_RAG_TOP_K`, `MEMORY_RECENT_EVENTS`, `MEMORY_CONTEXT_SUMMARY_CHARS`, `MEMORY_CONTEXT_ITEM_CHARS`, `MEMORY_CONTEXT_CHUNKS`, `MEMORY_CONTEXT_GRAPH_EDGES`, `MEMORY_SEARCH_MAX_DOCUMENTS`, `MEMORY_DOCUMENT_TAIL_BYTES`, `MEMORY_CONTEXT_TIMEOUT_MS`, `MEMORY_CHUNK_TURN_INTERVAL`, and `MEMORY_COMPACT_*` for longer conversations.

## Deploy

The public deployment target is `https://zeta.dcout.site`. It runs as a Next.js server behind Caddy so `/api/chat` can call the selected local AI provider from the server side.

In production, keep `CHAT_LOG_DIR` outside the git checkout, for example `/var/lib/zeta-chat-ui/data`, and back it up regularly. See `docs/operations.md`.

## Verification

```powershell
npm run lint
npm run build
```
