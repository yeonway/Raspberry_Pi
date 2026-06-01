from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import get_settings
from .database import get_connection, utc_now

GRAPH_BASE_URL = "https://graph.facebook.com"
DEFAULT_TIMEOUT_SECONDS = 12


@dataclass
class MetaApiError(Exception):
    user_message: str
    endpoint: str
    method: str
    status_code: int | None = None
    error_payload: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.user_message


def get_media_list(ig_user_id: str | None = None, access_token: str | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    ig_user_id = (ig_user_id or settings.meta_ig_user_id).strip()
    _require_setting(ig_user_id, "META_IG_USER_ID")
    payload = _graph_request(
        "GET",
        f"/{ig_user_id}/media",
        params={
            "fields": "id,caption,media_type,media_url,permalink,timestamp,comments_count",
            "limit": 25,
        },
        access_token=access_token or "",
    )
    return payload.get("data", [])


def get_comments(media_id: str, access_token: str | None = None) -> list[dict[str, Any]]:
    media_id = _require_identifier(media_id, "media_id")
    payload = _graph_request(
        "GET",
        f"/{media_id}/comments",
        params={
            "fields": "id,text,username,timestamp,like_count,replies{id,text,username,timestamp}",
            "limit": 50,
        },
        access_token=access_token or "",
    )
    return payload.get("data", [])


def get_comment_detail(comment_id: str, *, timeout_seconds: int = 3, access_token: str | None = None) -> dict[str, Any]:
    comment_id = _require_identifier(comment_id, "comment_id")
    return _graph_request(
        "GET",
        f"/{comment_id}",
        params={
            "fields": "id,text,media{id,caption,media_type,permalink}",
        },
        timeout_seconds=timeout_seconds,
        access_token=access_token or "",
    )


def reply_to_comment(comment_id: str, message: str, access_token: str | None = None) -> dict[str, Any]:
    comment_id = _require_identifier(comment_id, "comment_id")
    message = _require_message(message, "message")
    return _graph_request(
        "POST",
        f"/{comment_id}/replies",
        data={"message": message},
        access_token=access_token or "",
    )


def send_private_reply(
    page_id: str,
    comment_id: str,
    text: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
    access_token: str | None = None,
) -> dict[str, Any]:
    page_id = _require_identifier(page_id, "page_id")
    comment_id = _require_identifier(comment_id, "comment_id")
    payload = build_cta_payload(text, cta_label, cta_url)
    return _graph_request(
        "POST",
        f"/{page_id}/messages",
        data={
            "recipient": json.dumps({"comment_id": comment_id}, ensure_ascii=False),
            "message": json.dumps(payload, ensure_ascii=False),
        },
        access_token=access_token or "",
    )


def build_cta_payload(
    text: str,
    cta_label: str | None,
    cta_url: str | None,
) -> dict[str, Any]:
    text = _require_message(text, "text")
    cta_label = (cta_label or "").strip()
    cta_url = (cta_url or "").strip()
    if not cta_label and not cta_url:
        return {"text": text}
    if not cta_label or not cta_url:
        raise ValueError("CTA label and URL must be provided together.")
    return {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "button",
                "text": text,
                "buttons": [
                    {
                        "type": "web_url",
                        "url": cta_url,
                        "title": cta_label,
                    }
                ],
            },
        }
    }


def get_latest_meta_api_failure() -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT endpoint, method, status_code, user_message, error_payload, created_at
            FROM meta_api_failures
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "endpoint": row["endpoint"],
        "method": row["method"],
        "status_code": row["status_code"],
        "user_message": row["user_message"],
        "error_payload": json.loads(row["error_payload"]),
        "created_at": row["created_at"],
    }


def _graph_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    access_token: str = "",
) -> dict[str, Any]:
    settings = get_settings()
    token = (access_token or settings.meta_page_access_token).strip()
    _require_setting(token, "META_PAGE_ACCESS_TOKEN")

    version = settings.meta_graph_version.strip() or "v25.0"
    endpoint = f"/{version}{path}"
    request_params = dict(params or {})
    request_params["access_token"] = token
    url = f"{GRAPH_BASE_URL}{endpoint}"
    if method == "GET":
        url = f"{url}?{urllib.parse.urlencode(request_params)}"
        body = None
    else:
        body_params = dict(data or {})
        body_params["access_token"] = token
        body = urllib.parse.urlencode(body_params).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as error:
        payload = _decode_error_payload(error)
        raise _record_and_build_error(
            endpoint=endpoint,
            method=method,
            status_code=error.code,
            payload=payload,
        ) from error
    except (urllib.error.URLError, TimeoutError, socket.timeout) as error:
        payload = {"error": {"message": str(error), "type": error.__class__.__name__}}
        raise _record_and_build_error(
            endpoint=endpoint,
            method=method,
            status_code=None,
            payload=payload,
            user_message="Meta API에 연결하지 못했습니다. 네트워크 상태와 토큰 설정을 확인하세요.",
        ) from error
    except json.JSONDecodeError as error:
        payload = {"error": {"message": "Invalid JSON response", "type": "JSONDecodeError"}}
        raise _record_and_build_error(
            endpoint=endpoint,
            method=method,
            status_code=None,
            payload=payload,
            user_message="Meta API 응답을 해석하지 못했습니다.",
        ) from error


def _decode_error_payload(error: urllib.error.HTTPError) -> dict[str, Any]:
    try:
        raw_body = error.read().decode("utf-8")
    except Exception:
        raw_body = ""
    if not raw_body:
        return {"error": {"message": error.reason, "type": "HTTPError"}}
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return {"error": {"message": raw_body, "type": "HTTPError"}}


def _record_and_build_error(
    *,
    endpoint: str,
    method: str,
    status_code: int | None,
    payload: dict[str, Any],
    user_message: str | None = None,
) -> MetaApiError:
    message = user_message or _build_user_message(status_code, payload)
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO meta_api_failures (
                endpoint,
                method,
                status_code,
                user_message,
                error_payload,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                endpoint,
                method,
                status_code,
                message,
                json.dumps(payload, ensure_ascii=False),
                utc_now(),
            ),
        )
    return MetaApiError(
        user_message=message,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        error_payload=payload,
    )


def _build_user_message(status_code: int | None, payload: dict[str, Any]) -> str:
    error = payload.get("error", {})
    meta_message = error.get("message")
    if status_code == 400:
        return f"Meta API 요청 값이 올바르지 않습니다. {meta_message or ''}".strip()
    if status_code in (401, 403):
        return f"Meta API 권한 또는 토큰을 확인해야 합니다. {meta_message or ''}".strip()
    if status_code == 429:
        return "Meta API 호출 한도를 초과했습니다. 잠시 뒤 다시 시도하세요."
    if status_code is not None and status_code >= 500:
        return "Meta API 서버 오류가 발생했습니다. 잠시 뒤 다시 시도하세요."
    return f"Meta API 호출에 실패했습니다. {meta_message or ''}".strip()


def _require_setting(value: str, name: str) -> None:
    if not value.strip():
        raise MetaApiError(
            user_message=f"{name} 값이 .env에 설정되어 있지 않습니다.",
            endpoint="local_config",
            method="CONFIG",
            status_code=None,
            error_payload={"missing": name},
        )


def _require_identifier(value: str, name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value


def _require_message(value: str, name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value
