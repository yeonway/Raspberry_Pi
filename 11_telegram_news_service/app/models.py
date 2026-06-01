from __future__ import annotations

from dataclasses import dataclass


ARTICLE_STATUSES = {"pending", "scored", "ai_failed", "hidden", "duplicate"}
AI_JOB_STATUSES = {"pending", "running", "done", "failed"}


@dataclass(frozen=True)
class KeywordMatch:
    keyword: str
    group_name: str
    weight: int


@dataclass(frozen=True)
class ScoreResult:
    final_score: int
    ai_score_adjusted: int
    source_bonus: int
    duplicate_penalty: int
    spam_penalty: int
