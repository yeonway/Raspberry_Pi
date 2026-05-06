# Stress Test Checklist

## Minecraft

- [ ] Paper 서버 1시간 이상 실행
- [ ] 친구 4~5명 접속 테스트
- [ ] whitelist 정상 동작
- [ ] `/spark tps` 확인
- [ ] `/spark healthreport` 확인
- [ ] TPS 20 근처 유지
- [ ] MSPT 50ms 이하 유지

## 부하 유발 요소

- [ ] 레드스톤 클럭 확인
- [ ] 자동 농장 확인
- [ ] 호퍼 밀도 확인
- [ ] 주민 거래소 확인
- [ ] 몹팜 확인
- [ ] 아이템 엔티티 과다 확인
- [ ] 청크로더 사용 금지 확인

## FastAPI

- [ ] 로그인 유지 확인
- [ ] 상태 API 확인
- [ ] 로그 조회 확인
- [ ] Minecraft 시작/중지/재시작 버튼은 systemd 설정 후에만 테스트
- [ ] 백업 버튼은 dry-run 또는 로컬 zip 테스트로 먼저 확인

## NAS 백업

- [ ] 접속자 0명일 때 백업 실행
- [ ] 접속자 있을 때 대기/스킵 정책 확인
- [ ] `save-all flush` 성공
- [ ] 압축 파일 생성
- [ ] SHA256 검증 성공
- [ ] rsync 전송 성공
- [ ] 최신 5개 유지 정책 확인

## Phone AI Bridge

- [ ] Phone IP가 Raspberry Pi에서 접근 가능
- [ ] Token 인증 실패/성공 케이스 확인
- [ ] `/health` 응답 확인
- [ ] `/api/ask` 응답 확인
- [ ] 좌표 context 전달 형식 확인

## 장시간 테스트

- [ ] 6시간 이상 서버 유지
- [ ] 온도 기록
- [ ] 메모리 사용량 기록
- [ ] watchdog 재시작 로그 확인
- [ ] 치명적인 로그 오류 없음
