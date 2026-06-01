from __future__ import annotations

from typing import Any

import httpx

from app.config import FRED_SERIES, Settings


FRED_ENDPOINT = "https://api.stlouisfed.org/fred/series/observations"


def parse_fred_response(series_id: str, name: str, payload: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    observations = payload.get("observations") or []
    for observation in observations[-limit:]:
        value = observation.get("value")
        date = observation.get("date")
        if not date or value in {None, "."}:
            continue
        rows.append({"series_id": series_id, "name": name, "value": str(value), "date": str(date)})
    return rows


class FredCollector:
    name = "FRED"

    def __init__(self, settings: Settings, limit: int = 5):
        self.settings = settings
        self.limit = limit

    async def collect_indicators(self) -> list[dict[str, Any]]:
        if not self.settings.fred_api_key:
            return []
        rows: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for series_id, name in FRED_SERIES.items():
                response = await client.get(
                    FRED_ENDPOINT,
                    params={
                        "series_id": series_id,
                        "api_key": self.settings.fred_api_key,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": self.limit,
                    },
                )
                response.raise_for_status()
                rows.extend(parse_fred_response(series_id, name, response.json(), self.limit))
        return rows
