import os
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.logs import write_log
from app.phone_ai import phone_ai_configured, save_phone_coordinate
from app.security import env_bool


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATHS = (
    Path("/home/user/server/dashboard/dashboard.db"),
    PROJECT_DIR / "dashboard.db",
)

STATE: Dict[str, Any] = {
    "last_sync_started_at": None,
    "last_sync_finished_at": None,
    "last_sync_ok": None,
    "last_sync_message": None,
    "last_synced_count": 0,
    "last_failed_count": 0,
    "last_errors": [],
    "last_attempt_monotonic": 0.0,
}


@dataclass(frozen=True)
class DashboardCoordinate:
    id: str
    name: str
    world: str
    x: float
    y: Optional[float]
    z: float
    note: str
    owner: str
    updated_at: str

    def to_phone_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": f"pi-dashboard-{self.id}",
            "name": self.name,
            "world": self.world or "overworld",
            "x": self.x,
            "z": self.z,
            "description": self.note,
            "created_by": self.owner,
            "tags": ["raspberry_pi", "dashboard"],
        }
        if self.y is not None:
            payload["y"] = self.y
        return payload


def coordinate_sync_enabled() -> bool:
    return env_bool("COORDINATE_SYNC_TO_PHONE", True)


def coordinate_sync_limit() -> int:
    try:
        return max(1, int(os.getenv("COORDINATE_SYNC_LIMIT", "200")))
    except ValueError:
        return 200


def coordinate_sync_ttl_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("COORDINATE_SYNC_TTL_SECONDS", "300")))
    except ValueError:
        return 300.0


def coordinate_db_table() -> str:
    table = os.getenv("COORDINATE_DB_TABLE", "coordinates").strip() or "coordinates"
    if not table.replace("_", "").isalnum():
        raise ValueError("COORDINATE_DB_TABLE must be an alphanumeric SQLite identifier")
    return table


def coordinate_db_path() -> Optional[Path]:
    explicit = os.getenv("COORDINATE_DB_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser()

    for path in DEFAULT_DB_PATHS:
        if path.exists():
            return path
    return DEFAULT_DB_PATHS[0]


def coordinate_sync_status() -> Dict[str, Any]:
    path = coordinate_db_path()
    return {
        "enabled": coordinate_sync_enabled(),
        "db_path": str(path) if path else "",
        "db_exists": bool(path and path.exists()),
        "limit": coordinate_sync_limit(),
        "ttl_seconds": coordinate_sync_ttl_seconds(),
        **STATE,
    }


def sync_coordinates_to_phone(force: bool = False) -> Dict[str, Any]:
    started_at = datetime.now().isoformat(timespec="seconds")

    if not coordinate_sync_enabled():
        return _record_result(
            ok=True,
            message="coordinate sync disabled",
            started_at=started_at,
            synced_count=0,
            failed_count=0,
            errors=[],
        )

    if not phone_ai_configured():
        return _record_result(
            ok=False,
            message="PHONE_AI_BASE_URL is not configured",
            started_at=started_at,
            synced_count=0,
            failed_count=0,
            errors=[],
        )

    now = time.monotonic()
    ttl = coordinate_sync_ttl_seconds()
    if not force and STATE["last_sync_ok"] is True and now - float(STATE["last_attempt_monotonic"]) < ttl:
        return {
            "ok": True,
            "skipped": True,
            "message": "coordinate sync skipped by TTL",
            **coordinate_sync_status(),
        }

    path = coordinate_db_path()
    if path is None or not path.exists():
        return _record_result(
            ok=False,
            message=f"coordinate DB not found: {path}",
            started_at=started_at,
            synced_count=0,
            failed_count=0,
            errors=[],
        )

    try:
        coordinates = load_dashboard_coordinates(path, coordinate_db_table(), coordinate_sync_limit())
    except Exception as e:
        return _record_result(
            ok=False,
            message=f"coordinate DB read failed: {e}",
            started_at=started_at,
            synced_count=0,
            failed_count=0,
            errors=[str(e)],
        )

    synced_count = 0
    errors: List[str] = []
    for coordinate in coordinates:
        try:
            save_phone_coordinate(coordinate.to_phone_payload())
            synced_count += 1
        except Exception as e:
            errors.append(f"{coordinate.name}: {e}")

    ok = not errors
    message = f"synced {synced_count}/{len(coordinates)} dashboard coordinates to phone"
    if errors:
        message += f"; failed={len(errors)}"

    result = _record_result(
        ok=ok,
        message=message,
        started_at=started_at,
        synced_count=synced_count,
        failed_count=len(errors),
        errors=errors[:5],
    )

    level = "INFO" if ok else "WARN"
    write_log(f"Coordinate sync: {message}", level)
    return result


def load_dashboard_coordinates(path: Path, table: str, limit: int) -> List[DashboardCoordinate]:
    with closing(sqlite3.connect(str(path))) as conn:
        conn.row_factory = sqlite3.Row
        columns = _table_columns(conn, table)
        required = {"id", "name", "x", "z"}
        missing = required - columns
        if missing:
            raise RuntimeError(f"missing coordinate columns: {', '.join(sorted(missing))}")

        selected = [
            "id",
            "name",
            _select_column(columns, "world", "'overworld'"),
            "x",
            _select_column(columns, "y", "NULL"),
            "z",
            _select_column(columns, "note", "''"),
            _select_column(columns, "owner", "''"),
            _select_column(columns, "updated_at", _select_column(columns, "created_at", "''")),
        ]
        order_column = "updated_at" if "updated_at" in columns else "id"
        rows = conn.execute(
            f"SELECT {', '.join(selected)} FROM {table} ORDER BY {order_column} DESC LIMIT ?",
            (limit,),
        ).fetchall()

    coordinates: List[DashboardCoordinate] = []
    for row in rows:
        name = str(row["name"] or "").strip()
        if not name:
            continue
        coordinates.append(
            DashboardCoordinate(
                id=str(row["id"]),
                name=name,
                world=str(row["world"] or "overworld").strip() or "overworld",
                x=float(row["x"]),
                y=None if row["y"] is None else float(row["y"]),
                z=float(row["z"]),
                note=str(row["note"] or ""),
                owner=str(row["owner"] or ""),
                updated_at=str(row["updated_at"] or ""),
            )
        )
    return coordinates


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if not rows:
        raise RuntimeError(f"coordinate table not found: {table}")
    return {str(row[1]) for row in rows}


def _select_column(columns: set[str], name: str, fallback_sql: str) -> str:
    return name if name in columns else f"{fallback_sql} AS {name}"


def _record_result(
    ok: bool,
    message: str,
    started_at: str,
    synced_count: int,
    failed_count: int,
    errors: List[str],
) -> Dict[str, Any]:
    STATE.update(
        {
            "last_sync_started_at": started_at,
            "last_sync_finished_at": datetime.now().isoformat(timespec="seconds"),
            "last_sync_ok": ok,
            "last_sync_message": message,
            "last_synced_count": synced_count,
            "last_failed_count": failed_count,
            "last_errors": errors,
            "last_attempt_monotonic": time.monotonic(),
        }
    )
    return {
        "ok": ok,
        "skipped": False,
        "message": message,
        **coordinate_sync_status(),
    }
