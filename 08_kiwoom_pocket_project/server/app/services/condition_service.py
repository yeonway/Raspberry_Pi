from app.config import Settings
from app.kiwoom.client import KiwoomApiError, KiwoomClient
from app.kiwoom import tr_codes
from app.schemas import ConditionRunRequest, ConditionRunResponse, ConditionSummary
from app.services.stock_service import sample_quote


async def list_conditions(client: KiwoomClient, settings: Settings) -> list[ConditionSummary]:
    try:
        if settings.has_kiwoom_credentials:
            raw = await client.request(tr_codes.CONDITION_LIST, {"trnm": "CNSRLST"})
            body = raw.get("body", {})
            rows = body.get("condition") or body.get("items") or []
            conditions = [
                ConditionSummary(seq=str(row.get("seq") or row.get("cond_seq")), name=str(row.get("name") or row.get("cond_nm")))
                for row in rows
                if isinstance(row, dict)
            ]
            if conditions:
                return conditions
    except Exception as exc:
        if not settings.kiwoom_mock_fallback:
            raise _as_kiwoom_error(exc)
    return [
        ConditionSummary(seq="001", name="샘플 조건식 A", is_fallback=True),
        ConditionSummary(seq="002", name="샘플 조건식 B", is_fallback=True),
    ]


async def run_condition(seq: str, request: ConditionRunRequest, client: KiwoomClient, settings: Settings) -> ConditionRunResponse:
    try:
        if settings.has_kiwoom_credentials:
            raw = await client.request(
                tr_codes.CONDITION_RUN,
                {
                    "trnm": "CNSRREQ",
                    "seq": seq,
                    "search_type": request.search_type,
                    "stex_tp": request.stex_tp,
                    "cont_yn": request.cont_yn,
                },
                cont_yn=request.cont_yn,
                next_key=request.next_key,
            )
            body = raw.get("body", {})
            codes = [str(item.get("stk_cd") or item.get("code")) for item in body.get("items", []) if isinstance(item, dict)]
            return ConditionRunResponse(seq=seq, name=f"조건식 {seq}", results=[sample_quote(code) for code in codes if code])
    except Exception as exc:
        if not settings.kiwoom_mock_fallback:
            raise _as_kiwoom_error(exc)
    return ConditionRunResponse(
        seq=seq,
        name=f"샘플 조건식 {seq}",
        results=[sample_quote("005930"), sample_quote("035420"), sample_quote("005380")],
        is_fallback=True,
    )


def _as_kiwoom_error(exc: Exception) -> KiwoomApiError:
    if isinstance(exc, KiwoomApiError):
        return exc
    return KiwoomApiError("KIWOOM_BRIDGE_ERROR", "키움 조건검색 처리 중 오류가 발생했습니다.", 502, str(exc))
