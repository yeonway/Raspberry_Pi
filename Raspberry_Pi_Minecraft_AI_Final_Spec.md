# Raspberry Pi Minecraft AI Final Spec

이 문서는 Raspberry Pi 도착 전 정리 단계의 기준 스펙입니다. 루트에 원본 첨부 스펙 파일이 없어서, 현재 작업 지시의 내용을 기준으로 재구성했습니다.

## 목표

Raspberry Pi 5에서 친구 전용 Minecraft Paper 서버를 안정적으로 운영하고, Android Phone AI Bridge를 로컬 AI/RAG 장치로 연결하며, Synology NAS에 검증 가능한 백업을 보관한다.

## 최종 구성

### Raspberry Pi 5
- Minecraft Paper 서버
- FastAPI 웹 대시보드
- SQLite 좌표 DB
- systemd 자동실행/자동복구
- Synology NAS rsync 백업
- Android Phone AI Bridge 호출

### Android Phone
- Phone AI Bridge Android 앱
- 프로젝트 폴더: `06-1_phone_ai_bridge_android`
- Ktor 로컬 서버
- 내부 IP 표시
- Token 인증
- MockAiEngine
- RAG
- 플레이어 기억
- 요청 로그
- 2차 작업: Gemma 4 E2B 4bit, LiteRT-LM 연결

### Synology NAS
- Minecraft 월드 백업 저장소
- 프로젝트 백업 저장소
- 최신 5개 백업 유지

## 백업 정책

- 3일마다 새벽 3:30 실행
- 03:30에 접속자가 없으면 즉시 백업
- 접속자가 있으면 대기
- 모든 플레이어가 나간 뒤 10분 후 다시 확인
- 그날 계속 접속 중이면 백업 스킵
- `save-all` 후 압축
- SHA256 및 파일 크기 무결성 검사
- Synology NAS로 rsync 전송
- 최신 5개만 유지

## FastAPI 대시보드 기능 계획

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

## 좌표 DB 설계

`coordinates` 테이블:

| 컬럼 | 설명 |
| --- | --- |
| `id` | 정수 기본키 |
| `name` | 좌표 이름 |
| `world` | `overworld`, `nether`, `end` 등 |
| `x` | X 좌표 |
| `y` | Y 좌표 |
| `z` | Z 좌표 |
| `note` | 메모 |
| `owner_player` | 등록/소유 플레이어 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

## 제외 기능

Snake game, Snake 강화학습, YouTube Shorts Live, FFmpeg streaming, Shorts 영상/음악 제작, Android Phone을 저장소로 쓰는 구조, 복구 테스트, 복구 자동화, 서버 공지/규칙 페이지, 좌표 카테고리 확장, AI의 Minecraft 명령어 직접 실행, AI의 월드 블록 직접 수정, AI의 백업/삭제/복구 명령 실행은 현재 범위에서 제외한다.

## 보안 원칙

- 민감정보는 하드코딩하지 않는다.
- `.env`, `local.properties`, `*.apk`, `*.db`, `logs/`, `backups/`, `ngrok.yml`은 Git에 포함하지 않는다.
- Phone AI Bridge는 로컬 네트워크 전용으로 사용한다.
- 외부 공개 URL, ngrok, 포트포워딩은 기본 금지로 둔다.
