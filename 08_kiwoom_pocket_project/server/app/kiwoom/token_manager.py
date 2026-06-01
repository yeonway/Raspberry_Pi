import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings
from app.kiwoom.tr_codes import TOKEN_ISSUE
from app.security import mask_secret


class KiwoomTokenError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class KiwoomTokenManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._access_token: str | None = None
        self._expires_dt: str | None = None
        self._expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    def status(self) -> dict[str, Any]:
        expires_in_sec: int | None = None
        if self._expires_at:
            expires_in_sec = int((self._expires_at - datetime.now(timezone.utc)).total_seconds())
        return {
            "has_token": bool(self._access_token),
            "expires_dt": self._expires_dt,
            "expires_in_sec": expires_in_sec,
            "masked_token": mask_secret(self._access_token),
            "mode": self.settings.kiwoom_mode,
            "has_credentials": self.settings.has_kiwoom_credentials,
        }

    def _is_valid(self) -> bool:
        if not self._access_token or not self._expires_at:
            return False
        remaining = (self._expires_at - datetime.now(timezone.utc)).total_seconds()
        return remaining > self.settings.kiwoom_token_refresh_margin_sec

    async def get_token(self) -> str:
        if self._is_valid():
            return self._access_token or ""
        async with self._lock:
            if not self._is_valid():
                await self.refresh()
        return self._access_token or ""

    async def refresh(self) -> dict[str, Any]:
        if not self.settings.has_kiwoom_credentials:
            raise KiwoomTokenError(
                "KIWOOM_APP_KEY와 KIWOOM_SECRET_KEY가 설정되지 않았습니다.",
                status_code=503,
                payload={"return_code": "KIWOOM_CREDENTIALS_MISSING"},
            )

        url = f"{self.settings.kiwoom_base_url.rstrip('/')}/oauth2/token"
        request_body = {
            "grant_type": "client_credentials",
            "appkey": self.settings.kiwoom_app_key,
            "secretkey": self.settings.kiwoom_secret_key,
        }
        headers = {"api-id": TOKEN_ISSUE, "content-type": "application/json;charset=UTF-8"}

        try:
            async with httpx.AsyncClient(timeout=self.settings.kiwoom_timeout_sec) as client:
                response = await client.post(url, json=request_body, headers=headers)
        except httpx.HTTPError as exc:
            raise KiwoomTokenError("키움 토큰 발급 요청에 실패했습니다.", payload={"detail": str(exc)}) from exc

        data = _safe_json(response)
        if response.status_code >= 400 or str(data.get("return_code", "0")) not in {"0", "None"}:
            raise KiwoomTokenError(
                data.get("return_msg") or "키움 토큰 발급 응답이 실패입니다.",
                status_code=response.status_code,
                payload=data,
            )

        token = data.get("token") or data.get("access_token")
        expires_dt = data.get("expires_dt")
        if not token or not expires_dt:
            raise KiwoomTokenError("키움 토큰 응답에 token 또는 expires_dt가 없습니다.", payload=data)

        self._access_token = token
        self._expires_dt = str(expires_dt)
        self._expires_at = _parse_expires_dt(str(expires_dt))
        return self.status()


def _parse_expires_dt(value: str) -> datetime:
    parsed = datetime.strptime(value, "%Y%m%d%H%M%S")
    return parsed.replace(tzinfo=timezone.utc)


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"raw": data}
    except ValueError:
        return {"raw": response.text}
