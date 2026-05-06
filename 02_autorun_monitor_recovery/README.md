# 02 Autorun Monitor Recovery

Raspberry Pi에서 FastAPI 대시보드와 Minecraft Paper 서버를 systemd로 자동 실행하고, watchdog으로 비정상 종료를 감시하는 초안입니다.

## 파일

- `dashboard.service`: FastAPI 대시보드 서비스
- `minecraft.service`: Minecraft Paper 서버 서비스
- `watchdog.service`: watchdog 서비스
- `watchdog.sh`: 서비스 상태 확인 및 재시작 초안
- `scripts/service_control.py`: 대시보드에서 systemctl을 호출할 때 사용하는 보조 스크립트
- `scripts/watchdog.py`: 기존 Python watchdog 보존본

## 설치

Raspberry Pi에서 프로젝트가 `/home/user/Raspberry_Pi`에 있다고 가정합니다.

```bash
sudo cp /home/user/Raspberry_Pi/02_autorun_monitor_recovery/dashboard.service /etc/systemd/system/dashboard.service
sudo cp /home/user/Raspberry_Pi/02_autorun_monitor_recovery/minecraft.service /etc/systemd/system/minecraft.service
sudo cp /home/user/Raspberry_Pi/02_autorun_monitor_recovery/watchdog.service /etc/systemd/system/watchdog.service
sudo chmod +x /home/user/Raspberry_Pi/02_autorun_monitor_recovery/watchdog.sh
sudo systemctl daemon-reload
```

## 활성화

```bash
sudo systemctl enable dashboard.service
sudo systemctl enable minecraft.service
sudo systemctl enable watchdog.service
sudo systemctl start dashboard.service
sudo systemctl start minecraft.service
sudo systemctl start watchdog.service
```

## 상태 확인

```bash
systemctl status dashboard.service
systemctl status minecraft.service
systemctl status watchdog.service
journalctl -u dashboard.service -n 100 --no-pager
journalctl -u minecraft.service -n 100 --no-pager
```

## 대시보드 제어 권한

대시보드에서 Minecraft 시작/중지/재시작을 실제로 수행하려면 다음 조건을 만족해야 합니다.

- `dashboard.service`가 Raspberry Pi에서 실행 중
- `scripts/service_control.py`가 systemctl을 호출할 수 있음
- sudoers 또는 서비스 권한 설정 완료
- `.env`의 `DASHBOARD_ENABLE_SYSTEMCTL=true`

라즈베리파이 도착 전 또는 Windows 개발 환경에서는 `false`로 유지합니다.

## 주의

- 서비스 파일의 사용자 계정은 `user` 기준입니다. 실제 계정이 다르면 service 파일과 경로를 함께 바꿉니다.
- watchdog은 백업/삭제/복구 명령을 실행하지 않습니다.
- 복구 테스트와 복구 자동화는 현재 제외된 기능입니다.
