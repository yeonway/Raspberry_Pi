# Project Instructions

## Goal

- Build and maintain the zeta-chat-ui project.

## Paths

- Local: `C:\Users\HOME\Desktop\Raspberry_Pi\zeta-chat-ui`
- Raspberry Pi: `/home/user/Raspberry_Pi/zeta-chat-ui`

## Commands

- Build: `npm run build`
- Run: `npm run dev`
- Verify: `npm run lint`, `npm run build`
- Deploy: run as a Next.js server behind Caddy for `zeta.dcout.site` so `/api/chat` works server-side

## Notes

- Keep global Codex rules in `~/.codex`; do not copy global prompt/docs/skills into this project.
- Do not store SSH passwords, API keys, tokens, or secrets in project files.
