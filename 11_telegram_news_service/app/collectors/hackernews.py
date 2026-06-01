from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectedItem


HN_BASE = "https://hacker-news.firebaseio.com/v0"


def parse_hn_item(item: dict[str, Any] | None) -> CollectedItem | None:
    if not item or item.get("type") != "story" or not item.get("title"):
        return None
    story_id = item.get("id")
    url = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
    published_at = None
    if item.get("time"):
        published_at = datetime.fromtimestamp(int(item["time"]), timezone.utc).replace(microsecond=0).isoformat()
    score = int(item.get("score") or 0)
    comments = int(item.get("descendants") or 0)
    return CollectedItem(
        source_type="news",
        source_name="Hacker News",
        category="개발/인프라",
        title=str(item["title"]),
        url=str(url),
        snippet=f"HN score: {score}, comments: {comments}",
        published_at=published_at,
        language="en",
        raw_source_id=str(story_id),
    )


class HackerNewsCollector(BaseCollector):
    name = "Hacker News"

    def __init__(self, per_feed_limit: int = 50):
        self.per_feed_limit = per_feed_limit

    async def collect(self) -> list[CollectedItem]:
        results: list[CollectedItem] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for feed_name in ("topstories", "newstories"):
                ids_response = await client.get(f"{HN_BASE}/{feed_name}.json")
                ids_response.raise_for_status()
                ids = ids_response.json()[: self.per_feed_limit]
                for story_id in ids:
                    response = await client.get(f"{HN_BASE}/item/{story_id}.json")
                    response.raise_for_status()
                    parsed = parse_hn_item(response.json())
                    if parsed:
                        results.append(parsed)
        return results
