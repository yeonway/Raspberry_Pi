from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.kiwoom.client import KiwoomApiError, KiwoomClient
from app.kiwoom.token_manager import KiwoomTokenManager
from app.routers import account, conditions, health, orders, realtime, stocks, watchlist
from app.security import require_bridge_token

settings = get_settings()
token_manager = KiwoomTokenManager(settings)
kiwoom_client = KiwoomClient(settings, token_manager)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="kiwoom-bridge", version="0.1.0", lifespan=lifespan)


@app.exception_handler(KiwoomApiError)
async def kiwoom_api_error_handler(_: Request, exc: KiwoomApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=exc.envelope())


app.include_router(health.router)
app.include_router(
    account.router,
    dependencies=[Depends(require_bridge_token)],
)
app.include_router(
    stocks.router,
    dependencies=[Depends(require_bridge_token)],
)
app.include_router(
    watchlist.router,
    dependencies=[Depends(require_bridge_token)],
)
app.include_router(
    conditions.router,
    dependencies=[Depends(require_bridge_token)],
)
app.include_router(
    orders.router,
    dependencies=[Depends(require_bridge_token)],
)
app.include_router(realtime.router)
