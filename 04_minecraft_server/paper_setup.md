# Paper Setup

## Java 확인

```bash
java --version
```

Java 25를 목표로 하되, 실제 Paper 빌드가 요구하는 Java 버전을 Paper 공식 문서에서 다시 확인합니다.

## Paper 배치

`paper.jar`를 이 폴더에 둡니다.

```bash
cd /home/user/Raspberry_Pi/04_minecraft_server
ls -lh paper.jar
```

## 최초 실행

```bash
java -Xms1G -Xmx4G -jar paper.jar nogui
```

실행 후 생성된 `eula.txt`를 수정합니다.

```text
eula=true
```

## 설정 적용

```bash
cp server.properties.example server.properties
```

`server.properties`의 `rcon.password`는 `.env`의 `MINECRAFT_RCON_PASSWORD`와 같은 값으로 설정합니다. 실제 비밀번호는 문서나 Git에 쓰지 않습니다.

## systemd 실행

```bash
sudo systemctl start minecraft.service
sudo systemctl status minecraft.service
```

## 화이트리스트

```text
whitelist add PLAYER_NAME
whitelist list
```

화이트리스트는 친구 전용 운영의 기본 전제입니다.
