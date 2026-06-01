from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.kiwoom.client import KiwoomClient
from app.schemas import ChartResponse, OrderBookResponse, QuoteResponse
from app.services import stock_service

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


def get_client() -> KiwoomClient:
    from app.main import kiwoom_client

    return kiwoom_client


@router.get("/{code}/quote", response_model=QuoteResponse)
async def quote(
    code: str,
    client: Annotated[KiwoomClient, Depends(get_client)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> QuoteResponse:
    return await stock_service.get_quote(code, client, settings, db)


@router.get("/{code}/orderbook", response_model=OrderBookResponse)
async def orderbook(
    code: str,
    client: Annotated[KiwoomClient, Depends(get_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OrderBookResponse:
    return await stock_service.get_orderbook(code, client, settings)


@router.get("/{code}/chart/day", response_model=ChartResponse)
async def day_chart(
    code: str,
    client: Annotated[KiwoomClient, Depends(get_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChartResponse:
    return await stock_service.get_day_chart(code, client, settings)


@router.get("/{code}/chart/minute", response_model=ChartResponse)
async def minute_chart(
    code: str,
    client: Annotated[KiwoomClient, Depends(get_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChartResponse:
    return await stock_service.get_minute_chart(code, client, settings)
