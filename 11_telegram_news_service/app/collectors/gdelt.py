from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectedItem
from app.config import GDELT_QUERY_GROUPS


GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"


def parse_gdelt_response(payload: dict[str, Any], category: str) -> list[CollectedItem]:
    items: list[CollectedItem] = []
    for article in payload.get("articles", []) or []:
        title = article.get("title")
        url = article.get("url")
        if not title or not url:
            continue
        items.append(
            CollectedItem(
                source_type="news",
                source_name="GDELT",
                category=category,
                title=str(title),
                url=str(url),
                snippet=article.get("snippet") or article.get("summary") or article.get("seendate"),
                image_url=article.get("socialimage"),
                published_at=article.get("seendate"),
                language=article.get("language"),
                raw_source_id=article.get("url"),
            )
        )
    return items


class GdeltCollector(BaseCollector):
    name = "GDELT"

    def __init__(self, maxrecords: int = 10):
        self.maxrecords = max(1, min(maxrecords, 20))

    async def collect(self) -> list[CollectedItem]:
        results: list[CollectedItem] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for category, queries in GDELT_QUERY_GROUPS.items():
                for query in queries:
                    response = await client.get(
                        GDELT_ENDPOINT,
                        params={
                            "query": query,
                            "mode": "ArtList",
                            "format": "json",
                            "maxrecords": self.maxrecords,
                            "sort": "HybridRel",
                        },
                    )
                    response.raise_for_status()
                    results.extend(parse_gdelt_response(response.json(), category))
                    await asyncio.sleep(0.2)
        return results
