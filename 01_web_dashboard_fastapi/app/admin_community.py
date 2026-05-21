from typing import Dict
from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app import community_service
from app.news_auth import (
    clear_admin_session_cookie,
    csrf_token,
    get_current_admin,
    set_admin_session_cookie,
    verify_csrf,
    verify_news_admin_login,
)


router = APIRouter()
templates = Jinja2Templates(directory=str(community_service.PROJECT_DIR / "templates"))


async def read_form_data(request: Request) -> Dict[str, str]:
    body = await request.body()
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def login_template(request: Request, error: str = "", username: str = "", status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "community/admin_login.html",
        {"request": request, "error": error, "username": username},
        status_code=status_code,
    )


def require_admin(request: Request) -> str:
    admin = get_current_admin(request)
    if not admin:
        raise HTTPException(status_code=403, detail="community admin login required")
    return admin


def require_admin_csrf(request: Request, form: Dict[str, str]) -> str:
    admin = require_admin(request)
    if not verify_csrf(request, form.get("csrf_token", "")):
        raise HTTPException(status_code=403, detail="invalid csrf token")
    return admin


def context(request: Request, admin: str, **extra):
    data = {
        "request": request,
        "admin": admin,
        "csrf_token": csrf_token(request),
        "nav": "dashboard",
    }
    data.update(extra)
    return data


@router.get("/admin/community", response_class=HTMLResponse)
def admin_community_dashboard(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return login_template(request)
    return templates.TemplateResponse(
        request,
        "community/admin_dashboard.html",
        context(request, admin, **community_service.admin_dashboard_data()),
    )


@router.head("/admin/community")
def admin_community_head():
    community_service.ensure_community_tables()
    return Response(status_code=200)


@router.post("/admin/community/login")
async def admin_community_login(request: Request):
    form = await read_form_data(request)
    username = form.get("username", "").strip()
    password = form.get("password", "")
    if not verify_news_admin_login(username, password):
        return login_template(
            request,
            error="아이디 또는 비밀번호가 올바르지 않습니다. 관리자 환경 변수를 확인하세요.",
            username=username,
            status_code=401,
        )
    response = RedirectResponse(url="/admin/community", status_code=303)
    set_admin_session_cookie(response, username)
    return response


@router.post("/admin/community/logout")
async def admin_community_logout(request: Request):
    form = await read_form_data(request)
    admin = get_current_admin(request)
    if admin and not verify_csrf(request, form.get("csrf_token", "")):
        raise HTTPException(status_code=403, detail="invalid csrf token")
    response = RedirectResponse(url="/admin/community", status_code=303)
    clear_admin_session_cookie(response)
    return response


@router.get("/admin/community/posts", response_class=HTMLResponse)
def admin_community_posts(request: Request, status: str = ""):
    admin = require_admin(request)
    return templates.TemplateResponse(
        request,
        "community/admin_posts.html",
        context(request, admin, posts=community_service.admin_posts(status), status=status, nav="posts"),
    )


@router.get("/admin/community/notices/new", response_class=HTMLResponse)
def admin_community_notice_new(request: Request):
    admin = require_admin(request)
    return templates.TemplateResponse(
        request,
        "community/admin_notice_form.html",
        context(request, admin, boards=community_service.boards(), form={}, error="", nav="posts"),
    )


@router.post("/admin/community/notices/new")
async def admin_community_notice_create(request: Request):
    form = await read_form_data(request)
    admin = require_admin_csrf(request, form)
    form["board_slug"] = "notice"
    ok, message, post_id = community_service.create_post(
        form,
        request.headers,
        request.client.host if request.client else "",
        f"admin:{admin}",
        admin=True,
    )
    if ok and post_id:
        return RedirectResponse(url=f"/admin/community/posts?{urlencode({'message': message})}", status_code=303)
    return templates.TemplateResponse(
        request,
        "community/admin_notice_form.html",
        context(request, admin, boards=community_service.boards(), form=form, error=message, nav="posts"),
        status_code=400,
    )


@router.post("/admin/community/posts/{post_id}/hide")
async def admin_community_post_hide(request: Request, post_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.set_post_hidden(post_id, True, "관리자 숨김")
    return RedirectResponse(url="/admin/community/posts", status_code=303)


@router.post("/admin/community/posts/{post_id}/restore")
async def admin_community_post_restore(request: Request, post_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.set_post_hidden(post_id, False)
    return RedirectResponse(url="/admin/community/posts", status_code=303)


@router.post("/admin/community/posts/{post_id}/approve")
async def admin_community_post_approve(request: Request, post_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.set_post_hidden(post_id, False)
    return RedirectResponse(url=request.headers.get("referer", "/admin/community/review"), status_code=303)


@router.post("/admin/community/posts/{post_id}/delete")
async def admin_community_post_delete(request: Request, post_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.delete_post(post_id)
    return RedirectResponse(url="/admin/community/posts", status_code=303)


@router.get("/admin/community/comments", response_class=HTMLResponse)
def admin_community_comments(request: Request, status: str = ""):
    admin = require_admin(request)
    return templates.TemplateResponse(
        request,
        "community/admin_comments.html",
        context(request, admin, comments=community_service.admin_comments(status), status=status, nav="comments"),
    )


@router.post("/admin/community/comments/{comment_id}/hide")
async def admin_community_comment_hide(request: Request, comment_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.set_comment_hidden(comment_id, True, "관리자 숨김")
    return RedirectResponse(url="/admin/community/comments", status_code=303)


@router.post("/admin/community/comments/{comment_id}/restore")
async def admin_community_comment_restore(request: Request, comment_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.set_comment_hidden(comment_id, False)
    return RedirectResponse(url="/admin/community/comments", status_code=303)


@router.post("/admin/community/comments/{comment_id}/approve")
async def admin_community_comment_approve(request: Request, comment_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.set_comment_hidden(comment_id, False)
    return RedirectResponse(url=request.headers.get("referer", "/admin/community/review"), status_code=303)


@router.post("/admin/community/comments/{comment_id}/delete")
async def admin_community_comment_delete(request: Request, comment_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.delete_comment(comment_id)
    return RedirectResponse(url="/admin/community/comments", status_code=303)


@router.get("/admin/community/reports", response_class=HTMLResponse)
def admin_community_reports(request: Request, status: str = "open"):
    admin = require_admin(request)
    return templates.TemplateResponse(
        request,
        "community/admin_reports.html",
        context(request, admin, reports=community_service.admin_reports(status), status=status, nav="reports"),
    )


@router.get("/admin/community/review", response_class=HTMLResponse)
def admin_community_review(request: Request):
    admin = require_admin(request)
    return templates.TemplateResponse(
        request,
        "community/admin_review.html",
        context(request, admin, **community_service.admin_review_items(), nav="review"),
    )


@router.post("/admin/community/reports/{report_id}/resolve")
async def admin_community_report_resolve(request: Request, report_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.handle_report(report_id, "resolved", form.get("handler_note", ""))
    return RedirectResponse(url="/admin/community/reports", status_code=303)


@router.post("/admin/community/reports/{report_id}/dismiss")
async def admin_community_report_dismiss(request: Request, report_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.handle_report(report_id, "dismissed", form.get("handler_note", ""))
    return RedirectResponse(url="/admin/community/reports", status_code=303)


@router.post("/admin/community/reports/{report_id}/{action}")
async def admin_community_report_target_action(request: Request, report_id: int, action: str):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    if action not in {"hide", "restore", "delete"}:
        raise HTTPException(status_code=404, detail="unknown report action")
    community_service.act_on_report_target(report_id, action)
    return RedirectResponse(url=request.headers.get("referer", "/admin/community/reports"), status_code=303)


@router.get("/admin/community/moderation", response_class=HTMLResponse)
def admin_community_moderation(request: Request):
    admin = require_admin(request)
    return templates.TemplateResponse(
        request,
        "community/admin_moderation.html",
        context(request, admin, logs=community_service.admin_moderation_logs(), nav="moderation"),
    )


@router.get("/admin/community/bans", response_class=HTMLResponse)
def admin_community_bans(request: Request):
    admin = require_admin(request)
    return templates.TemplateResponse(
        request,
        "community/admin_bans.html",
        context(request, admin, bans=community_service.admin_bans(), nav="bans"),
    )


@router.post("/admin/community/bans")
async def admin_community_ban_create(request: Request):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.add_ban(form.get("ban_type", ""), form.get("ban_value", ""), form.get("reason", ""))
    return RedirectResponse(url=request.headers.get("referer", "/admin/community/bans"), status_code=303)


@router.get("/admin/community/activity", response_class=HTMLResponse)
def admin_community_activity(request: Request, subject_type: str = "", subject_value: str = ""):
    admin = require_admin(request)
    return templates.TemplateResponse(
        request,
        "community/admin_activity.html",
        context(request, admin, **community_service.admin_activity(subject_type, subject_value), nav="activity"),
    )


@router.get("/admin/community/revisions", response_class=HTMLResponse)
def admin_community_revisions(request: Request):
    admin = require_admin(request)
    return templates.TemplateResponse(
        request,
        "community/admin_revisions.html",
        context(request, admin, **community_service.admin_revisions(), nav="revisions"),
    )


@router.post("/admin/community/activity/notes")
async def admin_community_activity_note(request: Request):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    community_service.add_activity_note(form.get("subject_type", ""), form.get("subject_value", ""), form.get("note", ""))
    return RedirectResponse(
        url=f"/admin/community/activity?subject_type={form.get('subject_type', '')}&subject_value={form.get('subject_value', '')}",
        status_code=303,
    )


@router.get("/admin/community/settings", response_class=HTMLResponse)
def admin_community_settings(request: Request):
    admin = require_admin(request)
    return templates.TemplateResponse(
        request,
        "community/admin_settings.html",
        context(request, admin, settings=community_service.admin_settings(), nav="settings"),
    )


@router.post("/admin/community/settings")
async def admin_community_settings_update(request: Request):
    form = await read_form_data(request)
    admin = require_admin_csrf(request, form)
    community_service.update_settings(form)
    return templates.TemplateResponse(
        request,
        "community/admin_settings.html",
        context(request, admin, settings=community_service.admin_settings(), nav="settings", message="설정을 저장했습니다."),
    )
