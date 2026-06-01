from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock


class NoAvailableKeyError(Exception):
    """Raised when no enabled, non-cooled-down API key exists."""


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class APIKeyRecord:
    key_id: str
    provider: str
    secret: str = field(repr=False)
    is_enabled: bool = True
    cooldown_until: datetime | None = None
    daily_request_count: int = 0
    daily_error_count: int = 0
    last_used_at: datetime | None = None

    def is_available(self, now: datetime | None = None) -> bool:
        current = now or utc_now()
        return self.is_enabled and (self.cooldown_until is None or self.cooldown_until <= current)


class RoundRobinKeyPool:
    def __init__(self, keys: list[APIKeyRecord], cooldown_seconds: int = 3600):
        self._keys = keys
        self._cooldown_seconds = cooldown_seconds
        self._cursor = 0
        self._lock = Lock()

    @property
    def keys(self) -> list[APIKeyRecord]:
        return list(self._keys)

    def summary(self) -> dict[str, int]:
        now = utc_now()
        return {
            "registered_key_count": len(self._keys),
            "active_key_count": sum(1 for key in self._keys if key.is_enabled and key.is_available(now)),
            "cooldown_key_count": sum(
                1 for key in self._keys if key.is_enabled and key.cooldown_until is not None and key.cooldown_until > now
            ),
        }

    def get_next_key(self) -> APIKeyRecord:
        with self._lock:
            if not self._keys:
                raise NoAvailableKeyError("No API keys are configured.")

            now = utc_now()
            for offset in range(len(self._keys)):
                index = (self._cursor + offset) % len(self._keys)
                key = self._keys[index]
                if key.is_available(now):
                    self._cursor = (index + 1) % len(self._keys)
                    key.last_used_at = now
                    key.daily_request_count += 1
                    return key

            raise NoAvailableKeyError("No enabled API keys are currently available.")

    def mark_success(self, key_id: str) -> None:
        with self._lock:
            key = self._find_key(key_id)
            if key is not None:
                key.cooldown_until = None

    def mark_rate_limited(self, key_id: str) -> None:
        with self._lock:
            key = self._find_key(key_id)
            if key is not None:
                key.daily_error_count += 1
                key.cooldown_until = utc_now() + timedelta(seconds=self._cooldown_seconds)

    def mark_error(self, key_id: str, disable: bool = False) -> None:
        with self._lock:
            key = self._find_key(key_id)
            if key is not None:
                key.daily_error_count += 1
                if disable:
                    key.is_enabled = False

    def _find_key(self, key_id: str) -> APIKeyRecord | None:
        return next((key for key in self._keys if key.key_id == key_id), None)
