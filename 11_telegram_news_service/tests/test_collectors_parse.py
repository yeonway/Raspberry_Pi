from app.collectors.arxiv_collector import parse_arxiv_feed
from app.collectors.fred import parse_fred_response
from app.collectors.gdelt import parse_gdelt_response
from app.collectors.hackernews import parse_hn_item
from app.collectors.sec_edgar import parse_sec_atom


def test_parse_gdelt_json():
    items = parse_gdelt_response({"articles": [{"title": "AI news", "url": "https://e.test", "seendate": "20260602T120000Z"}]}, "AI")
    assert len(items) == 1
    assert items[0].category == "AI"


def test_parse_hn_item():
    item = parse_hn_item({"id": 1, "type": "story", "title": "PostgreSQL release", "score": 120, "descendants": 10, "time": 1700000000})
    assert item is not None
    assert item.url == "https://news.ycombinator.com/item?id=1"
    assert "HN score: 120" in (item.snippet or "")


def test_parse_arxiv_feed():
    feed = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/1234.5678</id>
        <title>Large Language Models</title>
        <summary>Paper summary.</summary>
        <published>2026-06-02T00:00:00Z</published>
        <author><name>A. Researcher</name></author>
        <link href="http://arxiv.org/abs/1234.5678" rel="alternate" type="text/html"/>
      </entry>
    </feed>"""
    items = parse_arxiv_feed(feed)
    assert len(items) == 1
    assert items[0].category == "AI Research"


def test_parse_fred_response():
    rows = parse_fred_response("DGS10", "10Y", {"observations": [{"date": "2026-01-01", "value": "."}, {"date": "2026-01-02", "value": "4.1"}]})
    assert rows == [{"series_id": "DGS10", "name": "10Y", "value": "4.1", "date": "2026-01-02"}]


def test_parse_sec_atom():
    feed = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>urn:sec</id>
        <title>8-K - NVIDIA CORP (0001045810) (Filer)</title>
        <updated>2026-06-02T00:00:00Z</updated>
        <link href="https://www.sec.gov/Archives/test-index.htm"/>
      </entry>
    </feed>"""
    items = parse_sec_atom(feed)
    assert len(items) == 1
    assert items[0].source_name == "SEC EDGAR"
