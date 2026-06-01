# AI 뉴스 레이더

Raspberry Pi에서 실행하는 개인용 뉴스 선별 웹사이트입니다. 무료 공개 API/RSS에서 메타데이터만 수집하고, 관심 키워드와 Android Phone 로컬 AI 서버 또는 mock scorer로 뉴스 우선순위를 계산합니다.

## 아키텍처

- FastAPI + Jinja2 + Vanilla JS
- SQLite 저장소
- 수집기: GDELT, FRED, arXiv, Hacker News Firebase API, SEC EDGAR Atom
- Phone AI HTTP client: `GET /health`, `POST /api/news-score`
- Telegram 30분 묶음 digest
- systemd + Caddy 배포 예시

## 사용하지 않는 소스

외부 AI API, NewsAPI, GNews, Google News RSS, Reddit RSS, 브라우저 자동화, 무작위 크롤링, paywall 우회, 기사 전문 저장은 MVP에서 제외합니다.

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## 환경변수

실제 secret은 코드에 넣지 말고 `.env` 또는 `/etc/pi-news-radar/pi-news-radar.env`에만 둡니다.

- `FRED_API_KEY`: 없으면 FRED 수집기는 skip됩니다.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: 없으면 digest 발송은 skip되고 로그만 남습니다.
- `SEC_USER_AGENT`: SEC 요청에 필요한 User-Agent입니다. 실제 이메일을 넣으세요.
- `PHONE_AI_ENABLED=false`: Android Phone AI 서버 없이 mock mode를 사용합니다.
- `ADMIN_TOKEN`: 설정하면 admin POST 요청에 `X-Admin-Token` 헤더가 필요합니다.

## DB 초기화

```bash
python scripts/init_db.py
```

초기 관심 키워드는 `watch_keywords` 테이블에 자동 seed 됩니다.

## 개발 실행

```bash
python scripts/run_dev.py
```

또는:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8020 --reload
```

## 수동 실행

```bash
python scripts/collect_once.py --dry-run
python scripts/collect_once.py
python scripts/score_once.py --dry-run
python scripts/score_once.py
python scripts/send_digest_once.py --dry-run
python scripts/send_digest_once.py
```

## Phone AI contract

Health:

```text
GET /health
```

Scoring:

```json
{
  "article_id": 123,
  "title": "Nvidia announces new AI chip",
  "source": "GDELT",
  "category": "AI",
  "snippet": "Short snippet only",
  "matched_keywords": ["Nvidia", "AI chip"],
  "published_at": "2026-06-02T10:00:00Z"
}
```

응답:

```json
{
  "ai_score": 87,
  "summary": "3줄 이내의 한국어 요약",
  "score_reason": "미국 기술주에 영향 가능성이 높음",
  "tags": ["Nvidia", "AI chip"]
}
```

`PHONE_AI_ENABLED=false`이면 로컬 mock scorer가 키워드 점수 기반으로 요약과 점수를 생성합니다.

## Telegram

Digest는 즉시 발송하지 않고 후보를 묶어 보냅니다. `NEWS_DIGEST_MIN_SCORE` 이상이거나 alert keyword가 매칭된 기사만 대상입니다. 토큰이나 chat id가 없으면 발송하지 않고 `telegram_digest_logs`에 skipped 상태를 남깁니다.

## systemd 배포

```bash
sudo mkdir -p /etc/pi-news-radar
sudo cp deploy/pi-news-radar.env.example /etc/pi-news-radar/pi-news-radar.env
sudo nano /etc/pi-news-radar/pi-news-radar.env
sudo cp deploy/pi-news-radar.service /etc/systemd/system/pi-news-radar.service
sudo systemctl daemon-reload
sudo systemctl enable --now pi-news-radar
systemctl status pi-news-radar --no-pager
```

다른 서비스가 `8020`을 이미 사용 중이면 `/etc/pi-news-radar/pi-news-radar.env`의 `APP_PORT`를 빈 포트로 바꾼 뒤 Caddy upstream도 같은 포트로 맞춥니다.

## Caddy reverse proxy

`deploy/Caddyfile.example`의 도메인을 실제 도메인으로 바꾼 뒤 `/etc/caddy/Caddyfile`에 반영합니다.

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## 테스트

```bash
python -m compileall app scripts
python -m pytest -q
python scripts/init_db.py
python scripts/collect_once.py --dry-run
python scripts/score_once.py --dry-run
python scripts/send_digest_once.py --dry-run
```

## 문제 해결

- FRED가 skipped이면 `FRED_API_KEY`를 확인합니다.
- SEC가 실패하면 `SEC_USER_AGENT`에 실제 연락 가능한 이메일을 넣었는지 확인합니다.
- Phone AI가 꺼져 있으면 `PHONE_AI_ENABLED=false` mock mode로 먼저 검증합니다.
- Telegram이 skipped이면 bot token과 chat id가 설정되어 있는지 확인합니다.
