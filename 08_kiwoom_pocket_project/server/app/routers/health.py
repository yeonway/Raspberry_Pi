from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.kiwoom.token_manager import KiwoomTokenError, KiwoomTokenManager
from app.schemas import HealthResponse, TokenRefreshResponse, TokenStatusResponse
from app.security import require_bridge_token

router = APIRouter(tags=["health"])


def get_token_manager() -> KiwoomTokenManager:
    from app.main import token_manager

    return token_manager


@router.get("/health", response_model=HealthResponse)
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(mode=settings.kiwoom_mode, mock_fallback=settings.kiwoom_mock_fallback)


@router.get("/api/token/status", response_model=TokenStatusResponse)
async def token_status(
    _: Annotated[None, Depends(require_bridge_token)],
    token_manager: Annotated[KiwoomTokenManager, Depends(get_token_manager)],
) -> TokenStatusResponse:
    return TokenStatusResponse(**token_manager.status())


@router.post("/api/token/refresh", response_model=TokenRefreshResponse)
async def token_refresh(
    _: Annotated[None, Depends(require_bridge_token)],
    token_manager: Annotated[KiwoomTokenManager, Depends(get_token_manager)],
) -> TokenRefreshResponse:
    try:
        status = await token_manager.refresh()
        return TokenRefreshResponse(**status, refreshed=True)
    except KiwoomTokenError as exc:
        from app.kiwoom.client import KiwoomApiError

        raise KiwoomApiError(
            return_code=exc.payload.get("return_code", "KIWOOM_TOKEN_ERROR"),
            return_msg=str(exc),
            http_status=exc.status_code,
            internal_message="token refresh failed",
            payload=exc.payload,
        ) from exc
