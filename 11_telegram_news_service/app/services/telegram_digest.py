from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings, load_settings
from app.database import connect, utc_now
from app.services.dedup import normalize_url


TELEGRAM_LIMIT = 3900


def _keyword_text(article: dict[str, Any]) -> str:
    raw = article.get("matched_keywords")
    items: list[dict[str, Any]] = []
    if isinstance(raw, str) and raw:
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            items = []
    elif isinstance(raw, list):
        items = raw
    names = [str(item.get("keyword")) for item in items if item.get("keyword")]
    return ", ".join(names[:8]) if names else "-"


def select_digest_candidates(conn, settings: Settings) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM articles
        WHERE telegram_sent_at IS NULL
          AND status NOT IN ('hidden', 'duplicate')
          AND (final_score >= ? OR alert_keyword_matched = 1)
        ORDER BY final_score DESC, COALESCE(published_at, collected_at) DESC
        LIMIT ?
        """,
        (settings.news_digest_min_score, settings.news_digest_max_items * 3),
    ).fetchall()
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        article = dict(row)
        normalized = normalize_url(article["url"])
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(article)
        if len(result) >= settings.news_digest_max_items:
            break
    return result


def build_digest_message(articles: list[dict[str, Any]]) -> str:
    if not articles:
        return "30분 뉴스 브리핑\n\n보낼 신규 고점수 뉴스가 없습니다."
    blocks = ["📰 30분 뉴스 브리핑"]
    for article in articles:
        score = article.get("final_score") or 0
        title = article.get("title") or "제목 없음"
        category = article.get("category") or "-"
        source = article.get("source_name") or "-"
        summary = article.get("summary") or (article.get("snippet") or "요약 없음")[:250]
        reason = article.get("score_reason") or "키워드와 출처 점수 기준"
        blocks.append(
            "\n".join(
                [
                    f"🔥 [{score}점] {title}",
                    f"분야: {category} / {source}",
                    f"매칭: {_keyword_text(article)}",
                    "요약:",
                    f"- {summary}",
                    f"이유: {reason}",
                    f"원문: {article.get('url')}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def split_message(message: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    if len(message) <= limit:
        return [message]
    parts: list[str] = []
    current = ""
    for block in message.split("\n\n---\n\n"):
        candidate = block if not current else current + "\n\n---\n\n" + block
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
        current = block
    if current:
        parts.append(current)
    return parts


async def _send_telegram(settings: Settings, message: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise RuntimeError("telegram token/chat_id is not configured")
    endpoint = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=20) as client:
        for part in split_message(message):
            response = await client.post(
                endpoint,
                json={"chat_id": settings.telegram_chat_id, "text": part, "disable_web_page_preview": True},
            )
            response.raise_for_status()


async def send_digest_once(settings: Settings | None = None, dry_run: bool = False) -> dict[str, Any]:
    settings = settings or load_settings()
    with connect(settings.database_path) as conn:
        articles = select_digest_candidates(conn, settings)
        message = build_digest_message(articles)
        if dry_run:
            return {"status": "dry-run", "article_count": len(articles), "message": message}

        status = "sent"
        error = None
        try:
            if not articles:
                status = "skipped"
            elif not settings.telegram_bot_token or not settings.telegram_chat_id:
                status = "skipped"
                error = "telegram token/chat_id is not configured"
            else:
                await _send_telegram(settings, message)
                now = utc_now()
                conn.executemany("UPDATE articles SET telegram_sent_at = ?, updated_at = ? WHERE id = ?", [(now, now, a["id"]) for a in articles])
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = str(exc)
        conn.execute(
            """
            INSERT INTO telegram_digest_logs (sent_at, article_count, message, status, error)
            VALUES (?, ?, ?, ?, ?)
            """,
            (utc_now(), len(articles), message, status, error),
        )
        return {"status": status, "article_count": len(articles), "message": message, "error": error}
