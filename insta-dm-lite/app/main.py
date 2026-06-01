import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs, quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .billing import (
    get_seed_user_id,
    get_usage_balance,
    grant_monthly_credits,
    list_subscription_plans,
    list_token_products,
)
from .automations import (
    AutomationValidationError,
    create_automation_rule,
    get_or_create_connected_account,
    list_automation_rules,
    set_rule_enabled,
)
from .comment_engine import (
    enqueue_comment_for_processing,
    list_automation_logs,
    list_job_queue,
    process_due_jobs,
)
from .database import get_connection, initialize_database
from .meta_api import (
    MetaApiError,
    get_comments,
    get_latest_meta_api_failure,
    get_media_list,
    reply_to_comment,
    send_private_reply,
)
from .webhooks import handle_meta_webhook_payload, verify_meta_challenge, verify_meta_request_signature
from .payments import (
    create_checkout_order,
    get_payment_order,
    handle_portone_webhook,
    list_checkout_products,
    list_recent_payment_orders,
)
from .facebook_oauth import (
    FacebookOAuthError,
    build_facebook_login_url,
    connect_selected_page,
    get_account_page_access_token,
    get_connection_usage,
    get_oauth_session,
    handle_oauth_callback,
    list_connected_accounts,
)
from .config import get_settings

LOG_STATUS_LABELS = {
    "success": "성공",
    "partial_success": "일부 성공",
    "queued": "대기 중",
    "processing": "처리 중",
    "skipped": "건너뜀",
    "skipped_keyword": "키워드 불일치",
    "skipped_media": "대상 게시물 아님",
    "skipped_rule_conflict": "규칙 충돌",
    "duplicate": "중복",
    "token_empty": "토큰 부족",
    "permission_error": "권한 오류",
    "rate_limited": "제한 대기",
    "failed": "실패",
}
LOG_STATUS_OPTIONS = [
    {"value": "success", "label": "성공"},
    {"value": "partial_success", "label": "일부 성공"},
    {"value": "queued", "label": "대기 중"},
    {"value": "skipped_keyword", "label": "키워드 불일치"},
    {"value": "skipped_media", "label": "대상 게시물 아님"},
    {"value": "skipped_rule_conflict", "label": "규칙 충돌"},
    {"value": "duplicate", "label": "중복"},
    {"value": "token_empty", "label": "토큰 부족"},
    {"value": "permission_error", "label": "권한 오류"},
    {"value": "rate_limited", "label": "제한 대기"},
    {"value": "failed", "label": "실패"},
]
PERIOD_OPTIONS = [
    {"value": "today", "label": "오늘"},
    {"value": "7d", "label": "최근 7일"},
    {"value": "30d", "label": "최근 30일"},
    {"value": "", "label": "전체"},
]


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    grant_monthly_credits(get_seed_user_id())
    yield


app = FastAPI(title="댓글DM 라이트", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    summary = _get_customer_dashboard_summary()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"request": request, **summary},
    )


@app.get("/billing", response_class=HTMLResponse)
async def billing(request: Request):
    user_id = get_seed_user_id()
    balance = _get_seed_user_balance()
    return templates.TemplateResponse(
        request,
        "billing.html",
        {
            "request": request,
            "balance": balance,
            "plans": list_subscription_plans(),
            "token_products": list_token_products(),
            "orders": _decorate_payment_orders(list_recent_payment_orders(user_id)),
        },
    )


@app.get("/billing/products")
async def billing_products():
    return {"products": list_checkout_products()}


@app.post("/billing/checkout/{product_id}")
async def billing_checkout(product_id: int):
    try:
        return create_checkout_order(product_id, user_id=get_seed_user_id())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/billing/portone/webhook")
async def billing_portone_webhook(request: Request):
    raw_body = await request.body()
    result = handle_portone_webhook(raw_body, dict(request.headers))
    return {"ok": bool(result.get("ok")), **result}


@app.get("/billing/orders/{order_id}")
async def billing_order(order_id: int):
    return {"order": _decorate_payment_order(get_payment_order(order_id))}


@app.get("/media", response_class=HTMLResponse)
async def media(request: Request):
    user_id = get_seed_user_id()
    meta_context = _get_default_meta_context(user_id)
    error = None
    media_items = []
    try:
        media_items = get_media_list(
            ig_user_id=meta_context.get("ig_user_id"),
            access_token=meta_context.get("access_token"),
        )
    except MetaApiError as exc:
        error = _friendly_error_message(exc)
    return templates.TemplateResponse(
        request,
        "media.html",
        {
            "request": request,
            "media_items": media_items,
            "error": error,
            "latest_failure": get_latest_meta_api_failure(),
        },
    )


@app.get("/automations", response_class=HTMLResponse)
async def automations(request: Request):
    user_id = get_seed_user_id()
    get_or_create_connected_account(user_id)
    return templates.TemplateResponse(
        request,
        "automations.html",
        {
            "request": request,
            "rules": list_automation_rules(user_id),
        },
    )


@app.get("/automations/new", response_class=HTMLResponse)
async def new_automation(request: Request):
    return _render_new_automation(request)


@app.post("/automations/new", response_class=HTMLResponse)
async def create_automation(request: Request):
    values = await _read_urlencoded_values(request)
    user_id = get_seed_user_id()
    try:
        create_automation_rule(
            user_id=user_id,
            name=_first(values, "name"),
            target_mode=_first(values, "target_mode", "all"),
            keywords_text=_first(values, "keywords"),
            exclude_keywords_text=_first(values, "exclude_keywords"),
            match_mode=_first(values, "match_mode", "contains"),
            public_reply_text=_first(values, "public_reply_text"),
            dm_text=_first(values, "dm_text"),
            cta_label=_first(values, "cta_label"),
            cta_url=_first(values, "cta_url"),
            delay_min_seconds=_parse_int(_first(values, "delay_min_seconds", "0")),
            delay_max_seconds=_parse_int(_first(values, "delay_max_seconds", "0")),
            selected_media=_extract_selected_media(values),
        )
    except (AutomationValidationError, ValueError) as exc:
        return _render_new_automation(request, error=str(exc), form=_flatten_values(values))
    return RedirectResponse("/automations", status_code=303)


@app.post("/automations/{rule_id}/toggle")
async def toggle_automation(request: Request, rule_id: int):
    values = await _read_urlencoded_values(request)
    user_id = get_seed_user_id()
    set_rule_enabled(user_id, rule_id, enabled=_first(values, "enabled") == "1")
    return RedirectResponse("/automations", status_code=303)


@app.get("/logs", response_class=HTMLResponse)
async def logs(request: Request):
    user_id = get_seed_user_id()
    status = request.query_params.get("status", "").strip()
    rule_id = request.query_params.get("rule_id", "").strip()
    media_id = request.query_params.get("media_id", "").strip()
    period = request.query_params.get("period", "today").strip()
    return templates.TemplateResponse(
        request,
        "logs.html",
        {
            "request": request,
            "logs": _decorate_logs(list_automation_logs(status=status, rule_id=rule_id, media_id=media_id, period=period)),
            "rules": list_automation_rules(user_id),
            "status_options": LOG_STATUS_OPTIONS,
            "period_options": PERIOD_OPTIONS,
            "filters": {"status": status, "rule_id": rule_id, "media_id": media_id, "period": period},
        },
    )


@app.get("/connections", response_class=HTMLResponse)
async def connections(request: Request):
    user_id = get_seed_user_id()
    error = request.query_params.get("error", "").strip()
    notice = request.query_params.get("notice", "").strip()
    return templates.TemplateResponse(
        request,
        "connections.html",
        {
            "request": request,
            "accounts": _decorate_connected_accounts(list_connected_accounts(user_id)),
            "usage": get_connection_usage(user_id),
            "error": error,
            "notice": notice,
        },
    )


@app.get("/connections/facebook/start")
async def facebook_connection_start():
    user_id = get_seed_user_id()
    try:
        return RedirectResponse(build_facebook_login_url(user_id), status_code=303)
    except FacebookOAuthError as exc:
        return RedirectResponse(f"/connections?error={_url_quote(str(exc))}", status_code=303)


@app.get("/connections/facebook/callback", response_class=HTMLResponse)
async def facebook_connection_callback(request: Request):
    user_id = get_seed_user_id()
    error = request.query_params.get("error_description") or request.query_params.get("error") or ""
    if error:
        return templates.TemplateResponse(
            request,
            "connections.html",
            {
                "request": request,
                "accounts": _decorate_connected_accounts(list_connected_accounts(user_id)),
                "usage": get_connection_usage(user_id),
                "error": _friendly_error_text(error),
                "notice": "",
            },
        )
    try:
        result = handle_oauth_callback(
            user_id=user_id,
            state=request.query_params.get("state", ""),
            code=request.query_params.get("code", ""),
        )
        return templates.TemplateResponse(
            request,
            "connection_pages.html",
            {
                "request": request,
                "state": result["state"],
                "pages": result["pages"],
                "usage": get_connection_usage(user_id),
                "error": "",
            },
        )
    except FacebookOAuthError as exc:
        return templates.TemplateResponse(
            request,
            "connections.html",
            {
                "request": request,
                "accounts": _decorate_connected_accounts(list_connected_accounts(user_id)),
                "usage": get_connection_usage(user_id),
                "error": str(exc),
                "notice": "",
            },
        )


@app.post("/connections/facebook/select", response_class=HTMLResponse)
async def facebook_connection_select(request: Request):
    user_id = get_seed_user_id()
    form = await _read_urlencoded_form(request)
    state = form.get("state", "")
    try:
        account = connect_selected_page(
            user_id=user_id,
            state=state,
            page_id=form.get("page_id", ""),
        )
        return RedirectResponse(
            f"/connections?notice={_url_quote(account['display_name'] + ' 계정을 연결했습니다.')}",
            status_code=303,
        )
    except FacebookOAuthError as exc:
        pages = []
        try:
            pages = get_oauth_session(user_id, state)["pages"]
        except FacebookOAuthError:
            pass
        return templates.TemplateResponse(
            request,
            "connection_pages.html",
            {
                "request": request,
                "state": state,
                "pages": _safe_session_pages_for_view(pages),
                "usage": get_connection_usage(user_id),
                "error": str(exc),
            },
        )


@app.post("/connections/reconnect")
async def facebook_connection_reconnect():
    return RedirectResponse("/connections/facebook/start", status_code=303)


@app.post("/connections/{account_id}/reconnect")
async def facebook_connection_reconnect_account(account_id: int):
    _ = account_id
    return RedirectResponse("/connections/facebook/start", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"request": request},
    )


@app.get("/debug/process-comment", response_class=HTMLResponse)
async def debug_process_comment(request: Request):
    return _render_debug_process_comment(request)


@app.post("/debug/process-comment", response_class=HTMLResponse)
async def debug_enqueue_comment(request: Request):
    form = await _read_urlencoded_form(request)
    user_id = get_seed_user_id()
    process_now = form.get("process_now") == "1"
    try:
        result = enqueue_comment_for_processing(
            user_id=user_id,
            media_id=form.get("media_id", ""),
            comment_id=form.get("comment_id", ""),
            comment_text=form.get("comment_text", ""),
            delay_override_seconds=0 if process_now else None,
        )
        processed = process_due_jobs(limit=1) if process_now else []
        return _render_debug_process_comment(
            request,
            notice="댓글 처리 테스트를 실행했습니다.",
            result=result,
            processed=processed,
            form=form,
        )
    except ValueError as exc:
        return _render_debug_process_comment(request, error=str(exc), form=form)


@app.post("/debug/run-queue", response_class=HTMLResponse)
async def debug_run_queue(request: Request):
    processed = process_due_jobs(limit=5)
    return _render_debug_process_comment(
        request,
        notice=f"큐 작업 {len(processed)}개를 처리했습니다.",
        processed=processed,
    )


@app.get("/webhooks/meta")
async def verify_meta_webhook(request: Request):
    challenge = verify_meta_challenge(
        mode=request.query_params.get("hub.mode", ""),
        verify_token=request.query_params.get("hub.verify_token", ""),
        challenge=request.query_params.get("hub.challenge", ""),
    )
    if challenge is None:
        return PlainTextResponse("Forbidden", status_code=403)
    return PlainTextResponse(challenge)


@app.post("/webhooks/meta")
async def receive_meta_webhook(request: Request):
    raw_body = await request.body()
    if not verify_meta_request_signature(raw_body, request.headers):
        raise HTTPException(status_code=403, detail="Invalid Meta webhook signature")
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
        if not isinstance(payload, dict):
            payload = {"_unexpected_payload": payload}
    except json.JSONDecodeError:
        payload = {"_invalid_json": raw_body.decode("utf-8", errors="replace")}
    result = handle_meta_webhook_payload(payload)
    return {"ok": True, **result}


@app.get("/media/{media_id}/comments", response_class=HTMLResponse)
async def media_comments(request: Request, media_id: str):
    return _render_comments(request, media_id)


@app.post("/media/{media_id}/comments/{comment_id}/reply", response_class=HTMLResponse)
async def test_public_reply(request: Request, media_id: str, comment_id: str):
    form = await _read_urlencoded_form(request)
    message = form.get("message", "테스트 공개 답글입니다.")
    meta_context = _get_default_meta_context(get_seed_user_id())
    try:
        reply_to_comment(comment_id, message, access_token=meta_context.get("access_token"))
        return _render_comments(request, media_id, notice="공개 답글 요청을 보냈습니다.")
    except (MetaApiError, ValueError) as exc:
        return _render_comments(request, media_id, error=str(exc))


@app.post("/media/{media_id}/comments/{comment_id}/private-reply", response_class=HTMLResponse)
async def test_private_reply(request: Request, media_id: str, comment_id: str):
    form = await _read_urlencoded_form(request)
    text = form.get("text", "테스트 DM입니다.")
    cta_label = form.get("cta_label") or None
    cta_url = form.get("cta_url") or None
    meta_context = _get_default_meta_context(get_seed_user_id())
    settings = get_settings()
    page_id = meta_context.get("page_id") or settings.meta_page_id.strip()
    if not page_id:
        return _render_comments(request, media_id, error="META_PAGE_ID 값이 .env에 설정되어 있지 않습니다.")
    try:
        send_private_reply(
            page_id,
            comment_id,
            text,
            cta_label=cta_label,
            cta_url=cta_url,
            access_token=meta_context.get("access_token"),
        )
        return _render_comments(request, media_id, notice="Private Reply DM 요청을 보냈습니다.")
    except (MetaApiError, ValueError) as exc:
        return _render_comments(request, media_id, error=str(exc))


@app.get("/health")
async def health():
    return {"ok": True}


def _get_seed_user_balance() -> dict:
    user_id = get_seed_user_id()
    grant_monthly_credits(user_id)
    return get_usage_balance(user_id)


def _render_comments(
    request: Request,
    media_id: str,
    *,
    notice: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    meta_context = _get_default_meta_context(get_seed_user_id())
    comments = []
    load_error = error
    try:
        comments = get_comments(media_id, access_token=meta_context.get("access_token"))
    except MetaApiError as exc:
        load_error = load_error or _friendly_error_message(exc)
    return templates.TemplateResponse(
        request,
        "comments.html",
        {
            "request": request,
            "media_id": media_id,
            "comments": comments,
            "notice": notice,
            "error": load_error,
            "latest_failure": get_latest_meta_api_failure(),
        },
    )


async def _read_urlencoded_form(request: Request) -> dict[str, str]:
    values = await _read_urlencoded_values(request)
    return {key: item[0].strip() for key, item in values.items() if item}


async def _read_urlencoded_values(request: Request) -> dict[str, list[str]]:
    raw_body = (await request.body()).decode("utf-8")
    return parse_qs(raw_body, keep_blank_values=True)


def _render_new_automation(
    request: Request,
    *,
    error: str | None = None,
    form: dict[str, str] | None = None,
) -> HTMLResponse:
    meta_context = _get_default_meta_context(get_seed_user_id())
    media_items = []
    media_error = None
    try:
        media_items = get_media_list(
            ig_user_id=meta_context.get("ig_user_id"),
            access_token=meta_context.get("access_token"),
        )
    except MetaApiError as exc:
        media_error = _friendly_error_message(exc)
    return templates.TemplateResponse(
        request,
        "automation_new.html",
        {
            "request": request,
            "media_items": media_items,
            "error": error,
            "media_error": media_error,
            "latest_failure": get_latest_meta_api_failure(),
            "form": form or {},
            "can_use_cta": _get_seed_user_balance()["plan"]["allow_cta_button"],
        },
    )


def _render_debug_process_comment(
    request: Request,
    *,
    notice: str | None = None,
    error: str | None = None,
    result: dict | None = None,
    processed: list[dict] | None = None,
    form: dict[str, str] | None = None,
) -> HTMLResponse:
    user_id = get_seed_user_id()
    return templates.TemplateResponse(
        request,
        "debug_process_comment.html",
        {
            "request": request,
            "notice": notice,
            "error": error,
            "result": result,
            "processed": processed or [],
            "form": form or {},
            "rules": list_automation_rules(user_id),
            "jobs": list_job_queue(),
        },
    )


def _first(values: dict[str, list[str]], key: str, default: str = "") -> str:
    item = values.get(key)
    if not item:
        return default
    return item[0].strip()


def _parse_int(value: str) -> int:
    if not value:
        return 0
    return int(value)


def _flatten_values(values: dict[str, list[str]]) -> dict[str, str]:
    return {key: item[0].strip() for key, item in values.items() if item}


def _extract_selected_media(values: dict[str, list[str]]) -> list[dict[str, str]]:
    selected_ids = {item.strip() for item in values.get("selected_media", []) if item.strip()}
    media_items = []
    for raw in values.get("media_meta", []):
        try:
            media = json_loads(raw)
        except ValueError:
            continue
        media_id = str(media.get("media_id", "")).strip()
        if media_id in selected_ids:
            media_items.append(
                {
                    "media_id": media_id,
                    "media_caption": str(media.get("media_caption", "")),
                    "media_permalink": str(media.get("media_permalink", "")),
                    "media_type": str(media.get("media_type", "")),
                    "thumbnail_url": str(media.get("thumbnail_url", "")),
                }
            )
    return media_items


def json_loads(value: str) -> dict:
    import json

    loaded = json.loads(value)
    if not isinstance(loaded, dict):
        raise ValueError("Expected object")
    return loaded


def _get_customer_dashboard_summary() -> dict:
    user_id = get_seed_user_id()
    balance = _get_seed_user_balance()
    get_or_create_connected_account(user_id)
    with get_connection() as connection:
        account_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM connected_accounts
            WHERE user_id = ? AND active = 1
            """,
            (user_id,),
        ).fetchone()[0]
        rule_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM automation_rules
            JOIN connected_accounts ON connected_accounts.id = automation_rules.account_id
            WHERE connected_accounts.user_id = ?
            """,
            (user_id,),
        ).fetchone()[0]
        today_start = _today_start()
        today_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM automation_logs
            JOIN connected_accounts ON connected_accounts.id = automation_logs.account_id
            WHERE connected_accounts.user_id = ?
              AND automation_logs.status IN ('success', 'partial_success')
              AND automation_logs.created_at >= ?
            """,
            (user_id, today_start),
        ).fetchone()[0]
        warning_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM automation_logs
            JOIN connected_accounts ON connected_accounts.id = automation_logs.account_id
            WHERE connected_accounts.user_id = ?
              AND automation_logs.status IN ('failed', 'permission_error', 'rate_limited', 'token_empty')
              AND automation_logs.created_at >= ?
            """,
            (user_id, today_start),
        ).fetchone()[0]

    plan = balance["plan"]
    cards = [
        {"label": "현재 플랜", "value": plan["name"], "hint": f"월 {plan['monthly_credits']:,}건 제공"},
        {"label": "자동화 계정", "value": f"{account_count} / {plan['automation_account_limit']}", "hint": "연결해 둔 인스타 계정 수"},
        {"label": "자동화 규칙", "value": f"{rule_count} / {plan['automation_rule_limit']}", "hint": "켜고 끌 수 있는 자동 응답"},
        {"label": "월 제공 잔여", "value": f"{balance['monthly_remaining']:,}건", "hint": "먼저 차감됩니다"},
        {"label": "구매 토큰 잔여", "value": f"{balance['purchased_remaining']:,}건", "hint": "월 제공량 이후 사용"},
        {"label": "오늘 처리", "value": f"{today_count:,}건", "hint": "성공 또는 일부 성공"},
        {
            "label": "실패/주의",
            "value": f"{warning_count:,}건",
            "hint": "확인이 필요한 오늘 알림",
            "tone": "warning" if warning_count else "ok",
        },
    ]
    return {"cards": cards, "warning_count": warning_count}


def _today_start() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _decorate_logs(logs: list[dict]) -> list[dict]:
    decorated = []
    for log in logs:
        item = dict(log)
        item["status_label"] = LOG_STATUS_LABELS.get(item["status"], "확인 필요")
        item["public_reply_label"] = _action_status_label(item.get("public_reply_status", ""))
        item["dm_label"] = _action_status_label(item.get("dm_status", ""))
        item["display_media"] = _short_identifier(item.get("media_id", ""))
        item["display_comment"] = _short_identifier(item.get("comment_id", ""))
        item["friendly_error"] = _friendly_error_text(item.get("error_message", ""))
        decorated.append(item)
    return decorated


def _action_status_label(status: str) -> str:
    return {
        "success": "완료",
        "failed": "실패",
        "permission_error": "권한 오류",
        "rate_limited": "잠시 대기",
        "not_attempted": "시도 안 함",
        "": "-",
    }.get(status, "확인 필요")


def _short_identifier(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return "-"
    if len(value) <= 10:
        return value
    return f"{value[:6]}..."


def _friendly_error_message(error: Exception) -> str:
    return _friendly_error_text(str(error)) or "잠시 후 다시 시도해 주세요."


def _friendly_error_text(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if "meta_page_access_token" in lowered or "access token" in lowered:
        return "인스타 연결 정보가 아직 준비되지 않았습니다. 인스타 연결 화면을 확인해 주세요."
    if "meta_ig_user_id" in lowered or "meta_page_id" in lowered:
        return "인스타 계정 연결이 필요합니다."
    if "권한" in text or "permission" in lowered:
        return "인스타 권한을 확인해 주세요."
    if "네트워크" in text or "연결" in text:
        return "인스타와 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
    return text


def _build_connection_view(account: dict) -> dict:
    active = bool(account.get("active"))
    return {
        "page_name": account.get("display_name") or "연결된 Facebook Page",
        "instagram_name": "Instagram 계정",
        "status": "연결됨" if active else "연결 필요",
        "status_detail": "댓글 자동화에 사용할 계정이 준비되어 있습니다." if active else "다시 연결해 주세요.",
    }


def _get_default_meta_context(user_id: int) -> dict[str, str]:
    for account in list_connected_accounts(user_id):
        if not account.get("active"):
            continue
        try:
            access_token = get_account_page_access_token(account["id"])
        except Exception:
            access_token = ""
        if access_token:
            return {
                "page_id": account.get("page_id", ""),
                "ig_user_id": account.get("ig_user_id", ""),
                "access_token": access_token,
            }
    return {}


def _decorate_connected_accounts(accounts: list[dict]) -> list[dict]:
    decorated = []
    for account in accounts:
        item = dict(account)
        item["page_label"] = account.get("display_name") or "Facebook Page"
        item["instagram_label"] = account.get("ig_username") or account.get("ig_user_id") or "Instagram 계정"
        item["status_label"] = "연결됨" if account.get("active") else "연결 필요"
        if account.get("webhook_subscribed"):
            item["webhook_label"] = "댓글 알림 연결됨"
        elif account.get("webhook_status") == "failed":
            item["webhook_label"] = "댓글 알림 확인 필요"
        else:
            item["webhook_label"] = "댓글 알림 대기"
        decorated.append(item)
    return decorated


def _safe_session_pages_for_view(pages: list[dict]) -> list[dict]:
    safe_pages = []
    for page in pages:
        safe_pages.append(
            {
                "page_id": page.get("page_id", ""),
                "page_name": page.get("page_name", ""),
                "ig_user_id": page.get("ig_user_id", ""),
                "ig_username": page.get("ig_username", ""),
                "connectable": bool(page.get("ig_user_id")),
            }
        )
    return safe_pages


def _url_quote(value: str) -> str:
    return quote(value, safe="")


def _decorate_payment_orders(orders: list[dict]) -> list[dict]:
    return [_decorate_payment_order(order) for order in orders]


def _decorate_payment_order(order: dict) -> dict:
    item = dict(order)
    item["status_label"] = {
        "pending": "결제 대기",
        "paid": "결제 완료",
        "failed": "결제 실패",
        "cancelled": "결제 취소",
    }.get(item.get("status"), "확인 필요")
    return item
