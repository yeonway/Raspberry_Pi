# Phone AI Bridge Connection

Android `06-1_phone_ai_bridge_android` is the local AI/RAG bridge for the Raspberry Pi Minecraft server. Keep it on the same trusted local network as the Raspberry Pi.

## 1. Check The Phone URL

1. Open the Android Phone AI Bridge app.
2. Start the foreground service.
3. Check `API Base URL` on the Home screen.

Example:

```text
Current Phone IP: 192.168.0.50
API Base URL: http://192.168.0.50:8765
```

## 2. Set The Token

Use the API token from the Android app Settings screen. Do not paste the real token into docs, logs, screenshots, issues, or commits.

If `Allowed Raspberry Pi IP` is set in the Android app, it must match the Minecraft server host IP that reaches the phone.

## 3. Raspberry Pi `.env`

```env
PHONE_AI_BASE_URL=http://192.168.0.50:8765
PHONE_AI_API_TOKEN=REAL_TOKEN_FROM_ANDROID_SETTINGS
PHONE_AI_TIMEOUT_SECONDS=30
COORDINATE_SYNC_TO_PHONE=true
COORDINATE_DB_PATH=/home/user/server/dashboard/dashboard.db
COORDINATE_DB_TABLE=coordinates
COORDINATE_SYNC_LIMIT=200
COORDINATE_SYNC_TTL_SECONDS=300
```

## 4. Health Test

`/health` is public in the Android app:

```bash
curl -s "$PHONE_AI_BASE_URL/health"
```

## 5. Ask Test

`/api/*` routes require the `X-API-Token` header:

```bash
curl -s \
  -H "X-API-Token: $PHONE_AI_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "player_uuid": "test-player-uuid",
    "player_name": "Steve",
    "message": "Where is the iron farm?",
    "server_context": "online_players=2/5; tps_1m_5m_15m=20.00,20.00,20.00",
    "coordinate_context": "player_location world=overworld x=120 y=64 z=-300",
    "spark_context": "",
    "max_tokens": 180
  }' \
  "$PHONE_AI_BASE_URL/api/ask"
```

## 6. Minecraft Server Event Bridge

Build and copy the Paper plugin from:

```text
04_minecraft_server/phone_ai_bridge_paper_plugin
```

After the plugin creates `plugins/PhoneAiBridge/config.yml`, set the FastAPI event endpoint:

```yaml
dashboard:
  base_url: "http://127.0.0.1:8000"
  event_token: "REAL_DASHBOARD_EVENT_TOKEN"
```

FastAPI reads the Android phone URL and token from `.env`, queues AI jobs, calls the phone app, and sends answers back through Minecraft RCON.

Before each queued AI request, FastAPI syncs the Raspberry Pi dashboard coordinate DB into the Android app through `POST /api/coordinates`. This keeps Android coordinate RAG aligned with the Pi-side saved coordinates such as farms, bases, portals, and other Minecraft locations.

Manual sync check from the Raspberry Pi:

```bash
curl -s -X POST \
  -H "X-Event-Token: $DASHBOARD_EVENT_TOKEN" \
  http://127.0.0.1:8000/coordinate-sync
```

AI queue and coordinate sync status:

```bash
curl -s \
  -H "X-Event-Token: $DASHBOARD_EVENT_TOKEN" \
  http://127.0.0.1:8000/event/status
```

Target phone model:

```text
Gemma 4 E4B-it 4bit GGUF
Recommended first quant: Q4_K_M, fallback: Q4_0
Galaxy S20 12GB default: context 2048, 4 threads, max_tokens 128-180
```

Service endpoints protected by `X-Event-Token`:

```text
GET  /status
GET  /logs
POST /command
POST /ai-proxy
POST /event
GET  /event/status
```

In game:

```text
/ai where is the iron farm?
@ai where is the iron farm?
```
