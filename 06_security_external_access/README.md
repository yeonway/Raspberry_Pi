# 06 Security External Access

Raspberry Pi Minecraft 서버, FastAPI 대시보드, Android Phone AI Bridge를 안전하게 운영하기 위한 문서 폴더입니다.

## 문서

- `security_policy.md`: 전체 보안 원칙
- `phone_ai_bridge_connection.md`: Raspberry Pi에서 Android Phone AI Bridge 연결 방법
- `token_management.md`: 토큰 생성, 저장, 교체 정책

## 기본 원칙

- `.env`는 Git에 포함하지 않습니다.
- `local.properties`는 Git에 포함하지 않습니다.
- APK와 키스토어는 Git에 포함하지 않습니다.
- Phone AI Bridge는 로컬 네트워크 전용입니다.
- ngrok/public URL은 기본적으로 금지합니다.
- 외부 공개가 필요하면 별도 보안 검토 후 진행합니다.
