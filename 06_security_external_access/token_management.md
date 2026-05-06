# Token Management

## 저장 위치

토큰은 `.env`에만 저장합니다.

```env
PHONE_AI_API_TOKEN=실제_토큰
DASHBOARD_SECRET_KEY=실제_랜덤값
MINECRAFT_RCON_PASSWORD=실제_RCON_비밀번호
```

`.env`는 `.gitignore`에 포함되어 있어야 하며, 문서나 로그에 값을 쓰지 않습니다.

## 생성

- Dashboard session secret: 길고 랜덤한 문자열
- Phone AI Bridge token: 앱 설정 화면에서 재생성
- RCON password: `server.properties`와 `.env`에 같은 값 입력

## 교체 시점

- 토큰이 노출되었을 때
- 폰을 바꾸거나 앱 데이터를 초기화했을 때
- public URL 테스트를 했을 때
- 다른 사람이 같은 네트워크에서 접근할 수 있었을 때

## 검증

토큰 없이 요청했을 때 실패해야 합니다.

```bash
curl -i "$PHONE_AI_BASE_URL/api/ask"
```

토큰을 넣으면 성공해야 합니다.

```bash
curl -i -H "Authorization: Bearer $PHONE_AI_API_TOKEN" "$PHONE_AI_BASE_URL/health"
```

## 금지

- 토큰 하드코딩 금지
- APK 안에 운영 토큰 포함 금지
- GitHub, 메신저, 스크린샷에 토큰 노출 금지
- ngrok/public URL에 인증 없는 API 공개 금지
