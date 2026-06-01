from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import get_settings


NOTE_FIELDS = {
    "title",
    "body",
    "tags",
    "folder_id",
    "pinned",
    "deleted_at",
    "checklist_json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _connect() -> sqlite3.Connection:
    db_path = Path(get_settings().db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_column(conn: sqlite3.Connection, table: str, column: str, sql: str) -> None:
    if column not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {sql}")


def init_db() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'admin')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL COLLATE NOCASE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            );

            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS note_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                changed_fields TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                tags TEXT NOT NULL,
                folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL,
                pinned INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT,
                checklist_json TEXT NOT NULL DEFAULT '[]',
                summary TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS note_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
                size_bytes INTEGER NOT NULL,
                data BLOB NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_notes_user_created
            ON notes(user_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_note_revisions_note
            ON note_revisions(note_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_note_attachments_note
            ON note_attachments(note_id, id ASC);
            """
        )
        _add_column(conn, "notes", "title", "title TEXT NOT NULL DEFAULT ''")
        _add_column(conn, "notes", "tags", "tags TEXT NOT NULL DEFAULT ''")
        _add_column(conn, "notes", "folder_id", "folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL")
        _add_column(conn, "notes", "pinned", "pinned INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "notes", "deleted_at", "deleted_at TEXT")
        _add_column(conn, "notes", "checklist_json", "checklist_json TEXT NOT NULL DEFAULT '[]'")
        _add_column(conn, "notes", "client_key", "client_key TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_folder ON notes(folder_id, updated_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_deleted ON notes(deleted_at)")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_notes_user_client_key ON notes(user_id, client_key) WHERE client_key IS NOT NULL"
        )
        conn.execute(
            """
            UPDATE notes
            SET title = CASE
                WHEN title = '' THEN substr(replace(body, char(10), ' '), 1, 80)
                ELSE title
            END
            """
        )


def row_to_note(row: sqlite3.Row) -> dict[str, Any]:
    try:
        checklist = json.loads(row["checklist_json"] or "[]")
        if not isinstance(checklist, list):
            checklist = []
    except json.JSONDecodeError:
        checklist = []
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "username": row["username"],
        "title": row["title"],
        "body": row["body"],
        "tags": row["tags"],
        "folder_id": row["folder_id"],
        "folder_name": row["folder_name"],
        "pinned": bool(row["pinned"]),
        "deleted_at": row["deleted_at"],
        "checklist": checklist,
        "attachment_count": row["attachment_count"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def find_user_by_id(user_id: int) -> sqlite3.Row | None:
    with connection() as conn:
        return conn.execute(
            "SELECT id, username, password_hash, role, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


def find_user_by_username(username: str) -> sqlite3.Row | None:
    with connection() as conn:
        return conn.execute(
            "SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def insert_user(username: str, password_hash: str, role: str = "user") -> int:
    with connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role),
        )
        return int(cursor.lastrowid)


def update_user_password_and_role(username: str, password_hash: str, role: str) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, role = ? WHERE username = ?",
            (password_hash, role, username),
        )


def list_users_with_note_counts() -> list[sqlite3.Row]:
    with connection() as conn:
        return conn.execute(
            """
            SELECT
                users.id,
                users.username,
                users.role,
                users.created_at,
                COUNT(notes.id) AS note_count
            FROM users
            LEFT JOIN notes ON notes.user_id = users.id AND notes.deleted_at IS NULL
            GROUP BY users.id
            ORDER BY users.created_at ASC, users.id ASC
            """
        ).fetchall()


def update_user_password(user_id: int, password_hash: str) -> bool:
    with connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id),
        )
        return cursor.rowcount > 0


def update_user_role(user_id: int, role: str) -> bool:
    with connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user_id),
        )
        return cursor.rowcount > 0


def delete_user(user_id: int) -> bool:
    with connection() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return cursor.rowcount > 0


def list_folders_for_user(user_id: int) -> list[sqlite3.Row]:
    with connection() as conn:
        return conn.execute(
            """
            SELECT
                folders.id,
                folders.user_id,
                folders.name,
                folders.created_at,
                folders.updated_at,
                COUNT(notes.id) AS note_count
            FROM folders
            LEFT JOIN notes ON notes.folder_id = folders.id AND notes.deleted_at IS NULL
            WHERE folders.user_id = ?
            GROUP BY folders.id
            ORDER BY folders.name ASC
            """,
            (user_id,),
        ).fetchall()


def find_folder(folder_id: int) -> sqlite3.Row | None:
    with connection() as conn:
        return conn.execute(
            "SELECT id, user_id, name, created_at, updated_at FROM folders WHERE id = ?",
            (folder_id,),
        ).fetchone()


def insert_folder(user_id: int, name: str) -> int:
    with connection() as conn:
        cursor = conn.execute(
            "INSERT INTO folders (user_id, name, updated_at) VALUES (?, ?, ?)",
            (user_id, name, utc_now()),
        )
        return int(cursor.lastrowid)


def update_folder(folder_id: int, user_id: int, name: str) -> bool:
    with connection() as conn:
        cursor = conn.execute(
            "UPDATE folders SET name = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (name, utc_now(), folder_id, user_id),
        )
        return cursor.rowcount > 0


def delete_folder(folder_id: int, user_id: int) -> bool:
    with connection() as conn:
        conn.execute("UPDATE notes SET folder_id = NULL, updated_at = ? WHERE folder_id = ?", (utc_now(), folder_id))
        cursor = conn.execute("DELETE FROM folders WHERE id = ? AND user_id = ?", (folder_id, user_id))
        return cursor.rowcount > 0


def _note_select_sql() -> str:
    return """
        SELECT
            notes.id,
            notes.user_id,
            notes.title,
            notes.body,
            notes.tags,
            notes.folder_id,
            notes.pinned,
            notes.deleted_at,
            notes.checklist_json,
            (
                SELECT COUNT(*)
                FROM note_attachments
                WHERE note_attachments.note_id = notes.id
            ) AS attachment_count,
            notes.created_at,
            notes.updated_at,
            users.username,
            folders.name AS folder_name
        FROM notes
        JOIN users ON users.id = notes.user_id
        LEFT JOIN folders ON folders.id = notes.folder_id
    """


def list_notes_for_user(user_id: int) -> list[sqlite3.Row]:
    with connection() as conn:
        return conn.execute(
            f"""
            {_note_select_sql()}
            WHERE notes.user_id = ? AND notes.deleted_at IS NULL
            ORDER BY notes.pinned DESC, notes.updated_at DESC, notes.id DESC
            """,
            (user_id,),
        ).fetchall()


def list_all_notes() -> list[sqlite3.Row]:
    with connection() as conn:
        return conn.execute(
            f"""
            {_note_select_sql()}
            WHERE notes.deleted_at IS NULL
            ORDER BY notes.pinned DESC, notes.updated_at DESC, notes.id DESC
            """
        ).fetchall()


def search_notes(
    requester_id: int,
    requester_role: str,
    *,
    folder_id: int | None = None,
    query: str = "",
    include_deleted: bool = False,
) -> list[sqlite3.Row]:
    filters: list[str] = []
    params: list[Any] = []
    if requester_role != "admin":
        filters.append("notes.user_id = ?")
        params.append(requester_id)
    if folder_id is not None:
        filters.append("notes.folder_id = ?")
        params.append(folder_id)
    if include_deleted:
        filters.append("notes.deleted_at IS NOT NULL")
    else:
        filters.append("notes.deleted_at IS NULL")
    if query.strip():
        like = f"%{query.strip()}%"
        filters.append(
            "(notes.title LIKE ? OR notes.body LIKE ? OR notes.tags LIKE ? OR folders.name LIKE ? OR users.username LIKE ?)"
        )
        params.extend([like, like, like, like, like])
    where = " AND ".join(filters) if filters else "1 = 1"
    with connection() as conn:
        return conn.execute(
            f"""
            {_note_select_sql()}
            WHERE {where}
            ORDER BY notes.pinned DESC, notes.updated_at DESC, notes.id DESC
            """,
            params,
        ).fetchall()


def find_note_for_request(note_id: int, requester_id: int, requester_role: str) -> sqlite3.Row | None:
    filters = ["notes.id = ?"]
    params: list[Any] = [note_id]
    if requester_role != "admin":
        filters.append("notes.user_id = ?")
        params.append(requester_id)
    with connection() as conn:
        return conn.execute(
            f"""
            {_note_select_sql()}
            WHERE {" AND ".join(filters)}
            """,
            params,
        ).fetchone()


def _normalize_checklist_json(value: Any) -> str:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = []
    else:
        decoded = value
    if not isinstance(decoded, list):
        decoded = []
    items = []
    for index, item in enumerate(decoded):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", ""))[:500]
        if not text.strip():
            continue
        items.append(
            {
                "id": str(item.get("id") or f"item-{index}"),
                "text": text,
                "checked": bool(item.get("checked")),
            }
        )
    return json.dumps(items, ensure_ascii=False)


def _normalize_client_key(value: Any) -> str | None:
    key = str(value or "").strip()
    return key[:80] if key else None


def _folder_allowed(conn: sqlite3.Connection, folder_id: int | None, user_id: int) -> bool:
    if folder_id is None:
        return True
    row = conn.execute("SELECT id FROM folders WHERE id = ? AND user_id = ?", (folder_id, user_id)).fetchone()
    return row is not None


def insert_note(
    user_id: int,
    body: str,
    *,
    title: str = "",
    tags: str = "",
    folder_id: int | None = None,
    checklist: Any = None,
    pinned: bool = False,
    client_key: Any = None,
) -> int:
    with connection() as conn:
        if not _folder_allowed(conn, folder_id, user_id):
            raise ValueError("Folder does not belong to user")
        normalized_client_key = _normalize_client_key(client_key)
        if normalized_client_key is not None:
            existing = conn.execute(
                "SELECT id FROM notes WHERE user_id = ? AND client_key = ?",
                (user_id, normalized_client_key),
            ).fetchone()
            if existing is not None:
                return int(existing["id"])
        now = utc_now()
        cursor = conn.execute(
            """
            INSERT INTO notes
                (user_id, title, body, tags, folder_id, pinned, checklist_json, client_key, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                title.strip()[:200],
                body,
                tags.strip()[:500],
                folder_id,
                1 if pinned else 0,
                _normalize_checklist_json(checklist or []),
                normalized_client_key,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)


def _create_revision(
    conn: sqlite3.Connection,
    note: sqlite3.Row,
    editor_id: int,
    changed_fields: list[str],
    summary: str,
) -> None:
    conn.execute(
        """
        INSERT INTO note_revisions
            (note_id, user_id, changed_fields, title, body, tags, folder_id, pinned, deleted_at, checklist_json, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            note["id"],
            editor_id,
            json.dumps(changed_fields, ensure_ascii=False),
            note["title"],
            note["body"],
            note["tags"],
            note["folder_id"],
            note["pinned"],
            note["deleted_at"],
            note["checklist_json"],
            summary[:200],
        ),
    )


def update_note(note_id: int, editor_id: int, editor_role: str, fields: dict[str, Any]) -> sqlite3.Row | None:
    with connection() as conn:
        note = conn.execute(f"{_note_select_sql()} WHERE notes.id = ?", (note_id,)).fetchone()
        if note is None:
            return None
        if editor_role != "admin" and note["user_id"] != editor_id:
            return None

        values: dict[str, Any] = {}
        for field, value in fields.items():
            if field not in NOTE_FIELDS:
                continue
            if field == "title":
                values[field] = str(value or "").strip()[:200]
            elif field == "tags":
                values[field] = str(value or "").strip()[:500]
            elif field == "folder_id":
                folder_id = int(value) if value not in {None, "", "null"} else None
                if not _folder_allowed(conn, folder_id, note["user_id"]):
                    raise ValueError("Folder does not belong to note owner")
                values[field] = folder_id
            elif field == "pinned":
                values[field] = 1 if bool(value) else 0
            elif field == "deleted_at":
                values[field] = value
            elif field == "checklist_json":
                values[field] = _normalize_checklist_json(value)
            else:
                values[field] = str(value or "")

        changed = [field for field, value in values.items() if note[field] != value]
        if changed:
            _create_revision(conn, note, editor_id, changed, f"Changed {', '.join(changed)}")
            values["updated_at"] = utc_now()
            assignments = ", ".join(f"{field} = ?" for field in values)
            params = list(values.values()) + [note_id]
            conn.execute(f"UPDATE notes SET {assignments} WHERE id = ?", params)

        return conn.execute(f"{_note_select_sql()} WHERE notes.id = ?", (note_id,)).fetchone()


def move_note_to_trash(note_id: int, editor_id: int, editor_role: str) -> bool:
    updated = update_note(note_id, editor_id, editor_role, {"deleted_at": utc_now()})
    return updated is not None


def restore_note(note_id: int, editor_id: int, editor_role: str) -> bool:
    updated = update_note(note_id, editor_id, editor_role, {"deleted_at": None})
    return updated is not None


def purge_note(note_id: int, editor_id: int, editor_role: str) -> bool:
    with connection() as conn:
        note = conn.execute("SELECT id, user_id FROM notes WHERE id = ?", (note_id,)).fetchone()
        if note is None:
            return False
        if editor_role != "admin" and note["user_id"] != editor_id:
            return False
        cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cursor.rowcount > 0


def delete_note(note_id: int, requester_id: int, requester_role: str) -> bool:
    return move_note_to_trash(note_id, requester_id, requester_role)


def list_revisions(note_id: int, requester_id: int, requester_role: str) -> list[sqlite3.Row]:
    note = find_note_for_request(note_id, requester_id, requester_role)
    if note is None:
        return []
    with connection() as conn:
        return conn.execute(
            """
            SELECT note_revisions.*, users.username
            FROM note_revisions
            JOIN users ON users.id = note_revisions.user_id
            WHERE note_revisions.note_id = ?
            ORDER BY note_revisions.created_at DESC, note_revisions.id DESC
            """,
            (note_id,),
        ).fetchall()


def restore_revision(note_id: int, revision_id: int, editor_id: int, editor_role: str) -> sqlite3.Row | None:
    with connection() as conn:
        note = conn.execute(f"{_note_select_sql()} WHERE notes.id = ?", (note_id,)).fetchone()
        if note is None:
            return None
        if editor_role != "admin" and note["user_id"] != editor_id:
            return None
        revision = conn.execute(
            "SELECT * FROM note_revisions WHERE id = ? AND note_id = ?",
            (revision_id, note_id),
        ).fetchone()
        if revision is None:
            return None
        _create_revision(conn, note, editor_id, ["restore_revision"], f"Restored revision {revision_id}")
        conn.execute(
            """
            UPDATE notes
            SET title = ?, body = ?, tags = ?, folder_id = ?, pinned = ?, deleted_at = ?,
                checklist_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                revision["title"],
                revision["body"],
                revision["tags"],
                revision["folder_id"],
                revision["pinned"],
                revision["deleted_at"],
                revision["checklist_json"],
                utc_now(),
                note_id,
            ),
        )
        return conn.execute(f"{_note_select_sql()} WHERE notes.id = ?", (note_id,)).fetchone()


def list_attachments(note_id: int, requester_id: int, requester_role: str) -> list[sqlite3.Row]:
    note = find_note_for_request(note_id, requester_id, requester_role)
    if note is None:
        return []
    with connection() as conn:
        return conn.execute(
            """
            SELECT id, note_id, filename, content_type, size_bytes, created_at
            FROM note_attachments
            WHERE note_id = ?
            ORDER BY id ASC
            """,
            (note_id,),
        ).fetchall()


def add_attachment(
    note_id: int,
    requester_id: int,
    requester_role: str,
    *,
    filename: str,
    content_type: str,
    data: bytes,
) -> sqlite3.Row | None:
    with connection() as conn:
        note = conn.execute("SELECT id, user_id FROM notes WHERE id = ?", (note_id,)).fetchone()
        if note is None:
            return None
        if requester_role != "admin" and note["user_id"] != requester_id:
            return None
        cursor = conn.execute(
            """
            INSERT INTO note_attachments
                (note_id, user_id, filename, content_type, size_bytes, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_id,
                note["user_id"],
                filename[:255] or "attachment",
                content_type[:120] or "application/octet-stream",
                len(data),
                data,
                utc_now(),
            ),
        )
        return conn.execute(
            """
            SELECT id, note_id, filename, content_type, size_bytes, created_at
            FROM note_attachments
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()


def find_attachment(attachment_id: int, requester_id: int, requester_role: str) -> sqlite3.Row | None:
    filters = ["note_attachments.id = ?"]
    params: list[Any] = [attachment_id]
    if requester_role != "admin":
        filters.append("notes.user_id = ?")
        params.append(requester_id)
    with connection() as conn:
        return conn.execute(
            f"""
            SELECT
                note_attachments.id,
                note_attachments.note_id,
                note_attachments.filename,
                note_attachments.content_type,
                note_attachments.size_bytes,
                note_attachments.data,
                note_attachments.created_at
            FROM note_attachments
            JOIN notes ON notes.id = note_attachments.note_id
            WHERE {" AND ".join(filters)}
            """,
            params,
        ).fetchone()


def delete_attachment(attachment_id: int, requester_id: int, requester_role: str) -> bool:
    attachment = find_attachment(attachment_id, requester_id, requester_role)
    if attachment is None:
        return False
    with connection() as conn:
        cursor = conn.execute("DELETE FROM note_attachments WHERE id = ?", (attachment_id,))
        return cursor.rowcount > 0


def count_attachments(note_id: int, requester_id: int, requester_role: str) -> int | None:
    note = find_note_for_request(note_id, requester_id, requester_role)
    if note is None:
        return None
    with connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM note_attachments WHERE note_id = ?",
            (note_id,),
        ).fetchone()
        return int(row["total"])


def export_data() -> dict[str, Any]:
    with connection() as conn:
        return {
            "version": 1,
            "exported_at": utc_now(),
            "users": [
                dict(row)
                for row in conn.execute("SELECT id, username, role, created_at FROM users ORDER BY id").fetchall()
            ],
            "folders": [dict(row) for row in conn.execute("SELECT * FROM folders ORDER BY id").fetchall()],
            "notes": [dict(row) for row in conn.execute("SELECT * FROM notes ORDER BY id").fetchall()],
            "note_attachments": [
                {
                    key: (row[key].hex() if key == "data" else row[key])
                    for key in row.keys()
                }
                for row in conn.execute("SELECT * FROM note_attachments ORDER BY id").fetchall()
            ],
            "note_revisions": [
                dict(row) for row in conn.execute("SELECT * FROM note_revisions ORDER BY id").fetchall()
            ],
        }


def import_data(data: dict[str, Any]) -> dict[str, int]:
    if data.get("version") != 1:
        raise ValueError("Unsupported backup version")
    imported_folders = 0
    imported_notes = 0
    with connection() as conn:
        users = {row["id"]: row for row in conn.execute("SELECT id, username FROM users").fetchall()}
        for folder in data.get("folders", []):
            if folder.get("user_id") not in users:
                continue
            exists = conn.execute(
                "SELECT id FROM folders WHERE user_id = ? AND name = ?",
                (folder.get("user_id"), folder.get("name")),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                """
                INSERT INTO folders (user_id, name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    folder.get("user_id"),
                    folder.get("name"),
                    folder.get("created_at") or utc_now(),
                    folder.get("updated_at") or utc_now(),
                ),
            )
            imported_folders += 1

        for note in data.get("notes", []):
            if note.get("user_id") not in users:
                continue
            conn.execute(
                """
                INSERT INTO notes
                    (user_id, title, body, tags, folder_id, pinned, deleted_at, checklist_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note.get("user_id"),
                    note.get("title") or "",
                    note.get("body") or "",
                    note.get("tags") or "",
                    note.get("folder_id"),
                    1 if note.get("pinned") else 0,
                    note.get("deleted_at"),
                    _normalize_checklist_json(note.get("checklist_json") or []),
                    note.get("created_at") or utc_now(),
                    note.get("updated_at") or utc_now(),
                ),
            )
            imported_notes += 1
    return {"folders": imported_folders, "notes": imported_notes}
