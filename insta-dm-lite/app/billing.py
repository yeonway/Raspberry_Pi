from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from .database import SEED_ADMIN_USERNAME, get_connection, utc_now


@dataclass(frozen=True)
class ReservationResult:
    ok: bool
    reserved: bool
    duplicate: bool
    ref_id: str
    status: str
    source: str = ""
    error: str = ""
    balance: dict | None = None


def get_current_period() -> str:
    return datetime.now().strftime("%Y-%m")


def get_seed_user_id() -> int:
    with get_connection() as connection:
        return _get_seed_user_id(connection)


def list_subscription_plans() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                code,
                name,
                monthly_price_krw,
                monthly_credits,
                automation_account_limit,
                automation_rule_limit,
                allow_token_purchase,
                allow_cta_button,
                log_retention_days
            FROM subscription_plans
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
    return [_plan_row_to_dict(row) for row in rows]


def list_token_products() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, code, name, token_amount, price_krw
            FROM token_products
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
    return [_token_product_row_to_dict(row) for row in rows]


def grant_monthly_credits(user_id: int) -> dict:
    period = get_current_period()
    ref_id = f"monthly:{period}"

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        user_plan = _get_user_plan(connection, user_id)
        balance = _ensure_usage_balance(connection, user_id, period)

        existing = _get_ledger_entry(connection, user_id, ref_id, "monthly_grant")
        if existing is not None:
            connection.commit()
            return {
                "ok": True,
                "granted": False,
                "duplicate": True,
                "ref_id": ref_id,
                "balance": _get_usage_balance_for_user(connection, user_id),
            }

        monthly_remaining = int(user_plan["monthly_credits"])
        purchased_remaining = int(balance["purchased_remaining"])
        monthly_delta = monthly_remaining - int(balance["monthly_remaining"])
        now = utc_now()

        connection.execute(
            """
            UPDATE usage_balances
            SET current_period = ?, monthly_remaining = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (period, monthly_remaining, now, user_id),
        )
        _insert_ledger_entry(
            connection=connection,
            user_id=user_id,
            ref_id=ref_id,
            entry_type="monthly_grant",
            reason="monthly_credit_reset",
            monthly_delta=monthly_delta,
            purchased_delta=0,
            balance_monthly_after=monthly_remaining,
            balance_purchased_after=purchased_remaining,
        )
        connection.commit()
        return {
            "ok": True,
            "granted": True,
            "duplicate": False,
            "ref_id": ref_id,
            "monthly_delta": monthly_delta,
            "balance": _get_usage_balance_for_user(connection, user_id),
        }


def grant_purchased_tokens(user_id: int, amount: int, ref_id: str) -> dict:
    _validate_positive_amount(amount)
    ref_id = _validate_ref_id(ref_id)

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _get_user_plan(connection, user_id)
        balance = _ensure_usage_balance(connection, user_id, get_current_period())

        existing = _get_ledger_entry(connection, user_id, ref_id, "purchase_grant")
        if existing is not None:
            connection.commit()
            return {
                "ok": True,
                "granted": False,
                "duplicate": True,
                "ref_id": ref_id,
                "balance": _get_usage_balance_for_user(connection, user_id),
            }

        monthly_remaining = int(balance["monthly_remaining"])
        purchased_remaining = int(balance["purchased_remaining"]) + amount
        now = utc_now()

        connection.execute(
            """
            UPDATE usage_balances
            SET purchased_remaining = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (purchased_remaining, now, user_id),
        )
        _insert_ledger_entry(
            connection=connection,
            user_id=user_id,
            ref_id=ref_id,
            entry_type="purchase_grant",
            reason="seed_token_grant",
            monthly_delta=0,
            purchased_delta=amount,
            balance_monthly_after=monthly_remaining,
            balance_purchased_after=purchased_remaining,
        )
        connection.commit()
        return {
            "ok": True,
            "granted": True,
            "duplicate": False,
            "ref_id": ref_id,
            "purchased_delta": amount,
            "balance": _get_usage_balance_for_user(connection, user_id),
        }


def consume_one_credit(user_id: int, ref_id: str, reason: str) -> dict:
    ref_id = _validate_ref_id(ref_id)
    reason = reason.strip()
    if not reason:
        raise ValueError("reason is required.")

    grant_monthly_credits(user_id)

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _get_user_plan(connection, user_id)
        balance = _ensure_usage_balance(connection, user_id, get_current_period())

        existing = _get_successful_consumption(connection, user_id, ref_id)
        if existing is not None:
            connection.commit()
            return {
                "ok": True,
                "consumed": False,
                "duplicate": True,
                "ref_id": ref_id,
                "source": _source_from_entry_type(existing["entry_type"]),
                "balance": _get_usage_balance_for_user(connection, user_id),
            }

        monthly_remaining = int(balance["monthly_remaining"])
        purchased_remaining = int(balance["purchased_remaining"])

        if monthly_remaining > 0:
            monthly_remaining -= 1
            entry_type = "consume_monthly"
            monthly_delta = -1
            purchased_delta = 0
            source = "monthly"
        elif purchased_remaining > 0:
            purchased_remaining -= 1
            entry_type = "consume_purchased"
            monthly_delta = 0
            purchased_delta = -1
            source = "purchased"
        else:
            _insert_failed_consumption_if_missing(
                connection=connection,
                user_id=user_id,
                ref_id=ref_id,
                reason=reason,
                monthly_remaining=monthly_remaining,
                purchased_remaining=purchased_remaining,
            )
            connection.commit()
            return {
                "ok": False,
                "consumed": False,
                "duplicate": False,
                "error": "insufficient_credit",
                "ref_id": ref_id,
                "balance": _get_usage_balance_for_user(connection, user_id),
            }

        now = utc_now()
        connection.execute(
            """
            UPDATE usage_balances
            SET monthly_remaining = ?,
                purchased_remaining = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (monthly_remaining, purchased_remaining, now, user_id),
        )
        _insert_ledger_entry(
            connection=connection,
            user_id=user_id,
            ref_id=ref_id,
            entry_type=entry_type,
            reason=reason,
            monthly_delta=monthly_delta,
            purchased_delta=purchased_delta,
            balance_monthly_after=monthly_remaining,
            balance_purchased_after=purchased_remaining,
        )
        connection.commit()
        return {
            "ok": True,
            "consumed": True,
            "duplicate": False,
            "ref_id": ref_id,
            "source": source,
            "balance": _get_usage_balance_for_user(connection, user_id),
        }


def reserve_one_credit(user_id: int, ref_id: str, reason: str) -> ReservationResult:
    ref_id = _validate_ref_id(ref_id)
    reason = _validate_reason(reason)
    grant_monthly_credits(user_id)

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _get_user_plan(connection, user_id)
        balance = _ensure_usage_balance(connection, user_id, get_current_period())

        committed_consumption = _get_successful_consumption(connection, user_id, ref_id)
        if committed_consumption is not None:
            connection.commit()
            return ReservationResult(
                ok=True,
                reserved=False,
                duplicate=True,
                ref_id=ref_id,
                status="committed",
                source=_source_from_entry_type(committed_consumption["entry_type"]),
                balance=_get_usage_balance_for_user(connection, user_id),
            )

        existing = _get_reservation(connection, user_id, ref_id)
        if existing is not None and existing["status"] == "reserved":
            connection.commit()
            return ReservationResult(
                ok=True,
                reserved=False,
                duplicate=True,
                ref_id=ref_id,
                status="reserved",
                source=existing["source"],
                balance=_get_usage_balance_for_user(connection, user_id),
            )
        if existing is not None and existing["status"] == "committed":
            connection.commit()
            return ReservationResult(
                ok=True,
                reserved=False,
                duplicate=True,
                ref_id=ref_id,
                status="committed",
                source=existing["source"],
                balance=_get_usage_balance_for_user(connection, user_id),
            )

        monthly_remaining = int(balance["monthly_remaining"])
        purchased_remaining = int(balance["purchased_remaining"])
        if monthly_remaining > 0:
            monthly_remaining -= 1
            source = "monthly"
        elif purchased_remaining > 0:
            purchased_remaining -= 1
            source = "purchased"
        else:
            _insert_failed_consumption_if_missing(
                connection=connection,
                user_id=user_id,
                ref_id=ref_id,
                reason=reason,
                monthly_remaining=monthly_remaining,
                purchased_remaining=purchased_remaining,
            )
            connection.commit()
            return ReservationResult(
                ok=False,
                reserved=False,
                duplicate=False,
                ref_id=ref_id,
                status="failed",
                error="insufficient_credit",
                balance=_get_usage_balance_for_user(connection, user_id),
            )

        now = utc_now()
        connection.execute(
            """
            UPDATE usage_balances
            SET monthly_remaining = ?,
                purchased_remaining = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (monthly_remaining, purchased_remaining, now, user_id),
        )
        if existing is None:
            connection.execute(
                """
                INSERT INTO credit_reservations (
                    user_id,
                    ref_id,
                    source,
                    amount,
                    status,
                    reason,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 1, 'reserved', ?, ?, ?)
                """,
                (user_id, ref_id, source, reason, now, now),
            )
        else:
            connection.execute(
                """
                UPDATE credit_reservations
                SET source = ?,
                    amount = 1,
                    status = 'reserved',
                    reason = ?,
                    updated_at = ?
                WHERE user_id = ? AND ref_id = ?
                """,
                (source, reason, now, user_id, ref_id),
            )
        connection.commit()
        return ReservationResult(
            ok=True,
            reserved=True,
            duplicate=False,
            ref_id=ref_id,
            status="reserved",
            source=source,
            balance=_get_usage_balance_for_user(connection, user_id),
        )


def commit_reserved_credit(user_id: int, ref_id: str) -> bool:
    ref_id = _validate_ref_id(ref_id)
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        reservation = _get_reservation(connection, user_id, ref_id)
        if reservation is None:
            return _get_successful_consumption(connection, user_id, ref_id) is not None
        if reservation["status"] == "committed":
            return True
        if reservation["status"] == "released":
            return False

        balance = _ensure_usage_balance(connection, user_id, get_current_period())
        entry_type = "consume_monthly" if reservation["source"] == "monthly" else "consume_purchased"
        existing_consumption = _get_successful_consumption(connection, user_id, ref_id)
        if existing_consumption is None:
            _insert_ledger_entry(
                connection=connection,
                user_id=user_id,
                ref_id=ref_id,
                entry_type=entry_type,
                reason=reservation["reason"],
                monthly_delta=-1 if reservation["source"] == "monthly" else 0,
                purchased_delta=-1 if reservation["source"] == "purchased" else 0,
                balance_monthly_after=int(balance["monthly_remaining"]),
                balance_purchased_after=int(balance["purchased_remaining"]),
            )
        connection.execute(
            """
            UPDATE credit_reservations
            SET status = 'committed',
                updated_at = ?
            WHERE user_id = ? AND ref_id = ?
            """,
            (utc_now(), user_id, ref_id),
        )
        connection.commit()
        return True


def release_reserved_credit(user_id: int, ref_id: str, reason: str) -> bool:
    ref_id = _validate_ref_id(ref_id)
    reason = _validate_reason(reason)
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        reservation = _get_reservation(connection, user_id, ref_id)
        if reservation is None:
            return False
        if reservation["status"] == "released":
            return True
        if reservation["status"] == "committed":
            return False

        balance = _ensure_usage_balance(connection, user_id, get_current_period())
        monthly_remaining = int(balance["monthly_remaining"])
        purchased_remaining = int(balance["purchased_remaining"])
        if reservation["source"] == "monthly":
            monthly_remaining += int(reservation["amount"])
        else:
            purchased_remaining += int(reservation["amount"])
        now = utc_now()
        connection.execute(
            """
            UPDATE usage_balances
            SET monthly_remaining = ?,
                purchased_remaining = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (monthly_remaining, purchased_remaining, now, user_id),
        )
        connection.execute(
            """
            UPDATE credit_reservations
            SET status = 'released',
                reason = ?,
                updated_at = ?
            WHERE user_id = ? AND ref_id = ?
            """,
            (reason, now, user_id, ref_id),
        )
        connection.commit()
        return True


def get_available_credit(user_id: int) -> int:
    grant_monthly_credits(user_id)
    balance = get_usage_balance(user_id)
    return int(balance["monthly_remaining"]) + int(balance["purchased_remaining"])


def get_usage_balance(user_id: int) -> dict:
    with get_connection() as connection:
        _ensure_usage_balance(connection, user_id, get_current_period())
        connection.commit()
        return _get_usage_balance_for_user(connection, user_id)


def has_available_credit(user_id: int) -> bool:
    return get_available_credit(user_id) > 0


def _get_seed_user_id(connection: sqlite3.Connection) -> int:
    row = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (SEED_ADMIN_USERNAME,),
    ).fetchone()
    if row is None:
        raise ValueError("Seed admin user does not exist. Run initialize_database() first.")
    return int(row["id"])


def _get_user_plan(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT
            users.id AS user_id,
            users.username,
            users.display_name,
            subscription_plans.code AS plan_code,
            subscription_plans.name AS plan_name,
            subscription_plans.monthly_price_krw,
            subscription_plans.monthly_credits,
            subscription_plans.automation_account_limit,
            subscription_plans.automation_rule_limit,
            subscription_plans.allow_token_purchase,
            subscription_plans.allow_cta_button,
            subscription_plans.log_retention_days
        FROM users
        JOIN subscription_plans ON subscription_plans.id = users.current_plan_id
        WHERE users.id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"User does not exist: {user_id}")
    return row


def _ensure_usage_balance(
    connection: sqlite3.Connection,
    user_id: int,
    period: str,
) -> sqlite3.Row:
    _get_user_plan(connection, user_id)
    row = connection.execute(
        """
        SELECT user_id, current_period, monthly_remaining, purchased_remaining, updated_at
        FROM usage_balances
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is not None:
        return row

    now = utc_now()
    connection.execute(
        """
        INSERT INTO usage_balances (
            user_id,
            current_period,
            monthly_remaining,
            purchased_remaining,
            updated_at
        )
        VALUES (?, ?, 0, 0, ?)
        """,
        (user_id, period, now),
    )
    return connection.execute(
        """
        SELECT user_id, current_period, monthly_remaining, purchased_remaining, updated_at
        FROM usage_balances
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()


def _get_usage_balance_for_user(connection: sqlite3.Connection, user_id: int) -> dict:
    row = connection.execute(
        """
        SELECT
            usage_balances.current_period,
            usage_balances.monthly_remaining,
            usage_balances.purchased_remaining,
            usage_balances.updated_at,
            users.id AS user_id,
            users.username,
            users.display_name,
            subscription_plans.code AS plan_code,
            subscription_plans.name AS plan_name,
            subscription_plans.monthly_price_krw,
            subscription_plans.monthly_credits,
            subscription_plans.automation_account_limit,
            subscription_plans.automation_rule_limit,
            subscription_plans.allow_token_purchase,
            subscription_plans.allow_cta_button,
            subscription_plans.log_retention_days
        FROM usage_balances
        JOIN users ON users.id = usage_balances.user_id
        JOIN subscription_plans ON subscription_plans.id = users.current_plan_id
        WHERE usage_balances.user_id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Usage balance does not exist for user: {user_id}")

    return {
        "user_id": int(row["user_id"]),
        "username": row["username"],
        "display_name": row["display_name"],
        "current_period": row["current_period"],
        "monthly_remaining": int(row["monthly_remaining"]),
        "purchased_remaining": int(row["purchased_remaining"]),
        "updated_at": row["updated_at"],
        "plan": {
            "code": row["plan_code"],
            "name": row["plan_name"],
            "monthly_price_krw": int(row["monthly_price_krw"]),
            "monthly_credits": int(row["monthly_credits"]),
            "automation_account_limit": int(row["automation_account_limit"]),
            "automation_rule_limit": int(row["automation_rule_limit"]),
            "allow_token_purchase": bool(row["allow_token_purchase"]),
            "allow_cta_button": bool(row["allow_cta_button"]),
            "log_retention_days": int(row["log_retention_days"]),
        },
    }


def _insert_ledger_entry(
    *,
    connection: sqlite3.Connection,
    user_id: int,
    ref_id: str,
    entry_type: str,
    reason: str,
    monthly_delta: int,
    purchased_delta: int,
    balance_monthly_after: int,
    balance_purchased_after: int,
) -> None:
    connection.execute(
        """
        INSERT INTO credit_ledger (
            user_id,
            ref_id,
            entry_type,
            reason,
            monthly_delta,
            purchased_delta,
            balance_monthly_after,
            balance_purchased_after,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            ref_id,
            entry_type,
            reason,
            monthly_delta,
            purchased_delta,
            balance_monthly_after,
            balance_purchased_after,
            utc_now(),
        ),
    )


def _insert_failed_consumption_if_missing(
    *,
    connection: sqlite3.Connection,
    user_id: int,
    ref_id: str,
    reason: str,
    monthly_remaining: int,
    purchased_remaining: int,
) -> None:
    existing = _get_ledger_entry(connection, user_id, ref_id, "consume_failed")
    if existing is not None:
        return
    _insert_ledger_entry(
        connection=connection,
        user_id=user_id,
        ref_id=ref_id,
        entry_type="consume_failed",
        reason=reason,
        monthly_delta=0,
        purchased_delta=0,
        balance_monthly_after=monthly_remaining,
        balance_purchased_after=purchased_remaining,
    )


def _get_ledger_entry(
    connection: sqlite3.Connection,
    user_id: int,
    ref_id: str,
    entry_type: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM credit_ledger
        WHERE user_id = ? AND ref_id = ? AND entry_type = ?
        """,
        (user_id, ref_id, entry_type),
    ).fetchone()


def _get_successful_consumption(
    connection: sqlite3.Connection,
    user_id: int,
    ref_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM credit_ledger
        WHERE user_id = ?
          AND ref_id = ?
          AND entry_type IN ('consume_monthly', 'consume_purchased')
        ORDER BY id
        LIMIT 1
        """,
        (user_id, ref_id),
    ).fetchone()


def _get_reservation(
    connection: sqlite3.Connection,
    user_id: int,
    ref_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM credit_reservations
        WHERE user_id = ? AND ref_id = ?
        """,
        (user_id, ref_id),
    ).fetchone()


def _source_from_entry_type(entry_type: str) -> str:
    if entry_type == "consume_monthly":
        return "monthly"
    if entry_type == "consume_purchased":
        return "purchased"
    return "unknown"


def _plan_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "code": row["code"],
        "name": row["name"],
        "monthly_price_krw": int(row["monthly_price_krw"]),
        "monthly_credits": int(row["monthly_credits"]),
        "automation_account_limit": int(row["automation_account_limit"]),
        "automation_rule_limit": int(row["automation_rule_limit"]),
        "allow_token_purchase": bool(row["allow_token_purchase"]),
        "allow_cta_button": bool(row["allow_cta_button"]),
        "log_retention_days": int(row["log_retention_days"]),
    }


def _token_product_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": int(row["id"]),
        "code": row["code"],
        "name": row["name"],
        "token_amount": int(row["token_amount"]),
        "price_krw": int(row["price_krw"]),
    }


def _validate_positive_amount(amount: int) -> None:
    if amount <= 0:
        raise ValueError("amount must be greater than 0.")


def _validate_ref_id(ref_id: str) -> str:
    ref_id = ref_id.strip()
    if not ref_id:
        raise ValueError("ref_id is required.")
    return ref_id


def _validate_reason(reason: str) -> str:
    reason = reason.strip()
    if not reason:
        raise ValueError("reason is required.")
    return reason
