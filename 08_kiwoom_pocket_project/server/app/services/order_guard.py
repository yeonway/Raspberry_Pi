import re
import time
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.schemas import MockOrderRequest


CODE_RE = re.compile(r"^[0-9A-Z]{6,12}$")
ALLOWED_MARKETS = {"KRX", "NXT", "SOR"}
BLOCKED_MARKET_ORDER_TYPES = {"market", "시장가", "3"}


@dataclass
class RecentOrder:
    code: str
    side: str
    created_at: float


_recent_orders: dict[tuple[str, str], RecentOrder] = {}


def validate_mock_order(payload: MockOrderRequest, side: str) -> None:
    if not CODE_RE.fullmatch(payload.code):
        _reject("INVALID_CODE", "종목코드는 6~12자리 숫자/영문이어야 합니다.")
    if payload.qty <= 0 or payload.qty > 1_000_000:
        _reject("INVALID_QTY", "수량은 1 이상 1,000,000 이하만 허용합니다.")
    if payload.price <= 0 or payload.price > 10_000_000:
        _reject("INVALID_PRICE", "가격은 1 이상 10,000,000 이하만 허용합니다.")
    if payload.market not in ALLOWED_MARKETS:
        _reject("INVALID_MARKET", "거래소 구분은 KRX, NXT, SOR만 허용합니다.")
    if payload.order_type.lower() in BLOCKED_MARKET_ORDER_TYPES:
        _reject("MARKET_ORDER_BLOCKED", "시장가 주문은 기본 차단되어 있습니다.")

    now = time.monotonic()
    key = (payload.code, side)
    recent = _recent_orders.get(key)
    if recent and now - recent.created_at < 5:
        _reject("DUPLICATE_ORDER_BLOCKED", "동일 종목 5초 내 중복 주문은 차단됩니다.")
    _recent_orders[key] = RecentOrder(code=payload.code, side=side, created_at=now)


def _reject(code: str, message: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error": {
                "return_code": code,
                "return_msg": message,
                "http_status": status.HTTP_400_BAD_REQUEST,
                "internal_message": "order_guard rejected request",
            }
        },
    )
