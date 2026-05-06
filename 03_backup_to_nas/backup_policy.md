# NAS Backup Policy

## 대상

- Minecraft 월드: `04_minecraft_server/world`, `world_nether`, `world_the_end`
- Minecraft 서버 설정과 Paper 운영 파일
- FastAPI 대시보드 코드와 문서
- systemd/watchdog 설정
- 백업/보안/라즈베리파이 체크리스트
- Android Phone AI Bridge 소스

## 제외

- `.env`
- `local.properties`
- `*.apk`, `*.aab`
- `*.db`
- `logs/`
- `backups/`
- `ngrok.yml`
- 키스토어 파일
- Gradle/Python 빌드 산출물

## 스케줄

- 3일마다 새벽 03:30
- systemd timer 또는 cron으로 등록
- 예시 cron:

```cron
30 3 */3 * * /bin/bash /home/user/Raspberry_Pi/03_backup_to_nas/backup_to_nas.sh >> /home/user/Raspberry_Pi/03_backup_to_nas/logs/cron.log 2>&1
```

## 접속자 처리

1. 03:30에 RCON `list`로 접속자 수를 확인한다.
2. 접속자가 0명이면 즉시 백업한다.
3. 접속자가 있으면 백업을 대기한다.
4. 모든 플레이어가 나가면 10분 후 다시 확인한다.
5. 다시 0명이면 백업한다.
6. 그날 `BACKUP_SKIP_CUTOFF`까지 계속 접속 중이면 백업을 스킵한다.

## 백업 절차

1. `save-all flush` 실행
2. tar.gz 또는 zip으로 압축
3. 파일 크기 기록
4. SHA256 생성
5. SHA256 검증
6. NAS로 rsync 전송
7. NAS에서 최신 5개만 유지
8. 로그에 결과 기록

## 보존

- 기본값: 최신 5개
- `.env`: `BACKUP_KEEP_COUNT=5`
- 오래된 백업 삭제는 NAS 경로가 확정된 뒤 Synology 측 스크립트 또는 SSH 명령으로 검증한다.

## 금지

- AI가 백업/삭제/복구 명령을 직접 실행하지 않는다.
- Phone AI Bridge를 백업 저장소로 사용하지 않는다.
- 검증 전 `rm -rf`, 강제 삭제, 복구 자동화를 넣지 않는다.
