# 03 Backup To NAS

Synology NAS로 Minecraft 월드와 프로젝트를 백업하기 위한 폴더입니다. Android Phone은 백업 저장소가 아니며, 이 프로젝트에서 폰은 AI/RAG 장치로만 사용합니다.

## 파일

- `backup_to_nas.sh`: Raspberry Pi용 dry-run 중심 백업 스크립트 초안
- `backup_policy.md`: 백업 정책
- `backup_test_commands.md`: 라즈베리파이 도착 후 테스트 명령
- `scripts/backup.py`: 대시보드에서 호출 가능한 로컬 zip 백업 초안
- `scripts/cleanup.py`: 로컬 zip 최신 N개 유지 도구
- `config/backup_config.json`: Python 백업 도구 설정

## 정책 요약

- 3일마다 03:30 실행
- 03:30에 접속자가 없으면 즉시 백업
- 접속자가 있으면 대기
- 모든 플레이어가 나간 뒤 10분 후 다시 확인
- 그날 계속 접속 중이면 백업 스킵
- `save-all` 후 압축
- SHA256/파일 크기 검사
- Synology NAS로 rsync 전송
- 최신 5개만 유지

## dry-run 실행

```bash
cd /home/user/Raspberry_Pi/03_backup_to_nas
BACKUP_DRY_RUN=true bash backup_to_nas.sh
```

실제 전송은 SSH 키, NAS 경로, RCON, 보관 정책을 모두 검증한 뒤에만 켭니다.

```bash
BACKUP_DRY_RUN=false bash backup_to_nas.sh
```

## 대시보드 연동

FastAPI 대시보드의 `backup_run` 명령은 현재 `scripts/backup.py`를 호출해 로컬 zip과 SHA256 파일을 생성합니다. NAS rsync 실제 전송은 Raspberry Pi 도착 후 `backup_to_nas.sh`에서 검증합니다.
