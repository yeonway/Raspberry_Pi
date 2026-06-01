import asyncio
import os
import hmac
import hashlib
import json
import unittest
import uuid
from pathlib import Path

from fastapi import HTTPException

from app.automations import create_automation_rule
from app.billing import get_seed_user_id
from app.config import get_settings
from app.database import get_connection, initialize_database
from app.main import receive_meta_webhook
from app.webhooks import handle_meta_webhook_payload, verify_meta_challenge, verify_meta_request_signature


class MetaWebhookTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.database_path = Path.cwd() / "data" / f"test-{uuid.uuid4().hex}.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path}"
        os.environ["META_PAGE_ID"] = "page_123"
        os.environ["META_IG_USER_ID"] = "ig_123"
        os.environ["META_WEBHOOK_VERIFY_TOKEN"] = "verify-token"
        os.environ["FACEBOOK_APP_SECRET"] = "app-secret"
        os.environ["META_WEBHOOK_VERIFY_SIGNATURE"] = "true"
        get_settings.cache_clear()
        initialize_database()
        self.user_id = get_seed_user_id()
        self._create_rule()

    def tearDown(self) -> None:
        for key in (
            "DATABASE_URL",
            "META_PAGE_ID",
            "META_IG_USER_ID",
            "META_WEBHOOK_VERIFY_TOKEN",
            "FACEBOOK_APP_SECRET",
            "META_WEBHOOK_VERIFY_SIGNATURE",
        ):
            os.environ.pop(key, None)
        get_settings.cache_clear()
        if self.database_path.exists():
            self.database_path.unlink()

    def test_verify_endpoint_returns_challenge_for_matching_token(self) -> None:
        challenge = verify_meta_challenge("subscribe", "verify-token", "challenge-123")

        self.assertEqual(challenge, "challenge-123")

    def test_verify_endpoint_rejects_wrong_token(self) -> None:
        challenge = verify_meta_challenge("subscribe", "wrong-token", "challenge-123")

        self.assertIsNone(challenge)

    def test_comment_payload_is_saved_and_queued(self) -> None:
        result = handle_meta_webhook_payload(self._comment_payload("comment_webhook_1"))

        self.assertTrue(result["queued"])
        self.assertEqual(result["status"], "queued")
        with get_connection() as connection:
            event_count = connection.execute("SELECT COUNT(*) FROM webhook_events").fetchone()[0]
            job_count = connection.execute("SELECT COUNT(*) FROM job_queue").fetchone()[0]

        self.assertEqual(event_count, 1)
        self.assertEqual(job_count, 1)

    def test_duplicate_payload_does_not_queue_twice(self) -> None:
        payload = self._comment_payload("comment_webhook_2")
        first = handle_meta_webhook_payload(payload)
        second = handle_meta_webhook_payload(payload)

        self.assertTrue(first["queued"])
        self.assertEqual(second["status"], "duplicate")
        with get_connection() as connection:
            event_count = connection.execute("SELECT COUNT(*) FROM webhook_events").fetchone()[0]
            job_count = connection.execute("SELECT COUNT(*) FROM job_queue").fetchone()[0]

        self.assertEqual(event_count, 1)
        self.assertEqual(job_count, 1)

    def test_unknown_payload_is_saved_as_skipped(self) -> None:
        result = handle_meta_webhook_payload({"object": "instagram", "entry": [{"id": "ig_123", "changes": []}]})

        self.assertEqual(result["status"], "skipped")
        with get_connection() as connection:
            row = connection.execute("SELECT status FROM webhook_events").fetchone()

        self.assertEqual(row["status"], "skipped")

    def test_post_rejects_missing_signature_before_saving_payload(self) -> None:
        raw_body = json.dumps(self._comment_payload("comment_webhook_missing")).encode("utf-8")

        with self.assertRaises(HTTPException) as context:
            asyncio.run(receive_meta_webhook(_FakeRequest(raw_body)))

        self.assertEqual(context.exception.status_code, 403)
        with get_connection() as connection:
            event_count = connection.execute("SELECT COUNT(*) FROM webhook_events").fetchone()[0]
        self.assertEqual(event_count, 0)

    def test_post_rejects_malformed_signature(self) -> None:
        raw_body = json.dumps(self._comment_payload("comment_webhook_malformed")).encode("utf-8")

        with self.assertRaises(HTTPException) as context:
            asyncio.run(
                receive_meta_webhook(
                    _FakeRequest(raw_body, {"X-Hub-Signature-256": "not-a-sha256-signature"})
                )
            )

        self.assertEqual(context.exception.status_code, 403)

    def test_post_rejects_bad_signature(self) -> None:
        raw_body = json.dumps(self._comment_payload("comment_webhook_bad")).encode("utf-8")

        with self.assertRaises(HTTPException) as context:
            asyncio.run(
                receive_meta_webhook(_FakeRequest(raw_body, {"X-Hub-Signature-256": "sha256:bad"}))
            )

        self.assertEqual(context.exception.status_code, 403)

    def test_post_accepts_valid_signature_and_queues_payload(self) -> None:
        raw_body = json.dumps(self._comment_payload("comment_webhook_signed")).encode("utf-8")

        response = asyncio.run(
            receive_meta_webhook(_FakeRequest(raw_body, {"X-Hub-Signature-256": self._signature(raw_body)}))
        )

        self.assertTrue(response["queued"])

    def test_signature_uses_raw_body_bytes(self) -> None:
        payload = self._comment_payload("comment_webhook_raw")
        raw_body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        compact_body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

        self.assertFalse(
            verify_meta_request_signature(
                raw_body,
                {"x-hub-signature-256": self._signature(compact_body)},
            )
        )
        self.assertTrue(
            verify_meta_request_signature(
                raw_body,
                {"X-Hub-Signature-256": self._signature(raw_body)},
            )
        )

    def _create_rule(self) -> int:
        return create_automation_rule(
            user_id=self.user_id,
            name="Webhook 문의 자동응답",
            target_mode="all",
            keywords_text="가격\n구매",
            exclude_keywords_text="품절",
            match_mode="contains",
            public_reply_text="DM으로 보내드렸습니다.",
            dm_text="안내 DM입니다.",
            cta_label="",
            cta_url="",
            delay_min_seconds=5,
            delay_max_seconds=30,
            selected_media=[],
        )

    def _comment_payload(self, comment_id: str) -> dict:
        return {
            "object": "instagram",
            "entry": [
                {
                    "id": "ig_123",
                    "time": 1770000000,
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": comment_id,
                                "text": "가격 문의드립니다",
                                "media": {"id": "media_webhook_1"},
                            },
                        }
                    ],
                }
            ],
        }

    def _signature(self, raw_body: bytes) -> str:
        digest = hmac.new(b"app-secret", raw_body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"


class _FakeRequest:
    def __init__(self, raw_body: bytes, headers: dict[str, str] | None = None) -> None:
        self._raw_body = raw_body
        self.headers = headers or {}

    async def body(self) -> bytes:
        return self._raw_body


if __name__ == "__main__":
    unittest.main()
