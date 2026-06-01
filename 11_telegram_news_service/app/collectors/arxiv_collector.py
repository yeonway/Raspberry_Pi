from __future__ import annotations

from typing import Any

import feedparser
import httpx

from app.collectors.base import BaseCollector, CollectedItem


ARXIV_ENDPOINT = "https://export.arxiv.org/api/query"


def parse_arxiv_feed(feed_text: str) -> list[CollectedItem]:
    feed = feedparser.parse(feed_text)
    items: list[CollectedItem] = []
    for entry in feed.entries:
        title = " ".join(str(entry.get("title", "")).split())
        url = entry.get("link")
        if not title or not url:
            continue
        authors: list[str] = []
        for author in entry.get("authors", []) or []:
            if isinstance(author, dict) and author.get("name"):
                authors.append(str(author["name"]))
        summary = " ".join(str(entry.get("summary", "")).split())[:500]
        if authors:
            summary = f"Authors: {', '.join(authors[:5])}. {summary}"
        items.append(
            CollectedItem(
                source_type="paper",
                source_name="arXiv",
                category="AI Research",
                title=title,
                url=str(url),
                snippet=summary,
                published_at=entry.get("published"),
                language="en",
                raw_source_id=entry.get("id"),
            )
        )
    return items


class ArxivCollector(BaseCollector):
    name = "arXiv"

    def __init__(self, max_results: int = 15):
        self.max_results = max_results

    async def collect(self) -> list[CollectedItem]:
        query = 'cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV OR "large language model" OR "multimodal AI" OR "AI agent"'
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                ARXIV_ENDPOINT,
                params={
                    "search_query": query,
                    "start": 0,
                    "max_results": self.max_results,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                },
            )
            response.raise_for_status()
            return parse_arxiv_feed(response.text)
