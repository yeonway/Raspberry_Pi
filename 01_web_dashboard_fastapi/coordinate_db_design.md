# Coordinate DB Design

FastAPI 대시보드에서 Minecraft 주요 좌표를 저장하기 위한 SQLite 설계 초안입니다.

## 테이블: coordinates

```sql
CREATE TABLE coordinates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  world TEXT NOT NULL,
  x INTEGER NOT NULL,
  y INTEGER NOT NULL,
  z INTEGER NOT NULL,
  note TEXT DEFAULT '',
  owner_player TEXT DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX idx_coordinates_world ON coordinates(world);
CREATE INDEX idx_coordinates_owner_player ON coordinates(owner_player);
CREATE INDEX idx_coordinates_name ON coordinates(name);
```

## 컬럼

- `id`: 내부 기본키
- `name`: 좌표 이름
- `world`: `overworld`, `nether`, `end`
- `x`, `y`, `z`: Minecraft 좌표
- `note`: 설명, 길 안내, 위험 요소
- `owner_player`: 등록자 또는 주 사용자
- `created_at`: ISO 8601 생성 시각
- `updated_at`: ISO 8601 수정 시각

## API 계획

- `GET /api/coordinates`: 목록/검색
- `POST /api/coordinates`: 좌표 생성
- `GET /api/coordinates/{id}`: 단건 조회
- `PATCH /api/coordinates/{id}`: 좌표 수정
- `DELETE /api/coordinates/{id}`: 좌표 삭제
- `POST /api/coordinates/nether`: 오버월드/네더 좌표 변환

## AI context 전달

AI 질문 테스트 시 대시보드는 질문과 함께 관련 좌표를 검색해 다음 형태로 Phone AI Bridge에 전달합니다.

```json
{
  "question": "철 농장 위치 알려줘",
  "player": "Steve",
  "context": {
    "coordinates": [
      {
        "name": "Iron Farm",
        "world": "overworld",
        "x": 120,
        "y": 64,
        "z": -300,
        "note": "마을 북쪽"
      }
    ]
  }
}
```
