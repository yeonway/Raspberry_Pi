from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.config import SEED_KEYWORDS, Settings, load_settings


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(database_path: Path | str | None = None) -> sqlite3.Connection:
    settings = load_settings()
    path = Path(database_path) if database_path else settings.database_path
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def initialize_database(database_path: Path | str | None = None) -> None:
    with connect(database_path) as conn:
        create_schema(conn)
        seed_keywords(conn)


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT,
            source_name TEXT,
            category TEXT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            snippet TEXT,
            image_url TEXT,
            published_at TEXT,
            collected_at TEXT NOT NULL,
            language TEXT,
            raw_source_id TEXT,
            matched_keywords TEXT,
            local_keyword_score INTEGER DEFAULT 0,
            ai_score INTEGER,
            final_score INTEGER DEFAULT 0,
            summary TEXT,
            score_reason TEXT,
            tags TEXT,
            status TEXT DEFAULT 'pending',
            telegram_queued INTEGER DEFAULT 0,
            telegram_sent_at TEXT,
            alert_keyword_matched INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS watch_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL UNIQUE,
            group_name TEXT NOT NULL,
            weight INTEGER NOT NULL DEFAULT 10,
            alert_enabled INTEGER NOT NULL DEFAULT 1,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(article_id),
            FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS source_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            new_count INTEGER DEFAULT 0,
            duplicate_count INTEGER DEFAULT 0,
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS telegram_digest_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sent_at TEXT NOT NULL,
            article_count INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS market_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id TEXT NOT NULL,
            name TEXT NOT NULL,
            value TEXT,
            date TEXT,
            source TEXT DEFAULT 'FRED',
            collected_at TEXT NOT NULL,
            UNIQUE(series_id, date)
        );

        CREATE TABLE IF NOT EXISTS sec_filings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            ticker TEXT,
            cik TEXT,
            form_type TEXT,
            title TEXT,
            url TEXT NOT NULL UNIQUE,
            published_at TEXT,
            collected_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_articles_final_score ON articles(final_score DESC);
        CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
        CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_articles_telegram ON articles(telegram_sent_at, final_score DESC);
        CREATE INDEX IF NOT EXISTS idx_ai_jobs_status ON ai_jobs(status, attempts);
        CREATE INDEX IF NOT EXISTS idx_source_runs_started ON source_runs(started_at DESC);
        """
    )


def seed_keywords(conn: sqlite3.Connection) -> None:
    now = utc_now()
    conn.executemany(
        """
        INSERT OR IGNORE INTO watch_keywords
            (keyword, group_name, weight, alert_enabled, enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [(keyword, group, weight, alert, enabled, now, now) for keyword, group, weight, alert, enabled in SEED_KEYWORDS],
    )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key in ("matched_keywords", "tags"):
        raw = data.get(key)
        if not raw:
            data[f"{key}_list"] = []
            continue
        try:
            data[f"{key}_list"] = json.loads(raw)
        except json.JSONDecodeError:
            data[f"{key}_list"] = []
    return data


def list_keywords(conn: sqlite3.Connection, enabled_only: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM watch_keywords"
    if enabled_only:
        sql += " WHERE enabled = 1"
    sql += " ORDER BY group_name, keyword"
    return [dict(row) for row in conn.execute(sql)]


def add_keyword(
    conn: sqlite3.Connection,
    keyword: str,
    group_name: str,
    weight: int,
    alert_enabled: bool,
    enabled: bool = True,
) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO watch_keywords
            (keyword, group_name, weight, alert_enabled, enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(keyword) DO UPDATE SET
            group_name = excluded.group_name,
            weight = excluded.weight,
            alert_enabled = excluded.alert_enabled,
            enabled = excluded.enabled,
            updated_at = excluded.updated_at
        """,
        (keyword.strip(), group_name.strip(), weight, int(alert_enabled), int(enabled), now, now),
    )


def toggle_keyword(conn: sqlite3.Connection, keyword_id: int, field: str) -> None:
    if field not in {"enabled", "alert_enabled"}:
        raise ValueError("unsupported keyword toggle field")
    now = utc_now()
    conn.execute(
        f"UPDATE watch_keywords SET {field} = CASE {field} WHEN 1 THEN 0 ELSE 1 END, updated_at = ? WHERE id = ?",
        (now, keyword_id),
    )


def delete_keyword(conn: sqlite3.Connection, keyword_id: int) -> None:
    conn.execute("DELETE FROM watch_keywords WHERE id = ?", (keyword_id,))


def insert_source_run(conn: sqlite3.Connection, source_name: str) -> int:
    cursor = conn.execute(
        "INSERT INTO source_runs (source_name, started_at, status) VALUES (?, ?, 'running')",
        (source_name, utc_now()),
    )
    return int(cursor.lastrowid)


def finish_source_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    new_count: int = 0,
    duplicate_count: int = 0,
    error: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE source_runs
        SET finished_at = ?, status = ?, new_count = ?, duplicate_count = ?, error = ?
        WHERE id = ?
        """,
        (utc_now(), status, new_count, duplicate_count, error, run_id),
    )


def upsert_article(conn: sqlite3.Connection, article: dict[str, Any]) -> tuple[int | None, bool]:
    now = utc_now()
    values = {
        "source_type": article.get("source_type"),
        "source_name": article.get("source_name"),
        "category": article.get("category"),
        "title": article["title"],
        "url": article["url"],
        "snippet": article.get("snippet"),
        "image_url": article.get("image_url"),
        "published_at": article.get("published_at"),
        "collected_at": article.get("collected_at") or now,
        "language": article.get("language"),
        "raw_source_id": article.get("raw_source_id"),
        "matched_keywords": json.dumps(article.get("matched_keywords") or [], ensure_ascii=False),
        "local_keyword_score": int(article.get("local_keyword_score") or 0),
        "ai_score": article.get("ai_score"),
        "final_score": int(article.get("final_score") or 0),
        "summary": article.get("summary"),
        "score_reason": article.get("score_reason"),
        "tags": json.dumps(article.get("tags") or [], ensure_ascii=False),
        "status": article.get("status") or "pending",
        "alert_keyword_matched": int(bool(article.get("alert_keyword_matched"))),
        "created_at": now,
        "updated_at": now,
    }
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO articles (
            source_type, source_name, category, title, url, snippet, image_url,
            published_at, collected_at, language, raw_source_id, matched_keywords,
            local_keyword_score, ai_score, final_score, summary, score_reason, tags,
            status, alert_keyword_matched, created_at, updated_at
        )
        VALUES (
            :source_type, :source_name, :category, :title, :url, :snippet, :image_url,
            :published_at, :collected_at, :language, :raw_source_id, :matched_keywords,
            :local_keyword_score, :ai_score, :final_score, :summary, :score_reason, :tags,
            :status, :alert_keyword_matched, :created_at, :updated_at
        )
        """,
        values,
    )
    if cursor.rowcount == 1:
        return int(cursor.lastrowid), True
    existing = conn.execute("SELECT id FROM articles WHERE url = ?", (values["url"],)).fetchone()
    return (int(existing["id"]) if existing else None), False


def get_article(conn: sqlite3.Connection, article_id: int) -> dict[str, Any] | None:
    return row_to_dict(conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone())


def list_articles(conn: sqlite3.Connection, filter_name: str | None = None, limit: int = 80) -> list[dict[str, Any]]:
    where: list[str] = ["status != 'hidden'"]
    params: list[Any] = []
    if filter_name and filter_name not in {"전체", "all"}:
        if filter_name == "고점수":
            where.append("final_score >= 80")
        elif filter_name == "미전송":
            where.append("telegram_sent_at IS NULL")
        elif filter_name == "AI 실패":
            where.append("status = 'ai_failed'")
        else:
            where.append("category = ?")
            params.append(filter_name)
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT * FROM articles
        WHERE {' AND '.join(where)}
        ORDER BY final_score DESC, COALESCE(published_at, collected_at) DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [row_to_dict(row) or {} for row in rows]


def list_source_runs(conn: sqlite3.Connection, limit: int = 80) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute("SELECT * FROM source_runs ORDER BY id DESC LIMIT ?", (limit,))]


def list_digest_logs(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute("SELECT * FROM telegram_digest_logs ORDER BY id DESC LIMIT ?", (limit,))]


def insert_market_indicators(conn: sqlite3.Connection, rows: Iterable[dict[str, Any]]) -> int:
    inserted = 0
    for row in rows:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO market_indicators
                (series_id, name, value, date, source, collected_at)
            VALUES (?, ?, ?, ?, 'FRED', ?)
            """,
            (row["series_id"], row["name"], row.get("value"), row.get("date"), utc_now()),
        )
        inserted += cursor.rowcount
    return inserted


def insert_sec_filing(conn: sqlite3.Connection, article: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO sec_filings
            (company_name, ticker, cik, form_type, title, url, published_at, collected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            article.get("company_name"),
            article.get("ticker"),
            article.get("cik"),
            article.get("form_type") or "8-K",
            article.get("title"),
            article.get("url"),
            article.get("published_at"),
            utc_now(),
        ),
    )


def enqueue_ai_job(conn: sqlite3.Connection, article_id: int) -> bool:
    now = utc_now()
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO ai_jobs (article_id, status, attempts, created_at, updated_at)
        VALUES (?, 'pending', 0, ?, ?)
        """,
        (article_id, now, now),
    )
    return cursor.rowcount == 1


def dashboard_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    today_prefix = datetime.now(timezone.utc).date().isoformat()
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN collected_at LIKE ? THEN 1 ELSE 0 END) AS today_count,
            SUM(CASE WHEN final_score >= 80 THEN 1 ELSE 0 END) AS high_count,
            MAX(collected_at) AS last_collected_at
        FROM articles
        """,
        (today_prefix + "%",),
    ).fetchone()
    return dict(row) if row else {"total": 0, "today_count": 0, "high_count": 0, "last_collected_at": None}
