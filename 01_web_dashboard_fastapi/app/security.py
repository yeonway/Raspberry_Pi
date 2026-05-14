import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Request, Response


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
COOKIE_NAME = "dashboard_session"
EPHEMERAL_SESSION_SECRET = secrets.token_urlsafe(32)
PUBLIC_AUTH_PATHS = (
    "/news",
    "/community",
    "/admin/community",
    "/admin/community/login",
    "/admin/community/logout",
    "/admin/news",
    "/admin/news/login",
    "/admin/news/logout",
    "/static/community/",
    "/static/news/",
)


def load_env_file():
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def get_username():
    return os.getenv("DASHBOARD_USERNAME", "admin")


def get_plain_password():
    return os.getenv("DASHBOARD_PASSWORD", "")


def get_password_hash():
    return os.getenv("DASHBOARD_PASSWORD_HASH", "").strip()


def get_session_secret():
    return (
        os.getenv("DASHBOARD_SECRET_KEY", "").strip()
        or os.getenv("SESSION_SECRET", "").strip()
        or EPHEMERAL_SESSION_SECRET
    )


def get_session_max_age():
    try:
        return int(os.getenv("SESSION_MAX_AGE_SECONDS", "86400"))
    except ValueError:
        return 86400


def password_hash(password: str, salt: Optional[bytes] = None, iterations: int = 200_000) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    salt_b64 = base64.urlsafe_b64encode(salt).decode("utf-8")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("utf-8")

    return f"pbkdf2_sha256${iterations}${salt_b64}${digest_b64}"


def verify_password_hash(password: str, saved_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_b64, digest_b64 = saved_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("utf-8"))

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(actual, expected)

    except Exception:
        return False


def verify_login(username: str, password: str) -> bool:
    if username != get_username():
        return False

    saved_hash = get_password_hash()
    if saved_hash:
        return verify_password_hash(password, saved_hash)

    plain_password = get_plain_password()
    if not plain_password:
        return False

    return hmac.compare_digest(password, plain_password)


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def sign_payload(payload_b64: str) -> str:
    secret = get_session_secret().encode("utf-8")
    return hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_token(username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + get_session_max_age(),
    }

    payload_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = sign_payload(payload_b64)
    return f"{payload_b64}.{signature}"


def verify_session_token(token: str) -> Optional[dict]:
    try:
        payload_b64, signature = token.split(".", 1)
        expected_signature = sign_payload(payload_b64)

        if not hmac.compare_digest(signature, expected_signature):
            return None

        payload = json.loads(b64url_decode(payload_b64).decode("utf-8"))

        if int(payload.get("exp", 0)) < int(time.time()):
            return None

        return payload

    except Exception:
        return None


def set_session_cookie(response: Response, username: str):
    token = create_session_token(username)

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=env_bool("COOKIE_SECURE", False),
        samesite="lax",
        max_age=get_session_max_age(),
        path="/",
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")


def get_current_user(request: Request) -> Optional[str]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None

    payload = verify_session_token(token)
    if not payload:
        return None

    return payload.get("sub")


def is_dashboard_auth_public_path(path: str) -> bool:
    normalized = path or "/"
    if normalized in {
        "/news",
        "/news/",
        "/community",
        "/community/",
        "/admin/news",
        "/admin/news/",
        "/admin/community",
        "/admin/community/",
    }:
        return True
    if normalized.startswith("/news/"):
        return True
    if normalized.startswith("/community/"):
        return True
    if normalized.startswith("/admin/news/"):
        return True
    if normalized.startswith("/admin/community/"):
        return True
    if normalized.startswith("/static/news/"):
        return True
    if normalized.startswith("/static/community/"):
        return True
    return any(normalized == item for item in PUBLIC_AUTH_PATHS)


def require_auth(request: Request) -> str:
    if is_dashboard_auth_public_path(request.url.path):
        return "__public_news_path__"

    username = get_current_user(request)

    if not username:
        raise HTTPException(status_code=401, detail="login required")

    return username
