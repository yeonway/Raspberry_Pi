# 쓸데없는 실험실

수업시간에 만든 잡동사니 미니게임을 모아두는 정적 웹앱입니다.

## 포함된 게임

- 반응속도: 초록색이 된 뒤 최대한 빨리 클릭합니다.
- 순간 클릭: 10초 동안 최대한 많이 클릭합니다.
- 가위바위보: 컴퓨터와 한 판씩 겨룹니다.
- 숫자 야구: 3자리 숫자를 맞춥니다.
- 낙서판: 브라우저에서 간단히 낙서합니다.

## 로컬 실행

```powershell
cd C:\Users\HOME\Desktop\Raspberry_Pi\10_useless_lab_site
python -m http.server 8011 --bind 127.0.0.1 --directory web
```

브라우저에서 `http://127.0.0.1:8011`로 접속합니다.

## 검증

```powershell
node --check web\app.js
python -m http.server 8011 --bind 127.0.0.1 --directory web
```

## 라즈베리파이 배포

자세한 명령은 `deploy/README.md`를 확인합니다.

배포 도메인:

- `https://minigame.dcout.site`
