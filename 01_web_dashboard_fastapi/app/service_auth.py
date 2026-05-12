import hmac
import os
from typing import Optional

from fastapi import HTTPException, Request

from app.security import env_bool


EVENT_TOKEN_HEADER = "x-event-token"


def get_event_token() -> str:
    return os.getenv("DASHBOARD_EVENT_TOKEN", "").strip()


def token_from_request(request: Request) -> Optional[str]:
    header_value = request.headers.get(EVENT_TOKEN_HEADER)
    if header_value:
        return header_value.strip()

    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    return None


def require_event_token(request: Request) -> str:
    expected = get_event_token()
    if not expected:
        if env_bool("DASHBOARD_ALLOW_UNAUTHENTICATED_EVENTS", False):
            return "event-client"
        raise HTTPException(status_code=503, detail="event token is not configured")

    supplied = token_from_request(request)
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="invalid event token")

    return "event-client"
