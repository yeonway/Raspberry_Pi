import io
import json
import os
import unittest
import urllib.error
import uuid
from pathlib import Path

from app.config import get_settings
from app.database import get_connection, initialize_database
from app import meta_api


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class MetaApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.database_path = Path.cwd() / "data" / f"test-{uuid.uuid4().hex}.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path}"
        os.environ["META_GRAPH_VERSION"] = "v25.0"
        os.environ["META_PAGE_ID"] = "page_123"
        os.environ["META_IG_USER_ID"] = "ig_123"
        os.environ["META_PAGE_ACCESS_TOKEN"] = "test_page_token"
        get_settings.cache_clear()
        initialize_database()
        self.original_urlopen = meta_api.urllib.request.urlopen

    def tearDown(self) -> None:
        meta_api.urllib.request.urlopen = self.original_urlopen
        for key in (
            "DATABASE_URL",
            "META_GRAPH_VERSION",
            "META_PAGE_ID",
            "META_IG_USER_ID",
            "META_PAGE_ACCESS_TOKEN",
        ):
            os.environ.pop(key, None)
        get_settings.cache_clear()
        if self.database_path.exists():
            self.database_path.unlink()

    def test_build_cta_payload_without_cta_returns_text_message(self) -> None:
        self.assertEqual(
            meta_api.build_cta_payload("안녕하세요 https://example.com", None, None),
            {"text": "안녕하세요 https://example.com"},
        )

    def test_build_cta_payload_requires_label_and_url_together(self) -> None:
        with self.assertRaises(ValueError):
            meta_api.build_cta_payload("안녕하세요", "자세히 보기", None)

    def test_get_media_list_uses_ig_user_id_and_access_token(self) -> None:
        seen = {}

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            seen["timeout"] = timeout
            return FakeResponse({"data": [{"id": "media_1", "caption": "hello"}]})

        meta_api.urllib.request.urlopen = fake_urlopen
        media = meta_api.get_media_list()

        self.assertEqual(media, [{"id": "media_1", "caption": "hello"}])
        self.assertIn("/v25.0/ig_123/media", seen["url"])
        self.assertIn("access_token=test_page_token", seen["url"])
        self.assertEqual(seen["timeout"], meta_api.DEFAULT_TIMEOUT_SECONDS)

    def test_send_private_reply_uses_page_id_and_comment_id(self) -> None:
        seen = {}

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            seen["body"] = request.data.decode("utf-8")
            return FakeResponse({"recipient_id": "ig_user", "message_id": "message_1"})

        meta_api.urllib.request.urlopen = fake_urlopen
        result = meta_api.send_private_reply("page_123", "comment_123", "DM text")

        self.assertEqual(result["message_id"], "message_1")
        self.assertTrue(seen["url"].endswith("/v25.0/page_123/messages"))
        self.assertIn("comment_123", seen["body"])
        self.assertIn("DM+text", seen["body"])

    def test_get_comment_detail_uses_comment_id_and_short_timeout(self) -> None:
        seen = {}

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            seen["timeout"] = timeout
            return FakeResponse({"id": "comment_123", "text": "가격 문의", "media": {"id": "media_123"}})

        meta_api.urllib.request.urlopen = fake_urlopen
        result = meta_api.get_comment_detail("comment_123", timeout_seconds=3)

        self.assertEqual(result["media"]["id"], "media_123")
        self.assertIn("/v25.0/comment_123", seen["url"])
        self.assertIn("fields=", seen["url"])
        self.assertEqual(seen["timeout"], 3)

    def test_http_error_is_recorded_for_display(self) -> None:
        def fake_urlopen(request, timeout):
            body = io.BytesIO(
                json.dumps(
                    {
                        "error": {
                            "message": "Missing permissions",
                            "type": "OAuthException",
                            "code": 10,
                        }
                    }
                ).encode("utf-8")
            )
            raise urllib.error.HTTPError(
                request.full_url,
                403,
                "Forbidden",
                hdrs=None,
                fp=body,
            )

        meta_api.urllib.request.urlopen = fake_urlopen

        with self.assertRaises(meta_api.MetaApiError) as context:
            meta_api.get_comments("media_123")

        self.assertIn("권한", context.exception.user_message)
        latest = meta_api.get_latest_meta_api_failure()
        self.assertIsNotNone(latest)
        self.assertEqual(latest["status_code"], 403)
        self.assertEqual(latest["method"], "GET")
        self.assertIn("/v25.0/media_123/comments", latest["endpoint"])

        with get_connection() as connection:
            count = connection.execute("SELECT COUNT(*) FROM meta_api_failures").fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
