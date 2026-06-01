# KiwoomPocket Android

Kotlin + Jetpack Compose 단일 Activity Android 앱입니다. Android 앱은 키움 `appkey`/`secretkey`를 저장하지 않고 FastAPI 중계 서버만 호출합니다.

## Android Studio에서 열기

1. Android Studio에서 `C:\Users\HOME\Desktop\Raspberry_Pi\08_kiwoom_pocket_project\android` 폴더를 엽니다.
2. Gradle Sync를 실행합니다.
3. `app` 모듈의 `MainActivity`를 디버그 실행합니다.

## 서버 주소 설정

앱 실행 후 `설정` 탭에서 입력합니다.

- 서버 주소: `http://라즈베리파이_IP:8000`
- Bridge API 토큰: 서버 `.env`의 `BRIDGE_API_TOKEN`
- 모의/실전 표시는 UI 안내용입니다. 키움 실제 모드는 서버 `.env`의 `KIWOOM_MODE`가 결정합니다.

키움 API 키는 Android 앱에 저장하지 않습니다.

## APK 빌드

```powershell
cd "C:\Users\HOME\Desktop\Raspberry_Pi\08_kiwoom_pocket_project\android"
.\gradlew.bat assembleDebug
```

빌드 결과:

```text
app/build/outputs/apk/debug/app-debug.apk
```

## 디버그 실행

```powershell
cd "C:\Users\HOME\Desktop\Raspberry_Pi\08_kiwoom_pocket_project\android"
.\gradlew.bat installDebug
```

빈 서버 주소 상태에서도 앱은 크래시하지 않고 설정 안내 오류를 표시합니다.
