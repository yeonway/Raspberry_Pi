from __future__ import annotations

import re
from typing import Any

from app.models import ScoreResult


TRUSTED_SOURCE_NAMES = {"GDELT", "arXiv", "Hacker News", "SEC EDGAR"}


def hn_score_bonus(snippet: str | None) -> int:
    if not snippet:
        return 0
    match = re.search(r"HN score:\s*(\d+)", snippet)
    if not match:
        return 0
    score = int(match.group(1))
    if score >= 500:
        return 10
    if score >= 200:
        return 7
    if score >= 100:
        return 5
    if score >= 50:
        return 3
    return 0


def calculate_final_score(
    *,
    local_keyword_score: int,
    ai_score: int | None = None,
    source_name: str | None = None,
    source_type: str | None = None,
    category: str | None = None,
    duplicate_suspected: bool = False,
    title: str | None = None,
    snippet: str | None = None,
) -> ScoreResult:
    ai_score_adjusted = 0 if ai_score is None else round(max(0, min(100, int(ai_score))) * 0.5)
    source_bonus = 0
    if source_name in TRUSTED_SOURCE_NAMES:
        source_bonus += 5
    if source_type == "sec" or category == "SEC":
        source_bonus += 10
    source_bonus += hn_score_bonus(snippet)

    duplicate_penalty = 20 if duplicate_suspected else 0
    clean_title = (title or "").strip()
    spam_penalty = 20 if len(clean_title) < 8 or clean_title.count("!") >= 4 else 0
    final_score = local_keyword_score + ai_score_adjusted + source_bonus - duplicate_penalty - spam_penalty
    final_score = max(0, min(100, final_score))
    return ScoreResult(
        final_score=final_score,
        ai_score_adjusted=ai_score_adjusted,
        source_bonus=source_bonus,
        duplicate_penalty=duplicate_penalty,
        spam_penalty=spam_penalty,
    )


def score_article_dict(article: dict[str, Any]) -> dict[str, Any]:
    result = calculate_final_score(
        local_keyword_score=int(article.get("local_keyword_score") or 0),
        ai_score=article.get("ai_score"),
        source_name=article.get("source_name"),
        source_type=article.get("source_type"),
        category=article.get("category"),
        duplicate_suspected=bool(article.get("duplicate_suspected")),
        title=article.get("title"),
        snippet=article.get("snippet"),
    )
    article["final_score"] = result.final_score
    return article
