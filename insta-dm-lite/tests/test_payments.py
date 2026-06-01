import hashlib
import hmac
import json
import os
import unittest
import uuid
from pathlib import Path

from app.billing import get_seed_user_id, get_usage_balance
from app.config import get_settings
from app.database import get_connection, initialize_database
from app import payments


class PaymentTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.database_path = Path.cwd() / "data" / f"test-{uuid.uuid4().hex}.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path}"
        os.environ["PORTONE_STORE_ID"] = "store_test"
        os.environ["PORTONE_CHANNEL_KEY"] = "channel_test"
        os.environ["PORTONE_API_SECRET"] = "api_secret_test"
        os.environ["PORTONE_WEBHOOK_SECRET"] = "webhook_secret_test"
        get_settings.cache_clear()
        initialize_database()
        self.user_id = get_seed_user_id()
        self._set_plan("basic")
        self.original_fetch = payments.fetch_portone_payment

    def tearDown(self) -> None:
        payments.fetch_portone_payment = self.original_fetch
        for key in (
            "DATABASE_URL",
            "PORTONE_STORE_ID",
            "PORTONE_CHANNEL_KEY",
            "PORTONE_API_SECRET",
            "PORTONE_WEBHOOK_SECRET",
        ):
            os.environ.pop(key, None)
        get_settings.cache_clear()
        if self.database_path.exists():
            self.database_path.unlink()

    def test_checkout_creates_pending_order_and_payment_request(self) -> None:
        checkout = payments.create_checkout_order(1, user_id=self.user_id)

        self.assertEqual(checkout["order"]["status"], "pending")
        self.assertEqual(checkout["order"]["amount_krw"], 3000)
        self.assertEqual(checkout["order"]["token_amount"], 1000)
        self.assertEqual(checkout["payment_request"]["storeId"], "store_test")
        self.assertEqual(checkout["payment_request"]["channelKey"], "channel_test")
        self.assertEqual(checkout["payment_request"]["paymentId"], checkout["order"]["order_ref"])
        self.assertEqual(checkout["payment_request"]["currency"], "CURRENCY_KRW")

    def test_paid_webhook_grants_tokens_once(self) -> None:
        checkout = payments.create_checkout_order(1, user_id=self.user_id)
        order_ref = checkout["order"]["order_ref"]
        payments.fetch_portone_payment = lambda payment_id: self._paid_payment(payment_id, 3000)

        first = payments.handle_portone_webhook(*self._signed_webhook(order_ref, "tx_paid_1", "PAID"))
        second = payments.handle_portone_webhook(*self._signed_webhook(order_ref, "tx_paid_1", "PAID"))
        balance = get_usage_balance(self.user_id)

        self.assertEqual(first["status"], "paid")
        self.assertEqual(second["status"], "duplicate")
        self.assertEqual(balance["purchased_remaining"], 1000)
        with get_connection() as connection:
            ledger_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM credit_ledger
                WHERE entry_type = 'purchase_grant'
                  AND ref_id = ?
                """,
                (f"payment:{order_ref}",),
            ).fetchone()[0]
        self.assertEqual(ledger_count, 1)

    def test_amount_mismatch_marks_failed_without_grant(self) -> None:
        checkout = payments.create_checkout_order(1, user_id=self.user_id)
        order_ref = checkout["order"]["order_ref"]
        payments.fetch_portone_payment = lambda payment_id: self._paid_payment(payment_id, 1)

        result = payments.handle_portone_webhook(*self._signed_webhook(order_ref, "tx_bad_amount", "PAID"))
        balance = get_usage_balance(self.user_id)
        order = payments.get_payment_order(checkout["order"]["id"])

        self.assertFalse(result["ok"])
        self.assertEqual(order["status"], "failed")
        self.assertEqual(balance["purchased_remaining"], 0)

    def test_failed_and_cancelled_orders_do_not_grant_tokens(self) -> None:
        failed = payments.create_checkout_order(1, user_id=self.user_id)
        payments.verify_and_apply_payment(
            failed["order"]["order_ref"],
            "tx_failed",
            self._payment(failed["order"]["order_ref"], "FAILED", 3000, "tx_failed"),
        )
        cancelled = payments.create_checkout_order(1, user_id=self.user_id)
        payments.verify_and_apply_payment(
            cancelled["order"]["order_ref"],
            "tx_cancelled",
            self._payment(cancelled["order"]["order_ref"], "CANCELLED", 3000, "tx_cancelled"),
        )
        balance = get_usage_balance(self.user_id)

        self.assertEqual(payments.get_payment_order(failed["order"]["id"])["status"], "failed")
        self.assertEqual(payments.get_payment_order(cancelled["order"]["id"])["status"], "cancelled")
        self.assertEqual(balance["purchased_remaining"], 0)

    def test_fetch_payment_uses_portone_v2_payment_lookup(self) -> None:
        captured = {}
        original_urlopen = payments.urllib.request.urlopen

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return b'{"payment":{"id":"pay_1","status":"PAID"}}'

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["authorization"] = request.get_header("Authorization")
            captured["timeout"] = timeout
            return FakeResponse()

        payments.urllib.request.urlopen = fake_urlopen
        try:
            payment = payments.fetch_portone_payment("pay_1")
        finally:
            payments.urllib.request.urlopen = original_urlopen

        self.assertEqual(payment["payment"]["id"], "pay_1")
        self.assertEqual(captured["url"], "https://api.portone.io/payments/pay_1")
        self.assertEqual(captured["authorization"], "PortOne api_secret_test")
        self.assertEqual(captured["timeout"], payments.DEFAULT_TIMEOUT_SECONDS)

    def test_invalid_signature_is_rejected(self) -> None:
        checkout = payments.create_checkout_order(1, user_id=self.user_id)
        raw_body = json.dumps(
            {"payment_id": checkout["order"]["order_ref"], "tx_id": "tx_1", "status": "PAID"},
            separators=(",", ":"),
        ).encode("utf-8")

        result = payments.handle_portone_webhook(raw_body, {"x-portone-signature": "bad"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "signature_failed")

    def test_free_plan_cannot_create_checkout_order(self) -> None:
        self._set_plan("free")

        with self.assertRaises(PermissionError):
            payments.create_checkout_order(1, user_id=self.user_id)

        with get_connection() as connection:
            order_count = connection.execute("SELECT COUNT(*) FROM payment_orders").fetchone()[0]
        self.assertEqual(order_count, 0)

    def _set_plan(self, code: str) -> None:
        with get_connection() as connection:
            plan = connection.execute(
                "SELECT id FROM subscription_plans WHERE code = ?",
                (code,),
            ).fetchone()
            connection.execute(
                "UPDATE users SET current_plan_id = ?, updated_at = 'test' WHERE id = ?",
                (plan["id"], self.user_id),
            )

    def _signed_webhook(self, payment_id: str, transaction_id: str, status: str):
        raw_body = json.dumps(
            {"payment_id": payment_id, "tx_id": transaction_id, "status": status},
            separators=(",", ":"),
        ).encode("utf-8")
        signature = hmac.new(b"webhook_secret_test", raw_body, hashlib.sha256).hexdigest()
        return raw_body, {"x-portone-signature": signature}

    def _paid_payment(self, payment_id: str, amount: int) -> dict:
        return self._payment(payment_id, "PAID", amount, "tx_paid_1")

    def _payment(self, payment_id: str, status: str, amount: int, transaction_id: str) -> dict:
        return {
            "payment": {
                "id": payment_id,
                "status": status,
                "transactions": [
                    {
                        "id": transaction_id,
                        "is_primary": True,
                        "amount": {"total": amount},
                    }
                ],
            }
        }


if __name__ == "__main__":
    unittest.main()
