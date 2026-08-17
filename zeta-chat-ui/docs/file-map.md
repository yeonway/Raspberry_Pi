# File Map

Read this first when deciding which files to inspect.

| Path | Role | Keywords | Read when |
| --- | --- | --- | --- |
| `AGENTS.md` | Project-specific Codex instructions | paths, commands, deploy | Starting any task in this project |
| `README.md` | Runtime, env, memory, deploy overview | provider, memory, deploy | Checking expected local or Pi behavior |
| `docs/operations.md` | Production data, backup, and tunnel operations | CHAT_LOG_DIR, backup, tunnel | Deploy hardening or Pi operations |
| `app/page.tsx` | Root chat page entry | ChatLayout | Finding the first UI entry point |
| `components/chat/ChatLayout.tsx` | Main chat state and API orchestration | messages, stream, room, response style | Chat behavior, sending, streaming, room state |
| `components/chat/ChatHeader.tsx` | Chat header and response controls | response style, admin link, character settings | Header controls or no-refresh settings |
| `components/chat/CustomPromptDialog.tsx` | Custom character prompt modal | character prompt, DeepSeek cleanup | Custom prompt modal UI |
| `components/chat/ChatSidebar.tsx` | Room list and chat navigation | rooms, new chat | Chat list, room rename/delete, sidebar UI |
| `components/chat/ChatInput.tsx` | Message composer | send, skip | Input, send button, skip-turn behavior |
| `app/api/chat/route.ts` | Server-side chat route orchestration | stream, persistence, memory update | Request lifecycle and `/api/chat` contract |
| `lib/chat-request.ts` | Chat request parsing and validation | chatId, messages, modelSelection, responseStyle | Chat request shape changes |
| `lib/chat-provider.ts` | Provider runtime, fetch, fallback, and stream parsers | Ollama, LM Studio, OpenAI, DeepSeek, SSE | Provider calls, fallback, stream parsing |
| `lib/chat-prompts.ts` | Chat system prompt and model message builder | persona, custom prompt, memory context | Prompt composition or model context window changes |
| `lib/chat-response.ts` | Response token budget and length clamping | max tokens, short, medium, long | Response length behavior |
| `lib/chat-persistence.ts` | Successful turn persistence and log-entry creation | rooms, account memory, chat logs | Saved rooms, account memory, admin log shape |
| `app/api/models/route.ts` | Provider model discovery | `/api/models`, fallback, provider status | Model dropdown or provider availability |
| `lib/runtime-models.ts` | Provider env and model fetching | AI_PROVIDER, OLLAMA, LM_STUDIO | Provider configuration changes |
| `lib/chat-api.ts` | Browser chat API helpers | SSE, stream parser | Client-side streaming issues |
| `lib/chat-memory.ts` | Per-chat memory storage and context assembly | memory, RAG, summary | Memory bugs or duplicate provider calls |
| `lib/chat-memory-extraction.ts` | Memory update prompt and JSON parser | MEMORY_LLM_ENABLED, extraction | Memory extraction prompt/parser changes |
| `lib/chat-memory-ranking.ts` | Memory document ranking and tokenization | RAG, Korean tokenization, relevance | Memory retrieval scoring changes |
| `lib/account-data.ts` | File-backed account chat state | accounts, rooms, response-style | Login-linked room/response persistence |
| `lib/auth.ts` | File-backed auth | session, login, register | Auth/session bugs |
| `lib/server-files.ts` | Shared server-side file helpers | CHAT_LOG_DIR, JSON, atomic write | File-backed runtime storage changes |
| `lib/rate-limit.ts` | In-process API request limiting | IP, brute force, 429 | Rate-limit tuning or abuse controls |
| `lib/prompt-store.ts` | Admin-editable prompt storage | response-prompts, categories | Prompt admin page or response style prompts |
| `lib/bot-config.ts` | Admin-editable chatbot metadata | chatbots.json, bot config | Bot profile/admin changes |
| `app/admin/page.tsx` | Admin page state and data orchestration | prompts, chatbots, logs | Admin page UX or API wiring |
| `components/admin/AdminWidgets.tsx` | Admin shared widgets and log cards | pagination, metrics, timeline | Admin log/card rendering changes |
| `scripts/next-build.mjs` | Build stability wrapper | NEXT_PRIVATE_BUILD_WORKER | Build failures |
| `scripts/ollama-reverse-tunnel.ps1` | Windows-to-Pi Ollama tunnel | 11434, ssh -R | Ollama provider unreachable from Pi |
| `scripts/lmstudio-reverse-tunnel.ps1` | Windows-to-Pi LM Studio tunnel | 1234, 1235, logging proxy | LM Studio provider unreachable from Pi |
| `scripts/install-lmstudio-tunnel-task.ps1` | Windows scheduled task installer for tunnel | scheduled task, reconnect | Making LM Studio tunnel persistent on Windows |
| `scripts/backup-zeta-data.sh` | Pi data backup archive helper | data, tar, cron | Adding or checking runtime data backups |
| `data/` | Runtime state, not source | chat logs, memory, accounts | Preserve during deploy; inspect only for data repair |
