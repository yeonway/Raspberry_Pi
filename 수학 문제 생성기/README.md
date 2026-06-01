# mathgen-web

Raspberry Pi에서 가볍게 실행하는 중학교 수학 문제 생성 웹앱입니다. FastAPI
백엔드를 API-first로 유지하고, 화면은 Jinja2 서버 렌더링으로 제공합니다. 이후
Android 앱과 다른 과목을 같은 API 위에 붙일 수 있게 설계합니다.

## 주요 기능

- 과목, 교과서 메타데이터, 학년, 단원, 문제 형식 seed 데이터 자동 초기화
- 학년/학기를 먼저 고르고 해당 범위의 단원을 선택하는 생성 폼
- 문제 형식 직접 선택, 랜덤, 혼합 랜덤, 자연어 요청 기반 generation plan
- Gemini structured JSON provider 구조와 여러 API 키 round-robin/cooldown 처리
- mock 테스트 가능한 문제 생성 서비스와 `problem_sets`, `problems`, `generation_logs` 저장
- 생성 전 계획 미리보기, 생성 이력 필터링, 문제 세트 삭제, 생성 로그 조회
- 제한된 중학교 수학 유형 자동검증과 수동검토 상태 처리
- 그래프, 표, 간단 도형 deterministic 렌더링 및 캐싱
- 문제 결과, 문제지 출력 화면, 정답지 출력 화면
- Raspberry Pi systemd/Caddy 배포 예시와 운영 문서

## 기술 스택

- Python, FastAPI, Uvicorn
- SQLite, SQLAlchemy
- Jinja2, 정적 CSS
- Pydantic Settings, python-dotenv
- SymPy 일부 사용, 단 제한된 검증만 허용
- pytest, FastAPI TestClient

React, Vue, Node 빌드 시스템은 사용하지 않습니다.

## 로컬 실행

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8020
```

Linux 또는 Raspberry Pi:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8020
```

접속:

- 홈 화면: `http://127.0.0.1:8020/`
- Health: `http://127.0.0.1:8020/health`
- OpenAPI 문서: `http://127.0.0.1:8020/docs`

## 환경변수

`.env.example`을 `.env`로 복사한 뒤 필요한 값만 수정합니다. 실제 API 키는 Git에
커밋하지 않습니다.

```env
MATHGEN_APP_NAME=mathgen-web
MATHGEN_ENVIRONMENT=development
MATHGEN_DATABASE_URL=sqlite:///./data/mathgen.sqlite3
MATHGEN_DEFAULT_PROBLEM_COUNT=5
MAX_PROBLEMS_PER_GENERATION=10
VALIDATION_TIMEOUT_SECONDS=3
```

Raspberry Pi 운영 DB 예:

```env
MATHGEN_DATABASE_URL=sqlite:////opt/mathgen/data/mathgen.sqlite3
```

## Gemini API 키 설정

Gemini 키는 `.env` 또는 운영 환경파일에 쉼표로 구분해 넣습니다.

```env
GEMINI_API_KEYS=
GEMINI_MODEL_DEFAULT=gemini-2.5-flash-lite
AI_REQUEST_TIMEOUT_SECONDS=45
AI_MAX_RETRIES=3
AI_KEY_COOLDOWN_SECONDS=3600
```

여러 키가 있으면 round-robin으로 사용하고, 429/503/quota 계열 오류가 난 키는
cooldown 처리합니다. `/api/ai/status`는 키 개수만 반환하며 secret은 노출하지
않습니다. API 키가 없어도 서버는 실행되고, `/api/ai/test`는 명확한 unavailable
응답을 반환합니다.

## 문제 생성 흐름

1. 사용자가 과목, 교과서 메타데이터, 단원, 난이도, 문제 수, 문제 형식을 선택합니다.
2. `POST /api/generation/plan`이 Gemini 호출 없이 problem slot 계획을 만듭니다.
3. `POST /api/generate`가 problem set을 만들고 slot 단위로 Gemini structured JSON을 요청합니다.
4. JSON 응답은 `problems`에 저장되고, 호출 기록은 `generation_logs`에 저장됩니다.
5. 실패한 문제도 삭제하지 않고 `generation_failed` 또는 `needs_review` 상태로 보존합니다.
6. 필요하면 검증 API와 렌더링 API를 별도로 실행합니다.

## 문제 형식

- `multiple_choice`: 객관식, 보기/정답 일관성 검증 가능
- `short_answer`: 단답형, 산술/방정식 일부 자동검증 가능
- `free_response`: 주관식, 기본 수동검토
- `descriptive`: 서술형, rubric 또는 수동검토
- `solution_steps`: 풀이과정형, rubric 또는 수동검토
- `graph`: 그래프형, deterministic SVG 렌더링과 payload 검증
- `table_interpretation`: 표해석형, HTML table 렌더링과 제한 검증
- `proof`: 증명형, 수동검토
- `mixed`: 혼합 생성 옵션

## 자동검증

가능한 유형:

- 단순 산술: `fractions.Fraction`
- 일차방정식: 제한된 SymPy 사용
- 2원 1차 연립방정식
- `y = ax + b` 함수값
- 객관식 보기 중복/정답 일관성
- 그래프 payload 데이터 검증
- 표 데이터 기반 정답 비교

불가능하거나 수동검토가 필요한 유형:

- 서술형, 증명형, 복잡한 풀이과정 채점
- 고차방정식, 행렬, 미적분, 긴 식, 무거운 CAS 탐색
- 이미지 자체 판독

검증 실패는 앱 오류로 처리하지 않고 `validation_results`와 `problems.validation_status`에 저장합니다.

## 그래프/표 렌더링

AI 이미지 생성은 사용하지 않습니다.

- `graph_svg`: 좌표평면, 점, 일차/간단 이차식 SVG
- `coordinate_svg`: 좌표점 SVG
- `html_table`: 표 HTML
- `geometry_svg`: 직사각형, 삼각형, 원 SVG

SVG는 `data/rendered/`에 저장하고 `/rendered/{filename}`으로 제공합니다. HTML table은
DB에 캐싱합니다. 잘못된 payload는 `render_failed`로 저장하고 문제 텍스트는 계속 표시합니다.

## 주요 API

자세한 목록은 [docs/api.md](docs/api.md)를 봅니다.

- `GET /health`, `GET /api/health`
- `GET /api/subjects`, `GET /api/textbooks`, `GET /api/units`
- `GET /api/problem-formats`, `GET /api/units/{unit_id}/allowed-formats`
- `GET /api/ai/status`, `POST /api/ai/test`
- `POST /api/generation/plan`, `POST /api/generate`
- `POST /api/generation/create`
- `GET /api/problem-sets`
- `GET /api/problem-sets/{id}`, `GET /api/problem-sets/{id}/logs`
- `DELETE /api/problem-sets/{id}`
- `GET /api/problems`, `GET /api/problems/{id}`
- `POST /api/validate/problem/{id}`, `POST /api/validate/problem-set/{id}`
- `POST /api/problems/{id}/render`, `POST /api/problem-sets/{id}/render`

## 테스트

실제 문제 생성 API:

```bash
curl -X POST http://127.0.0.1:8020/api/generation/create \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": 1,
    "unit_id": 2,
    "difficulty_level": 3,
    "requested_count": 3,
    "generation_mode": "selected",
    "selected_format_codes": ["short_answer"],
    "generation_instruction": "중학교 1학년 수준의 일차방정식 기본 문제로 만들어줘"
  }'
```

`GEMINI_API_KEYS`가 비어 있으면 이 API는 앱을 죽이지 않고 503 오류와 명확한
메시지를 반환합니다. 생성 이력은 `GET /api/problem-sets` 또는 웹
`/problem-sets`에서 확인합니다.

개발 중 DB 스키마가 바뀌면 운영 DB를 삭제하지 말고 먼저 백업합니다. 로컬 개발
DB는 필요할 때 `data/mathgen.sqlite3`를 백업한 뒤 재초기화할 수 있습니다.

```bash
python -m compileall app
python -m pytest
```

가능하면 로컬 환경에 ruff가 설치되어 있을 때만 실행합니다.

```bash
python -m ruff check .
```

## Raspberry Pi 배포 요약

운영 목표:

- 설치 경로: `/opt/mathgen`
- 서비스명: `mathgen.service`
- 내부 포트: `127.0.0.1:8020`
- 도메인: `math.dcout.site`
- DB: `/opt/mathgen/data/mathgen.sqlite3`
- 환경파일: `/etc/mathgen/mathgen.env`
- 로그: `journalctl -u mathgen -f`

배포 파일:

- `deploy/mathgen.service.example`
- `deploy/Caddyfile.math.dcout.site.example`
- `deploy/install_pi.sh`
- `deploy/backup_db.sh`

문서:

- [docs/deploy_raspberry_pi.md](docs/deploy_raspberry_pi.md)
- [docs/operations.md](docs/operations.md)

Caddyfile 전체를 덮어쓰지 말고 `math.dcout.site` 블록만 추가합니다. DNS가 먼저
도메인을 Raspberry Pi로 가리켜야 Caddy HTTPS가 정상 발급됩니다.

## Android 앱 확장 계획

- Android 앱은 별도 클라이언트로 만들고, 이 서버의 `/api/*`를 그대로 사용합니다.
- 인증이 추가되면 웹과 Android가 같은 토큰/세션 정책을 공유하도록 설계합니다.
- 과목 확장은 `subjects`, `textbooks`, `units`, `problem_formats` 메타데이터를 추가하는 방식으로 진행합니다.
- 생성, 검증, 렌더링 실패 상태를 API 응답에 안정적으로 노출해 모바일에서도 재시도/검토 UX를 만들 수 있게 유지합니다.

## 제한사항

- 실제 교과서 본문/문항은 저장하거나 재생성하지 않습니다.
- Gemini free tier 한도와 응답 JSON 품질에 영향을 받습니다.
- 자동검증은 중학교 수준의 제한된 유형만 지원합니다.
- 그래프/도형 렌더링은 MVP 범위의 단순 SVG 중심입니다.
- 공개 서비스화 전 관리자 기능과 생성 기능에 인증이 필요합니다.

## 다음 단계

- 운영 인증/관리자 기능 추가
- DB 마이그레이션 도구 검토
- 생성 큐와 작업 상태 조회 API 추가
- Android 앱용 인증 및 목록/상세 API 정리
- 문제 세트 내보내기 PDF 또는 인쇄 스타일 고도화
