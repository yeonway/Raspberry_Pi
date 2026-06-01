from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CollectedItem:
    source_type: str
    source_name: str
    category: str
    title: str
    url: str
    snippet: str | None = None
    image_url: str | None = None
    published_at: str | None = None
    language: str | None = None
    raw_source_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class BaseCollector:
    name = "base"

    async def collect(self) -> list[CollectedItem]:
        raise NotImplementedError
