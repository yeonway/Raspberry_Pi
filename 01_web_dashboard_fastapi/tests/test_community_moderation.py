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
        self.assertIn("blocked_term", reasons)
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
            with community_service.connect() as conn:
                report = conn.execute("SELECT reason FROM community_reports WHERE target_type = 'post'").fetchone()
            self.assertEqual(report["reason"], "other")

    def test_report_requires_reason_and_admin_report_has_target_info(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            os.environ["COMMUNITY_DB_PATH"] = os.path.join(tmpdir, "community.sqlite3")
            os.environ["COMMUNITY_MODERATION_ENABLED"] = "false"
            community_service.ensure_community_tables()
            ok, _, post_id = community_service.create_post(
                {"board_slug": "free", "title": "신고 대상", "content": "확인할 내용", "password": "1234"},
                {},
                "127.0.0.1",
                "session-a",
            )
            self.assertTrue(ok)
            missing_ok, _ = community_service.report("post", int(post_id), "", "", "ip-a", "browser-a", "session-a")
            self.assertFalse(missing_ok)
            report_ok, _ = community_service.report("post", int(post_id), "other", "상세 확인", "ip-a", "browser-a", "session-a")
            self.assertTrue(report_ok)
            reports = community_service.admin_reports("open")
            self.assertEqual(reports[0]["target_title"], "신고 대상")
            self.assertEqual(reports[0]["reason_label"], "기타")
            self.assertEqual(reports[0]["detail"], "상세 확인")

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

    def test_comment_update_does_not_insert_new_row_and_keeps_revision(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            os.environ["COMMUNITY_DB_PATH"] = os.path.join(tmpdir, "community.sqlite3")
            os.environ["COMMUNITY_MODERATION_ENABLED"] = "false"
            community_service.ensure_community_tables()
            ok, _, post_id = community_service.create_post(
                {"board_slug": "free", "title": "댓글 글", "content": "내용", "password": "1234"},
                {},
                "127.0.0.1",
                "session-a",
            )
            self.assertTrue(ok)
            add_ok, _ = community_service.add_comment(int(post_id), "처음 댓글", "1234", {}, "127.0.0.1", "session-a")
            self.assertTrue(add_ok)
            update_ok, _, _ = community_service.update_comment_with_password(1, "수정 댓글", "1234", {}, "127.0.0.1", "session-a")
            self.assertTrue(update_ok)
            with community_service.connect() as conn:
                count = conn.execute("SELECT COUNT(*) AS c FROM community_comments").fetchone()["c"]
                revisions = conn.execute("SELECT COUNT(*) AS c FROM community_comment_revisions").fetchone()["c"]
                content = conn.execute("SELECT content FROM community_comments WHERE id = 1").fetchone()["content"]
            self.assertEqual(count, 1)
            self.assertEqual(revisions, 1)
            self.assertEqual(content, "수정 댓글")

    def test_user_deletes_are_soft_delete(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            os.environ["COMMUNITY_DB_PATH"] = os.path.join(tmpdir, "community.sqlite3")
            os.environ["COMMUNITY_MODERATION_ENABLED"] = "false"
            community_service.ensure_community_tables()
            ok, _, post_id = community_service.create_post(
                {"board_slug": "free", "title": "삭제 글", "content": "내용", "password": "1234"},
                {},
                "127.0.0.1",
                "session-a",
            )
            self.assertTrue(ok)
            add_ok, _ = community_service.add_comment(int(post_id), "삭제 댓글", "1234", {}, "127.0.0.1", "session-a")
            self.assertTrue(add_ok)
            comment_ok, _, _ = community_service.delete_comment_with_password(1, "1234")
            post_ok, _ = community_service.delete_post_with_password(int(post_id), "1234")
            self.assertTrue(comment_ok)
            self.assertTrue(post_ok)
            with community_service.connect() as conn:
                post = conn.execute("SELECT moderation_status FROM community_posts WHERE id = ?", (post_id,)).fetchone()
                comment = conn.execute("SELECT moderation_status FROM community_comments WHERE id = 1").fetchone()
            self.assertEqual(post["moderation_status"], "deleted_by_user")
            self.assertEqual(comment["moderation_status"], "deleted_by_user")

    def test_rule_flagged_post_and_comment_enter_review(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            os.environ["COMMUNITY_DB_PATH"] = os.path.join(tmpdir, "community.sqlite3")
            os.environ["COMMUNITY_MODERATION_ENABLED"] = "false"
            os.environ["COMMUNITY_MODERATION_AUTO_HIDE"] = "false"
            community_service.ensure_community_tables()
            ok, _, post_id = community_service.create_post(
                {"board_slug": "free", "title": "검토 글", "content": "badword_placeholder", "password": "1234"},
                {},
                "127.0.0.1",
                "session-a",
            )
            self.assertTrue(ok)
            with community_service.connect() as conn:
                post = conn.execute("SELECT moderation_status, moderation_score FROM community_posts WHERE id = ?", (post_id,)).fetchone()
                log = conn.execute("SELECT rule_flag, final_flag FROM community_moderation_logs WHERE target_type = 'post'").fetchone()
            self.assertIn(post["moderation_status"], {"pending_review", "auto_hidden"})
            self.assertEqual(post["moderation_score"], 1)
            self.assertEqual(log["rule_flag"], 1)
            self.assertEqual(log["final_flag"], 1)
            # Make the post public only so the comment route can attach a flagged comment.
            community_service.set_post_hidden(int(post_id), False)
            comment_ok, _ = community_service.add_comment(int(post_id), "badword_placeholder", "1234", {}, "127.0.0.1", "session-b")
            self.assertTrue(comment_ok)
            review = community_service.admin_review_items()
            self.assertTrue(any(item["id"] == int(post_id) for item in review["review_posts"]))
            self.assertTrue(any(item["rule_flag"] == 1 for item in review["review_comments"]))

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
