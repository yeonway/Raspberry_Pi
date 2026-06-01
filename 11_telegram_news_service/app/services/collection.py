from __future__ import annotations

from typing import Any

from app.collectors.arxiv_collector import ArxivCollector
from app.collectors.base import BaseCollector, CollectedItem
from app.collectors.fred import FredCollector
from app.collectors.gdelt import GdeltCollector
from app.collectors.hackernews import HackerNewsCollector
from app.collectors.sec_edgar import SecEdgarCollector
from app.config import Settings, load_settings
from app.database import (
    connect,
    finish_source_run,
    initialize_database,
    insert_market_indicators,
    insert_sec_filing,
    insert_source_run,
    list_keywords,
    upsert_article,
    utc_now,
)
from app.services.ai_jobs import should_enqueue_ai_job
from app.services.dedup import normalize_url
from app.services.keyword_matcher import match_keywords
from app.services.scoring import score_article_dict


def build_collectors(settings: Settings, only: set[str] | None = None) -> list[BaseCollector]:
    collectors: list[BaseCollector] = []
    if settings.collector_gdelt_enabled and (only is None or "GDELT" in only):
        collectors.append(GdeltCollector())
    if settings.collector_arxiv_enabled and (only is None or "arXiv" in only):
        collectors.append(ArxivCollector())
    if settings.collector_hn_enabled and (only is None or "Hacker News" in only):
        collectors.append(HackerNewsCollector())
    if settings.collector_sec_enabled and (only is None or "SEC EDGAR" in only):
        collectors.append(SecEdgarCollector(settings))
    return collectors


def prepare_article(item: CollectedItem, keywords: list[dict[str, Any]]) -> dict[str, Any]:
    article = item.to_dict()
    article["url"] = normalize_url(article["url"])
    article["collected_at"] = utc_now()
    text = " ".join([article.get("title") or "", article.get("snippet") or "", article.get("source_name") or "", article.get("category") or ""])
    match = match_keywords(text, keywords)
    article.update(match)
    score_article_dict(article)
    return article


def save_items(conn, items: list[CollectedItem]) -> tuple[int, int, int]:
    keywords = list_keywords(conn, enabled_only=True)
    new_count = 0
    duplicate_count = 0
    ai_jobs = 0
    for item in items:
        article = prepare_article(item, keywords)
        article_id, inserted = upsert_article(conn, article)
        if inserted:
            new_count += 1
            if item.source_type == "sec":
                insert_sec_filing(conn, article)
            if article_id and should_enqueue_ai_job({**article, "id": article_id}):
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO ai_jobs (article_id, status, attempts, created_at, updated_at)
                    VALUES (?, 'pending', 0, ?, ?)
                    """,
                    (article_id, utc_now(), utc_now()),
                )
                ai_jobs += cursor.rowcount
        else:
            duplicate_count += 1
    return new_count, duplicate_count, ai_jobs


async def run_collectors_once(settings: Settings | None = None, dry_run: bool = False, only: set[str] | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    initialize_database(settings.database_path)
    collectors = build_collectors(settings, only)
    enabled_names = [collector.name for collector in collectors]
    run_fred = settings.collector_fred_enabled and (only is None or "FRED" in only)
    if run_fred:
        enabled_names.append("FRED")
    if dry_run:
        return {"status": "dry-run", "collectors": enabled_names}

    summary: dict[str, Any] = {"status": "ok", "sources": {}, "new_count": 0, "duplicate_count": 0, "ai_jobs": 0}
    with connect(settings.database_path) as conn:
        for collector in collectors:
            run_id = insert_source_run(conn, collector.name)
            try:
                items = await collector.collect()
                new_count, duplicate_count, ai_jobs = save_items(conn, items)
                finish_source_run(conn, run_id, "success", new_count, duplicate_count)
                summary["sources"][collector.name] = {"new": new_count, "duplicates": duplicate_count, "ai_jobs": ai_jobs}
                summary["new_count"] += new_count
                summary["duplicate_count"] += duplicate_count
                summary["ai_jobs"] += ai_jobs
            except Exception as exc:  # noqa: BLE001
                finish_source_run(conn, run_id, "failed", 0, 0, str(exc))
                summary["sources"][collector.name] = {"error": str(exc)}

        if run_fred:
            run_id = insert_source_run(conn, "FRED")
            try:
                indicators = await FredCollector(settings).collect_indicators()
                inserted = insert_market_indicators(conn, indicators)
                status = "success" if settings.fred_api_key else "skipped"
                finish_source_run(conn, run_id, status, inserted, 0, None if settings.fred_api_key else "FRED_API_KEY is not configured")
                summary["sources"]["FRED"] = {"new": inserted, "skipped": not bool(settings.fred_api_key)}
            except Exception as exc:  # noqa: BLE001
                finish_source_run(conn, run_id, "failed", 0, 0, str(exc))
                summary["sources"]["FRED"] = {"error": str(exc)}
    return summary
