from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .billing import get_seed_user_id, grant_purchased_tokens
from .config import get_settings
from .database import get_connection, utc_now

PORTONE_API_BASE_URL = "https://api.portone.io"
DEFAULT_TIMEOUT_SECONDS = 8
PAID_STATUSES = {"PAID", "PAID_PAYMENT", "SUCCESS", "Success", "paid", "success"}
FAILED_STATUSES = {"FAILED", "FAIL", "failed", "FAILURE", "PAYMENT_FAILED"}
CANCELLED_STATUSES = {"CANCELLED", "CANCELED", "cancelled", "canceled", "CANCEL"}


@dataclass
class PaymentVerificationError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def list_checkout_products() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, code, name, token_amount, price_krw
            FROM token_products
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_checkout_order(product_id: int, user_id: int | None = None) -> dict[str, Any]:
    user_id = user_id or get_seed_user_id()
    settings = get_settings()
    _ensure_token_purchase_allowed(user_id)
    product = _get_token_product(product_id)
    order_ref = f"tokens-{product['id']}-{secrets.token_urlsafe(10)}"
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO payment_orders (
                user_id,
                token_product_id,
                order_ref,
                status,
                amount_krw,
                token_amount,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
            """,
            (
                user_id,
                product["id"],
                order_ref,
                product["price_krw"],
                product["token_amount"],
                now,
                now,
            ),
        )
        order_id = int(cursor.lastrowid)
    return {
        "order": get_payment_order(order_id),
        "payment_request": {
            "storeId": settings.portone_store_id,
            "channelKey": settings.portone_channel_key,
            "paymentId": order_ref,
            "orderName": f"{product['name']} 토큰팩",
            "totalAmount": product["price_krw"],
            "currency": "CURRENCY_KRW",
            "payMethod": "CARD",
            "noticeUrls": ["/billing/portone/webhook"],
        },
    }


def get_payment_order(order_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                payment_orders.*,
                token_products.name AS product_name,
                token_products.code AS product_code
            FROM payment_orders
            LEFT JOIN token_products ON token_products.id = payment_orders.token_product_id
            WHERE payment_orders.id = ?
            """,
            (order_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"Payment order does not exist: {order_id}")
    return _order_to_dict(row)


def list_recent_payment_orders(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                payment_orders.*,
                token_products.name AS product_name,
                token_products.code AS product_code
            FROM payment_orders
            LEFT JOIN token_products ON token_products.id = payment_orders.token_product_id
            WHERE payment_orders.user_id = ?
            ORDER BY payment_orders.id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [_order_to_dict(row) for row in rows]


def handle_portone_webhook(raw_body: bytes, headers: dict[str, str]) -> dict[str, Any]:
    payload = _load_json(raw_body)
    payment_id = _first_text(payload, "payment_id", "paymentId", "merchant_order_ref", "order_ref")
    transaction_id = _first_text(payload, "tx_id", "transaction_id", "transactionId")
    event_ref = _build_event_ref(payload, raw_body, payment_id, transaction_id)

    if not verify_portone_signature(raw_body, headers, payload):
        _record_payment_event(
            event_ref=event_ref,
            payment_id=payment_id,
            transaction_id=transaction_id,
            status="signature_failed",
            raw_payload_json=_json_dumps(payload),
            error_message="Webhook signature verification failed.",
        )
        return {"ok": False, "status": "signature_failed"}

    inserted = _record_payment_event(
        event_ref=event_ref,
        payment_id=payment_id,
        transaction_id=transaction_id,
        status="received",
        raw_payload_json=_json_dumps(payload),
    )
    if not inserted:
        return {"ok": True, "status": "duplicate", "payment_id": payment_id}

    if not payment_id:
        _update_event(event_ref, "failed", error_message="payment_id is missing.")
        return {"ok": False, "status": "failed", "error": "payment_id is missing."}

    try:
        payment = fetch_portone_payment(payment_id)
        result = verify_and_apply_payment(payment_id, transaction_id, payment, payload)
        _update_event(event_ref, result["status"], order_id=result.get("order_id"), error_message=result.get("error", ""))
        return result
    except Exception as exc:
        message = str(exc)
        _update_event(event_ref, "failed", error_message=message)
        return {"ok": False, "status": "failed", "payment_id": payment_id, "error": message}


def verify_and_apply_payment(
    payment_id: str,
    transaction_id: str,
    payment: dict[str, Any],
    webhook_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verified = _normalize_payment(payment, fallback_payment_id=payment_id, fallback_transaction_id=transaction_id)
    order = _find_order_for_payment(verified["payment_id"])
    raw_payload_json = _json_dumps(webhook_payload or {})

    if order["status"] == "paid":
        return {"ok": True, "status": "duplicate", "order_id": order["id"], "payment_id": verified["payment_id"]}

    if verified["status"] in CANCELLED_STATUSES:
        _mark_order_terminal(
            order_id=order["id"],
            status="cancelled",
            payment_id=verified["payment_id"],
            transaction_id=verified["transaction_id"],
            raw_webhook_json=raw_payload_json,
            failure_reason="결제가 취소되었습니다.",
        )
        return {"ok": True, "status": "cancelled", "order_id": order["id"], "payment_id": verified["payment_id"]}

    if verified["status"] in FAILED_STATUSES:
        _mark_order_terminal(
            order_id=order["id"],
            status="failed",
            payment_id=verified["payment_id"],
            transaction_id=verified["transaction_id"],
            raw_webhook_json=raw_payload_json,
            failure_reason="결제가 실패했습니다.",
        )
        return {"ok": True, "status": "failed", "order_id": order["id"], "payment_id": verified["payment_id"]}

    if verified["status"] not in PAID_STATUSES:
        return {"ok": True, "status": "pending", "order_id": order["id"], "payment_id": verified["payment_id"]}

    if verified["amount"] != order["amount_krw"]:
        _mark_order_terminal(
            order_id=order["id"],
            status="failed",
            payment_id=verified["payment_id"],
            transaction_id=verified["transaction_id"],
            raw_webhook_json=raw_payload_json,
            failure_reason="결제 금액이 주문 금액과 다릅니다.",
        )
        raise PaymentVerificationError("결제 금액이 주문 금액과 다릅니다.")

    grant = grant_purchased_tokens(
        order["user_id"],
        order["token_amount"],
        ref_id=f"payment:{verified['payment_id']}",
    )
    _mark_order_paid(
        order_id=order["id"],
        payment_id=verified["payment_id"],
        transaction_id=verified["transaction_id"],
        raw_webhook_json=raw_payload_json,
    )
    return {
        "ok": True,
        "status": "paid",
        "order_id": order["id"],
        "payment_id": verified["payment_id"],
        "granted": bool(grant.get("granted")),
        "duplicate": bool(grant.get("duplicate")),
    }


def verify_portone_signature(raw_body: bytes, headers: dict[str, str], payload: dict[str, Any]) -> bool:
    secret = get_settings().portone_webhook_secret.strip()
    if not secret:
        return False
    normalized_headers = {key.lower(): value for key, value in headers.items()}
    candidates = [
        normalized_headers.get("x-portone-signature", ""),
        normalized_headers.get("portone-signature", ""),
        normalized_headers.get("x-webhook-signature", ""),
        _first_text(payload, "signature", "signature_hash"),
    ]
    expected_hex = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    expected_base64 = base64.b64encode(
        hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    ).decode("ascii")
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        if candidate.startswith("sha256="):
            candidate = candidate.removeprefix("sha256=")
        if hmac.compare_digest(candidate, expected_hex) or hmac.compare_digest(candidate, expected_base64):
            return True
    return False


def fetch_portone_payment(payment_id: str) -> dict[str, Any]:
    api_secret = get_settings().portone_api_secret.strip()
    if not api_secret:
        raise PaymentVerificationError("PORTONE_API_SECRET 값이 설정되어 있지 않습니다.")
    request = urllib.request.Request(
        f"{PORTONE_API_BASE_URL}/payments/{payment_id}",
        method="GET",
        headers={"Authorization": f"PortOne {api_secret}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            return _load_json(response.read())
    except urllib.error.HTTPError as exc:
        raise PaymentVerificationError(f"PortOne 결제 조회에 실패했습니다. HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise PaymentVerificationError("PortOne 결제 조회에 연결하지 못했습니다.") from exc


def _get_token_product(product_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, code, name, token_amount, price_krw
            FROM token_products
            WHERE id = ? AND is_active = 1
            """,
            (product_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"Token product does not exist: {product_id}")
    return dict(row)


def _ensure_token_purchase_allowed(user_id: int) -> None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT subscription_plans.allow_token_purchase
            FROM users
            JOIN subscription_plans ON subscription_plans.id = users.current_plan_id
            WHERE users.id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"User does not exist: {user_id}")
    if not bool(row["allow_token_purchase"]):
        raise PermissionError("Current plan does not allow token purchases.")


def _find_order_for_payment(payment_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM payment_orders
            WHERE order_ref = ? OR payment_id = ?
            ORDER BY id
            LIMIT 1
            """,
            (payment_id, payment_id),
        ).fetchone()
    if row is None:
        raise PaymentVerificationError("주문을 찾을 수 없습니다.")
    return dict(row)


def _mark_order_paid(
    *,
    order_id: int,
    payment_id: str,
    transaction_id: str,
    raw_webhook_json: str,
) -> None:
    now = utc_now()
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE payment_orders
            SET status = 'paid',
                payment_id = ?,
                transaction_id = ?,
                raw_webhook_json = ?,
                failure_reason = '',
                updated_at = ?,
                paid_at = COALESCE(paid_at, ?)
            WHERE id = ? AND status != 'paid'
            """,
            (payment_id, transaction_id, raw_webhook_json, now, now, order_id),
        )


def _mark_order_terminal(
    *,
    order_id: int,
    status: str,
    payment_id: str,
    transaction_id: str,
    raw_webhook_json: str,
    failure_reason: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE payment_orders
            SET status = ?,
                payment_id = ?,
                transaction_id = ?,
                raw_webhook_json = ?,
                failure_reason = ?,
                updated_at = ?
            WHERE id = ? AND status != 'paid'
            """,
            (status, payment_id, transaction_id, raw_webhook_json, failure_reason, utc_now(), order_id),
        )


def _record_payment_event(
    *,
    event_ref: str,
    payment_id: str,
    transaction_id: str,
    status: str,
    raw_payload_json: str,
    order_id: int | None = None,
    error_message: str = "",
) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO payment_events (
                provider,
                event_ref,
                order_id,
                payment_id,
                transaction_id,
                status,
                raw_payload_json,
                error_message,
                created_at
            )
            VALUES ('portone', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_ref, order_id, payment_id, transaction_id, status, raw_payload_json, error_message, utc_now()),
        )
    return cursor.rowcount == 1


def _update_event(event_ref: str, status: str, order_id: int | None = None, error_message: str = "") -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE payment_events
            SET status = ?,
                order_id = COALESCE(?, order_id),
                error_message = ?
            WHERE provider = 'portone' AND event_ref = ?
            """,
            (status, order_id, error_message, event_ref),
        )


def _normalize_payment(
    payload: dict[str, Any],
    *,
    fallback_payment_id: str,
    fallback_transaction_id: str,
) -> dict[str, Any]:
    payment = payload.get("payment") if isinstance(payload.get("payment"), dict) else payload
    payment_id = _first_text(payment, "id", "paymentId", "payment_id") or fallback_payment_id
    transaction = _primary_transaction(payment)
    status = _first_text(payment, "status") or _first_text(transaction, "status")
    transaction_id = _first_text(transaction, "id", "transactionId", "transaction_id") or fallback_transaction_id
    amount = _extract_amount(payment, transaction)
    if not payment_id:
        raise PaymentVerificationError("결제 ID가 없습니다.")
    return {
        "payment_id": payment_id,
        "transaction_id": transaction_id,
        "status": status,
        "amount": amount,
    }


def _primary_transaction(payment: dict[str, Any]) -> dict[str, Any]:
    transactions = payment.get("transactions")
    if isinstance(transactions, list):
        for transaction in transactions:
            if isinstance(transaction, dict) and transaction.get("is_primary") is True:
                return transaction
        for transaction in transactions:
            if isinstance(transaction, dict):
                return transaction
    return {}


def _extract_amount(payment: dict[str, Any], transaction: dict[str, Any]) -> int:
    for source in (transaction, payment):
        amount = source.get("amount")
        if isinstance(amount, dict):
            total = amount.get("total")
            if total is not None:
                return int(total)
        if amount is not None and not isinstance(amount, dict):
            return int(amount)
        total_amount = source.get("totalAmount") or source.get("total_amount")
        if total_amount is not None:
            return int(total_amount)
    raise PaymentVerificationError("결제 금액을 확인할 수 없습니다.")


def _build_event_ref(
    payload: dict[str, Any],
    raw_body: bytes,
    payment_id: str,
    transaction_id: str,
) -> str:
    explicit = _first_text(payload, "webhook_id", "webhookId", "event_id", "eventId")
    if explicit:
        return explicit
    if payment_id or transaction_id:
        status = _first_text(payload, "status", "type")
        return f"{payment_id}:{transaction_id}:{status}"
    return hashlib.sha256(raw_body).hexdigest()


def _load_json(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8") if raw else "{}")
    except json.JSONDecodeError as exc:
        raise PaymentVerificationError("Webhook JSON을 해석하지 못했습니다.") from exc
    if not isinstance(payload, dict):
        raise PaymentVerificationError("Webhook payload는 JSON 객체여야 합니다.")
    return payload


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


def _order_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "user_id": int(row["user_id"]),
        "token_product_id": row["token_product_id"],
        "product_name": row["product_name"] if "product_name" in row.keys() else "",
        "product_code": row["product_code"] if "product_code" in row.keys() else "",
        "order_ref": row["order_ref"],
        "status": row["status"],
        "amount_krw": int(row["amount_krw"]),
        "token_amount": int(row["token_amount"]),
        "payment_id": row["payment_id"],
        "transaction_id": row["transaction_id"],
        "failure_reason": row["failure_reason"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "paid_at": row["paid_at"],
    }
