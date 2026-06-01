from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import GenerationLog
from app.services.ai.base import ProviderResponseError
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.key_pool import APIKeyRecord, NoAvailableKeyError, RoundRobinKeyPool, utc_now
from app.services.ai.schemas import SIMPLE_AI_TEST_SCHEMA


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    monkeypatch.delenv("MATHGEN_GEMINI_API_KEYS", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_ai_status_without_keys(client: TestClient) -> None:
    response = client.get("/api/ai/status")

    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["registered_key_count"] == 0
    assert data["active_key_count"] == 0
    assert data["cooldown_key_count"] == 0
    assert data["default_model"] == "gemini-2.5-flash-lite"


def test_ai_test_without_keys_returns_clear_error(client: TestClient) -> None:
    response = client.post("/api/ai/test", json={"prompt": "Return a tiny JSON object."})

    assert response.status_code == 503
    assert response.json()["detail"]["available"] is False
    assert "not configured" in response.json()["detail"]["error"]


def test_ai_status_never_exposes_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "secret-key-that-must-not-leak"
    monkeypatch.setenv("GEMINI_API_KEYS", f"{secret},another-secret")
    get_settings.cache_clear()

    with TestClient(app) as test_client:
        response = test_client.get("/api/ai/status")

    body = response.text
    assert response.status_code == 200
    assert secret not in body
    assert "another-secret" not in body
    assert response.json()["registered_key_count"] == 2
    get_settings.cache_clear()


def test_generation_log_does_not_store_secret(client: TestClient) -> None:
    response = client.post("/api/ai/test", json={"prompt": "No sensitive values here."})
    assert response.status_code == 503

    with SessionLocal() as session:
        log = session.scalars(select(GenerationLog).order_by(GenerationLog.id.desc())).first()

    assert log is not None
    combined = f"{log.request_summary} {log.response_summary} {log.error_message}"
    assert "GEMINI_API_KEYS" not in combined
    assert "secret" not in combined.lower()


def test_key_pool_round_robin() -> None:
    pool = RoundRobinKeyPool(
        [
            APIKeyRecord(key_id="k1", provider="gemini", secret="secret-1"),
            APIKeyRecord(key_id="k2", provider="gemini", secret="secret-2"),
            APIKeyRecord(key_id="k3", provider="gemini", secret="secret-3"),
        ]
    )

    assert [pool.get_next_key().key_id for _ in range(5)] == ["k1", "k2", "k3", "k1", "k2"]


def test_key_pool_skips_cooldown_and_recovers() -> None:
    pool = RoundRobinKeyPool(
        [
            APIKeyRecord(key_id="k1", provider="gemini", secret="secret-1"),
            APIKeyRecord(key_id="k2", provider="gemini", secret="secret-2"),
        ],
        cooldown_seconds=60,
    )

    pool.mark_rate_limited("k1")
    assert pool.get_next_key().key_id == "k2"
    assert pool.summary()["cooldown_key_count"] == 1

    pool.keys[0].cooldown_until = utc_now() - timedelta(seconds=1)
    assert pool.get_next_key().key_id == "k1"


def test_key_pool_raises_when_all_keys_unavailable() -> None:
    pool = RoundRobinKeyPool(
        [
            APIKeyRecord(key_id="k1", provider="gemini", secret="secret-1"),
            APIKeyRecord(key_id="k2", provider="gemini", secret="secret-2", is_enabled=False),
        ],
        cooldown_seconds=60,
    )

    pool.mark_rate_limited("k1")

    with pytest.raises(NoAvailableKeyError):
        pool.get_next_key()


def test_gemini_provider_retries_next_key_after_rate_limit() -> None:
    seen_keys: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.url.params["key"]
        seen_keys.append(key)
        if key == "secret-1":
            return httpx.Response(429, json={"error": {"message": "quota exceeded"}})
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": '{"ok": true, "message": "provider test passed"}'},
                            ]
                        }
                    }
                ]
            },
        )

    pool = RoundRobinKeyPool(
        [
            APIKeyRecord(key_id="k1", provider="gemini", secret="secret-1"),
            APIKeyRecord(key_id="k2", provider="gemini", secret="secret-2"),
        ],
        cooldown_seconds=60,
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GeminiProvider(key_pool=pool, client=client)

    result = provider.generate_structured("Return JSON.", SIMPLE_AI_TEST_SCHEMA)

    assert seen_keys == ["secret-1", "secret-2"]
    assert result.key_id == "k2"
    assert result.data["ok"] is True
    assert pool.summary()["cooldown_key_count"] == 1
    client.close()


def test_gemini_provider_reports_json_parse_failure() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": "not json"}]}}]},
            )
        )
    )
    pool = RoundRobinKeyPool([APIKeyRecord(key_id="k1", provider="gemini", secret="secret-1")])
    provider = GeminiProvider(key_pool=pool, client=client)

    with pytest.raises(ProviderResponseError, match="valid JSON"):
        provider.generate_structured("Return JSON.", SIMPLE_AI_TEST_SCHEMA)

    client.close()
