from app.database import initialize_database, upsert_article
from app.database import connect
from app.services.dedup import dedupe_urls, normalize_url


def test_normalize_removes_tracking_and_trailing_slash():
    assert normalize_url("HTTPS://Example.COM/news/?utm_source=x&b=2&a=1") == "https://example.com/news?a=1&b=2"


def test_dedupe_urls():
    urls = ["https://a.test/post/?utm_campaign=x", "https://a.test/post", "https://b.test/"]
    assert dedupe_urls(urls) == ["https://a.test/post", "https://b.test/"]


def test_same_url_reinsert_prevented(tmp_path):
    db_path = tmp_path / "news.db"
    initialize_database(db_path)
    article = {
        "source_type": "news",
        "source_name": "GDELT",
        "category": "AI",
        "title": "Nvidia AI chip news",
        "url": "https://example.com/news",
        "final_score": 10,
    }
    with connect(db_path) as conn:
        _, inserted_first = upsert_article(conn, article)
        _, inserted_second = upsert_article(conn, article)
    assert inserted_first is True
    assert inserted_second is False
