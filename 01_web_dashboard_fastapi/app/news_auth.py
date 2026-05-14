import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

from fastapi import Request, Response

from app.security import env_bool, verify_password_hash


COOKIE_NAME = "news_admin_session"
EPHEMERAL_NEWS_SESSION_SECRET = secrets.token_urlsafe(32)


def get_news_admin_username() -> str:
    return os.getenv("NEWS_ADMIN_USERNAME", "").strip()


def get_news_admin_password_hash() -> str:
    return os.getenv("NEWS_ADMIN_PASSWORD_HASH", "").strip()


def get_news_session_secret() -> str:
    return (
        os.getenv("NEWS_SESSION_SECRET", "").strip()
        or os.getenv("DASHBOARD_SECRET_KEY", "").strip()
        or os.getenv("SESSION_SECRET", "").strip()
        or EPHEMERAL_NEWS_SESSION_SECRET
    )


def get_news_session_max_age() -> int:
    try:
        return int(os.getenv("NEWS_SESSION_MAX_AGE_SECONDS", os.getenv("SESSION_MAX_AGE_SECONDS", "86400")))
    except ValueError:
        return 86400


def verify_news_admin_login(username: str, password: str) -> bool:
    configured_username = get_news_admin_username()
    saved_hash = get_news_admin_password_hash()
    if not configured_username or not saved_hash:
        return False
    if not hmac.compare_digest(username, configured_username):
        return False
    return verify_password_hash(password, saved_hash)


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def sign_payload(payload_b64: str) -> str:
    secret = get_news_session_secret().encode("utf-8")
    return hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()


def create_admin_session_token(username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + get_news_session_max_age(),
        "scope": "news_admin",
    }
    payload_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{payload_b64}.{sign_payload(payload_b64)}"


def verify_admin_session_token(token: str) -> Optional[dict]:
    try:
        payload_b64, signature = token.split(".", 1)
        expected_signature = sign_payload(payload_b64)
        if not hmac.compare_digest(signature, expected_signature):
            return None
        payload = json.loads(b64url_decode(payload_b64).decode("utf-8"))
        if payload.get("scope") != "news_admin":
            return None
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def set_admin_session_cookie(response: Response, username: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_admin_session_token(username),
        httponly=True,
        secure=env_bool("NEWS_COOKIE_SECURE", env_bool("COOKIE_SECURE", False)),
        samesite="lax",
        max_age=get_news_session_max_age(),
        path="/admin",
    )


def clear_admin_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/admin")
    response.delete_cookie(key=COOKIE_NAME, path="/admin/news")


def get_current_admin(request: Request) -> Optional[str]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    payload = verify_admin_session_token(token)
    if not payload:
        return None
    return payload.get("sub")


def csrf_token(request: Request) -> str:
    token = request.cookies.get(COOKIE_NAME, "")
    if not token:
        return ""
    return hmac.new(
        get_news_session_secret().encode("utf-8"),
        f"csrf:{token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_csrf(request: Request, submitted_token: str) -> bool:
    expected = csrf_token(request)
    return bool(expected and submitted_token and hmac.compare_digest(expected, submitted_token))
