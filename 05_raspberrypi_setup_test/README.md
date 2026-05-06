# 05 Raspberry Pi Setup Test

Raspberry Pi 5 도착 후 하드웨어, OS, Java, Paper, FastAPI, NAS, Phone AI Bridge 연결을 순서대로 검증하기 위한 체크리스트입니다.

## 문서

- `hardware_checklist.md`: 전원, SSD, 쿨러, 온도 확인
- `os_setup_checklist.md`: OS 업데이트, Java 25, Python, systemd 준비
- `stress_test_checklist.md`: Minecraft/FastAPI/NAS/Phone AI Bridge 통합 부하 테스트

## 기존 스크립트

- `scripts/check_system.sh`
- `scripts/stress_test.sh`
- `scripts/temperature_watch.sh`

스크립트는 Raspberry Pi에서만 실행합니다. Windows 개발 환경에서는 문서 검토만 합니다.
