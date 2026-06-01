# AGENTS.md

- 이 프로젝트는 라즈베리파이에서 운영할 FastAPI 웹서비스다.
- 실제 비밀값, API 키, access token, 결제 키는 절대 코드에 넣지 않는다.
- 모든 비밀값은 `.env`로만 관리한다.
- 기존 라즈베리파이의 Caddy, systemd, 다른 서비스는 명시 요청 없이는 수정하지 않는다.
- 각 단계는 작게 구현하고 테스트한다.
- 변경 후 항상 아래 검증 명령을 실행한다.
  - `python -m compileall app`
- 가능하면 실행 확인도 한다.
  - `uvicorn app.main:app --host 127.0.0.1 --port 8015`
  - `curl http://127.0.0.1:8015/health`
- 작업 완료 보고에는 변경 파일 목록, 실행한 명령, 결과, 다음 단계 제안을 포함한다.
