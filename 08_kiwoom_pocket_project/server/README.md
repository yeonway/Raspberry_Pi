# kiwoom-bridge

라즈베리파이에서 실행하는 FastAPI 기반 키움 REST API 중계 서버입니다. Android 앱에는 키움 `appkey`와 `secretkey`를 저장하지 않고, 이 서버만 키움 인증과 실제 API 호출을 담당합니다.

## 설치

```powershell
cd "C:\Users\HOME\Desktop\Raspberry_Pi\08_kiwoom_pocket_project\server"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

라즈베리파이/Linux:

```bash
cd /opt/kiwoom-pocket-project/server
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## `.env` 설정

```env
KIWOOM_MODE=mock
KIWOOM_BASE_URL=https://mockapi.kiwoom.com
KIWOOM_WS_URL=wss://mockapi.kiwoom.com:10000/api/dostk/websocket
KIWOOM_APP_KEY=
KIWOOM_SECRET_KEY=
KIWOOM_MOCK_FALLBACK=true
BRIDGE_API_TOKEN=긴_랜덤_토큰
```

- 실제 키는 `.env.example`에 넣지 않습니다.
- `.env`는 git에 포함하지 않습니다.
- `KIWOOM_MOCK_FALLBACK=true`이면 키움 키가 없거나 호출 실패 시 샘플 데이터를 반환합니다.
- 운영 도메인은 `https://api.kiwoom.com`, 모의 도메인은 `https://mockapi.kiwoom.com`입니다.

## 실행

```powershell
cd "C:\Users\HOME\Desktop\Raspberry_Pi\08_kiwoom_pocket_project\server"
.\.venv\Scripts\Activate.ps1
python scripts\init_db.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 테스트

```powershell
python -m compileall app
pytest
curl http://127.0.0.1:8000/health
curl -H "Authorization: Bearer replace-this-with-a-long-random-token" http://127.0.0.1:8000/api/token/status
curl -H "Authorization: Bearer replace-this-with-a-long-random-token" http://127.0.0.1:8000/api/watchlist
```

키움 토큰 직접 테스트:

```powershell
python scripts\test_kiwoom_token.py
```

## 보안

- Android 앱에는 `KIWOOM_APP_KEY`, `KIWOOM_SECRET_KEY`, 키움 access token을 넣지 않습니다.
- 서버 로그에 appkey, secretkey, access token 전체를 출력하지 않습니다.
- `/api/*` 요청은 `Authorization: Bearer {BRIDGE_API_TOKEN}`이 필요합니다.
- `/health`만 인증 없이 허용합니다.
- 실전 주문은 코드상 차단되어 있으며, `/api/orders/mock/*`는 `KIWOOM_MODE=mock`일 때만 검증 후 로그를 남깁니다.
- 시장가 주문과 동일 종목 5초 내 중복 모의 주문은 차단합니다.
- 이 서버는 자동매매, 투자 판단, 매수/매도 추천 기능을 제공하지 않습니다.

## systemd 등록 예시

`systemd/kiwoom-bridge.service.example`을 `/etc/systemd/system/kiwoom-bridge.service`로 복사한 뒤 경로와 사용자명을 환경에 맞게 수정합니다.

```bash
sudo cp systemd/kiwoom-bridge.service.example /etc/systemd/system/kiwoom-bridge.service
sudo systemctl daemon-reload
sudo systemctl enable --now kiwoom-bridge
sudo systemctl status kiwoom-bridge
```
