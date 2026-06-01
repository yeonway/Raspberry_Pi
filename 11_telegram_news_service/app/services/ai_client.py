from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings
from app.services.keyword_matcher import keywords_to_names


class PhoneAiError(RuntimeError):
    pass


@dataclass(frozen=True)
class AIResult:
    ai_score: int
    summary: str
    score_reason: str
    tags: list[str]


def _headers(settings: Settings) -> dict[str, str]:
    if not settings.phone_ai_token:
        return {}
    return {
        "Authorization": f"Bearer {settings.phone_ai_token}",
        "X-API-Token": settings.phone_ai_token,
    }


def mock_score_article(article: dict[str, Any]) -> AIResult:
    matched = article.get("matched_keywords_list")
    if matched is None:
        matched = article.get("matched_keywords") or []
    keyword_names = keywords_to_names(matched)
    local_score = int(article.get("local_keyword_score") or 0)
    score = max(35, min(95, local_score + 35))
    title = article.get("title") or "제목 없음"
    category = article.get("category") or "기타"
    keywords_text = ", ".join(keyword_names[:5]) if keyword_names else "주요 키워드 없음"
    return AIResult(
        ai_score=score,
        summary=f"{category} 분야 기사입니다. '{title[:80]}' 내용을 키워드 기반으로 우선순위 평가했습니다. 매칭: {keywords_text}.",
        score_reason="PHONE_AI_ENABLED=false mock mode에서 로컬 키워드 점수를 기준으로 산정했습니다.",
        tags=keyword_names[:6] or [category],
    )


class PhoneAiClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def health(self) -> dict[str, Any]:
        if not self.settings.phone_ai_enabled:
            return {"ok": True, "mode": "mock", "enabled": False}
        try:
            async with httpx.AsyncClient(timeout=self.settings.phone_ai_timeout_seconds) as client:
                response = await client.get(f"{self.settings.phone_ai_base_url.rstrip('/')}/health", headers=_headers(self.settings))
                response.raise_for_status()
                return response.json()
        except Exception as exc:  # noqa: BLE001 - surface a concise app-level error.
            raise PhoneAiError(str(exc)) from exc

    async def score_article(self, article: dict[str, Any]) -> AIResult:
        if not self.settings.phone_ai_enabled:
            return mock_score_article(article)

        matched = article.get("matched_keywords_list")
        if matched is None:
            matched = article.get("matched_keywords") or []
        payload = {
            "article_id": article.get("id"),
            "title": article.get("title"),
            "source": article.get("source_name"),
            "category": article.get("category"),
            "snippet": article.get("snippet"),
            "matched_keywords": keywords_to_names(matched),
            "published_at": article.get("published_at"),
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.phone_ai_timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.phone_ai_base_url.rstrip('/')}/api/news-score",
                    json=payload,
                    headers=_headers(self.settings),
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:  # noqa: BLE001
            raise PhoneAiError(str(exc)) from exc

        try:
            tags = data.get("tags") or []
            if not isinstance(tags, list):
                tags = [str(tags)]
            return AIResult(
                ai_score=max(0, min(100, int(data["ai_score"]))),
                summary=str(data.get("summary") or ""),
                score_reason=str(data.get("score_reason") or ""),
                tags=[str(tag) for tag in tags],
            )
        except Exception as exc:  # noqa: BLE001
            raise PhoneAiError(f"invalid phone AI response: {exc}") from exc
