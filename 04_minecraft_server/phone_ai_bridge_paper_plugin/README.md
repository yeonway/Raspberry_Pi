# Phone AI Bridge Paper Plugin

This Paper plugin sends Minecraft chat AI requests to the Raspberry Pi FastAPI `/event` endpoint. FastAPI queues requests, calls the Android Phone AI Bridge app in `06-1_phone_ai_bridge_android`, and returns answers to Minecraft through RCON.

## Build

From this folder on Windows:

```cmd
C:\Users\HOME\Desktop\python\.1\gradle-9.4.1\bin\gradle.bat clean build copyToServerPlugins
```

The copy task writes the local runtime jar to:

```text
04_minecraft_server\plugins\phone-ai-bridge-paper.jar
```

## Configure

Start the Paper server once so the plugin creates:

```text
04_minecraft_server\plugins\PhoneAiBridge\config.yml
```

Then set:

```yaml
dashboard:
  base_url: "http://127.0.0.1:8000"
  event_token: "DASHBOARD_EVENT_TOKEN_FROM_FASTAPI_ENV"
```

Set `PHONE_AI_BASE_URL`, `PHONE_AI_API_TOKEN`, and RCON values in `01_web_dashboard_fastapi/.env`. The plugin only needs the FastAPI dashboard URL and `DASHBOARD_EVENT_TOKEN`.

## Use In Game

Ask directly:

```text
/ai where is the iron farm?
```

Or use the chat trigger:

```text
@ai where is the iron farm?
```

Admin checks:

```text
/phoneai status
/phoneai health
/phoneai reload
```

The plugin sends `player_uuid`, `player_name`, the question, current player coordinates, online player count, and Paper TPS context to FastAPI `POST /event` with the `X-Event-Token` header.
