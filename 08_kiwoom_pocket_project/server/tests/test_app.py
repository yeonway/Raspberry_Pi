import os

os.environ.setdefault("BRIDGE_API_TOKEN", "test-bridge-token-for-pytest-only")

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import init_db
from app.main import app


init_db()
client = TestClient(app)


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_settings().bridge_api_token}"}


def test_health_is_public() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_token_status_requires_auth() -> None:
    response = client.get("/api/token/status")
    assert response.status_code == 401


def test_token_status_with_auth() -> None:
    response = client.get("/api/token/status", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["mode"] in {"mock", "real"}


def test_watchlist_crud() -> None:
    headers = auth_headers()
    created = client.post("/api/watchlist", json={"code": "005930", "memo": "sample"}, headers=headers)
    assert created.status_code in {200, 201}
    listed = client.get("/api/watchlist", headers=headers)
    assert listed.status_code == 200
    assert any(item["code"] == "005930" for item in listed.json())
