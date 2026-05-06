# Raspberry Pi 5 Minecraft AI Server

Raspberry Pi 5에서 Paper Minecraft 서버와 FastAPI 대시보드를 운영하고, Android Phone AI Bridge를 로컬 AI/RAG 장치로 호출하며, Synology NAS에 월드와 프로젝트 백업을 보관하는 프로젝트입니다.

## 장치 역할

### Raspberry Pi 5
- Minecraft Paper 서버 실행
- FastAPI 웹 대시보드 제공
- SQLite 좌표 DB 운영
- systemd 자동실행 및 watchdog 자동복구
- Synology NAS로 rsync 백업 전송
- Android Phone AI Bridge API 호출

### Android Phone
- Phone AI Bridge Android 앱 실행
- Ktor 로컬 서버 제공
- Token 인증
- MockAiEngine 기반 1차 MVP
- RAG, 플레이어 기억, 요청 로그 저장
- 2차 작업에서 Gemma 4 E2B 4bit 및 LiteRT-LM 연결

### Synology NAS
- Minecraft 월드와 프로젝트 백업 저장소
- SHA256/파일 크기 검증된 백업 보관
- 최신 5개 백업 유지

## 현재 완료된 것

- Android `ai` 폴더는 Phone AI Bridge 1차 MVP 완료 상태로 본다.
- FastAPI 대시보드 초안은 로그인, 상태 확인, 로그 조회, Minecraft 제어 요청, 백업 요청 API를 포함한다.
- systemd 서비스 초안과 watchdog 초안이 정리되어 있다.
- Minecraft Paper 서버 폴더에는 실행 파일과 기본 설정 초안이 있다.
- NAS 백업 정책과 dry-run 중심 스크립트 초안이 있다.

## Raspberry Pi 도착 후 할 일

1. SSD 부팅과 정품 27W 전원 확인
2. Raspberry Pi OS 업데이트
3. Java 25 설치 확인
4. Paper 서버 최초 실행 및 `eula=true` 설정
5. spark 플러그인 설치
6. FastAPI `.venv` 재생성 및 대시보드 실행
7. systemd 서비스 등록 및 자동실행 확인
8. Synology NAS SSH/rsync 테스트
9. Phone AI Bridge와 `/health`, `/api/ask` 연결 테스트
10. 전체 부하 테스트 및 TPS/MSPT 확인

## 폴더 설명

- `01_web_dashboard_fastapi`: FastAPI 대시보드, 좌표 DB 계획, 정적 화면
- `02_autorun_monitor_recovery`: systemd 서비스와 watchdog 자동복구
- `03_backup_to_nas`: Synology NAS 백업 정책, 테스트 명령, dry-run 백업 초안
- `04_minecraft_server`: Paper 서버 설정, Java/Paper/spark 안내
- `05_raspberrypi_setup_test`: 라즈베리파이 하드웨어, OS, 부하 테스트 체크리스트
- `06_security_external_access`: 보안 정책, Phone AI Bridge 연결, 토큰 관리
- `ai`: Android Phone AI Bridge 앱

## 제외된 기능

현재 계획에서 제외된 기능은 Snake game, Snake 강화학습, YouTube Shorts Live, FFmpeg streaming, Shorts 영상/음악 제작, Android Phone을 저장소로 쓰는 구조, 복구 테스트, 복구 자동화, 서버 공지/규칙 페이지, 좌표 카테고리 확장, AI의 Minecraft 명령어 직접 실행, AI의 월드 블록 직접 수정, AI의 백업/삭제/복구 명령 실행입니다.

## 1차 작업

- Raspberry Pi 기준 폴더/문서 정리
- `.env.example` 정리
- NAS 백업 정책 문서화
- systemd 서비스 초안 정리
- Minecraft Paper 운영 체크리스트 작성
- Phone AI Bridge 연결 문서 작성

## 2차 작업

- Raspberry Pi 실기기에서 Paper와 FastAPI 실행 검증
- NAS rsync 실제 연결
- Phone AI Bridge 실기기 연결
- Gemma 4 E2B 4bit 및 LiteRT-LM 연결
- 대시보드의 좌표 DB CRUD, AI 질문 테스트, 화이트리스트 관리 구현

## 민감정보 원칙

`.env`, `local.properties`, `*.apk`, `*.db`, `logs/`, `backups/`, `ngrok.yml`, 키스토어 파일은 Git에 포함하지 않습니다. Phone AI Bridge는 로컬 네트워크 전용으로 운영하고, public URL 공개는 기본적으로 금지합니다.
