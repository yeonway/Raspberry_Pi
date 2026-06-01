import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.config import Settings, get_settings
from app.database import get_db
from app.schemas import MockOrderRequest, MockOrderResponse
from app.services.order_guard import validate_mock_order

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("/mock/buy", response_model=MockOrderResponse)
async def mock_buy(
    payload: MockOrderRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> MockOrderResponse:
    return _handle_mock_order("buy", payload, settings, db)


@router.post("/mock/sell", response_model=MockOrderResponse)
async def mock_sell(
    payload: MockOrderRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> MockOrderResponse:
    return _handle_mock_order("sell", payload, settings, db)


def _handle_mock_order(side: str, payload: MockOrderRequest, settings: Settings, db: Session) -> MockOrderResponse:
    if settings.kiwoom_mode == "real":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "return_code": "REAL_ORDER_BLOCKED",
                    "return_msg": "실전 주문은 구현하지 않았고 코드상 차단되어 있습니다.",
                    "http_status": status.HTTP_403_FORBIDDEN,
                    "internal_message": "real mode order endpoint blocked",
                }
            },
        )

    validate_mock_order(payload, side)
    response = MockOrderResponse(
        accepted=True,
        mode=settings.kiwoom_mode,
        side=side,
        code=payload.code,
        qty=payload.qty,
        price=payload.price,
        order_type=payload.order_type,
        message="모의 주문 스켈레톤에서 검증 후 로그만 기록했습니다. 실제 주문 전송은 수행하지 않습니다.",
        kiwoom_response=None,
    )
    db.add(
        models.OrderLog(
            mode=settings.kiwoom_mode,
            side=side,
            code=payload.code,
            qty=payload.qty,
            price=payload.price,
            order_type=payload.order_type,
            request_json=payload.model_dump_json(),
            response_json=json.dumps(response.model_dump(mode="json"), ensure_ascii=False),
        )
    )
    db.commit()
    return response
