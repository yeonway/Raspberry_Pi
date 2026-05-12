import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict


def phone_ai_base_url() -> str:
    return os.getenv("PHONE_AI_BASE_URL", "").strip().rstrip("/")


def phone_ai_api_token() -> str:
    return os.getenv("PHONE_AI_API_TOKEN", "").strip()


def phone_ai_timeout() -> float:
    try:
        return max(1.0, float(os.getenv("PHONE_AI_TIMEOUT_SECONDS", "30")))
    except ValueError:
        return 30.0


def phone_ai_configured() -> bool:
    return bool(phone_ai_base_url())


def call_phone_ai(path: str, method: str = "GET", payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    base_url = phone_ai_base_url()
    if not base_url:
        raise RuntimeError("PHONE_AI_BASE_URL is not configured")

    url = f"{base_url}{path}"
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    token = phone_ai_api_token()
    if token and path.startswith("/api/"):
        headers["X-API-Token"] = token

    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=phone_ai_timeout()) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Phone AI HTTP {e.code}: {body[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Phone AI connection failed: {e.reason}") from e


def phone_ai_health() -> Dict[str, Any]:
    return call_phone_ai("/health")


def ask_phone_ai(payload: Dict[str, Any]) -> Dict[str, Any]:
    return call_phone_ai("/api/ask", method="POST", payload=payload)


def save_phone_coordinate(payload: Dict[str, Any]) -> Dict[str, Any]:
    return call_phone_ai("/api/coordinates", method="POST", payload=payload)
