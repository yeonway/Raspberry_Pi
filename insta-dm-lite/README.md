# 댓글DM 라이트

Instagram 댓글 자동 DM 웹서비스의 FastAPI 뼈대입니다. 현재 단계는 실행 가능한 기본 웹앱, SQLite 연결, Jinja2 화면, health check, 요금/토큰 seed 기능을 포함합니다.

## 로컬 실행 방법

```sh
cd insta-dm-lite
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8015
```

Windows PowerShell에서는 가상환경 활성화 명령을 아래처럼 실행합니다.

```powershell
.\.venv\Scripts\Activate.ps1
```

## 개발 서버 실행 스크립트

```sh
cd insta-dm-lite
sh scripts/run_dev.sh
```

## Health Check

```sh
curl http://127.0.0.1:8015/health
```

정상 응답:

```json
{"ok":true}
```

## 1단계 요금/토큰 seed

앱 시작 시 SQLite에 플랜, 토큰 상품, seed 관리자 사용자가 생성됩니다.

```sh
python scripts/seed_billing.py
python scripts/seed_billing.py --grant-tokens 1000 --ref-id seed:manual:001
```

`/billing`에서 현재 플랜, 월 제공 잔여 건수, 구매 토큰 잔여 건수, 토큰 상품 목록을 확인할 수 있습니다.

## 2단계 Meta API 테스트

고객 OAuth 없이 `.env`의 단일 테스트 계정 값으로 Meta Graph API를 호출합니다.

```env
META_GRAPH_VERSION=v25.0
META_PAGE_ID=
META_IG_USER_ID=
META_PAGE_ACCESS_TOKEN=
META_WEBHOOK_VERIFY_TOKEN=
META_WEBHOOK_VERIFY_SIGNATURE=true
```

- `META_IG_USER_ID`: 게시물 목록과 댓글 조회에 사용하는 Instagram Professional 계정 ID
- `META_PAGE_ID`: Private Reply DM 발송에 사용하는 연결된 Facebook Page ID
- `META_PAGE_ACCESS_TOKEN`: 게시물/댓글/메시지 권한이 포함된 Page access token
- `META_WEBHOOK_VERIFY_TOKEN`: Meta Webhook 검증 요청에서 비교할 임의의 공유 토큰

테스트 화면:

```sh
curl http://127.0.0.1:8015/media
```

`/media`에서 게시물을 조회하고, `/media/{media_id}/comments`에서 댓글 조회, 공개 답글, Private Reply DM 발송을 테스트할 수 있습니다. 실제 토큰 값은 README나 코드에 넣지 않습니다.

## 3단계 자동화 규칙

`/automations`에서 자동화 목록을 보고 ON/OFF를 바꿀 수 있습니다. `/automations/new`에서 새 규칙을 만듭니다.

저장 항목:

- 적용 대상: 전체 게시물 또는 선택 게시물
- 키워드/제외 키워드: JSON 배열로 저장
- 매칭 방식: 포함 매칭 또는 정확히 일치
- 공개 답글 문구
- DM 문구
- CTA 버튼명과 CTA 링크
- 발송 지연 시간

## 4단계 댓글 처리 큐

Webhook 없이 `/debug/process-comment`에서 `media_id`, `comment_id`, 댓글 내용을 직접 입력해 자동화 처리 흐름을 테스트할 수 있습니다.

처리 흐름:

- 활성 연결 계정과 활성 자동화 규칙 확인
- 대상 게시물, 포함 키워드, 제외 키워드 검사
- 같은 `comment_id` 중복 처리 방지
- 사용 가능한 월 제공량 또는 구매 토큰 확인
- `job_queue`에 작업 등록 후 기본 5~30초 지연
- 공개 답글과 Private Reply DM 발송 시도
- 성공 또는 부분 성공일 때만 1건 차감
- `automation_logs`에 처리 결과 기록

`/logs`에서 상태, 규칙, 게시물 ID로 처리 로그를 필터링할 수 있습니다. 개발 중 즉시 처리가 필요하면 디버그 화면의 즉시 처리 옵션을 사용합니다.

## 5단계 Meta Webhook

Meta Webhook 검증 엔드포인트:

```sh
curl "http://127.0.0.1:8015/webhooks/meta?hub.mode=subscribe&hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=1234"
```

댓글 이벤트 수신 엔드포인트:

```sh
curl -X POST http://127.0.0.1:8015/webhooks/meta \
  -H "Content-Type: application/json" \
  --data @docs/meta_webhook_comment_payload.example.json
```

POST 요청은 payload를 `webhook_events`에 저장하고, 댓글 ID와 게시물 ID, 댓글 내용을 추출한 뒤 기존 자동화 매칭 로직으로 `job_queue`에 등록합니다. 같은 Webhook 이벤트 또는 같은 `comment_id`가 다시 들어와도 중복 큐 등록하지 않습니다. 알 수 없는 이벤트는 저장 후 skipped 상태로 둡니다.

POST 요청은 JSON 파싱 전에 `X-Hub-Signature-256` 헤더를 HMAC-SHA256으로 검증합니다. 검증에는 `.env`의 `FACEBOOK_APP_SECRET`을 사용하며, 운영 기본값은 `META_WEBHOOK_VERIFY_SIGNATURE=true`입니다. 로컬 개발에서만 필요한 경우 `false`로 끌 수 있습니다.

실제 공개 답글/DM 발송은 Webhook 요청 안에서 처리하지 않고 큐 worker 흐름이 담당합니다. 큐 worker는 SQLite 운영 안정성을 위해 기본적으로 단일 worker 기준으로 둡니다. Meta App Review, Advanced Access, Webhook 구독 권한, 공개 URL HTTPS 설정은 코드만으로 해결할 수 없으며 Meta 개발자 콘솔과 운영 인프라 설정에서 별도로 처리해야 합니다.

## 6단계 고객용 화면

고객이 기술 용어를 몰라도 자동화를 만들 수 있도록 주요 화면을 정리했습니다.

- `/dashboard`: 플랜, 자동화 사용량, 토큰 잔여량, 오늘 처리 건수, 주의 알림
- `/automations`: 자동화 목록과 ON/OFF
- `/automations/new`: 게시물, 키워드, 공개 답글, DM/버튼 입력 후 저장
- `/logs`: 기간, 상태, 자동화, 게시물 필터가 있는 댓글 로그
- `/billing`: 결제/토큰 잔여량, 토큰팩, 차감 순서
- `/connections`: 인스타 연결 상태
- `/settings`: 운영 설정 요약

## 7단계 PortOne 결제

토큰팩 결제는 서버 주문 생성과 PortOne Webhook 검증을 기준으로 처리합니다.

```env
PORTONE_STORE_ID=
PORTONE_CHANNEL_KEY=
PORTONE_API_SECRET=
PORTONE_WEBHOOK_SECRET=
```

결제 흐름:

- `/billing/products`에서 토큰팩 목록을 조회합니다.
- `/billing/checkout/{product_id}`가 `payment_orders`에 pending 주문을 만들고 PortOne 결제창 호출 데이터를 반환합니다.
- PortOne Webhook은 `/billing/portone/webhook`으로 받습니다.
- 서버는 Webhook 서명을 확인한 뒤 PortOne 결제 단건 조회로 실제 결제 상태와 금액을 검증합니다.
- 주문 금액과 결제 금액이 같고 결제 완료 상태일 때만 구매 토큰을 지급합니다.
- 같은 `payment_id`는 `credit_ledger`의 `purchase_grant` ref로 중복 지급하지 않습니다.
- `/billing/orders/{order_id}`에서 주문 상태를 확인할 수 있고, `/billing` 하단에 최근 결제 로그가 표시됩니다.

실제 PortOne 키는 `.env`에만 넣고 README, `.env.example`, 코드에는 넣지 않습니다.

## 8단계 Facebook OAuth 인스타 연결

고객이 직접 Facebook Login으로 Page와 Instagram 비즈니스 계정을 연결할 수 있습니다.

```env
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_REDIRECT_URI=
TOKEN_ENCRYPTION_KEY=
```

운영 env 파일은 `/etc/insta-dm-lite/insta-dm-lite.env`처럼 git 밖에 두고 권한을 제한합니다.

```bash
sudo chown root:instadm /etc/insta-dm-lite/insta-dm-lite.env
sudo chmod 640 /etc/insta-dm-lite/insta-dm-lite.env
python - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
```

필요 권한:

- `pages_show_list`
- `pages_manage_metadata`
- `pages_read_engagement`
- `instagram_basic`
- `instagram_manage_comments`
- `instagram_manage_messages`

연결 흐름:

- `/connections`에서 새 계정 연결을 누르면 Facebook Login으로 이동합니다.
- OAuth callback에서 `/me/accounts`로 Page 목록을 가져오고 고객이 연결할 Page를 선택합니다.
- 선택한 Page의 `instagram_business_account`를 확인한 뒤 `connected_accounts`에 저장합니다.
- Page Access Token은 `TOKEN_ENCRYPTION_KEY`로 암호화해서 저장하며 화면에 표시하지 않습니다.
- 연결 시 Page Webhook 구독을 시도하고 결과를 연결 상태에 표시합니다.
- 자동화 계정 수 제한은 현재 플랜의 `automation_account_limit`을 사용합니다. Free 1개, Basic 이상은 seed 플랜 기준 5개입니다.
- 기존 `.env` 단일 계정 테스트 값은 fallback으로 유지됩니다.

Meta App Review 전에는 앱 역할에 등록된 개발자/테스트 사용자와 테스트 Page 기준으로만 동작합니다. 실제 고객에게 공개하려면 Meta App Review와 필요한 Advanced Access, HTTPS callback/Webhook URL 설정을 별도로 완료해야 합니다.

## 아직 구현하지 않은 기능

- 실제 고객 대상 Meta Advanced Access 승인
