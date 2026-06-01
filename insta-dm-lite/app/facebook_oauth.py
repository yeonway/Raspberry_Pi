from __future__ import annotations

import json
import secrets
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .billing import get_seed_user_id
from .config import get_settings
from .database import get_connection, utc_now
from .token_crypto import TokenCryptoError, decrypt_token, encrypt_token

GRAPH_BASE_URL = "https://graph.facebook.com"
DEFAULT_TIMEOUT_SECONDS = 12
OAUTH_SESSION_TTL_MINUTES = 20
FACEBOOK_SCOPES = [
    "pages_show_list",
    "pages_manage_metadata",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_manage_comments",
    "instagram_manage_messages",
]
PAGE_WEBHOOK_FIELDS = "feed,messages,messaging_postbacks,mentions"


@dataclass
class FacebookOAuthError(Exception):
    user_message: str

    def __str__(self) -> str:
        return self.user_message


def get_connection_usage(user_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT subscription_plans.automation_account_limit
            FROM users
            JOIN subscription_plans ON subscription_plans.id = users.current_plan_id
            WHERE users.id = ?
            """,
            (user_id,),
        ).fetchone()
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM connected_accounts
            WHERE user_id = ? AND provider = 'meta' AND active = 1
            """,
            (user_id,),
        ).fetchone()[0]
    limit = int(row["automation_account_limit"]) if row else 1
    return {
        "used": int(count),
        "limit": limit,
        "remaining": max(limit - int(count), 0),
        "can_connect": int(count) < limit,
    }


def list_connected_accounts(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                user_id,
                provider,
                page_id,
                ig_user_id,
                display_name,
                ig_username,
                facebook_user_id,
                webhook_subscribed,
                webhook_status,
                last_error,
                token_updated_at,
                active,
                created_at,
                updated_at
            FROM connected_accounts
            WHERE user_id = ? AND provider = 'meta'
            ORDER BY active DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
    return [_account_to_dict(row) for row in rows]


def build_facebook_login_url(user_id: int | None = None) -> str:
    user_id = user_id or get_seed_user_id()
    settings = _require_oauth_settings()
    state = _create_oauth_session(user_id)
    query = urllib.parse.urlencode(
        {
            "client_id": settings.facebook_app_id,
            "redirect_uri": settings.facebook_redirect_uri,
            "state": state,
            "scope": ",".join(FACEBOOK_SCOPES),
            "response_type": "code",
        }
    )
    return f"https://www.facebook.com/{_graph_version()}/dialog/oauth?{query}"


def handle_oauth_callback(*, user_id: int, state: str, code: str) -> dict[str, Any]:
    _require_oauth_settings()
    session = get_oauth_session(user_id, state)
    if session["status"] not in {"started", "pages_ready"}:
        raise FacebookOAuthError("이미 처리된 연결 요청입니다. 다시 연결을 시작해주세요.")
    token_payload = _exchange_code_for_user_token(code)
    user_access_token = _first_text(token_payload, "access_token")
    if not user_access_token:
        raise FacebookOAuthError("Facebook 로그인 응답에서 사용자 토큰을 받지 못했습니다.")
    facebook_user_id = _fetch_facebook_user_id(user_access_token)
    pages = _fetch_user_pages(user_access_token)
    if not pages:
        raise FacebookOAuthError("연결할 수 있는 Facebook Page가 없습니다.")

    cleaned_pages = [_clean_page_for_session(page, facebook_user_id) for page in pages]
    now = utc_now()
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE facebook_oauth_sessions
            SET pages_json = ?,
                status = 'pages_ready',
                updated_at = ?,
                error_message = ''
            WHERE state = ? AND user_id = ?
            """,
            (json.dumps(cleaned_pages, ensure_ascii=False), now, state, user_id),
        )
    return {"state": state, "pages": _safe_pages(cleaned_pages)}


def get_oauth_session(user_id: int, state: str) -> dict[str, Any]:
    state = (state or "").strip()
    if not state:
        raise FacebookOAuthError("연결 상태값이 없습니다. 다시 시도해주세요.")
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT state, user_id, pages_json, status, error_message, expires_at
            FROM facebook_oauth_sessions
            WHERE state = ? AND user_id = ?
            """,
            (state, user_id),
        ).fetchone()
    if row is None:
        raise FacebookOAuthError("연결 요청을 찾을 수 없습니다. 다시 시작해주세요.")
    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        raise FacebookOAuthError("연결 요청 시간이 만료되었습니다. 다시 시작해주세요.")
    return {
        "state": row["state"],
        "user_id": int(row["user_id"]),
        "pages": json.loads(row["pages_json"]),
        "status": row["status"],
        "error_message": row["error_message"],
        "expires_at": row["expires_at"],
    }


def connect_selected_page(*, user_id: int, state: str, page_id: str) -> dict[str, Any]:
    session = get_oauth_session(user_id, state)
    pages = session["pages"]
    page = next((item for item in pages if str(item.get("page_id")) == str(page_id)), None)
    if page is None:
        raise FacebookOAuthError("선택한 Page를 찾을 수 없습니다.")
    if not page.get("ig_user_id"):
        raise FacebookOAuthError("이 Page에는 연결된 Instagram 비즈니스 계정이 없습니다.")

    encrypted_token = page.get("page_access_token_encrypted", "")
    try:
        page_access_token = decrypt_token(encrypted_token)
    except TokenCryptoError as exc:
        raise FacebookOAuthError(str(exc)) from exc

    fresh_page = _fetch_page_instagram(page["page_id"], page_access_token)
    if fresh_page:
        page.update(fresh_page)
    if not page.get("ig_user_id"):
        raise FacebookOAuthError("Instagram 비즈니스 계정 정보를 확인하지 못했습니다.")

    existing_account = _find_connected_account(user_id, page["page_id"], page["ig_user_id"])
    usage = get_connection_usage(user_id)
    if existing_account is None and not usage["can_connect"]:
        raise FacebookOAuthError(
            f"현재 플랜은 자동화 계정을 {usage['limit']}개까지 연결할 수 있습니다. 플랜을 업그레이드해주세요."
        )

    webhook_result = _subscribe_page_to_webhook(page["page_id"], page_access_token)
    account = _upsert_connected_account(
        user_id=user_id,
        page=page,
        page_access_token=page_access_token,
        webhook_result=webhook_result,
    )
    _mark_session_connected(user_id, state)
    return account


def get_account_page_access_token(account_id: int) -> str:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT page_access_token_encrypted
            FROM connected_accounts
            WHERE id = ?
            """,
            (account_id,),
        ).fetchone()
    if row is None or not row["page_access_token_encrypted"]:
        return ""
    return decrypt_token(row["page_access_token_encrypted"])


def get_page_access_token_for_identifiers(*identifiers: str) -> str:
    values = [str(item).strip() for item in identifiers if str(item).strip()]
    if not values:
        return ""
    placeholders = ",".join("?" for _ in values)
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT page_access_token_encrypted
            FROM connected_accounts
            WHERE provider = 'meta'
              AND active = 1
              AND (page_id IN ({placeholders}) OR ig_user_id IN ({placeholders}))
            ORDER BY id
            LIMIT 1
            """,
            (*values, *values),
        ).fetchone()
    if row is None or not row["page_access_token_encrypted"]:
        return ""
    return decrypt_token(row["page_access_token_encrypted"])


def _require_oauth_settings():
    settings = get_settings()
    missing = []
    if not settings.facebook_app_id.strip():
        missing.append("FACEBOOK_APP_ID")
    if not settings.facebook_app_secret.strip():
        missing.append("FACEBOOK_APP_SECRET")
    if not settings.facebook_redirect_uri.strip():
        missing.append("FACEBOOK_REDIRECT_URI")
    if not settings.token_encryption_key.strip():
        missing.append("TOKEN_ENCRYPTION_KEY")
    if missing:
        raise FacebookOAuthError(f"{', '.join(missing)} 값이 .env에 설정되어 있지 않습니다.")
    return settings


def _create_oauth_session(user_id: int) -> str:
    state = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    expires_at = now + timedelta(minutes=OAUTH_SESSION_TTL_MINUTES)
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO facebook_oauth_sessions (
                state,
                user_id,
                pages_json,
                status,
                created_at,
                updated_at,
                expires_at
            )
            VALUES (?, ?, '[]', 'started', ?, ?, ?)
            """,
            (state, user_id, now.isoformat(), now.isoformat(), expires_at.isoformat()),
        )
    return state


def _exchange_code_for_user_token(code: str) -> dict[str, Any]:
    settings = get_settings()
    return _graph_request(
        "GET",
        "/oauth/access_token",
        params={
            "client_id": settings.facebook_app_id,
            "redirect_uri": settings.facebook_redirect_uri,
            "client_secret": settings.facebook_app_secret,
            "code": code,
        },
    )


def _fetch_facebook_user_id(user_access_token: str) -> str:
    payload = _graph_request(
        "GET",
        "/me",
        params={"fields": "id"},
        access_token=user_access_token,
    )
    return _first_text(payload, "id")


def _fetch_user_pages(user_access_token: str) -> list[dict[str, Any]]:
    payload = _graph_request(
        "GET",
        "/me/accounts",
        params={
            "fields": "id,name,access_token,instagram_business_account{id,username,name}",
            "limit": 100,
        },
        access_token=user_access_token,
    )
    return payload.get("data", []) if isinstance(payload.get("data"), list) else []


def _fetch_page_instagram(page_id: str, page_access_token: str) -> dict[str, Any]:
    payload = _graph_request(
        "GET",
        f"/{page_id}",
        params={"fields": "id,name,instagram_business_account{id,username,name}"},
        access_token=page_access_token,
    )
    ig = payload.get("instagram_business_account") or {}
    if not isinstance(ig, dict):
        ig = {}
    return {
        "page_id": _first_text(payload, "id") or page_id,
        "page_name": _first_text(payload, "name"),
        "ig_user_id": _first_text(ig, "id"),
        "ig_username": _first_text(ig, "username", "name"),
    }


def _subscribe_page_to_webhook(page_id: str, page_access_token: str) -> dict[str, Any]:
    try:
        payload = _graph_request(
            "POST",
            f"/{page_id}/subscribed_apps",
            data={"subscribed_fields": PAGE_WEBHOOK_FIELDS},
            access_token=page_access_token,
        )
        success = bool(payload.get("success", True))
        return {
            "subscribed": success,
            "status": "subscribed" if success else "failed",
            "error": "" if success else "Webhook 구독 응답이 성공이 아닙니다.",
        }
    except FacebookOAuthError as exc:
        return {"subscribed": False, "status": "failed", "error": str(exc)}


def _clean_page_for_session(page: dict[str, Any], facebook_user_id: str) -> dict[str, Any]:
    token = _first_text(page, "access_token")
    if not token:
        raise FacebookOAuthError("Page Access Token을 받지 못했습니다.")
    ig = page.get("instagram_business_account") or {}
    if not isinstance(ig, dict):
        ig = {}
    return {
        "page_id": _first_text(page, "id"),
        "page_name": _first_text(page, "name"),
        "ig_user_id": _first_text(ig, "id"),
        "ig_username": _first_text(ig, "username", "name"),
        "facebook_user_id": facebook_user_id,
        "page_access_token_encrypted": encrypt_token(token),
    }


def _safe_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe = []
    for page in pages:
        safe.append(
            {
                "page_id": page.get("page_id", ""),
                "page_name": page.get("page_name", ""),
                "ig_user_id": page.get("ig_user_id", ""),
                "ig_username": page.get("ig_username", ""),
                "connectable": bool(page.get("ig_user_id")),
            }
        )
    return safe


def _find_connected_account(user_id: int, page_id: str, ig_user_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM connected_accounts
            WHERE user_id = ?
              AND provider = 'meta'
              AND page_id = ?
              AND ig_user_id = ?
            """,
            (user_id, page_id, ig_user_id),
        ).fetchone()
    return dict(row) if row is not None else None


def _upsert_connected_account(
    *,
    user_id: int,
    page: dict[str, Any],
    page_access_token: str,
    webhook_result: dict[str, Any],
) -> dict[str, Any]:
    now = utc_now()
    encrypted_token = encrypt_token(page_access_token)
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO connected_accounts (
                user_id,
                provider,
                page_id,
                ig_user_id,
                display_name,
                ig_username,
                page_access_token_encrypted,
                facebook_user_id,
                webhook_subscribed,
                webhook_status,
                last_error,
                token_updated_at,
                active,
                created_at,
                updated_at
            )
            VALUES (?, 'meta', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(user_id, provider, page_id, ig_user_id) DO UPDATE SET
                display_name = excluded.display_name,
                ig_username = excluded.ig_username,
                page_access_token_encrypted = excluded.page_access_token_encrypted,
                facebook_user_id = excluded.facebook_user_id,
                webhook_subscribed = excluded.webhook_subscribed,
                webhook_status = excluded.webhook_status,
                last_error = excluded.last_error,
                token_updated_at = excluded.token_updated_at,
                active = 1,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                page["page_id"],
                page["ig_user_id"],
                page.get("page_name") or "Facebook Page",
                page.get("ig_username", ""),
                encrypted_token,
                page.get("facebook_user_id", ""),
                1 if webhook_result.get("subscribed") else 0,
                webhook_result.get("status", ""),
                webhook_result.get("error", ""),
                now,
                now,
                now,
            ),
        )
        row = connection.execute(
            """
            SELECT
                id,
                user_id,
                provider,
                page_id,
                ig_user_id,
                display_name,
                ig_username,
                facebook_user_id,
                webhook_subscribed,
                webhook_status,
                last_error,
                token_updated_at,
                active,
                created_at,
                updated_at
            FROM connected_accounts
            WHERE user_id = ? AND provider = 'meta' AND page_id = ? AND ig_user_id = ?
            """,
            (user_id, page["page_id"], page["ig_user_id"]),
        ).fetchone()
    if row is None:
        raise FacebookOAuthError("연결 계정을 저장하지 못했습니다.")
    return _account_to_dict(row)


def _mark_session_connected(user_id: int, state: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE facebook_oauth_sessions
            SET status = 'connected', updated_at = ?
            WHERE user_id = ? AND state = ?
            """,
            (utc_now(), user_id, state),
        )


def _graph_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    access_token: str = "",
) -> dict[str, Any]:
    request_params = dict(params or {})
    if access_token:
        request_params["access_token"] = access_token
    endpoint = f"/{_graph_version()}{path}"
    url = f"{GRAPH_BASE_URL}{endpoint}"
    body = None
    if method == "GET":
        url = f"{url}?{urllib.parse.urlencode(request_params)}"
    else:
        body_params = dict(data or {})
        body_params.update(request_params)
        body = urllib.parse.urlencode(body_params).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            raw_body = response.read().decode("utf-8")
            return json.loads(raw_body) if raw_body else {}
    except urllib.error.HTTPError as exc:
        payload = _decode_error(exc)
        raise FacebookOAuthError(_meta_error_message(payload, exc.code)) from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise FacebookOAuthError("Facebook 연결 중 네트워크 오류가 발생했습니다.") from exc
    except json.JSONDecodeError as exc:
        raise FacebookOAuthError("Facebook 응답을 해석하지 못했습니다.") from exc


def _decode_error(error: urllib.error.HTTPError) -> dict[str, Any]:
    try:
        raw_body = error.read().decode("utf-8")
        return json.loads(raw_body) if raw_body else {}
    except Exception:
        return {"error": {"message": str(error)}}


def _meta_error_message(payload: dict[str, Any], status_code: int) -> str:
    error = payload.get("error") if isinstance(payload, dict) else {}
    message = error.get("message") if isinstance(error, dict) else ""
    if status_code in {401, 403}:
        return f"Facebook 권한을 확인해주세요. {message}".strip()
    return f"Facebook 연결 요청이 실패했습니다. {message}".strip()


def _graph_version() -> str:
    return (get_settings().meta_graph_version.strip() or "v25.0").lstrip("/")


def _first_text(source: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _account_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "user_id": int(row["user_id"]),
        "provider": row["provider"],
        "page_id": row["page_id"],
        "ig_user_id": row["ig_user_id"],
        "display_name": row["display_name"],
        "ig_username": row["ig_username"],
        "facebook_user_id": row["facebook_user_id"],
        "webhook_subscribed": bool(row["webhook_subscribed"]),
        "webhook_status": row["webhook_status"],
        "last_error": row["last_error"],
        "token_updated_at": row["token_updated_at"],
        "active": bool(row["active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
