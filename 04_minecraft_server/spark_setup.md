# spark Setup

spark는 Paper 서버 성능 분석용 플러그인입니다.

## 설치

1. spark 플러그인 jar를 다운로드합니다.
2. `04_minecraft_server/plugins/` 폴더에 둡니다.
3. Minecraft 서버를 재시작합니다.

```bash
ls -lh /home/user/Raspberry_Pi/04_minecraft_server/plugins
sudo systemctl restart minecraft.service
```

## 기본 확인

Minecraft 콘솔 또는 OP 권한 플레이어로 실행합니다.

```text
/spark tps
/spark healthreport
/spark profiler start
/spark profiler stop
```

## 확인 항목

- TPS가 20 근처인지
- MSPT가 50ms 이하인지
- 특정 월드/청크/엔티티가 과도한 시간을 쓰는지
- 레드스톤, 농장, 호퍼, 주민, 몹팜이 병목인지
- 청크 생성이나 탐험으로 CPU가 치솟는지

## 운영 판단

TPS/MSPT 문제가 반복되면 다음 순서로 조정합니다.

1. view-distance 축소
2. simulation-distance 축소
3. 자동화 장치 제한
4. 호퍼/주민/몹팜 밀도 줄이기
5. 아이템 엔티티 정리
6. 청크로더 금지
