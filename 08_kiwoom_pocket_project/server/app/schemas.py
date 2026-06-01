from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorEnvelope(BaseModel):
    return_code: str | int | None = None
    return_msg: str
    http_status: int
    internal_message: str


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "kiwoom-bridge"
    mode: str
    mock_fallback: bool


class TokenStatusResponse(BaseModel):
    has_token: bool
    expires_dt: str | None = None
    expires_in_sec: int | None = None
    masked_token: str | None = None
    mode: str
    has_credentials: bool


class TokenRefreshResponse(TokenStatusResponse):
    refreshed: bool


class Continuation(BaseModel):
    cont_yn: str | None = None
    next_key: str | None = None


class AccountNumbersResponse(BaseModel):
    accounts: list[str]
    is_fallback: bool = False


class BalanceResponse(BaseModel):
    deposit: int
    available_cash: int
    total_asset: int
    is_fallback: bool = False


class PortfolioItem(BaseModel):
    code: str
    name: str
    qty: int
    avg_price: int
    current_price: int
    eval_amount: int
    eval_profit: int
    profit_rate: float


class PortfolioResponse(BaseModel):
    items: list[PortfolioItem]
    total_eval_amount: int
    total_profit: int
    is_fallback: bool = False


class QuoteResponse(BaseModel):
    code: str
    name: str
    price: int
    change_price: int
    change_rate: float
    volume: int
    updated_at: datetime
    continuation: Continuation | None = None
    is_fallback: bool = False


class OrderBookLevel(BaseModel):
    price: int
    qty: int


class OrderBookResponse(BaseModel):
    code: str
    asks: list[OrderBookLevel]
    bids: list[OrderBookLevel]
    updated_at: datetime
    continuation: Continuation | None = None
    is_fallback: bool = False


class ChartPoint(BaseModel):
    date: str
    time: str | None = None
    open: int
    high: int
    low: int
    close: int
    volume: int


class ChartResponse(BaseModel):
    code: str
    points: list[ChartPoint]
    continuation: Continuation | None = None
    is_fallback: bool = False


class WatchStockCreate(BaseModel):
    code: str = Field(min_length=6, max_length=12)
    name: str = ""
    market: str = "KRX"
    memo: str = ""


class WatchStockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    market: str
    memo: str
    created_at: datetime


class ConditionSummary(BaseModel):
    seq: str
    name: str
    is_fallback: bool = False


class ConditionRunRequest(BaseModel):
    search_type: str = "0"
    stex_tp: str = "K"
    cont_yn: str = "N"
    next_key: str = ""


class ConditionRunResponse(BaseModel):
    seq: str
    name: str
    results: list[QuoteResponse]
    continuation: Continuation | None = None
    is_fallback: bool = False


class MockOrderRequest(BaseModel):
    code: str = Field(min_length=6, max_length=12)
    qty: int = Field(gt=0)
    price: int = Field(gt=0)
    order_type: str = "limit"
    market: str = "KRX"


class MockOrderResponse(BaseModel):
    accepted: bool
    mode: str
    side: str
    code: str
    qty: int
    price: int
    order_type: str
    message: str
    kiwoom_response: dict[str, Any] | None = None
