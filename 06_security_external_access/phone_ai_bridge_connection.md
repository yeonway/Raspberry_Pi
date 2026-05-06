# Phone AI Bridge Connection

Android `ai` 폴더는 Phone AI Bridge 앱입니다. 이 앱은 백업 저장소가 아니라 AI/RAG 장치입니다.

## 1. 폰 앱에서 IP 확인

1. Android Phone AI Bridge 앱을 실행합니다.
2. Home 화면에서 `Current Phone IP`를 확인합니다.
3. Raspberry Pi와 같은 로컬 네트워크인지 확인합니다.

예시:

```text
Current Phone IP: 192.168.0.50
API Base URL: http://192.168.0.50:8080
```

## 2. API Token 재생성

앱 설정 화면에서 API Token을 재생성합니다. 토큰은 `.env`에만 저장하고 문서, README, 로그에 남기지 않습니다.

## 3. Raspberry Pi `.env` 입력

```env
PHONE_AI_BASE_URL=http://192.168.0.50:8080
PHONE_AI_API_TOKEN=실제_토큰
PHONE_AI_TIMEOUT_SECONDS=30
```

## 4. `/health` 테스트

```bash
curl -s "$PHONE_AI_BASE_URL/health"
```

토큰이 필요한 구현이면 다음 형식을 사용합니다.

```bash
curl -s -H "Authorization: Bearer $PHONE_AI_API_TOKEN" "$PHONE_AI_BASE_URL/health"
```

## 5. `/api/ask` 테스트

```bash
curl -s \
  -H "Authorization: Bearer $PHONE_AI_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "철 농장 위치 알려줘",
    "player": "Steve",
    "context": {
      "coordinates": [
        {
          "name": "Iron Farm",
          "world": "overworld",
          "x": 120,
          "y": 64,
          "z": -300,
          "note": "마을 북쪽"
        }
      ]
    }
  }' \
  "$PHONE_AI_BASE_URL/api/ask"
```

## 좌표 context 전달

FastAPI 대시보드는 SQLite `coordinates` 테이블에서 질문과 관련된 좌표를 검색해 `context.coordinates` 배열로 전달합니다. Phone AI Bridge는 이 context를 RAG/Memory와 함께 사용해 응답을 생성합니다.

## 2차 작업

Gemma 4 E2B 4bit 및 LiteRT-LM 연결은 Raspberry Pi 실기기 연결과 1차 안정화 후 진행합니다.
