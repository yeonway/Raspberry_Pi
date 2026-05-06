# Security Policy

## 민감정보 금지

다음 파일과 값은 Git에 포함하지 않습니다.

- `.env`
- `local.properties`
- `*.apk`, `*.aab`
- `*.db`
- `logs/`
- `backups/`
- `ngrok.yml`
- `*.jks`, `*.keystore`
- API token
- RCON password
- NAS SSH private key

## 대시보드

- 기본 비밀번호를 사용하지 않습니다.
- `DASHBOARD_PASSWORD_HASH`를 사용하고 평문 비밀번호는 비워 둡니다.
- 외부 인터넷에 직접 공개하지 않습니다.
- systemd 제어는 Raspberry Pi에서 권한을 확인한 뒤에만 켭니다.

## Minecraft

- `online-mode=true`
- `white-list=true`
- `enforce-whitelist=true`
- RCON은 로컬 또는 제한된 네트워크에서만 사용
- `rcon.password`는 문서에 쓰지 않음

## Phone AI Bridge

- 로컬 네트워크 전용
- Token 인증 필수
- public URL, 포트포워딩, ngrok 공개 금지
- 폰은 백업 저장소가 아니라 AI/RAG 장치

## NAS

- rsync는 SSH 키 기반 인증 권장
- 백업 대상 디렉터리 권한 최소화
- 삭제/보존 정책은 dry-run으로 먼저 검증
- 최신 5개 유지 정책 외 임의 삭제 금지

## ngrok/public URL 주의

ngrok 또는 public URL은 실수로 대시보드, Phone AI Bridge, RCON을 외부에 노출할 수 있습니다. 현재 단계에서는 사용하지 않습니다. 임시 테스트가 필요하면 토큰, 접근 IP, 만료 시간, 로그를 별도 점검합니다.
