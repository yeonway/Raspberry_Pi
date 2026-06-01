from __future__ import annotations

import re

import feedparser
import httpx

from app.collectors.base import BaseCollector, CollectedItem
from app.config import Settings


SEC_CURRENT_8K_ATOM = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&count=40&output=atom"


def _company_from_title(title: str) -> str | None:
    match = re.search(r"8-K\s+-\s+(.+?)\s+\(", title)
    if match:
        return match.group(1).strip()
    return None


def parse_sec_atom(feed_text: str) -> list[CollectedItem]:
    feed = feedparser.parse(feed_text)
    items: list[CollectedItem] = []
    for entry in feed.entries:
        title = " ".join(str(entry.get("title", "")).split())
        url = entry.get("link")
        if not title or not url:
            continue
        company = _company_from_title(title)
        snippet = f"SEC 8-K filing metadata"
        if company:
            snippet += f" for {company}"
        items.append(
            CollectedItem(
                source_type="sec",
                source_name="SEC EDGAR",
                category="SEC",
                title=title,
                url=str(url),
                snippet=snippet,
                published_at=entry.get("updated") or entry.get("published"),
                language="en",
                raw_source_id=entry.get("id"),
            )
        )
    return items


class SecEdgarCollector(BaseCollector):
    name = "SEC EDGAR"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def collect(self) -> list[CollectedItem]:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": self.settings.sec_user_agent}) as client:
            response = await client.get(SEC_CURRENT_8K_ATOM)
            response.raise_for_status()
            return parse_sec_atom(response.text)
