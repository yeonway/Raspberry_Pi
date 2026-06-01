from __future__ import annotations

import re
from typing import Any


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword.strip())
    if not escaped:
        return re.compile(r"a^")
    if re.fullmatch(r"[A-Za-z0-9.+#-]{1,3}", keyword.strip()):
        return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


def match_keywords(text: str, keywords: list[dict[str, Any]]) -> dict[str, Any]:
    matched: list[dict[str, Any]] = []
    seen: set[str] = set()
    score = 0
    alert = False
    haystack = text or ""
    for keyword in keywords:
        if not int(keyword.get("enabled", 1)):
            continue
        name = str(keyword.get("keyword", "")).strip()
        if not name or name.casefold() in seen:
            continue
        if not _keyword_pattern(name).search(haystack):
            continue
        seen.add(name.casefold())
        weight = int(keyword.get("weight") or 0)
        score += weight
        if int(keyword.get("alert_enabled", 0)):
            alert = True
        matched.append(
            {
                "keyword": name,
                "group_name": keyword.get("group_name", ""),
                "weight": weight,
            }
        )
    return {
        "matched_keywords": matched,
        "local_keyword_score": score,
        "alert_keyword_matched": alert,
    }


def keywords_to_names(matched_keywords: list[dict[str, Any]] | None) -> list[str]:
    return [str(item.get("keyword", "")) for item in matched_keywords or [] if item.get("keyword")]
