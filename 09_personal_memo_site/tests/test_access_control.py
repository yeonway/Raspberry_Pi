from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import get_settings
from app.main import app
from app.security import hash_password


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMO_DB_PATH", str(tmp_path / "memo.db"))
    monkeypatch.setenv("MEMO_SECRET_KEY", "test-secret-key")
    monkeypatch.delenv("MEMO_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("MEMO_ADMIN_PASSWORD", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def register(test_client: TestClient, username: str, password: str = "secret123") -> None:
    response = test_client.post(
        "/register",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303


def login(test_client: TestClient, username: str, password: str = "secret123") -> None:
    response = test_client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303


def logout(test_client: TestClient) -> None:
    response = test_client.post("/logout", follow_redirects=False)
    assert response.status_code == 303


def add_note(test_client: TestClient, body: str) -> None:
    response = test_client.post("/notes", data={"body": body}, follow_redirects=False)
    assert response.status_code == 303


def test_guest_is_redirected_to_login(client: TestClient):
    response = client.get("/notes", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_regular_users_only_see_their_own_notes(client: TestClient):
    register(client, "alice")
    add_note(client, "alice private memo")
    logout(client)

    register(client, "bob")
    add_note(client, "bob private memo")

    response = client.get("/notes")
    assert response.status_code == 200
    assert "bob private memo" in response.text
    assert "alice private memo" not in response.text

    logout(client)
    login(client, "alice")
    response = client.get("/notes")
    assert "alice private memo" in response.text
    assert "bob private memo" not in response.text


def test_admin_can_see_all_user_notes(client: TestClient):
    register(client, "alice")
    add_note(client, "alice visible to admin")
    logout(client)

    register(client, "bob")
    add_note(client, "bob visible to admin")
    logout(client)

    db.insert_user("admin", hash_password("adminpass"), "admin")
    login(client, "admin", "adminpass")

    response = client.get("/notes")
    assert response.status_code == 200
    assert "전체 메모" in response.text
    assert "alice visible to admin" in response.text
    assert "bob visible to admin" in response.text
    assert "alice" in response.text
    assert "bob" in response.text


def test_regular_user_cannot_manage_accounts(client: TestClient):
    register(client, "alice")

    response = client.get("/admin/users", follow_redirects=False)

    assert response.status_code == 403


def test_admin_can_manage_user_accounts(client: TestClient):
    db.insert_user("admin", hash_password("adminpass"), "admin")
    login(client, "admin", "adminpass")

    response = client.post(
        "/admin/users",
        data={"username": "charlie", "password": "firstpass", "role": "user"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    response = client.get("/admin/users")
    assert response.status_code == 200
    assert "charlie" in response.text

    charlie = db.find_user_by_username("charlie")
    assert charlie is not None
    response = client.post(
        f"/admin/users/{charlie['id']}/password",
        data={"password": "secondpass"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    logout(client)
    response = client.post(
        "/login",
        data={"username": "charlie", "password": "firstpass"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    login(client, "charlie", "secondpass")
    logout(client)

    login(client, "admin", "adminpass")
    response = client.post(
        f"/admin/users/{charlie['id']}/role",
        data={"role": "admin"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert db.find_user_by_username("charlie")["role"] == "admin"

    response = client.post(f"/admin/users/{charlie['id']}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert db.find_user_by_username("charlie") is None


def test_admin_cannot_delete_or_demote_self(client: TestClient):
    admin_id = db.insert_user("admin", hash_password("adminpass"), "admin")
    login(client, "admin", "adminpass")

    response = client.post(
        f"/admin/users/{admin_id}/role",
        data={"role": "user"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert db.find_user_by_username("admin")["role"] == "admin"

    response = client.post(f"/admin/users/{admin_id}/delete", follow_redirects=False)
    assert response.status_code == 400
    assert db.find_user_by_username("admin") is not None


def test_note_workspace_features(client: TestClient):
    register(client, "alice")

    folder_response = client.post("/api/folders", json={"name": "work"})
    assert folder_response.status_code == 201
    folder_id = folder_response.json()["folder"]["id"]

    note_response = client.post(
        "/api/notes",
        json={
            "title": "first title",
            "body": "first body",
            "tags": "todo,work",
            "folder_id": folder_id,
            "pinned": True,
            "checklist": [{"id": "a", "text": "ship it", "checked": False}],
        },
    )
    assert note_response.status_code == 201
    note = note_response.json()["note"]
    note_id = note["id"]
    assert note["folder_id"] == folder_id
    assert note["pinned"] is True
    assert note["checklist"][0]["text"] == "ship it"

    update_response = client.patch(
        f"/api/notes/{note_id}",
        json={
            "title": "updated title",
            "body": "updated body",
            "tags": "done,work",
            "checklist": [{"id": "a", "text": "ship it", "checked": True}],
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()["note"]
    assert updated["title"] == "updated title"
    assert updated["checklist"][0]["checked"] is True

    search_response = client.get("/api/notes", params={"q": "done"})
    assert search_response.status_code == 200
    assert search_response.json()["notes"][0]["id"] == note_id

    revisions_response = client.get(f"/api/notes/{note_id}/revisions")
    assert revisions_response.status_code == 200
    revisions = revisions_response.json()["revisions"]
    assert revisions
    assert "title" in revisions[0]["changed_fields"]

    trash_response = client.post(f"/api/notes/{note_id}/trash")
    assert trash_response.status_code == 200
    assert client.get("/api/notes").json()["notes"] == []
    assert client.get("/api/notes", params={"trash": "true"}).json()["notes"][0]["id"] == note_id

    restore_response = client.post(f"/api/notes/{note_id}/restore")
    assert restore_response.status_code == 200
    assert client.get("/api/notes").json()["notes"][0]["id"] == note_id


def test_note_attachments_limits_and_download(client: TestClient):
    register(client, "alice")
    note_response = client.post("/api/notes", json={"title": "with files", "body": "body"})
    note_id = note_response.json()["note"]["id"]

    files = [("files", (f"file-{index}.txt", b"hello", "text/plain")) for index in range(5)]
    upload_response = client.post(f"/api/notes/{note_id}/attachments", files=files)
    assert upload_response.status_code == 201
    assert len(upload_response.json()["attachments"]) == 5

    list_response = client.get(f"/api/notes/{note_id}/attachments")
    assert list_response.status_code == 200
    attachments = list_response.json()["attachments"]
    assert attachments[0]["filename"] == "file-0.txt"
    assert attachments[0]["size_bytes"] == 5

    blocked_count = client.post(
        f"/api/notes/{note_id}/attachments",
        files=[("files", ("extra.txt", b"extra", "text/plain"))],
    )
    assert blocked_count.status_code == 400
    assert "5" in blocked_count.json()["detail"]

    other_note = client.post("/api/notes", json={"title": "large", "body": "body"}).json()["note"]
    blocked_size = client.post(
        f"/api/notes/{other_note['id']}/attachments",
        files=[("files", ("large.bin", b"x" * (10 * 1024 * 1024 + 1), "application/octet-stream"))],
    )
    assert blocked_size.status_code == 400
    assert "10MB" in blocked_size.json()["detail"]

    download = client.get(f"/api/attachments/{attachments[0]['id']}/download")
    assert download.status_code == 200
    assert download.content == b"hello"

    delete_response = client.delete(f"/api/attachments/{attachments[0]['id']}")
    assert delete_response.status_code == 200
    assert len(client.get(f"/api/notes/{note_id}/attachments").json()["attachments"]) == 4


def test_client_key_prevents_duplicate_note_creates(client: TestClient):
    register(client, "alice")
    payload = {"title": "one", "body": "body", "client_key": "local-1"}

    first = client.post("/api/notes", json=payload)
    second = client.post("/api/notes", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["note"]["id"] == second.json()["note"]["id"]
    assert len(client.get("/api/notes").json()["notes"]) == 1


def test_revisions_include_before_after_snapshots(client: TestClient):
    register(client, "alice")
    note = client.post("/api/notes", json={"title": "before", "body": "old"}).json()["note"]
    update_response = client.patch(f"/api/notes/{note['id']}", json={"title": "after", "body": "new"})
    assert update_response.status_code == 200

    revisions = client.get(f"/api/notes/{note['id']}/revisions").json()["revisions"]

    assert revisions[0]["before"]["title"] == "before"
    assert revisions[0]["before"]["body"] == "old"
    assert revisions[0]["after"]["title"] == "after"
    assert revisions[0]["after"]["body"] == "new"


def test_admin_can_export_backup(client: TestClient):
    db.insert_user("admin", hash_password("adminpass"), "admin")
    login(client, "admin", "adminpass")

    response = client.get("/admin/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["version"] == 1
