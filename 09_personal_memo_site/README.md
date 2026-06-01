# 09 Personal Memo Site

개인별 메모를 저장하는 작은 FastAPI 웹앱입니다. 일반 사용자는 자기 메모만 볼 수 있고, 관리자 계정은 모든 사용자의 메모를 볼 수 있습니다.

## 기능

- 회원가입, 로그인, 로그아웃
- 개인 메모 작성과 삭제
- 일반 사용자: 본인 메모만 조회
- 관리자: 전체 사용자 메모 조회 및 삭제
- SQLite 저장소
- 비밀번호 PBKDF2 해시 저장
- HttpOnly 세션 쿠키

## 설치

```bash
cd C:\Users\HOME\Desktop\Raspberry_Pi\09_personal_memo_site
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 실행

```bash
$env:MEMO_SECRET_KEY = "긴-랜덤-문자열로-변경"
uvicorn app.main:app --host 127.0.0.1 --port 8009
```

브라우저에서 `http://127.0.0.1:8009`로 접속합니다.

## 관리자 만들기

관리자 비밀번호를 코드에 넣지 않기 위해 대화형 스크립트로 생성합니다.

```bash
python scripts/create_admin.py
```

또는 최초 실행 시 환경변수로 관리자 계정을 만들 수 있습니다.

```bash
$env:MEMO_ADMIN_USERNAME = "admin"
$env:MEMO_ADMIN_PASSWORD = "관리자-비밀번호"
uvicorn app.main:app --host 127.0.0.1 --port 8009
```

## 검증

```bash
pytest
```

## 운영 메모

- `memo.db`에는 사용자와 메모가 저장됩니다.
- `.env`, `memo.db`, 비밀번호, 토큰은 Git에 올리지 않습니다.
- 외부 공개 전에는 HTTPS 뒤에서 실행하고 `MEMO_SECURE_COOKIES=true`를 설정하세요.
