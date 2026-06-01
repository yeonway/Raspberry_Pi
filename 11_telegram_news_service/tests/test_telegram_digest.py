from app.config import Settings
from app.database import connect, initialize_database, upsert_article
from app.services.telegram_digest import build_digest_message, select_digest_candidates, split_message


def settings(tmp_path):
    return Settings(
        app_env="test",
        app_host="127.0.0.1",
        app_port=8020,
        database_path=tmp_path / "news.db",
        admin_token=None,
        fred_api_key=None,
        telegram_bot_token=None,
        telegram_chat_id=None,
        sec_user_agent="test",
        phone_ai_base_url="http://phone.test",
        phone_ai_token=None,
        phone_ai_enabled=False,
        phone_ai_timeout_seconds=1,
        news_digest_interval_minutes=30,
        news_digest_min_score=80,
        news_digest_max_items=2,
        collector_gdelt_enabled=True,
        collector_fred_enabled=True,
        collector_arxiv_enabled=True,
        collector_hn_enabled=True,
        collector_sec_enabled=True,
        scheduler_enabled=False,
    )


def test_build_message():
    message = build_digest_message([{"title": "Nvidia news", "final_score": 95, "category": "AI", "source_name": "GDELT", "url": "https://e.test"}])
    assert "30분 뉴스 브리핑" in message
    assert "Nvidia news" in message


def test_max_items_and_sent_exclusion(tmp_path):
    cfg = settings(tmp_path)
    initialize_database(cfg.database_path)
    with connect(cfg.database_path) as conn:
        for idx in range(3):
            upsert_article(
                conn,
                {
                    "source_type": "news",
                    "source_name": "GDELT",
                    "category": "AI",
                    "title": f"Article {idx}",
                    "url": f"https://example.com/{idx}",
                    "final_score": 90 - idx,
                },
            )
        conn.execute("UPDATE articles SET telegram_sent_at = '2026-01-01T00:00:00+00:00' WHERE url = 'https://example.com/0'")
        rows = select_digest_candidates(conn, cfg)
    assert [row["title"] for row in rows] == ["Article 1", "Article 2"]


def test_long_message_split():
    parts = split_message("A" * 100 + "\n\n---\n\n" + "B" * 100, limit=120)
    assert len(parts) == 2
