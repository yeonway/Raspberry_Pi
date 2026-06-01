from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.kiwoom.client import KiwoomClient
from app.schemas import AccountNumbersResponse, BalanceResponse, PortfolioResponse
from app.services import account_service

router = APIRouter(prefix="/api/account", tags=["account"])


def get_client() -> KiwoomClient:
    from app.main import kiwoom_client

    return kiwoom_client


@router.get("/numbers", response_model=AccountNumbersResponse)
async def account_numbers(
    client: Annotated[KiwoomClient, Depends(get_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AccountNumbersResponse:
    return await account_service.get_account_numbers(client, settings)


@router.get("/balance", response_model=BalanceResponse)
async def account_balance(
    client: Annotated[KiwoomClient, Depends(get_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BalanceResponse:
    return await account_service.get_balance(client, settings)


@router.get("/portfolio", response_model=PortfolioResponse)
async def account_portfolio(
    client: Annotated[KiwoomClient, Depends(get_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PortfolioResponse:
    return await account_service.get_portfolio(client, settings)
