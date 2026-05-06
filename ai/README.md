# Phone AI Bridge Android

Phone AI Bridge Android는 Raspberry Pi 5의 Minecraft Paper/FastAPI 환경에서 Android 폰으로 로컬 네트워크 HTTP 요청을 보내면, 폰이 AI/RAG API 서버처럼 응답하는 MVP Android 앱입니다.

현재 HTTP 서버 구현은 Ktor 기반입니다. 앱 화면, API 범위, Room DB, Keyword RAG, Mock AI 흐름은 MVP 범위 안에서 유지합니다.

## 현재 MVP 범위

- Jetpack Compose 화면: Home, Settings, Memory, Knowledge, Logs
- Foreground Service 기반 로컬 네트워크 HTTP 서버
- Ktor 기반 HTTP 서버
- 앱 내부에서 현재 Android 폰의 로컬 IPv4 주소 표시
- `GET /health` 공개 상태 확인
- `POST /api/ask` Mock AI 응답 생성
- `X-API-Token` 기반 `/api/*` 인증
- Allowed Raspberry Pi IP 제한 설정
- Room DB 기반 플레이어 기억, 지식 문서, RAG chunk, 요청 로그 저장
- Keyword RAG 검색
- `LiteRtLmAiEngine`은 TODO stub 상태

## 현재 AI 엔진 상태

현재 `/api/ask`는 `MockAiEngine` 기반으로 동작합니다. 실제 Gemma/LiteRT-LM 모델 로딩과 추론은 2차 작업 범위입니다.

`LiteRtLmAiEngine`은 실제 모델을 로드하지 않는 TODO stub입니다. MVP 검증 기준은 Mock 응답, Memory 반영, Keyword RAG 반영, 로그 저장까지입니다.

## 빌드

Windows CMD 기준:

```cmd
C:\Users\HOME\Desktop\python\.1\gradle-9.4.1\bin\gradle.bat :app:assembleDebug
```

Debug APK:

```text
app\build\outputs\apk\debug\app-debug.apk
```

## APK 설치 방법

ADB가 연결되어 있으면 Windows CMD에서 다음 명령으로 설치합니다.

```cmd
adb install app\build\outputs\apk\debug\app-debug.apk
```

이미 같은 applicationId의 앱이 설치되어 있어 덮어써야 하면 다음 명령을 사용할 수 있습니다.

```cmd
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

ADB를 사용하지 않는 경우 `app\build\outputs\apk\debug\app-debug.apk` 파일을 폰으로 복사한 뒤 Android 파일 관리자에서 직접 설치할 수 있습니다. 이 경우 Android 설정에서 해당 파일 관리자 또는 브라우저의 "알 수 없는 앱 설치" 권한이 필요할 수 있습니다.

앱 설치 후 Home 화면에서 Service를 시작합니다. Android 13 이상에서는 알림 권한을 허용해야 Foreground Service 알림이 정상 표시됩니다.

## PHONE_IP 확인 방법

PC나 Raspberry Pi에서 `curl` 테스트할 때 사용할 `PHONE_IP`는 앱 Home 화면에서 바로 확인할 수 있습니다.

Home 화면에 다음 값이 표시됩니다.

- Current Phone IP
- Current Port
- API Base URL
- Health URL
- All local IPs

`Refresh IP` 버튼으로 현재 네트워크 IP를 다시 조회할 수 있습니다. `Copy API URL`, `Copy Health URL` 버튼으로 테스트용 URL을 복사할 수 있습니다.

Android 시스템 설정에서도 IP를 확인할 수 있습니다.

1. Android 설정을 엽니다.
2. Wi-Fi로 이동합니다.
3. 현재 연결된 Wi-Fi를 선택합니다.
4. IP 주소 항목을 확인합니다.

PC와 Android 폰은 같은 로컬 네트워크에 있어야 합니다. 서로 다른 Wi-Fi, 게스트 네트워크, 모바일 데이터, VPN, AP isolation 환경에서는 PC나 Raspberry Pi에서 폰의 `8765` 포트에 접근하지 못할 수 있습니다.

기본 테스트 흐름에서는 앱 Home 화면에 표시되는 `Current Phone IP`를 `PHONE_IP`로 사용합니다.

## API Token 및 IP 설정

Settings 화면에서 다음 값을 설정합니다.

- Port: 기본 `8765`
- API Token: `/api/*` 요청에 필요한 토큰
- Allowed Raspberry Pi IP: 비워두면 토큰만 검사, 입력하면 해당 IP와 토큰이 모두 맞아야 허용

Settings 화면에도 참고용으로 Current Phone IP와 Current API URL이 표시됩니다.

주의: 테스트 중 CMD, 문서, 채팅, 로그 등에 노출된 API Token은 더 이상 안전한 토큰으로 보면 안 됩니다. 노출된 토큰은 Settings 화면에서 재생성한 뒤 Raspberry Pi/FastAPI 쪽 설정도 새 토큰으로 갱신하세요.

## Git 보안 주의

- `local.properties`는 로컬 Android SDK 경로를 담는 환경 파일이므로 Git에 포함하지 않습니다.
- 실제 API Token은 README, GitHub, 스크린샷, 채팅, 이슈, PR 설명에 올리지 않습니다.
- 테스트 중 노출된 토큰은 Settings 화면에서 즉시 재생성합니다.
- 새 토큰을 만들면 PC, Raspberry Pi, FastAPI, Paper 플러그인 쪽 설정도 같은 값으로 갱신해야 합니다.

## 제공 API

- `GET /health`
- `POST /api/ask`
- `GET /api/player/{uuid}/memory`
- `POST /api/player/{uuid}/memory`
- `POST /api/rag/ingest`
- `POST /api/rag/search`
- `GET /api/logs`

## `/health` 응답

기존 응답 필드는 유지하며 로컬 네트워크 IP 관련 필드를 추가로 반환합니다.

```json
{
  "ok": true,
  "server_running": true,
  "model_loaded": false,
  "engine": "MockAiEngine",
  "db_ready": true,
  "port": 8765,
  "time": "2026-05-06T21:00:00+09:00",
  "primary_ip": "192.168.0.20",
  "local_ips": ["192.168.0.20"],
  "api_base_url": "http://192.168.0.20:8765",
  "health_url": "http://192.168.0.20:8765/health"
}
```

IP 조회는 외부 서비스나 인터넷 API를 호출하지 않고 Android 기기의 로컬 `NetworkInterface` 목록만 사용합니다. IPv4 주소를 우선 사용하고 loopback/link-local 주소는 제외합니다. 가능하면 `wlan0` 주소가 primary IP로 선택됩니다.

## Windows CMD 테스트 명령어

아래 예시는 Windows CMD 기준입니다. `PHONE_IP`는 앱 Home 화면의 Current Phone IP 값을 사용합니다.

```cmd
set PHONE_IP=192.168.0.20
set API_TOKEN=YOUR_REGENERATED_TOKEN
set PLAYER_UUID=test-player-uuid
```

`/health` 확인:

```cmd
curl http://%PHONE_IP%:8765/health
```

`/api/logs` 토큰 없이 unauthorized 확인:

```cmd
curl http://%PHONE_IP%:8765/api/logs
```

`/api/logs` 토큰 포함 조회:

```cmd
curl -H "X-API-Token: %API_TOKEN%" http://%PHONE_IP%:8765/api/logs
```

`/api/ask` 및 `coordinate_context` 반영 확인:

```cmd
curl -X POST http://%PHONE_IP%:8765/api/ask ^
  -H "Content-Type: application/json" ^
  -H "X-API-Token: %API_TOKEN%" ^
  -d "{\"player_uuid\":\"%PLAYER_UUID%\",\"player_name\":\"Steve\",\"message\":\"철팜 어디야?\",\"server_context\":\"TPS 20.0, 접속자 2명\",\"coordinate_context\":\"철팜: overworld x=100 y=60 z=100\",\"spark_context\":\"\",\"max_tokens\":160}"
```

RAG 문서 등록:

```cmd
curl -X POST http://%PHONE_IP%:8765/api/rag/ingest ^
  -H "Content-Type: application/json" ^
  -H "X-API-Token: %API_TOKEN%" ^
  -d "{\"title\":\"철팜 기본 조건\",\"content\":\"철팜은 주민, 침대, 작업대, 골렘 스폰 공간 조건이 중요하다.\",\"source_type\":\"manual\",\"tags\":\"iron_farm,villager,golem\"}"
```

RAG 검색:

```cmd
curl -X POST http://%PHONE_IP%:8765/api/rag/search ^
  -H "Content-Type: application/json" ^
  -H "X-API-Token: %API_TOKEN%" ^
  -d "{\"query\":\"철팜 골렘 조건\",\"limit\":5}"
```

Player memory 저장:

```cmd
curl -X POST http://%PHONE_IP%:8765/api/player/%PLAYER_UUID%/memory ^
  -H "Content-Type: application/json" ^
  -H "X-API-Token: %API_TOKEN%" ^
  -d "{\"player_name\":\"Steve\",\"summary\":\"철팜 위치를 자주 묻는 플레이어\",\"current_goal\":\"철팜 찾기\",\"last_location_text\":\"spawn 근처\",\"recent_question\":\"철팜 어디야?\",\"confidence\":0.9}"
```

Player memory 조회:

```cmd
curl -H "X-API-Token: %API_TOKEN%" http://%PHONE_IP%:8765/api/player/%PLAYER_UUID%/memory
```

Memory와 RAG가 동시에 반영되는 `/api/ask` 확인:

```cmd
curl -X POST http://%PHONE_IP%:8765/api/ask ^
  -H "Content-Type: application/json" ^
  -H "X-API-Token: %API_TOKEN%" ^
  -d "{\"player_uuid\":\"%PLAYER_UUID%\",\"player_name\":\"Steve\",\"message\":\"철팜 조건이랑 위치 알려줘\",\"server_context\":\"TPS 20.0\",\"coordinate_context\":\"철팜: overworld x=100 y=60 z=100\",\"spark_context\":\"\",\"max_tokens\":160}"
```

응답에서 다음 값을 확인합니다.

```json
{
  "used_memory": true,
  "used_rag": true
}
```

요청 로그 저장 확인:

```cmd
curl -H "X-API-Token: %API_TOKEN%" http://%PHONE_IP%:8765/api/logs?limit=20
```

## 백그라운드 유지 테스트

Foreground Service가 앱 백그라운드 상태에서도 유지되는지 확인하는 절차입니다.

1. 앱 Home 화면에서 Service를 시작합니다.
2. 앱을 홈으로 내리거나 화면을 끕니다.
3. PC에서 Windows CMD를 열고 다음 명령을 실행합니다.

```cmd
curl http://%PHONE_IP%:8765/health
```

응답이 오면 Foreground Service 유지에 성공한 것입니다. 응답이 오지 않으면 폰과 PC가 같은 로컬 네트워크에 있는지, 앱의 Service가 실행 중인지, 폰의 배터리 절전 정책이 앱을 제한하지 않는지 확인합니다.

## 실기기 테스트 결과

다음 항목을 실기기에서 확인했습니다.

- `GET /health` 성공
- `/api/logs` 토큰 없이 unauthorized 정상
- `X-API-Token` 포함 시 `/api/logs` 정상
- `POST /api/ask` 정상
- `coordinate_context` 반영 정상
- `POST /api/rag/ingest` 정상
- `POST /api/rag/search` 정상
- `/api/ask`에서 `used_rag=true` 확인
- Player memory 저장/조회 정상
- `/api/ask`에서 `used_memory=true`, `used_rag=true` 동시 확인
- `ai_request_logs` 저장 및 조회 정상
- 앱 백그라운드 상태에서도 `/health` 응답 정상

## MVP 통과 체크리스트

- [x] Home / Settings / Memory / Knowledge / Logs 화면 유지
- [x] Home 화면에서 Current Phone IP 확인 가능
- [x] Home 화면에서 API Base URL / Health URL 확인 및 복사 가능
- [x] `/health`에서 `primary_ip`, `local_ips`, `api_base_url`, `health_url` 반환
- [x] Ktor 기반 로컬 HTTP 서버 동작
- [x] `GET /health` 동작
- [x] `/api/*`에 `X-API-Token` 인증 적용
- [x] 토큰 없는 `/api/logs` 요청 unauthorized 확인
- [x] Allowed Raspberry Pi IP 설정 유지
- [x] `POST /api/ask` MockAiEngine 응답 동작
- [x] `coordinate_context`가 Mock 응답 흐름에 반영됨
- [x] Room DB 기반 Player memory 저장/조회 동작
- [x] Room DB 기반 Knowledge/RAG chunk 저장 동작
- [x] Keyword RAG 검색 동작
- [x] `/api/ask`에서 Memory와 RAG 동시 사용 확인
- [x] `ai_request_logs` 저장 및 조회 동작
- [x] 앱 백그라운드 상태에서 `/health` 응답 유지
- [x] Debug APK 빌드 성공

## 2차 작업 TODO

- LiteRT-LM 실제 의존성 추가
- Gemma 모델 실제 로딩 및 추론 구현
- 스트리밍 응답
- Raspberry Pi FastAPI 실제 연동 테스트 확대
- Paper 플러그인 채팅 연동
- 성능/발열 최적화

## 보안/역할 제한

Android 앱은 외부 인터넷 공개 서버, 포트포워딩, ngrok/public URL 기능을 제공하지 않습니다. Minecraft 명령어 실행, 월드 블록 수정, 백업/삭제/복구 자동화도 수행하지 않습니다.

좌표 DB와 NAS 백업은 Raspberry Pi/Synology 측 책임이며, Android 앱은 전달받은 context와 저장된 Memory/RAG를 참고해 답변만 생성합니다.
