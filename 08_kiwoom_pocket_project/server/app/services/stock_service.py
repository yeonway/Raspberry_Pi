from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app import models
from app.config import Settings
from app.kiwoom.client import KiwoomApiError, KiwoomClient
from app.kiwoom import tr_codes
from app.schemas import ChartPoint, ChartResponse, Continuation, OrderBookLevel, OrderBookResponse, QuoteResponse


SAMPLE_STOCKS: dict[str, dict[str, Any]] = {
    "005930": {"name": "삼성전자", "price": 78400, "change_price": 900, "change_rate": 1.16, "volume": 15832000},
    "000660": {"name": "SK하이닉스", "price": 187500, "change_price": -2500, "change_rate": -1.32, "volume": 4210000},
    "035420": {"name": "NAVER", "price": 203000, "change_price": 1500, "change_rate": 0.74, "volume": 693000},
    "035720": {"name": "카카오", "price": 53800, "change_price": -400, "change_rate": -0.74, "volume": 1820000},
    "005380": {"name": "현대차", "price": 247000, "change_price": 3000, "change_rate": 1.23, "volume": 890000},
}


async def get_quote(code: str, client: KiwoomClient, settings: Settings, db: Session) -> QuoteResponse:
    try:
        if settings.has_kiwoom_credentials:
            raw = await client.request(tr_codes.STOCK_QUOTE, {"stk_cd": code})
            quote = _quote_from_kiwoom(code, raw)
            _save_recent_quote(db, quote)
            return quote
    except Exception as exc:
        if not settings.kiwoom_mock_fallback:
            raise _as_kiwoom_error(exc)

    quote = sample_quote(code)
    _save_recent_quote(db, quote)
    return quote


async def get_orderbook(code: str, client: KiwoomClient, settings: Settings) -> OrderBookResponse:
    try:
        if settings.has_kiwoom_credentials:
            raw = await client.request(tr_codes.STOCK_ORDERBOOK, {"stk_cd": code})
            return _orderbook_from_kiwoom(code, raw)
    except Exception as exc:
        if not settings.kiwoom_mock_fallback:
            raise _as_kiwoom_error(exc)
    return sample_orderbook(code)


async def get_day_chart(code: str, client: KiwoomClient, settings: Settings) -> ChartResponse:
    try:
        if settings.has_kiwoom_credentials:
            raw = await client.request(tr_codes.STOCK_DAY_CHART, {"stk_cd": code, "base_dt": "", "upd_stkpc_tp": "1"})
            return _chart_from_kiwoom(code, raw)
    except Exception as exc:
        if not settings.kiwoom_mock_fallback:
            raise _as_kiwoom_error(exc)
    return sample_chart(code, minute=False)


async def get_minute_chart(code: str, client: KiwoomClient, settings: Settings) -> ChartResponse:
    try:
        if settings.has_kiwoom_credentials:
            raw = await client.request(tr_codes.STOCK_MINUTE_CHART, {"stk_cd": code, "tic_scope": "1", "upd_stkpc_tp": "1"})
            return _chart_from_kiwoom(code, raw)
    except Exception as exc:
        if not settings.kiwoom_mock_fallback:
            raise _as_kiwoom_error(exc)
    return sample_chart(code, minute=True)


def sample_quote(code: str) -> QuoteResponse:
    data = SAMPLE_STOCKS.get(code, {"name": code, "price": 10000, "change_price": 0, "change_rate": 0.0, "volume": 0})
    return QuoteResponse(
        code=code,
        name=data["name"],
        price=int(data["price"]),
        change_price=int(data["change_price"]),
        change_rate=float(data["change_rate"]),
        volume=int(data["volume"]),
        updated_at=datetime.now(timezone.utc),
        is_fallback=True,
    )


def sample_orderbook(code: str) -> OrderBookResponse:
    quote = sample_quote(code)
    asks = [OrderBookLevel(price=quote.price + step * 100, qty=1000 + step * 130) for step in range(5, 0, -1)]
    bids = [OrderBookLevel(price=quote.price - step * 100, qty=900 + step * 150) for step in range(1, 6)]
    return OrderBookResponse(code=code, asks=asks, bids=bids, updated_at=datetime.now(timezone.utc), is_fallback=True)


def sample_chart(code: str, minute: bool) -> ChartResponse:
    quote = sample_quote(code)
    points: list[ChartPoint] = []
    for idx in range(12):
        close = quote.price - (11 - idx) * 120 + (idx % 3) * 80
        points.append(
            ChartPoint(
                date=f"202605{10 + idx:02d}",
                time=f"09{idx:02d}00" if minute else None,
                open=close - 100,
                high=close + 300,
                low=close - 350,
                close=close,
                volume=quote.volume // 20 + idx * 1000,
            )
        )
    return ChartResponse(code=code, points=points, is_fallback=True)


def _quote_from_kiwoom(code: str, raw: dict[str, Any]) -> QuoteResponse:
    body = raw.get("body", {})
    name = str(body.get("stk_nm") or body.get("name") or SAMPLE_STOCKS.get(code, {}).get("name", code))
    quote = QuoteResponse(
        code=code,
        name=name,
        price=_to_int(body.get("cur_prc") or body.get("price")),
        change_price=_to_int(body.get("pred_pre") or body.get("change_price")),
        change_rate=_to_float(body.get("flu_rt") or body.get("change_rate")),
        volume=_to_int(body.get("trde_qty") or body.get("volume")),
        updated_at=datetime.now(timezone.utc),
        continuation=Continuation(**raw.get("continuation", {})),
    )
    return quote


def _orderbook_from_kiwoom(code: str, raw: dict[str, Any]) -> OrderBookResponse:
    body = raw.get("body", {})
    asks: list[OrderBookLevel] = []
    bids: list[OrderBookLevel] = []
    for idx in range(1, 6):
        asks.append(OrderBookLevel(price=_to_int(body.get(f"sel_{idx}th_pre_req_pre")), qty=_to_int(body.get(f"sel_{idx}th_pre_req"))))
        bids.append(OrderBookLevel(price=_to_int(body.get(f"buy_{idx}th_pre_req_pre")), qty=_to_int(body.get(f"buy_{idx}th_pre_req"))))
    if not any(level.price for level in asks + bids):
        return sample_orderbook(code)
    return OrderBookResponse(code=code, asks=asks, bids=bids, updated_at=datetime.now(timezone.utc), continuation=Continuation(**raw.get("continuation", {})))


def _chart_from_kiwoom(code: str, raw: dict[str, Any]) -> ChartResponse:
    body = raw.get("body", {})
    rows = body.get("stk_dt_pole_chart_qry") or body.get("stk_min_pole_chart_qry") or body.get("items") or []
    points = [
        ChartPoint(
            date=str(row.get("dt") or row.get("date") or ""),
            time=str(row.get("tm") or row.get("time") or "") or None,
            open=_to_int(row.get("open_pric") or row.get("open")),
            high=_to_int(row.get("high_pric") or row.get("high")),
            low=_to_int(row.get("low_pric") or row.get("low")),
            close=_to_int(row.get("cur_prc") or row.get("close")),
            volume=_to_int(row.get("trde_qty") or row.get("volume")),
        )
        for row in rows
        if isinstance(row, dict)
    ]
    if not points:
        return sample_chart(code, minute=False)
    return ChartResponse(code=code, points=points, continuation=Continuation(**raw.get("continuation", {})))


def _save_recent_quote(db: Session, quote: QuoteResponse) -> None:
    recent = db.get(models.RecentQuote, quote.code)
    if recent is None:
        recent = models.RecentQuote(code=quote.code)
        db.add(recent)
    recent.name = quote.name
    recent.price = quote.price
    recent.change_price = quote.change_price
    recent.change_rate = f"{quote.change_rate:.2f}"
    recent.volume = quote.volume
    recent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    return int(str(value).replace(",", "").replace("+", "").strip() or "0")


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(str(value).replace("%", "").replace("+", "").strip() or "0")


def _as_kiwoom_error(exc: Exception) -> KiwoomApiError:
    if isinstance(exc, KiwoomApiError):
        return exc
    return KiwoomApiError("KIWOOM_BRIDGE_ERROR", "키움 API 처리 중 오류가 발생했습니다.", 502, str(exc))
