import httpx
import pytest

from app.config import Settings
from app.services.ai_client import PhoneAiClient, PhoneAiError


def make_settings(enabled=True):
    return Settings(
        app_env="test",
        app_host="127.0.0.1",
        app_port=8020,
        database_path=":memory:",
        admin_token=None,
        fred_api_key=None,
        telegram_bot_token=None,
        telegram_chat_id=None,
        sec_user_agent="test",
        phone_ai_base_url="http://phone.test",
        phone_ai_token="token",
        phone_ai_enabled=enabled,
        phone_ai_timeout_seconds=1,
        news_digest_interval_minutes=30,
        news_digest_min_score=80,
        news_digest_max_items=10,
        collector_gdelt_enabled=True,
        collector_fred_enabled=True,
        collector_arxiv_enabled=True,
        collector_hn_enabled=True,
        collector_sec_enabled=True,
        scheduler_enabled=False,
    )


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, *args, payload=None, error=None, **kwargs):
        self.payload = payload or {"ai_score": 87, "summary": "요약", "score_reason": "이유", "tags": ["Nvidia"]}
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        if self.error:
            raise self.error
        return FakeResponse(self.payload)


@pytest.mark.asyncio
async def test_phone_ai_success(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    result = await PhoneAiClient(make_settings()).score_article({"id": 1, "title": "Nvidia", "matched_keywords": []})
    assert result.ai_score == 87
    assert result.tags == ["Nvidia"]


@pytest.mark.asyncio
async def test_phone_ai_timeout(monkeypatch):
    class TimeoutClient(FakeClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, error=httpx.TimeoutException("timeout"), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", TimeoutClient)
    with pytest.raises(PhoneAiError):
        await PhoneAiClient(make_settings()).score_article({"id": 1, "title": "Nvidia", "matched_keywords": []})


@pytest.mark.asyncio
async def test_phone_ai_invalid_json(monkeypatch):
    class InvalidClient(FakeClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, payload={"summary": "missing score"}, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", InvalidClient)
    with pytest.raises(PhoneAiError):
        await PhoneAiClient(make_settings()).score_article({"id": 1, "title": "Nvidia", "matched_keywords": []})


@pytest.mark.asyncio
async def test_mock_mode():
    result = await PhoneAiClient(make_settings(enabled=False)).score_article(
        {
            "title": "Nvidia announces AI chip",
            "category": "반도체",
            "local_keyword_score": 45,
            "matched_keywords": [{"keyword": "Nvidia"}, {"keyword": "AI chip"}],
        }
    )
    assert result.ai_score >= 80
    assert "mock mode" in result.score_reason
