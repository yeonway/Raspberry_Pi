import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.coordinate_sync import coordinate_db_path, coordinate_db_table


def list_coordinates(query: str = "", limit: int = 200, owner: str = "") -> Dict[str, Any]:
    path = _ensure_db()
    table = coordinate_db_table()
    q = f"%{query.strip()}%"
    owner_value = owner.strip()

    conditions: list[str] = []
    params: list[Any] = []
    if query.strip():
        conditions.append("(name LIKE ? OR world LIKE ? OR note LIKE ? OR owner LIKE ?)")
        params.extend([q, q, q, q])
    if owner_value:
        conditions.append("LOWER(owner) = LOWER(?)")
        params.append(owner_value)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    params.append(max(1, min(limit, 500)))
    with closing(sqlite3.connect(str(path))) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT id, name, world, x, y, z, note, owner, created_at, updated_at
            FROM {table}
            {where}
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    return {"ok": True, "count": len(rows), "items": [_row_to_dict(row) for row in rows]}


def save_coordinate(payload: Dict[str, Any], owner_fallback: str = "") -> Dict[str, Any]:
    path = _ensure_db()
    table = coordinate_db_table()
    now = datetime.now().isoformat(timespec="seconds")

    name = str(payload.get("name") or "").strip()
    if not name:
        return {"ok": False, "message": "좌표 이름을 입력하세요."}

    try:
        x = float(payload.get("x"))
        z = float(payload.get("z"))
    except (TypeError, ValueError):
        return {"ok": False, "message": "x, z 좌표는 숫자로 입력하세요."}

    try:
        y = _optional_float(payload.get("y"))
    except (TypeError, ValueError):
        return {"ok": False, "message": "y coordinate must be a number."}
    world = str(payload.get("world") or "overworld").strip() or "overworld"
    note = str(payload.get("note") or "").strip()
    owner = str(payload.get("owner") or owner_fallback or "").strip()
    coordinate_id = payload.get("id")
    saved_id: int | None = None
    if coordinate_id:
        try:
            saved_id = int(coordinate_id)
        except (TypeError, ValueError):
            return {"ok": False, "message": "coordinate id must be a number."}

    with closing(sqlite3.connect(str(path))) as conn:
        conn.row_factory = sqlite3.Row
        if saved_id is not None:
            cursor = conn.execute(
                f"""
                UPDATE {table}
                SET name = ?, world = ?, x = ?, y = ?, z = ?, note = ?, owner = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, world, x, y, z, note, owner, now, saved_id),
            )
            if cursor.rowcount == 0:
                return {"ok": False, "message": "coordinate not found."}
        else:
            cursor = conn.execute(
                f"""
                INSERT INTO {table} (name, world, x, y, z, note, owner, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, world, x, y, z, note, owner, now, now),
            )
            saved_id = int(cursor.lastrowid)

        conn.commit()
        row = conn.execute(
            f"SELECT id, name, world, x, y, z, note, owner, created_at, updated_at FROM {table} WHERE id = ?",
            (saved_id,),
        ).fetchone()

    if row is None:
        return {"ok": False, "message": "coordinate not found."}
    return {"ok": True, "item": _row_to_dict(row), "message": "좌표 저장 완료"}


def delete_coordinate(coordinate_id: int, owner: str = "") -> Dict[str, Any]:
    path = _ensure_db()
    table = coordinate_db_table()
    owner_value = owner.strip()
    where = "id = ?"
    params: list[Any] = [coordinate_id]
    if owner_value:
        where += " AND LOWER(owner) = LOWER(?)"
        params.append(owner_value)

    with closing(sqlite3.connect(str(path))) as conn:
        cursor = conn.execute(f"DELETE FROM {table} WHERE {where}", params)
        conn.commit()
    return {"ok": True, "deleted": cursor.rowcount, "message": "좌표 삭제 완료"}


def _ensure_db() -> Path:
    path = coordinate_db_path()
    if path is None:
        raise RuntimeError("coordinate DB path is not configured")
    path.parent.mkdir(parents=True, exist_ok=True)
    table = coordinate_db_table()

    with closing(sqlite3.connect(str(path))) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                world TEXT NOT NULL DEFAULT 'overworld',
                x REAL NOT NULL,
                y REAL,
                z REAL NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                owner TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(conn, table, "owner", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, table, "note", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, table, "updated_at", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, table, "created_at", "TEXT NOT NULL DEFAULT ''")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_world ON {table}(world)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_name ON {table}(name)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_owner ON {table}(owner)")
        conn.commit()
    return path


def _ensure_column(conn: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    columns = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def _optional_float(value: Any) -> Optional[float]:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "world": row["world"],
        "x": row["x"],
        "y": row["y"],
        "z": row["z"],
        "note": row["note"],
        "owner": row["owner"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
