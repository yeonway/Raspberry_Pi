from app.config import Settings
from app.kiwoom.client import KiwoomApiError, KiwoomClient
from app.kiwoom import tr_codes
from app.schemas import AccountNumbersResponse, BalanceResponse, PortfolioItem, PortfolioResponse


async def get_account_numbers(client: KiwoomClient, settings: Settings) -> AccountNumbersResponse:
    try:
        if settings.has_kiwoom_credentials:
            raw = await client.request(tr_codes.ACCOUNT_NUMBERS, {"qry_tp": "1"})
            body = raw.get("body", {})
            accounts = body.get("accounts") or body.get("acnt_no_list") or []
            if isinstance(accounts, str):
                accounts = [item for item in accounts.split(";") if item]
            if accounts:
                return AccountNumbersResponse(accounts=accounts)
    except Exception as exc:
        if not settings.kiwoom_mock_fallback:
            raise _as_kiwoom_error(exc)
    return AccountNumbersResponse(accounts=["0000000000"], is_fallback=True)


async def get_balance(client: KiwoomClient, settings: Settings) -> BalanceResponse:
    try:
        if settings.has_kiwoom_credentials:
            raw = await client.request(tr_codes.ACCOUNT_BALANCE, {"qry_tp": "1"})
            body = raw.get("body", {})
            return BalanceResponse(
                deposit=_to_int(body.get("entr") or body.get("deposit")),
                available_cash=_to_int(body.get("ord_psbl_cash") or body.get("available_cash")),
                total_asset=_to_int(body.get("tot_asst") or body.get("total_asset")),
            )
    except Exception as exc:
        if not settings.kiwoom_mock_fallback:
            raise _as_kiwoom_error(exc)
    return BalanceResponse(deposit=10_000_000, available_cash=8_500_000, total_asset=24_350_000, is_fallback=True)


async def get_portfolio(client: KiwoomClient, settings: Settings) -> PortfolioResponse:
    try:
        if settings.has_kiwoom_credentials:
            raw = await client.request(tr_codes.ACCOUNT_PORTFOLIO, {"qry_tp": "1"})
            body = raw.get("body", {})
            rows = body.get("items") or body.get("acnt_evlt_remn_indv_tot") or []
            items = [_portfolio_item(row) for row in rows if isinstance(row, dict)]
            if items:
                return PortfolioResponse(
                    items=items,
                    total_eval_amount=sum(item.eval_amount for item in items),
                    total_profit=sum(item.eval_profit for item in items),
                )
    except Exception as exc:
        if not settings.kiwoom_mock_fallback:
            raise _as_kiwoom_error(exc)
    items = [
        PortfolioItem(code="005930", name="삼성전자", qty=10, avg_price=72000, current_price=78400, eval_amount=784000, eval_profit=64000, profit_rate=8.89),
        PortfolioItem(code="000660", name="SK하이닉스", qty=3, avg_price=192000, current_price=187500, eval_amount=562500, eval_profit=-13500, profit_rate=-2.34),
    ]
    return PortfolioResponse(items=items, total_eval_amount=1_346_500, total_profit=50_500, is_fallback=True)


def _portfolio_item(row: dict) -> PortfolioItem:
    qty = _to_int(row.get("rmnd_qty") or row.get("qty"))
    current_price = _to_int(row.get("cur_prc") or row.get("current_price"))
    return PortfolioItem(
        code=str(row.get("stk_cd") or row.get("code") or ""),
        name=str(row.get("stk_nm") or row.get("name") or ""),
        qty=qty,
        avg_price=_to_int(row.get("avg_prc") or row.get("avg_price")),
        current_price=current_price,
        eval_amount=_to_int(row.get("evlt_amt") or qty * current_price),
        eval_profit=_to_int(row.get("evltv_prft") or row.get("eval_profit")),
        profit_rate=float(str(row.get("prft_rt") or row.get("profit_rate") or "0").replace("%", "")),
    )


def _to_int(value) -> int:
    if value is None:
        return 0
    return int(str(value).replace(",", "").replace("+", "").strip() or "0")


def _as_kiwoom_error(exc: Exception) -> KiwoomApiError:
    if isinstance(exc, KiwoomApiError):
        return exc
    return KiwoomApiError("KIWOOM_BRIDGE_ERROR", "키움 API 처리 중 오류가 발생했습니다.", 502, str(exc))
