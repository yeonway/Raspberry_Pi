# OS Setup Checklist

## 업데이트

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

- [ ] OS 업데이트 완료
- [ ] 재부팅 후 SSH 접속 가능

## 기본 도구

```bash
sudo apt install -y git curl wget unzip rsync python3 python3-venv python3-pip
```

- [ ] Python 3 설치
- [ ] rsync 설치
- [ ] curl/wget 설치

## Java 25

```bash
java --version
```

- [ ] Java 25 설치 확인
- [ ] Paper 요구 Java 버전과 일치 확인

## FastAPI

```bash
cd /home/user/Raspberry_Pi/01_web_dashboard_fastapi
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- [ ] `/health` 응답 확인
- [ ] 로그인 확인

## systemd

- [ ] `dashboard.service` 등록
- [ ] `minecraft.service` 등록
- [ ] `watchdog.service` 등록
- [ ] `systemctl enable` 완료
- [ ] 재부팅 후 자동 실행 확인

## NAS

- [ ] SSH 키 등록
- [ ] rsync dry-run 성공
- [ ] 백업 대상 폴더 쓰기 권한 확인

## Phone AI Bridge

- [ ] Android 앱 실행
- [ ] Home 화면에서 Current Phone IP 확인
- [ ] API token 재생성
- [ ] Raspberry Pi `.env` 입력
- [ ] `/health` 테스트
- [ ] `/api/ask` 테스트
