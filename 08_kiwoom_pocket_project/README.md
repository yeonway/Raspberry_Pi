# kiwoom-pocket-project

`KiwoomPocket` Android 앱과 라즈베리파이용 `kiwoom-bridge` FastAPI 중계 서버를 한 폴더에서 관리하는 프로젝트입니다.

- `server/`: 키움 REST API 인증, 토큰 관리, DB, Android용 중계 API
- `android/`: Kotlin + Jetpack Compose 단일 모듈 Android 앱

키움 `appkey`와 `secretkey`는 Android 앱에 포함하지 않습니다. Android 앱은 `BRIDGE_API_TOKEN`만 저장하고 FastAPI 서버만 호출합니다.
