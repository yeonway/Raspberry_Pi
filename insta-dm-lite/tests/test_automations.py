import json
import os
import unittest
import uuid
from pathlib import Path

from app.automations import (
    AutomationValidationError,
    create_automation_rule,
    get_or_create_connected_account,
    list_automation_rules,
    parse_keywords,
    set_rule_enabled,
)
from app.billing import get_seed_user_id
from app.config import get_settings
from app.database import get_connection, initialize_database


class AutomationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.database_path = Path.cwd() / "data" / f"test-{uuid.uuid4().hex}.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path}"
        os.environ["META_PAGE_ID"] = "page_123"
        os.environ["META_IG_USER_ID"] = "ig_123"
        get_settings.cache_clear()
        initialize_database()
        self.user_id = get_seed_user_id()

    def tearDown(self) -> None:
        for key in ("DATABASE_URL", "META_PAGE_ID", "META_IG_USER_ID"):
            os.environ.pop(key, None)
        get_settings.cache_clear()
        if self.database_path.exists():
            self.database_path.unlink()

    def test_connected_account_uses_page_and_ig_ids_separately(self) -> None:
        account = get_or_create_connected_account(self.user_id)

        self.assertEqual(account["page_id"], "page_123")
        self.assertEqual(account["ig_user_id"], "ig_123")

    def test_parse_keywords_splits_commas_and_lines(self) -> None:
        self.assertEqual(parse_keywords("가격, 구매\n링크\n가격"), ["가격", "구매", "링크"])

    def test_create_all_media_rule_stores_keyword_json_and_cta(self) -> None:
        self._set_plan("basic")
        rule_id = self._create_rule(target_mode="all", selected_media=[], use_cta=True)
        rules = list_automation_rules(self.user_id)

        self.assertEqual(rule_id, rules[0]["id"])
        self.assertEqual(rules[0]["target_mode"], "all")
        self.assertEqual(rules[0]["keywords"], ["가격", "구매"])
        self.assertEqual(rules[0]["exclude_keywords"], ["품절"])
        self.assertEqual(rules[0]["cta_label"], "자세히 보기")
        self.assertEqual(rules[0]["cta_url"], "https://example.com")
        self.assertEqual(rules[0]["media_target_count"], 0)

        with get_connection() as connection:
            row = connection.execute(
                "SELECT keywords_json, exclude_keywords_json FROM automation_rules WHERE id = ?",
                (rule_id,),
            ).fetchone()
        self.assertEqual(json.loads(row["keywords_json"]), ["가격", "구매"])
        self.assertEqual(json.loads(row["exclude_keywords_json"]), ["품절"])

    def test_create_selected_media_rule_stores_targets(self) -> None:
        rule_id = self._create_rule(
            target_mode="selected",
            selected_media=[
                {
                    "media_id": "media_1",
                    "media_caption": "첫 게시물",
                    "media_permalink": "https://example.com/p/1",
                    "media_type": "IMAGE",
                    "thumbnail_url": "https://example.com/thumb.jpg",
                }
            ],
        )

        with get_connection() as connection:
            target = connection.execute(
                """
                SELECT media_id, media_caption, media_permalink, media_type, thumbnail_url
                FROM rule_media_targets
                WHERE rule_id = ?
                """,
                (rule_id,),
            ).fetchone()

        self.assertEqual(target["media_id"], "media_1")
        self.assertEqual(target["media_caption"], "첫 게시물")
        self.assertEqual(target["media_type"], "IMAGE")

    def test_selected_mode_requires_at_least_one_media(self) -> None:
        with self.assertRaises(AutomationValidationError):
            self._create_rule(target_mode="selected", selected_media=[])

    def test_rule_can_be_toggled_off_and_on(self) -> None:
        rule_id = self._create_rule(target_mode="all", selected_media=[])

        set_rule_enabled(self.user_id, rule_id, False)
        self.assertFalse(list_automation_rules(self.user_id)[0]["enabled"])

        set_rule_enabled(self.user_id, rule_id, True)
        self.assertTrue(list_automation_rules(self.user_id)[0]["enabled"])

    def test_free_plan_rejects_cta_button(self) -> None:
        with self.assertRaises(AutomationValidationError):
            self._create_rule(target_mode="all", selected_media=[], use_cta=True)

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

    def _create_rule(
        self,
        target_mode: str,
        selected_media: list[dict[str, str]],
        *,
        use_cta: bool = False,
    ) -> int:
        return create_automation_rule(
            user_id=self.user_id,
            name="문의 자동응답",
            target_mode=target_mode,
            keywords_text="가격\n구매",
            exclude_keywords_text="품절",
            match_mode="contains",
            public_reply_text="DM으로 보내드렸습니다. 확인해주세요.",
            dm_text="안녕하세요. 요청하신 정보를 보내드립니다.",
            cta_label="자세히 보기" if use_cta else "",
            cta_url="https://example.com" if use_cta else "",
            delay_min_seconds=1,
            delay_max_seconds=3,
            selected_media=selected_media,
        )


if __name__ == "__main__":
    unittest.main()
