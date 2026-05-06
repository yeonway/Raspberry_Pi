# Hardware Checklist

## 필수

- [ ] Raspberry Pi 5 본체 확인
- [ ] 정품 27W USB-C 전원 사용
- [ ] SSD 부팅 장치 준비
- [ ] SSD 케이블/어댑터 안정성 확인
- [ ] 쿨러 또는 액티브 케이스 장착
- [ ] 유선 LAN 또는 안정적인 Wi-Fi 확인

## 부팅

- [ ] SSD에서 정상 부팅
- [ ] 전원 부족 경고 없음
- [ ] 재부팅 후 자동 마운트 정상
- [ ] 장시간 켜둔 뒤 연결 끊김 없음

## 온도

```bash
vcgencmd measure_temp
```

- [ ] 유휴 온도 기록
- [ ] Paper 실행 중 온도 기록
- [ ] 부하 테스트 중 스로틀링 없음

## 네트워크

- [ ] Raspberry Pi 고정 IP 또는 DHCP 예약 설정
- [ ] Android Phone과 같은 로컬 네트워크에 있음
- [ ] Synology NAS와 같은 로컬 네트워크에서 접근 가능
