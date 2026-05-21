# 04 Minecraft Server

Raspberry Pi 5에서 Paper Minecraft 서버를 실행하기 위한 폴더입니다. 현재 `paper.jar`, `server.properties`, 월드 폴더가 있을 수 있지만, Git에는 실제 서버 파일과 월드 데이터를 포함하지 않습니다.

## Raspberry Pi 준비

```bash
java --version
```

Java 25가 설치되어 있는지 확인합니다. Paper가 요구하는 Java 버전은 Paper 릴리스 기준에 맞춰 다시 확인합니다.

## 최초 실행

```bash
cd /home/user/Raspberry_Pi/04_minecraft_server
java -Xms1G -Xmx4G -jar paper.jar nogui
```

최초 실행 후 `eula.txt`를 열어 다음처럼 바꿉니다.

```text
eula=true
```

그 뒤 `server.properties.example`을 참고해 실제 `server.properties`를 작성합니다.

## 운영 기준

- 친구 전용, 4~5명 기준
- `white-list=true`
- `enforce-whitelist=true`
- `online-mode=true`
- `view-distance=6`
- `simulation-distance=4`
- `max-players=5`
- RCON 비밀번호는 `.env`와 실제 `server.properties`에만 저장

## 부하 관리

Raspberry Pi 5는 대형 자동화 장치에 취약할 수 있습니다. 다음 요소는 TPS/MSPT 저하 원인이므로 spark로 주기적으로 확인합니다.

- 레드스톤 클럭
- 자동 농장
- 호퍼 체인
- 주민 거래소
- 몹팜
- 아이템 엔티티 과다
- 청크로더
- 과도한 탐험으로 인한 신규 청크 생성

목표는 TPS 20 근처, MSPT 50ms 이하입니다. 문제가 생기면 view-distance, simulation-distance, 엔티티 수, 자동화 장치 사용량을 먼저 조정합니다.

## 관련 문서

- `phone_ai_bridge_paper_plugin/README.md`
- `paper_setup.md`
- `spark_setup.md`
- `server.properties.example`
