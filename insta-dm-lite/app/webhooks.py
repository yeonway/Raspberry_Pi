from __future__ import annotations

import hmac
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from . import meta_api
from .automations import get_or_create_connected_account
from .billing import get_seed_user_id
from .comment_engine import enqueue_comment_for_processing
from .config import get_settings
from .database import get_connection, utc_now
from .facebook_oauth import get_page_access_token_for_identifiers
from .token_crypto import TokenCryptoError

PROVIDER_META = "meta"
DETAIL_FETCH_TIMEOUT_SECONDS = 3


@dataclass
class CommentEvent:
    comment_id: str
    media_id: str
    text: str
    account_id: str
    page_id: str
    ig_user_id: str


def handle_meta_webhook_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_payload_json = _json_dumps(payload)
    event_id = _build_event_id(payload, raw_payload_json)
    inserted = _insert_webhook_event(event_id, raw_payload_json)
    if not inserted:
        return {"status": "duplicate", "queued": False, "event_id": event_id}

    try:
        event = _extract_comment_event(payload)
        if event is None:
            _update_event_status(event_id, "skipped")
            return {"status": "skipped", "queued": False, "event_id": event_id}

        if not event.media_id or not event.text:
            event = _fill_missing_comment_detail(event)
        if not event.media_id or not event.text:
            _update_event_status(event_id, "skipped")
            return {
                "status": "skipped",
                "queued": False,
                "event_id": event_id,
                "comment_id": event.comment_id,
            }

        user_id = _resolve_user_id(event)
        result = enqueue_comment_for_processing(
            user_id=user_id,
            media_id=event.media_id,
            comment_id=event.comment_id,
            comment_text=event.text,
        )
        status = str(result.get("status", "queued"))
        _update_event_status(event_id, status)
        return {
            **result,
            "event_id": event_id,
            "comment_id": event.comment_id,
            "media_id": event.media_id,
        }
    except Exception as exc:
        _update_event_status(event_id, "failed")
        return {"status": "failed", "queued": False, "event_id": event_id, "error": str(exc)}


def _insert_webhook_event(event_id: str, raw_payload_json: str) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO webhook_events (
                provider,
                event_id,
                raw_payload_json,
                status,
                created_at
            )
            VALUES (?, ?, ?, 'received', ?)
            """,
            (PROVIDER_META, event_id, raw_payload_json, utc_now()),
        )
    return cursor.rowcount == 1


def _update_event_status(event_id: str, status: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE webhook_events
            SET status = ?
            WHERE provider = ? AND event_id = ?
            """,
            (status, PROVIDER_META, event_id),
        )


def _extract_comment_event(payload: dict[str, Any]) -> CommentEvent | None:
    entries = payload.get("entry")
    if not isinstance(entries, list):
        return None

    object_type = str(payload.get("object", "")).lower()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_account_id = str(entry.get("id", "")).strip()
        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict):
                continue
            field = str(change.get("field", "")).lower()
            value = change.get("value")
            if not isinstance(value, dict) or not _looks_like_comment_event(field, value):
                continue
            event = _event_from_change_value(value, object_type, entry_account_id)
            if event is not None:
                return event
    return None


def _looks_like_comment_event(field: str, value: dict[str, Any]) -> bool:
    if field in {"comments", "comment", "live_comments"}:
        return True
    if field == "feed" and (value.get("comment_id") or value.get("item") == "comment"):
        return True
    return bool(value.get("comment_id") and (value.get("media") or value.get("post_id") or value.get("text")))


def _event_from_change_value(
    value: dict[str, Any],
    object_type: str,
    entry_account_id: str,
) -> CommentEvent | None:
    comment_id = _first_text(value, "comment_id", "id")
    if not comment_id:
        return None

    media = value.get("media")
    media_id = ""
    if isinstance(media, dict):
        media_id = _first_text(media, "id")
    media_id = media_id or _first_text(value, "media_id", "post_id")
    text = _first_text(value, "text", "message", "comment_text")
    page_id = _first_text(value, "page_id")
    ig_user_id = _first_text(value, "ig_user_id", "instagram_business_account_id")

    if object_type == "page" and entry_account_id:
        page_id = page_id or entry_account_id
    if object_type == "instagram" and entry_account_id:
        ig_user_id = ig_user_id or entry_account_id

    return CommentEvent(
        comment_id=comment_id,
        media_id=media_id,
        text=text,
        account_id=entry_account_id,
        page_id=page_id,
        ig_user_id=ig_user_id,
    )


def _fill_missing_comment_detail(event: CommentEvent) -> CommentEvent:
    try:
        access_token = _get_event_access_token(event)
        detail = meta_api.get_comment_detail(
            event.comment_id,
            timeout_seconds=DETAIL_FETCH_TIMEOUT_SECONDS,
            access_token=access_token,
        )
    except Exception:
        return event

    media = detail.get("media")
    media_id = event.media_id
    if not media_id and isinstance(media, dict):
        media_id = _first_text(media, "id")
    return CommentEvent(
        comment_id=event.comment_id,
        media_id=media_id,
        text=event.text or _first_text(detail, "text", "message"),
        account_id=event.account_id,
        page_id=event.page_id,
        ig_user_id=event.ig_user_id,
    )


def _get_event_access_token(event: CommentEvent) -> str:
    try:
        return get_page_access_token_for_identifiers(event.account_id, event.page_id, event.ig_user_id)
    except TokenCryptoError:
        return ""


def _resolve_user_id(event: CommentEvent) -> int:
    account_ids = {event.account_id, event.page_id, event.ig_user_id}
    account_ids = {item for item in account_ids if item}
    if account_ids:
        with get_connection() as connection:
            placeholders = ",".join("?" for _ in account_ids)
            row = connection.execute(
                f"""
                SELECT user_id
                FROM connected_accounts
                WHERE provider = 'meta'
                  AND active = 1
                  AND (page_id IN ({placeholders}) OR ig_user_id IN ({placeholders}))
                ORDER BY id
                LIMIT 1
                """,
                (*account_ids, *account_ids),
            ).fetchone()
        if row is not None:
            return int(row["user_id"])

    user_id = get_seed_user_id()
    get_or_create_connected_account(user_id)
    return user_id


def _build_event_id(payload: dict[str, Any], raw_payload_json: str) -> str:
    candidate = _extract_event_id_candidate(payload)
    if candidate:
        return candidate
    return f"payload:{hashlib.sha256(raw_payload_json.encode('utf-8')).hexdigest()}"


def _extract_event_id_candidate(payload: dict[str, Any]) -> str:
    entries = payload.get("entry")
    if not isinstance(entries, list):
        return ""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id", "")).strip()
        entry_time = str(entry.get("time", "")).strip()
        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue
        for index, change in enumerate(changes):
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            comment_id = _first_text(value, "comment_id", "id")
            if comment_id:
                field = str(change.get("field", "")).strip() or "unknown"
                return f"{entry_id}:{entry_time}:{field}:{comment_id}"
            change_id = _first_text(value, "event_id", "mid")
            if change_id:
                return f"{entry_id}:{entry_time}:{change_id}"
            if entry_id or entry_time:
                return f"{entry_id}:{entry_time}:change:{index}"
    return ""


def _first_text(source: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def verify_meta_challenge(mode: str, verify_token: str, challenge: str) -> str | None:
    settings = get_settings()
    expected_token = settings.meta_webhook_verify_token.strip()
    if mode == "subscribe" and expected_token and verify_token == expected_token:
        return challenge
    return None


def verify_meta_request_signature(raw_body: bytes, headers: Any) -> bool:
    settings = get_settings()
    if not settings.meta_webhook_verify_signature:
        return True

    app_secret = settings.facebook_app_secret.strip()
    if not app_secret:
        return False

    signature_header = _get_header(headers, "x-hub-signature-256")
    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False

    received_signature = signature_header[len(prefix) :]
    if not received_signature:
        return False

    expected_signature = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(received_signature, expected_signature)


def _get_header(headers: Any, name: str) -> str:
    if hasattr(headers, "get"):
        value = headers.get(name)
        if value:
            return str(value).strip()

    lowered_name = name.lower()
    try:
        items = headers.items()
    except AttributeError:
        return ""
    for key, value in items:
        if str(key).lower() == lowered_name:
            return str(value).strip()
    return ""
