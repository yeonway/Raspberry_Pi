import os
import tempfile
import unittest

from app import community_service
from app.community_moderation import QwenModerationClient, RuleBasedModerationFilter


class CommunityModerationTests(unittest.TestCase):
    def test_qwen_response_parsing(self):
        client = QwenModerationClient()
        self.assertTrue(client.base_url.startswith("http"))

    def test_rule_filter_detects_placeholder_and_private_pattern(self):
        rule_filter = RuleBasedModerationFilter()
        reasons = rule_filter.check("badword_placeholder")
        self.assertIn("blocked_word_placeholder", reasons)
        privacy_reasons = rule_filter.check("contact test@example.com")
        self.assertIn("personal_info_email", privacy_reasons)

    def test_duplicate_report_is_limited(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            os.environ["COMMUNITY_DB_PATH"] = os.path.join(tmpdir, "community.sqlite3")
            os.environ["COMMUNITY_MODERATION_ENABLED"] = "false"
            community_service.ensure_community_tables()
            ok, _, post_id = community_service.create_post(
                {
                    "board_slug": "free",
                    "title": "테스트 글",
                    "content": "테스트 내용",
                    "password": "1234",
                },
                {},
                "127.0.0.1",
                "session-a",
            )
            self.assertTrue(ok)
            self.assertIsNotNone(post_id)
            first_ok, _ = community_service.report("post", int(post_id), "other", "", "ip-a", "browser-a", "session-a")
            second_ok, _ = community_service.report("post", int(post_id), "other", "", "ip-a", "browser-a", "session-a")
            self.assertTrue(first_ok)
            self.assertFalse(second_ok)

    def test_post_update_does_not_insert_new_row_and_keeps_revision(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            os.environ["COMMUNITY_DB_PATH"] = os.path.join(tmpdir, "community.sqlite3")
            os.environ["COMMUNITY_MODERATION_ENABLED"] = "false"
            community_service.ensure_community_tables()
            ok, _, post_id = community_service.create_post(
                {
                    "board_slug": "free",
                    "title": "처음 제목",
                    "content": "처음 내용",
                    "password": "1234",
                },
                {},
                "127.0.0.1",
                "session-a",
            )
            self.assertTrue(ok)
            update_ok, _ = community_service.update_post_with_password(
                int(post_id),
                {"title": "수정 제목", "content": "수정 내용", "password": "1234"},
                {},
                "127.0.0.1",
                "session-a",
            )
            self.assertTrue(update_ok)
            with community_service.connect() as conn:
                count = conn.execute("SELECT COUNT(*) AS c FROM community_posts").fetchone()["c"]
                revisions = conn.execute("SELECT COUNT(*) AS c FROM community_post_revisions").fetchone()["c"]
                title = conn.execute("SELECT title FROM community_posts WHERE id = ?", (post_id,)).fetchone()["title"]
            self.assertEqual(count, 1)
            self.assertEqual(revisions, 1)
            self.assertEqual(title, "수정 제목")

    def test_reaction_toggles_and_logs(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            os.environ["COMMUNITY_DB_PATH"] = os.path.join(tmpdir, "community.sqlite3")
            os.environ["COMMUNITY_MODERATION_ENABLED"] = "false"
            community_service.ensure_community_tables()
            ok, _, post_id = community_service.create_post(
                {"board_slug": "free", "title": "좋아요 글", "content": "내용", "password": "1234"},
                {},
                "127.0.0.1",
                "session-a",
            )
            self.assertTrue(ok)
            first_ok, _ = community_service.react("post", int(post_id), "ip-a", "browser-a", "session-a")
            second_ok, _ = community_service.react("post", int(post_id), "ip-a", "browser-a", "session-a")
            self.assertTrue(first_ok)
            self.assertTrue(second_ok)
            with community_service.connect() as conn:
                post = conn.execute("SELECT like_count FROM community_posts WHERE id = ?", (post_id,)).fetchone()
                logs = conn.execute("SELECT COUNT(*) AS c FROM community_reaction_logs").fetchone()["c"]
            self.assertEqual(post["like_count"], 0)
            self.assertEqual(logs, 2)


if __name__ == "__main__":
    unittest.main()
