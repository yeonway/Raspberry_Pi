from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db
from .config import get_settings
from .security import (
    SESSION_COOKIE,
    hash_password,
    make_session,
    read_session,
    validate_password,
    validate_username,
    verify_password,
)


APP_ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=APP_ROOT / "templates")
MAX_ATTACHMENTS_PER_NOTE = 5
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def _seed_admin_from_env() -> None:
    settings = get_settings()
    if not settings.admin_username or not settings.admin_password:
        return
    username = validate_username(settings.admin_username)
    password = validate_password(settings.admin_password)
    password_hash = hash_password(password)
    existing = db.find_user_by_username(username)
    if existing:
        db.update_user_password_and_role(username, password_hash, "admin")
    else:
        db.insert_user(username, password_hash, "admin")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    _seed_admin_from_env()
    yield


app = FastAPI(title="Personal Memo Site", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_ROOT / "static"), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "manifest-src 'self'; "
        "worker-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    return response


def current_user(request: Request) -> sqlite3.Row | None:
    session = read_session(request.cookies.get(SESSION_COOKIE))
    if session is None:
        return None
    user = db.find_user_by_id(session.user_id)
    if user is None:
        return None
    if user["username"] != session.username or user["role"] != session.role:
        return None
    return user


def require_user(request: Request) -> sqlite3.Row:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


def require_admin(request: Request) -> sqlite3.Row:
    user = require_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def render(request: Request, template: str, context: dict | None = None, status_code: int = 200):
    payload = dict(context or {})
    payload.setdefault("user", current_user(request))
    return templates.TemplateResponse(request, template, payload, status_code=status_code)


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=status.HTTP_303_SEE_OTHER)


def set_login_cookie(response: RedirectResponse, user: sqlite3.Row) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        make_session(user["id"], user["username"], user["role"]),
        max_age=settings.session_seconds,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
    )


def note_rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [db.row_to_note(row) for row in rows]


def folder_rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def attachment_rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def parse_folder_id(value: Any) -> int | None:
    if value in {None, "", "all", "null"}:
        return None
    return int(value)


def json_response(data: dict[str, Any], status_code: int = 200) -> Response:
    return Response(
        content=json.dumps(data, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
    )


def _revision_snapshot(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    return {
        "title": row["title"],
        "body": row["body"],
        "tags": row["tags"],
        "folder_id": row["folder_id"],
        "pinned": bool(row["pinned"]),
        "deleted_at": row["deleted_at"],
        "checklist": json.loads(row["checklist_json"] or "[]") if "checklist_json" in row.keys() else row.get("checklist", []),
    }


def render_admin_users(
    request: Request,
    admin: sqlite3.Row,
    *,
    error: str | None = None,
    username: str = "",
    role: str = "user",
    status_code: int = 200,
):
    return render(
        request,
        "admin_users.html",
        {
            "user": admin,
            "users": db.list_users_with_note_counts(),
            "error": error,
            "username": username,
            "role": role,
        },
        status_code=status_code,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(APP_ROOT / "static" / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(
        APP_ROOT / "static" / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


@app.get("/", include_in_schema=False)
def home(request: Request):
    if current_user(request):
        return redirect("/notes")
    return redirect("/login")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render(request, "login.html")


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    user = db.find_user_by_username(username)
    if user is None or not verify_password(password, user["password_hash"]):
        return render(
            request,
            "login.html",
            {"error": "아이디 또는 비밀번호가 맞지 않습니다.", "username": username},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    response = redirect("/notes")
    set_login_cookie(response, user)
    return response


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return render(request, "register.html")


@app.post("/register", response_class=HTMLResponse)
async def register(request: Request):
    form = await request.form()
    raw_username = str(form.get("username", ""))
    raw_password = str(form.get("password", ""))
    try:
        username = validate_username(raw_username)
        password = validate_password(raw_password)
    except ValueError as exc:
        return render(
            request,
            "register.html",
            {"error": str(exc), "username": raw_username.strip()},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user_id = db.insert_user(username, hash_password(password), "user")
    except sqlite3.IntegrityError:
        return render(
            request,
            "register.html",
            {"error": "이미 사용 중인 아이디입니다.", "username": username},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = db.find_user_by_id(user_id)
    response = redirect("/notes")
    set_login_cookie(response, user)
    return response


@app.post("/logout")
def logout():
    response = redirect("/login")
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/notes", response_class=HTMLResponse)
def notes_page(request: Request):
    user = require_user(request)
    rows = db.list_all_notes() if user["role"] == "admin" else db.list_notes_for_user(user["id"])
    folders = db.list_folders_for_user(user["id"])
    title = "전체 메모" if user["role"] == "admin" else "내 메모"
    bootstrap = {
        "currentUser": {"id": user["id"], "username": user["username"], "role": user["role"]},
        "notes": note_rows_to_dicts(rows),
        "folders": folder_rows_to_dicts(folders),
    }
    return render(
        request,
        "notes.html",
        {
            "notes": rows,
            "folders": folders,
            "title": title,
            "error": None,
            "bootstrap_json": json.dumps(bootstrap, ensure_ascii=False),
        },
    )


@app.post("/notes", response_class=HTMLResponse)
async def create_note(request: Request):
    user = require_user(request)
    form = await request.form()
    body = str(form.get("body", "")).strip()
    title = str(form.get("title", "")).strip()
    folder_id = parse_folder_id(form.get("folder_id"))
    if not body and not title:
        rows = db.list_all_notes() if user["role"] == "admin" else db.list_notes_for_user(user["id"])
        return render(
            request,
            "notes.html",
            {
                "notes": rows,
                "folders": db.list_folders_for_user(user["id"]),
                "title": "전체 메모" if user["role"] == "admin" else "내 메모",
                "error": "메모 내용을 입력하세요.",
                "bootstrap_json": json.dumps(
                    {
                        "currentUser": {"id": user["id"], "username": user["username"], "role": user["role"]},
                        "notes": note_rows_to_dicts(rows),
                        "folders": folder_rows_to_dicts(db.list_folders_for_user(user["id"])),
                    },
                    ensure_ascii=False,
                ),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    db.insert_note(user["id"], body, title=title, folder_id=folder_id)
    return redirect("/notes")


@app.post("/notes/{note_id}/delete")
def delete_note(request: Request, note_id: int):
    user = require_user(request)
    deleted = db.delete_note(note_id, user["id"], user["role"])
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return redirect("/notes")


@app.get("/api/notes")
def api_list_notes(request: Request, q: str = "", folder_id: str = "", trash: bool = False):
    user = require_user(request)
    rows = db.search_notes(
        user["id"],
        user["role"],
        folder_id=parse_folder_id(folder_id),
        query=q,
        include_deleted=trash,
    )
    return json_response({"notes": note_rows_to_dicts(rows)})


@app.post("/api/notes")
async def api_create_note(request: Request):
    user = require_user(request)
    payload = await request.json()
    note_id = db.insert_note(
        user["id"],
        str(payload.get("body") or ""),
        title=str(payload.get("title") or ""),
        tags=str(payload.get("tags") or ""),
        folder_id=parse_folder_id(payload.get("folder_id")),
        checklist=payload.get("checklist") or [],
        pinned=bool(payload.get("pinned")),
        client_key=payload.get("client_key"),
    )
    note = db.find_note_for_request(note_id, user["id"], user["role"])
    return json_response({"note": db.row_to_note(note)}, status_code=status.HTTP_201_CREATED)


@app.patch("/api/notes/{note_id}")
async def api_update_note(request: Request, note_id: int):
    user = require_user(request)
    payload = await request.json()
    fields: dict[str, Any] = {}
    for key in ["title", "body", "tags", "folder_id", "pinned"]:
        if key in payload:
            fields[key] = payload[key]
    if "checklist" in payload:
        fields["checklist_json"] = payload["checklist"]
    try:
        note = db.update_note(note_id, user["id"], user["role"], fields)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return json_response({"note": db.row_to_note(note)})


@app.post("/api/notes/{note_id}/trash")
def api_trash_note(request: Request, note_id: int):
    user = require_user(request)
    if not db.move_note_to_trash(note_id, user["id"], user["role"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return json_response({"ok": True})


@app.post("/api/notes/{note_id}/restore")
def api_restore_note(request: Request, note_id: int):
    user = require_user(request)
    if not db.restore_note(note_id, user["id"], user["role"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return json_response({"ok": True})


@app.delete("/api/notes/{note_id}")
def api_purge_note(request: Request, note_id: int):
    user = require_user(request)
    if not db.purge_note(note_id, user["id"], user["role"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return json_response({"ok": True})


@app.get("/api/notes/{note_id}/revisions")
def api_note_revisions(request: Request, note_id: int):
    user = require_user(request)
    note = db.find_note_for_request(note_id, user["id"], user["role"])
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    revision_rows = db.list_revisions(note_id, user["id"], user["role"])
    by_id: dict[int, dict[str, Any]] = {}
    ordered = list(reversed(revision_rows))
    current_after = {
        **db.row_to_note(note),
        "checklist_json": note["checklist_json"],
    }
    for index, row in enumerate(ordered):
        next_snapshot = ordered[index + 1] if index + 1 < len(ordered) else current_after
        by_id[row["id"]] = {
            "before": _revision_snapshot(row),
            "after": _revision_snapshot(next_snapshot),
        }
    revisions = []
    for row in revision_rows:
        revisions.append(
            {
                "id": row["id"],
                "note_id": row["note_id"],
                "username": row["username"],
                "created_at": row["created_at"],
                "changed_fields": json.loads(row["changed_fields"] or "[]"),
                "title": row["title"],
                "body": row["body"],
                "tags": row["tags"],
                "summary": row["summary"],
                "before": by_id[row["id"]]["before"],
                "after": by_id[row["id"]]["after"],
            }
        )
    return json_response({"revisions": revisions})


@app.get("/api/notes/{note_id}/attachments")
def api_list_attachments(request: Request, note_id: int):
    user = require_user(request)
    note = db.find_note_for_request(note_id, user["id"], user["role"])
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return json_response({"attachments": attachment_rows_to_dicts(db.list_attachments(note_id, user["id"], user["role"]))})


@app.post("/api/notes/{note_id}/attachments")
async def api_upload_attachments(request: Request, note_id: int, files: list[UploadFile] = File(...)):
    user = require_user(request)
    note = db.find_note_for_request(note_id, user["id"], user["role"])
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    existing_count = db.count_attachments(note_id, user["id"], user["role"])
    if existing_count is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    if existing_count + len(files) > MAX_ATTACHMENTS_PER_NOTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Attachments are limited to {MAX_ATTACHMENTS_PER_NOTE} files per note.",
        )

    prepared: list[tuple[str, str, bytes]] = []
    for upload in files:
        raw = await upload.read()
        if len(raw) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Each attachment must be 10MB or smaller: {upload.filename}",
            )
        filename = Path(upload.filename or "attachment").name
        prepared.append((filename, upload.content_type or "application/octet-stream", raw))

    attachments = []
    for filename, content_type, raw in prepared:
        attachment = db.add_attachment(
            note_id,
            user["id"],
            user["role"],
            filename=filename,
            content_type=content_type,
            data=raw,
        )
        if attachment is not None:
            attachments.append(dict(attachment))
    return json_response({"attachments": attachments}, status_code=status.HTTP_201_CREATED)


@app.get("/api/attachments/{attachment_id}/download")
def api_download_attachment(request: Request, attachment_id: int):
    user = require_user(request)
    attachment = db.find_attachment(attachment_id, user["id"], user["role"])
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    filename = quote(attachment["filename"])
    return Response(
        content=attachment["data"],
        media_type=attachment["content_type"] or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@app.delete("/api/attachments/{attachment_id}")
def api_delete_attachment(request: Request, attachment_id: int):
    user = require_user(request)
    if not db.delete_attachment(attachment_id, user["id"], user["role"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return json_response({"ok": True})


@app.post("/api/notes/{note_id}/revisions/{revision_id}/restore")
def api_restore_revision(request: Request, note_id: int, revision_id: int):
    user = require_user(request)
    note = db.restore_revision(note_id, revision_id, user["id"], user["role"])
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
    return json_response({"note": db.row_to_note(note)})


@app.get("/api/folders")
def api_list_folders(request: Request):
    user = require_user(request)
    return json_response({"folders": folder_rows_to_dicts(db.list_folders_for_user(user["id"]))})


@app.post("/api/folders")
async def api_create_folder(request: Request):
    user = require_user(request)
    payload = await request.json()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder name required")
    try:
        folder_id = db.insert_folder(user["id"], name[:80])
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder already exists") from exc
    folder = db.find_folder(folder_id)
    return json_response({"folder": dict(folder)}, status_code=status.HTTP_201_CREATED)


@app.patch("/api/folders/{folder_id}")
async def api_update_folder(request: Request, folder_id: int):
    user = require_user(request)
    payload = await request.json()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder name required")
    if not db.update_folder(folder_id, user["id"], name[:80]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    folder = db.find_folder(folder_id)
    return json_response({"folder": dict(folder)})


@app.delete("/api/folders/{folder_id}")
def api_delete_folder(request: Request, folder_id: int):
    user = require_user(request)
    if not db.delete_folder(folder_id, user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return json_response({"ok": True})


@app.get("/admin/export")
def admin_export(request: Request):
    require_admin(request)
    data = db.export_data()
    filename = f"memo-backup-{db.utc_now().replace(':', '').replace('+', 'Z')}.json"
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/admin/import")
async def admin_import(request: Request, backup_file: UploadFile = File(...)):
    require_admin(request)
    raw = await backup_file.read()
    try:
        data = json.loads(raw.decode("utf-8"))
        result = db.import_data(data)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return json_response({"ok": True, "imported": result})


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users_page(request: Request):
    admin = require_admin(request)
    return render_admin_users(request, admin)


@app.post("/admin/users", response_class=HTMLResponse)
async def admin_create_user(request: Request):
    admin = require_admin(request)
    form = await request.form()
    raw_username = str(form.get("username", ""))
    raw_password = str(form.get("password", ""))
    role = str(form.get("role", "user")).strip()
    if role not in {"user", "admin"}:
        return render_admin_users(
            request,
            admin,
            error="권한 값이 올바르지 않습니다.",
            username=raw_username.strip(),
            role="user",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        username = validate_username(raw_username)
        password = validate_password(raw_password)
    except ValueError as exc:
        return render_admin_users(
            request,
            admin,
            error=str(exc),
            username=raw_username.strip(),
            role=role,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        db.insert_user(username, hash_password(password), role)
    except sqlite3.IntegrityError:
        return render_admin_users(
            request,
            admin,
            error="이미 사용 중인 아이디입니다.",
            username=username,
            role=role,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return redirect("/admin/users")


@app.post("/admin/users/{user_id}/password", response_class=HTMLResponse)
async def admin_reset_user_password(request: Request, user_id: int):
    admin = require_admin(request)
    target_user = db.find_user_by_id(user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    form = await request.form()
    raw_password = str(form.get("password", ""))
    try:
        password = validate_password(raw_password)
    except ValueError as exc:
        return render_admin_users(
            request,
            admin,
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    db.update_user_password(user_id, hash_password(password))
    return redirect("/admin/users")


@app.post("/admin/users/{user_id}/role", response_class=HTMLResponse)
async def admin_change_user_role(request: Request, user_id: int):
    admin = require_admin(request)
    target_user = db.find_user_by_id(user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    form = await request.form()
    role = str(form.get("role", "user")).strip()
    if role not in {"user", "admin"}:
        return render_admin_users(
            request,
            admin,
            error="권한 값이 올바르지 않습니다.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if user_id == admin["id"] and role != "admin":
        return render_admin_users(
            request,
            admin,
            error="현재 로그인한 관리자 계정은 일반 사용자로 바꿀 수 없습니다.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    db.update_user_role(user_id, role)
    return redirect("/admin/users")


@app.post("/admin/users/{user_id}/delete", response_class=HTMLResponse)
def admin_delete_user(request: Request, user_id: int):
    admin = require_admin(request)
    target_user = db.find_user_by_id(user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user_id == admin["id"]:
        return render_admin_users(
            request,
            admin,
            error="현재 로그인한 관리자 계정은 삭제할 수 없습니다.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    db.delete_user(user_id)
    return redirect("/admin/users")
