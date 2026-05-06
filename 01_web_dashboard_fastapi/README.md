# 01 Web Dashboard FastAPI

Raspberry Pi에서 Minecraft 서버를 관리하기 위한 FastAPI 대시보드입니다. 현재는 라즈베리파이 도착 전 초안이며, 실제 systemd 제어는 `.env`에서 `DASHBOARD_ENABLE_SYSTEMCTL=true`로 바꾸기 전까지 비활성화합니다.

## 구조

- `app/`: FastAPI 애플리케이션 코드
- `static/`: 브라우저용 CSS/JavaScript
- `templates/`: HTML 화면
- `scripts/`: 비밀번호 해시 등 관리 스크립트
- `requirements.txt`: Python 의존성

## 설치

```bash
cd /home/user/Raspberry_Pi/01_web_dashboard_fastapi
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Raspberry Pi 운영 기준은 `0.0.0.0:8000`입니다. 외부 인터넷에 직접 공개하지 말고 로컬 네트워크에서만 접근합니다.

## 로그인 설정

```bash
python scripts/make_password_hash.py "새비밀번호"
```

생성된 값을 `.env`의 `DASHBOARD_PASSWORD_HASH`에 넣고, `DASHBOARD_PASSWORD`는 비워 둡니다.

## 기능 계획

- 로그인/API 보호
- 서버 상태 확인
- Minecraft 시작/중지/재시작
- 로그 조회
- 좌표 저장/검색/수정/삭제
- 백업 상태 확인
- Phone AI Bridge 설정
- AI 질문 테스트
- 화이트리스트 관리
- 접속 통계
- 네더 좌표 계산기
- 서버 점검 모드
- 업데이트 로그

## Phone AI Bridge 연동 계획

대시보드는 `.env`의 `PHONE_AI_BASE_URL`, `PHONE_AI_API_TOKEN`, `PHONE_AI_TIMEOUT_SECONDS`를 사용해 Android Phone AI Bridge에 요청합니다. 좌표 DB에서 검색한 결과는 `/api/ask` 요청의 context로 전달합니다. 실제 Gemma/LiteRT-LM 연결은 Android 2차 작업으로 남깁니다.

## 주의

- `.env`는 Git에 포함하지 않습니다.
- Windows에서 만든 `.venv`는 Raspberry Pi에서 재사용하지 않습니다.
- systemd 제어는 Raspberry Pi에서 sudo 권한과 서비스 등록을 마친 뒤에만 켭니다.
