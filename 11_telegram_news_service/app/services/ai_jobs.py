from __future__ import annotations

import json
from typing import Any

from app.config import Settings, load_settings
from app.database import connect, row_to_dict, utc_now
from app.services.ai_client import PhoneAiClient
from app.services.scoring import calculate_final_score


AI_GDELT_CATEGORIES = {"미국시장", "AI", "반도체", "Database", "개발/인프라"}


def should_enqueue_ai_job(article: dict[str, Any]) -> bool:
    matched = article.get("matched_keywords")
    if isinstance(matched, str):
        try:
            matched = json.loads(matched)
        except json.JSONDecodeError:
            matched = []
    if matched:
        return True
    if article.get("source_name") == "GDELT" and article.get("category") in AI_GDELT_CATEGORIES:
        return True
    if article.get("source_name") == "Hacker News" and int(article.get("final_score") or 0) >= 50:
        return True
    if article.get("source_type") == "sec" or article.get("category") == "SEC":
        return True
    if article.get("category") == "AI Research":
        return True
    return False


def enqueue_pending_ai_jobs(conn) -> int:
    rows = conn.execute(
        """
        SELECT a.*
        FROM articles a
        LEFT JOIN ai_jobs j ON j.article_id = a.id
        WHERE j.id IS NULL
          AND a.status NOT IN ('hidden', 'duplicate')
        ORDER BY a.final_score DESC, a.id DESC
        LIMIT 200
        """
    ).fetchall()
    inserted = 0
    for row in rows:
        article = dict(row)
        if not should_enqueue_ai_job(article):
            continue
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO ai_jobs (article_id, status, attempts, created_at, updated_at)
            VALUES (?, 'pending', 0, ?, ?)
            """,
            (article["id"], utc_now(), utc_now()),
        )
        inserted += cursor.rowcount
    return inserted


async def run_ai_jobs_once(settings: Settings | None = None, limit: int = 10, dry_run: bool = False) -> dict[str, Any]:
    settings = settings or load_settings()
    with connect(settings.database_path) as conn:
        candidate_count = conn.execute("SELECT COUNT(*) AS count FROM articles WHERE status != 'hidden'").fetchone()["count"]
        if dry_run:
            pending = conn.execute("SELECT COUNT(*) AS count FROM ai_jobs WHERE status = 'pending'").fetchone()["count"]
            return {"status": "dry-run", "candidate_articles": candidate_count, "pending_jobs": pending}

        enqueued = enqueue_pending_ai_jobs(conn)
        jobs = conn.execute(
            """
            SELECT j.*, a.*
            FROM ai_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status = 'pending' AND j.attempts < 3
            ORDER BY a.final_score DESC, j.id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        client = PhoneAiClient(settings)
        done = 0
        failed = 0
        for row in jobs:
            article = row_to_dict(row) or dict(row)
            job_id = row["id"]
            article_id = row["article_id"]
            article["id"] = article_id
            conn.execute("UPDATE ai_jobs SET status = 'running', updated_at = ? WHERE id = ?", (utc_now(), job_id))
            try:
                result = await client.score_article(article)
                score = calculate_final_score(
                    local_keyword_score=int(article.get("local_keyword_score") or 0),
                    ai_score=result.ai_score,
                    source_name=article.get("source_name"),
                    source_type=article.get("source_type"),
                    category=article.get("category"),
                    title=article.get("title"),
                    snippet=article.get("snippet"),
                )
                conn.execute(
                    """
                    UPDATE articles
                    SET ai_score = ?, final_score = ?, summary = ?, score_reason = ?,
                        tags = ?, status = 'scored', updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        result.ai_score,
                        score.final_score,
                        result.summary,
                        result.score_reason,
                        json.dumps(result.tags, ensure_ascii=False),
                        utc_now(),
                        article_id,
                    ),
                )
                conn.execute("UPDATE ai_jobs SET status = 'done', updated_at = ? WHERE id = ?", (utc_now(), job_id))
                done += 1
            except Exception as exc:  # noqa: BLE001
                attempts = int(row["attempts"]) + 1
                status = "failed" if attempts >= 3 else "pending"
                conn.execute(
                    """
                    UPDATE ai_jobs
                    SET status = ?, attempts = ?, last_error = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, attempts, str(exc), utc_now(), job_id),
                )
                if status == "failed":
                    conn.execute("UPDATE articles SET status = 'ai_failed', updated_at = ? WHERE id = ?", (utc_now(), article_id))
                failed += 1
        return {"status": "ok", "enqueued": enqueued, "done": done, "failed": failed}
