import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings


bearer_scheme = HTTPBearer(auto_error=False)


def mask_secret(value: str | None, visible: int = 6) -> str:
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * (len(value) - visible)}"


async def require_bridge_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    expected = settings.bridge_api_token
    provided = credentials.credentials if credentials else ""
    if not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "return_code": "BRIDGE_AUTH_FAILED",
                    "return_msg": "서버 인증 토큰이 없거나 올바르지 않습니다.",
                    "http_status": status.HTTP_401_UNAUTHORIZED,
                    "internal_message": "Invalid Authorization bearer token.",
                }
            },
        )


def validate_ws_token(auth_header: str | None, query_token: str | None, settings: Settings) -> bool:
    token = query_token or ""
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    return bool(settings.bridge_api_token and hmac.compare_digest(token, settings.bridge_api_token))
