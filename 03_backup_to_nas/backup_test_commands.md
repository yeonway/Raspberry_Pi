# Backup Test Commands

Raspberry Pi와 Synology NAS가 준비된 뒤 순서대로 실행합니다.

## 1. SSH 연결

```bash
ssh user@192.168.0.20
```

## 2. NAS 대상 폴더 확인

```bash
ssh user@192.168.0.20 'mkdir -p /volume1/minecraft_backups/raspberry_pi && ls -ld /volume1/minecraft_backups/raspberry_pi'
```

## 3. rsync dry-run

```bash
rsync -avhn /home/user/Raspberry_Pi/README.md user@192.168.0.20:/volume1/minecraft_backups/raspberry_pi/
```

## 4. RCON 확인

```bash
mcrcon -H 127.0.0.1 -P 25575 -p "$MINECRAFT_RCON_PASSWORD" "list"
mcrcon -H 127.0.0.1 -P 25575 -p "$MINECRAFT_RCON_PASSWORD" "save-all flush"
```

## 5. 로컬 백업 초안 실행

```bash
cd /home/user/Raspberry_Pi
python3 03_backup_to_nas/scripts/backup.py
sha256sum -c 03_backup_to_nas/backups/*.sha256
```

## 6. NAS 스크립트 dry-run

```bash
cd /home/user/Raspberry_Pi/03_backup_to_nas
BACKUP_DRY_RUN=true bash backup_to_nas.sh
```

## 7. 실제 전송

```bash
BACKUP_DRY_RUN=false bash backup_to_nas.sh
```

## 8. NAS 보관 확인

```bash
ssh user@192.168.0.20 'ls -lh /volume1/minecraft_backups/raspberry_pi | tail'
```

## 9. 스케줄 등록 전 점검

- 접속자가 있을 때 스킵/대기 로직이 설계대로 동작하는지 확인
- 백업 파일 크기가 0이 아닌지 확인
- SHA256 검증이 성공하는지 확인
- 최신 5개 유지 정책을 수동으로 먼저 검증
