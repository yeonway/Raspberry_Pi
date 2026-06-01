import json
import os
import unittest
import uuid
from pathlib import Path

from app import facebook_oauth
from app.billing import get_seed_user_id
from app.config import get_settings
from app.database import get_connection, initialize_database
from app.token_crypto import decrypt_token, encrypt_token


class FacebookOAuthTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.database_path = Path.cwd() / "data" / f"test-{uuid.uuid4().hex}.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path}"
        os.environ["FACEBOOK_APP_ID"] = "fb_app"
        os.environ["FACEBOOK_APP_SECRET"] = "fb_secret"
        os.environ["FACEBOOK_REDIRECT_URI"] = "https://example.test/connections/facebook/callback"
        os.environ["TOKEN_ENCRYPTION_KEY"] = "local-test-encryption-key"
        get_settings.cache_clear()
        initialize_database()
        self.user_id = get_seed_user_id()
        self.original_graph_request = facebook_oauth._graph_request
        self.original_fetch_page = facebook_oauth._fetch_page_instagram
        self.original_subscribe = facebook_oauth._subscribe_page_to_webhook

    def tearDown(self) -> None:
        facebook_oauth._graph_request = self.original_graph_request
        facebook_oauth._fetch_page_instagram = self.original_fetch_page
        facebook_oauth._subscribe_page_to_webhook = self.original_subscribe
        for key in (
            "DATABASE_URL",
            "FACEBOOK_APP_ID",
            "FACEBOOK_APP_SECRET",
            "FACEBOOK_REDIRECT_URI",
            "TOKEN_ENCRYPTION_KEY",
        ):
            os.environ.pop(key, None)
        get_settings.cache_clear()
        if self.database_path.exists():
            self.database_path.unlink()

    def test_token_encryption_does_not_store_plain_text(self) -> None:
        encrypted = encrypt_token("page-token-secret")

        self.assertNotIn("page-token-secret", encrypted)
        self.assertEqual(decrypt_token(encrypted), "page-token-secret")

    def test_login_url_creates_state_and_requests_required_permissions(self) -> None:
        login_url = facebook_oauth.build_facebook_login_url(self.user_id)

        self.assertIn("client_id=fb_app", login_url)
        self.assertIn("pages_show_list", login_url)
        self.assertIn("instagram_manage_messages", login_url)
        with get_connection() as connection:
            session_count = connection.execute("SELECT COUNT(*) FROM facebook_oauth_sessions").fetchone()[0]
        self.assertEqual(session_count, 1)

    def test_oauth_callback_stores_page_tokens_encrypted(self) -> None:
        state = self._create_state()
        facebook_oauth._graph_request = self._graph_for_callback

        result = facebook_oauth.handle_oauth_callback(user_id=self.user_id, state=state, code="code_1")

        self.assertEqual(result["pages"][0]["page_id"], "page_1")
        self.assertNotIn("page_access_token", result["pages"][0])
        with get_connection() as connection:
            row = connection.execute(
                "SELECT pages_json FROM facebook_oauth_sessions WHERE state = ?",
                (state,),
            ).fetchone()
        stored_pages = json.loads(row["pages_json"])
        encrypted_token = stored_pages[0]["page_access_token_encrypted"]
        self.assertNotIn("page_token_1", encrypted_token)
        self.assertEqual(decrypt_token(encrypted_token), "page_token_1")

    def test_connect_selected_page_saves_encrypted_token_and_enforces_limit(self) -> None:
        state = self._create_ready_session("page_1", "ig_1", "page_token_1")
        facebook_oauth._fetch_page_instagram = lambda page_id, token: {
            "page_id": page_id,
            "page_name": "Page One",
            "ig_user_id": "ig_1",
            "ig_username": "brand_one",
        }
        facebook_oauth._subscribe_page_to_webhook = lambda page_id, token: {
            "subscribed": True,
            "status": "subscribed",
            "error": "",
        }

        account = facebook_oauth.connect_selected_page(user_id=self.user_id, state=state, page_id="page_1")

        self.assertEqual(account["display_name"], "Page One")
        self.assertEqual(account["ig_username"], "brand_one")
        self.assertTrue(account["webhook_subscribed"])
        with get_connection() as connection:
            row = connection.execute(
                "SELECT page_access_token_encrypted FROM connected_accounts WHERE id = ?",
                (account["id"],),
            ).fetchone()
        self.assertNotIn("page_token_1", row["page_access_token_encrypted"])
        self.assertEqual(facebook_oauth.get_account_page_access_token(account["id"]), "page_token_1")

        second_state = self._create_ready_session("page_2", "ig_2", "page_token_2")
        with self.assertRaises(facebook_oauth.FacebookOAuthError) as context:
            facebook_oauth.connect_selected_page(user_id=self.user_id, state=second_state, page_id="page_2")
        self.assertIn("플랜을 업그레이드", str(context.exception))

    def _create_state(self) -> str:
        login_url = facebook_oauth.build_facebook_login_url(self.user_id)
        return login_url.split("state=", 1)[1].split("&", 1)[0]

    def _create_ready_session(self, page_id: str, ig_user_id: str, token: str) -> str:
        state = self._create_state()
        page = {
            "page_id": page_id,
            "page_name": "Page One",
            "ig_user_id": ig_user_id,
            "ig_username": "brand_one",
            "facebook_user_id": "fb_user_1",
            "page_access_token_encrypted": encrypt_token(token),
        }
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE facebook_oauth_sessions
                SET pages_json = ?, status = 'pages_ready'
                WHERE state = ?
                """,
                (json.dumps([page], ensure_ascii=False), state),
            )
        return state

    def _graph_for_callback(self, method, path, *, params=None, data=None, access_token=""):
        if path == "/oauth/access_token":
            return {"access_token": "user_token_1"}
        if path == "/me":
            return {"id": "fb_user_1"}
        if path == "/me/accounts":
            return {
                "data": [
                    {
                        "id": "page_1",
                        "name": "Page One",
                        "access_token": "page_token_1",
                        "instagram_business_account": {
                            "id": "ig_1",
                            "username": "brand_one",
                        },
                    }
                ]
            }
        raise AssertionError(f"Unexpected graph request: {method} {path}")


if __name__ == "__main__":
    unittest.main()
