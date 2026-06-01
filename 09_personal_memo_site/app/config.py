from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    db_path: Path
    secret_key: str
    secure_cookies: bool
    session_seconds: int
    admin_username: str | None
    admin_password: str | None


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    secret_key = os.getenv("MEMO_SECRET_KEY") or secrets.token_urlsafe(32)
    return Settings(
        db_path=Path(os.getenv("MEMO_DB_PATH", PROJECT_ROOT / "memo.db")),
        secret_key=secret_key,
        secure_cookies=_env_bool("MEMO_SECURE_COOKIES", False),
        session_seconds=int(os.getenv("MEMO_SESSION_SECONDS", "604800")),
        admin_username=os.getenv("MEMO_ADMIN_USERNAME"),
        admin_password=os.getenv("MEMO_ADMIN_PASSWORD"),
    )
