import os
import unittest
import uuid
from pathlib import Path

from app.automations import create_automation_rule
from app.billing import consume_one_credit, get_seed_user_id, get_usage_balance
from app.comment_engine import enqueue_comment_for_processing, list_automation_logs, process_due_jobs
from app.config import get_settings
from app.database import get_connection, initialize_database
from app import comment_engine


class CommentEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.database_path = Path.cwd() / "data" / f"test-{uuid.uuid4().hex}.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path}"
        os.environ["META_PAGE_ID"] = "page_123"
        os.environ["META_IG_USER_ID"] = "ig_123"
        get_settings.cache_clear()
        initialize_database()
        self.user_id = get_seed_user_id()
        self.original_reply = comment_engine.meta_api.reply_to_comment
        self.original_dm = comment_engine.meta_api.send_private_reply

    def tearDown(self) -> None:
        comment_engine.meta_api.reply_to_comment = self.original_reply
        comment_engine.meta_api.send_private_reply = self.original_dm
        for key in ("DATABASE_URL", "META_PAGE_ID", "META_IG_USER_ID"):
            os.environ.pop(key, None)
        get_settings.cache_clear()
        if self.database_path.exists():
            self.database_path.unlink()

    def test_target_media_mismatch_is_skipped(self) -> None:
        self._create_rule(target_mode="selected", media_id="media_1")

        result = enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_2",
            comment_id="comment_1",
            comment_text="가격 문의",
            delay_override_seconds=0,
        )

        self.assertEqual(result["status"], "skipped_media")
        self.assertFalse(result["queued"])
        self.assertEqual(list_automation_logs(status="skipped_media")[0]["comment_id"], "comment_1")

    def test_keyword_mismatch_is_skipped(self) -> None:
        self._create_rule()

        result = enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_1",
            comment_id="comment_2",
            comment_text="안녕하세요",
            delay_override_seconds=0,
        )

        self.assertEqual(result["status"], "skipped_keyword")
        self.assertFalse(result["queued"])

    def test_duplicate_comment_is_not_queued_twice(self) -> None:
        self._create_rule()

        first = enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_1",
            comment_id="comment_3",
            comment_text="가격 문의",
            delay_override_seconds=0,
        )
        second = enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_1",
            comment_id="comment_3",
            comment_text="가격 문의",
            delay_override_seconds=0,
        )

        self.assertTrue(first["queued"])
        self.assertEqual(second["status"], "duplicate")
        with get_connection() as connection:
            count = connection.execute("SELECT COUNT(*) FROM job_queue").fetchone()[0]
        self.assertEqual(count, 1)

    def test_token_empty_is_not_queued(self) -> None:
        self._create_rule()
        for index in range(30):
            consume_one_credit(self.user_id, f"preconsume:{index}", "test")
        calls = {"reply": 0, "dm": 0}
        comment_engine.meta_api.reply_to_comment = lambda *args, **kwargs: calls.__setitem__("reply", calls["reply"] + 1)
        comment_engine.meta_api.send_private_reply = lambda *args, **kwargs: calls.__setitem__("dm", calls["dm"] + 1)

        result = enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_1",
            comment_id="comment_4",
            comment_text="가격 문의",
            delay_override_seconds=0,
        )
        processed = process_due_jobs(limit=1)

        self.assertEqual(result["status"], "queued")
        self.assertTrue(result["queued"])
        self.assertEqual(processed[0]["status"], "token_empty")
        self.assertEqual(calls["reply"], 0)
        self.assertEqual(calls["dm"], 0)

    def test_successful_job_charges_one_credit_and_logs_success(self) -> None:
        self._create_rule()
        comment_engine.meta_api.reply_to_comment = lambda comment_id, message: {"id": "reply_1"}
        comment_engine.meta_api.send_private_reply = lambda *args, **kwargs: {"message_id": "dm_1"}

        enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_1",
            comment_id="comment_5",
            comment_text="가격 문의",
            delay_override_seconds=0,
        )
        processed = process_due_jobs(limit=1)
        balance = get_usage_balance(self.user_id)

        self.assertEqual(processed[0]["status"], "success")
        self.assertTrue(processed[0]["charged"])
        self.assertEqual(balance["monthly_remaining"], 29)
        logs = list_automation_logs(status="success")
        self.assertEqual(logs[0]["charge_amount"], 1)

    def test_partial_success_charges_one_credit(self) -> None:
        self._create_rule()
        comment_engine.meta_api.reply_to_comment = lambda comment_id, message: {"id": "reply_1"}

        def fail_dm(*args, **kwargs):
            raise RuntimeError("dm failed")

        comment_engine.meta_api.send_private_reply = fail_dm

        enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_1",
            comment_id="comment_6",
            comment_text="가격 문의",
            delay_override_seconds=0,
        )
        processed = process_due_jobs(limit=1)
        balance = get_usage_balance(self.user_id)

        self.assertEqual(processed[0]["status"], "partial_success")
        self.assertTrue(processed[0]["charged"])
        self.assertEqual(balance["monthly_remaining"], 29)

    def test_private_reply_success_public_reply_failure_still_charges_one_credit(self) -> None:
        self._create_rule()

        def fail_reply(*args, **kwargs):
            raise RuntimeError("reply failed")

        comment_engine.meta_api.reply_to_comment = fail_reply
        comment_engine.meta_api.send_private_reply = lambda *args, **kwargs: {"message_id": "dm_1"}

        enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_1",
            comment_id="comment_7",
            comment_text="가격 문의",
            delay_override_seconds=0,
        )
        processed = process_due_jobs(limit=1)
        balance = get_usage_balance(self.user_id)

        self.assertEqual(processed[0]["status"], "partial_success")
        self.assertTrue(processed[0]["charged"])
        self.assertEqual(balance["monthly_remaining"], 29)

    def test_all_send_failures_release_reserved_credit(self) -> None:
        self._create_rule()

        def fail(*args, **kwargs):
            raise RuntimeError("send failed")

        comment_engine.meta_api.reply_to_comment = fail
        comment_engine.meta_api.send_private_reply = fail

        enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_1",
            comment_id="comment_8",
            comment_text="가격 문의",
            delay_override_seconds=0,
        )
        processed = process_due_jobs(limit=1)
        balance = get_usage_balance(self.user_id)

        self.assertEqual(processed[0]["status"], "failed")
        self.assertFalse(processed[0]["charged"])
        self.assertEqual(balance["monthly_remaining"], 30)

    def test_rate_limited_job_releases_credit_and_requeues(self) -> None:
        self._create_rule()

        def rate_limited(*args, **kwargs):
            raise comment_engine.meta_api.MetaApiError(
                "rate limited",
                endpoint="/comments",
                method="POST",
                status_code=429,
            )

        comment_engine.meta_api.reply_to_comment = rate_limited
        comment_engine.meta_api.send_private_reply = rate_limited

        enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_1",
            comment_id="comment_9",
            comment_text="가격 문의",
            delay_override_seconds=0,
        )
        processed = process_due_jobs(limit=1)
        balance = get_usage_balance(self.user_id)

        self.assertEqual(processed[0]["status"], "rate_limited")
        self.assertFalse(processed[0]["charged"])
        self.assertEqual(balance["monthly_remaining"], 30)
        with get_connection() as connection:
            row = connection.execute("SELECT status FROM job_queue WHERE comment_id = 'comment_9'").fetchone()
        self.assertEqual(row["status"], "queued")

    def test_multiple_matching_rules_only_queue_first_and_log_conflict(self) -> None:
        self._allow_two_rules()
        first_rule_id = self._create_rule()
        second_rule_id = self._create_rule()
        calls = {"reply": 0, "dm": 0}
        comment_engine.meta_api.reply_to_comment = lambda *args, **kwargs: calls.__setitem__("reply", calls["reply"] + 1)
        comment_engine.meta_api.send_private_reply = lambda *args, **kwargs: calls.__setitem__("dm", calls["dm"] + 1)

        result = enqueue_comment_for_processing(
            user_id=self.user_id,
            media_id="media_1",
            comment_id="comment_10",
            comment_text="가격 문의",
            delay_override_seconds=0,
        )
        processed = process_due_jobs(limit=1)
        balance = get_usage_balance(self.user_id)
        conflict_logs = list_automation_logs(status="skipped_rule_conflict")

        self.assertEqual(result["rule_id"], first_rule_id)
        self.assertEqual(conflict_logs[0]["rule_id"], second_rule_id)
        self.assertEqual(processed[0]["status"], "success")
        self.assertEqual(calls["reply"], 1)
        self.assertEqual(calls["dm"], 1)
        self.assertEqual(balance["monthly_remaining"], 29)

    def _create_rule(self, target_mode: str = "all", media_id: str = "media_1") -> int:
        selected_media = []
        if target_mode == "selected":
            selected_media = [
                {
                    "media_id": media_id,
                    "media_caption": "테스트 게시물",
                    "media_permalink": "https://example.com/p/1",
                    "media_type": "IMAGE",
                    "thumbnail_url": "https://example.com/t.jpg",
                }
            ]
        return create_automation_rule(
            user_id=self.user_id,
            name="문의 자동응답",
            target_mode=target_mode,
            keywords_text="가격\n구매",
            exclude_keywords_text="품절",
            match_mode="contains",
            public_reply_text="DM으로 보내드렸습니다.",
            dm_text="안내 DM입니다.",
            cta_label="",
            cta_url="",
            delay_min_seconds=0,
            delay_max_seconds=0,
            selected_media=selected_media,
        )

    def _allow_two_rules(self) -> None:
        with get_connection() as connection:
            connection.execute(
                "UPDATE subscription_plans SET automation_rule_limit = 2 WHERE code = 'free'"
            )


if __name__ == "__main__":
    unittest.main()
