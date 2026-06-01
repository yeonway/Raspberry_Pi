from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import time
from typing import NamedTuple

from .config import get_settings


SESSION_COOKIE = "memo_session"
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
PASSWORD_ITERATIONS = 260_000


class SessionUser(NamedTuple):
    user_id: int
    username: str
    role: str


def validate_username(username: str) -> str:
    normalized = username.strip()
    if not USERNAME_RE.fullmatch(normalized):
        raise ValueError("아이디는 영문, 숫자, _, ., - 조합 3~32자로 입력하세요.")
    return normalized


def validate_password(password: str) -> str:
    if len(password) < 6:
        raise ValueError("비밀번호는 6자 이상이어야 합니다.")
    if len(password) > 256:
        raise ValueError("비밀번호가 너무 깁니다.")
    return password


def hash_password(password: str, salt: str | None = None) -> str:
    chosen_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(chosen_salt),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${chosen_salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        int(iterations),
    ).hex()
    return hmac.compare_digest(digest, expected)


def make_session(user_id: int, username: str, role: str) -> str:
    settings = get_settings()
    expires_at = int(time.time()) + settings.session_seconds
    payload = f"{user_id}:{username}:{role}:{expires_at}"
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    token = f"{payload}:{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(token).decode("ascii")


def read_session(token: str | None) -> SessionUser | None:
    if not token:
        return None
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        user_id, username, role, expires_at, signature = decoded.rsplit(":", 4)
        payload = f"{user_id}:{username}:{role}:{expires_at}"
        expected = hmac.new(
            get_settings().secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    except (ValueError, UnicodeDecodeError):
        return None
    if not hmac.compare_digest(signature, expected):
        return None
    if int(expires_at) < int(time.time()):
        return None
    if role not in {"user", "admin"}:
        return None
    return SessionUser(user_id=int(user_id), username=username, role=role)
