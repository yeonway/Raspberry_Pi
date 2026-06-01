import os
import unittest
import uuid
from pathlib import Path

from app.billing import (
    commit_reserved_credit,
    consume_one_credit,
    get_available_credit,
    get_seed_user_id,
    get_usage_balance,
    grant_monthly_credits,
    grant_purchased_tokens,
    has_available_credit,
    release_reserved_credit,
    reserve_one_credit,
)
from app.config import get_settings
from app.database import get_connection, initialize_database


class BillingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.database_path = Path.cwd() / "data" / f"test-{uuid.uuid4().hex}.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path}"
        get_settings.cache_clear()
        initialize_database()
        self.user_id = get_seed_user_id()

    def tearDown(self) -> None:
        get_settings.cache_clear()
        os.environ.pop("DATABASE_URL", None)
        if self.database_path.exists():
            self.database_path.unlink()

    def test_seed_data_is_created(self) -> None:
        with get_connection() as connection:
            plans = connection.execute(
                """
                SELECT code, monthly_price_krw, monthly_credits, automation_account_limit,
                       automation_rule_limit, allow_token_purchase, allow_cta_button,
                       log_retention_days
                FROM subscription_plans
                ORDER BY sort_order
                """
            ).fetchall()
            product_count = connection.execute("SELECT COUNT(*) FROM token_products").fetchone()[0]
            user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        self.assertEqual([plan["code"] for plan in plans], ["free", "basic", "plus", "pro"])
        self.assertEqual(
            [
                (
                    plan["monthly_price_krw"],
                    plan["monthly_credits"],
                    plan["automation_account_limit"],
                    plan["automation_rule_limit"],
                    plan["allow_token_purchase"],
                    plan["allow_cta_button"],
                    plan["log_retention_days"],
                )
                for plan in plans
            ],
            [
                (0, 30, 1, 1, 0, 0, 7),
                (2900, 1000, 5, 10, 1, 1, 30),
                (4900, 2000, 5, 30, 1, 1, 90),
                (9900, 5000, 5, 100, 1, 1, 180),
            ],
        )
        self.assertEqual(product_count, 4)
        self.assertEqual(user_count, 1)

    def test_legacy_lite_plan_users_are_migrated_to_free(self) -> None:
        with get_connection() as connection:
            now = "2026-01-01T00:00:00+00:00"
            cursor = connection.execute(
                """
                INSERT INTO subscription_plans (
                    code,
                    name,
                    monthly_price_krw,
                    monthly_credits,
                    automation_account_limit,
                    automation_rule_limit,
                    allow_token_purchase,
                    allow_cta_button,
                    log_retention_days,
                    is_active,
                    sort_order,
                    created_at,
                    updated_at
                )
                VALUES ('lite', 'Lite', 1900, 500, 2, 3, 1, 1, 14, 1, 20, ?, ?)
                """,
                (now, now),
            )
            connection.execute(
                "UPDATE users SET current_plan_id = ?, updated_at = ? WHERE id = ?",
                (cursor.lastrowid, now, self.user_id),
            )

        initialize_database()

        with get_connection() as connection:
            user_plan = connection.execute(
                """
                SELECT subscription_plans.code
                FROM users
                JOIN subscription_plans ON subscription_plans.id = users.current_plan_id
                WHERE users.id = ?
                """,
                (self.user_id,),
            ).fetchone()
            lite_count = connection.execute(
                "SELECT COUNT(*) FROM subscription_plans WHERE code = 'lite'"
            ).fetchone()[0]

        self.assertEqual(user_plan["code"], "free")
        self.assertEqual(lite_count, 0)

    def test_monthly_grant_is_idempotent(self) -> None:
        first = grant_monthly_credits(self.user_id)
        second = grant_monthly_credits(self.user_id)
        balance = get_usage_balance(self.user_id)

        self.assertTrue(first["granted"])
        self.assertFalse(second["granted"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(balance["monthly_remaining"], 30)

        with get_connection() as connection:
            ledger_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM credit_ledger
                WHERE entry_type = 'monthly_grant'
                """
            ).fetchone()[0]
        self.assertEqual(ledger_count, 1)

    def test_purchased_token_grant_is_idempotent(self) -> None:
        first = grant_purchased_tokens(self.user_id, 1000, "seed:tokens:test")
        second = grant_purchased_tokens(self.user_id, 1000, "seed:tokens:test")
        balance = get_usage_balance(self.user_id)

        self.assertTrue(first["granted"])
        self.assertFalse(second["granted"])
        self.assertEqual(balance["purchased_remaining"], 1000)

        with get_connection() as connection:
            ledger_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM credit_ledger
                WHERE entry_type = 'purchase_grant'
                """
            ).fetchone()[0]
        self.assertEqual(ledger_count, 1)

    def test_consume_prefers_monthly_and_deduplicates_ref_id(self) -> None:
        grant_monthly_credits(self.user_id)

        consumed = consume_one_credit(self.user_id, "comment:1", "dm_sent")
        duplicate = consume_one_credit(self.user_id, "comment:1", "dm_sent")
        balance = get_usage_balance(self.user_id)

        self.assertTrue(consumed["consumed"])
        self.assertEqual(consumed["source"], "monthly")
        self.assertFalse(duplicate["consumed"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(balance["monthly_remaining"], 29)
        self.assertEqual(balance["purchased_remaining"], 0)

    def test_consume_uses_purchased_tokens_after_monthly_balance(self) -> None:
        grant_monthly_credits(self.user_id)
        grant_purchased_tokens(self.user_id, 2, "seed:tokens:fallback")
        for index in range(30):
            consume_one_credit(self.user_id, f"comment:monthly:{index}", "reply_sent")

        consumed = consume_one_credit(self.user_id, "comment:purchased:1", "dm_partially_sent")
        balance = get_usage_balance(self.user_id)

        self.assertTrue(consumed["consumed"])
        self.assertEqual(consumed["source"], "purchased")
        self.assertEqual(balance["monthly_remaining"], 0)
        self.assertEqual(balance["purchased_remaining"], 1)

    def test_consume_fails_without_negative_balance_when_empty(self) -> None:
        grant_monthly_credits(self.user_id)
        for index in range(30):
            consume_one_credit(self.user_id, f"comment:empty:{index}", "reply_sent")

        failed = consume_one_credit(self.user_id, "comment:empty:31", "dm_sent")
        repeated_failure = consume_one_credit(self.user_id, "comment:empty:31", "dm_sent")
        balance = get_usage_balance(self.user_id)

        self.assertFalse(failed["ok"])
        self.assertEqual(failed["error"], "insufficient_credit")
        self.assertFalse(has_available_credit(self.user_id))
        self.assertFalse(repeated_failure["ok"])
        self.assertEqual(balance["monthly_remaining"], 0)
        self.assertEqual(balance["purchased_remaining"], 0)

        with get_connection() as connection:
            failed_ledger_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM credit_ledger
                WHERE entry_type = 'consume_failed'
                  AND ref_id = 'comment:empty:31'
                """
            ).fetchone()[0]
        self.assertEqual(failed_ledger_count, 1)

    def test_sqlite_pragmas_are_applied(self) -> None:
        with get_connection() as connection:
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
            foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
            synchronous = connection.execute("PRAGMA synchronous").fetchone()[0]

        self.assertEqual(journal_mode.lower(), "wal")
        self.assertEqual(busy_timeout, 5000)
        self.assertEqual(foreign_keys, 1)
        self.assertEqual(synchronous, 1)

    def test_reserve_commit_is_idempotent_and_blocks_second_monthly_job(self) -> None:
        grant_monthly_credits(self.user_id)
        self._set_balance(monthly=1, purchased=0)

        first = reserve_one_credit(self.user_id, "comment:reserve:1", "test")
        second = reserve_one_credit(self.user_id, "comment:reserve:2", "test")
        first_commit = commit_reserved_credit(self.user_id, "comment:reserve:1")
        second_commit = commit_reserved_credit(self.user_id, "comment:reserve:1")
        balance = get_usage_balance(self.user_id)

        self.assertTrue(first.ok)
        self.assertTrue(first.reserved)
        self.assertEqual(first.source, "monthly")
        self.assertFalse(second.ok)
        self.assertEqual(second.error, "insufficient_credit")
        self.assertTrue(first_commit)
        self.assertTrue(second_commit)
        self.assertEqual(balance["monthly_remaining"], 0)
        self.assertEqual(get_available_credit(self.user_id), 0)
        with get_connection() as connection:
            ledger_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM credit_ledger
                WHERE ref_id = 'comment:reserve:1'
                  AND entry_type = 'consume_monthly'
                """
            ).fetchone()[0]
        self.assertEqual(ledger_count, 1)

    def test_reserve_uses_purchased_tokens_and_release_restores_once(self) -> None:
        grant_monthly_credits(self.user_id)
        grant_purchased_tokens(self.user_id, 1, "seed:tokens:reserve")
        self._set_balance(monthly=0, purchased=1)

        reserved = reserve_one_credit(self.user_id, "comment:reserve:purchased", "test")
        first_release = release_reserved_credit(self.user_id, "comment:reserve:purchased", "failed")
        second_release = release_reserved_credit(self.user_id, "comment:reserve:purchased", "failed")
        balance = get_usage_balance(self.user_id)

        self.assertTrue(reserved.ok)
        self.assertEqual(reserved.source, "purchased")
        self.assertTrue(first_release)
        self.assertTrue(second_release)
        self.assertEqual(balance["monthly_remaining"], 0)
        self.assertEqual(balance["purchased_remaining"], 1)

    def test_released_reservation_can_be_reserved_again_for_retry(self) -> None:
        grant_monthly_credits(self.user_id)
        self._set_balance(monthly=1, purchased=0)

        first = reserve_one_credit(self.user_id, "comment:retry", "test")
        released = release_reserved_credit(self.user_id, "comment:retry", "rate_limited")
        second = reserve_one_credit(self.user_id, "comment:retry", "test_retry")
        committed = commit_reserved_credit(self.user_id, "comment:retry")
        balance = get_usage_balance(self.user_id)

        self.assertTrue(first.ok)
        self.assertTrue(released)
        self.assertTrue(second.ok)
        self.assertTrue(second.reserved)
        self.assertTrue(committed)
        self.assertEqual(balance["monthly_remaining"], 0)

    def _set_balance(self, *, monthly: int, purchased: int) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE usage_balances
                SET monthly_remaining = ?,
                    purchased_remaining = ?
                WHERE user_id = ?
                """,
                (monthly, purchased, self.user_id),
            )


if __name__ == "__main__":
    unittest.main()
