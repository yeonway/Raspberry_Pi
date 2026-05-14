from typing import Dict
from urllib.parse import parse_qs, quote_plus

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app import news_service
from app.news_auth import (
    clear_admin_session_cookie,
    csrf_token,
    get_current_admin,
    set_admin_session_cookie,
    verify_csrf,
    verify_news_admin_login,
)


router = APIRouter()
templates = Jinja2Templates(directory=str(news_service.PROJECT_DIR / "templates"))
templates.env.filters["urlencode"] = quote_plus

CATEGORY_OPTIONS = news_service.CATEGORY_OPTIONS


async def read_form_data(request: Request) -> Dict[str, str]:
    body = await request.body()
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def login_template(
    request: Request,
    error: str = "",
    username: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "news/admin_login.html",
        {
            "request": request,
            "error": error,
            "username": username,
        },
        status_code=status_code,
    )


def require_admin(request: Request) -> str:
    admin = get_current_admin(request)
    if not admin:
        raise HTTPException(status_code=403, detail="news admin login required")
    return admin


def require_admin_csrf(request: Request, form: Dict[str, str]) -> str:
    admin = require_admin(request)
    if not verify_csrf(request, form.get("csrf_token", "")):
        raise HTTPException(status_code=403, detail="invalid csrf token")
    return admin


def admin_context(request: Request, admin: str, **extra):
    context = {
        "request": request,
        "admin": admin,
        "csrf_token": csrf_token(request),
        "category_options": CATEGORY_OPTIONS,
    }
    context.update(extra)
    return context


@router.get("/admin/news", response_class=HTMLResponse)
def admin_news_dashboard(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return login_template(request)

    data = news_service.admin_dashboard_data()
    return templates.TemplateResponse(
        request,
        "news/admin_dashboard.html",
        admin_context(request, admin, **data),
    )


@router.head("/admin/news")
def admin_news_head():
    news_service.ensure_news_tables()
    return Response(status_code=200)


@router.post("/admin/news/login")
async def admin_news_login(request: Request):
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

    response = RedirectResponse(url="/admin/news", status_code=303)
    set_admin_session_cookie(response, username)
    return response


@router.post("/admin/news/logout")
async def admin_news_logout(request: Request):
    form = await read_form_data(request)
    admin = get_current_admin(request)
    if admin and not verify_csrf(request, form.get("csrf_token", "")):
        raise HTTPException(status_code=403, detail="invalid csrf token")
    response = RedirectResponse(url="/admin/news", status_code=303)
    clear_admin_session_cookie(response)
    return response


@router.get("/admin/news/new", response_class=HTMLResponse)
def admin_news_new(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/news", status_code=303)
    return templates.TemplateResponse(
        request,
        "news/admin_form.html",
        admin_context(
            request,
            admin,
            mode="new",
            page_title="새 뉴스 작성",
            form_action="/admin/news/new",
            post=news_service.empty_post_form(),
            errors={},
        ),
    )


@router.post("/admin/news/new")
async def admin_news_create(request: Request):
    form = await read_form_data(request)
    admin = require_admin_csrf(request, form)
    data, errors = news_service.build_post_data(form)
    if errors:
        post = news_service.empty_post_form()
        post.update(data)
        return templates.TemplateResponse(
            request,
            "news/admin_form.html",
            admin_context(
                request,
                admin,
                mode="new",
                page_title="새 뉴스 작성",
                form_action="/admin/news/new",
                post=post,
                errors=errors,
            ),
            status_code=400,
        )

    news_service.create_post(data)
    return RedirectResponse(url="/admin/news", status_code=303)


@router.get("/admin/news/{post_id}/edit", response_class=HTMLResponse)
def admin_news_edit(request: Request, post_id: int):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/news", status_code=303)
    post = news_service.get_admin_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="news post not found")
    return templates.TemplateResponse(
        request,
        "news/admin_form.html",
        admin_context(
            request,
            admin,
            mode="edit",
            page_title="뉴스 수정",
            form_action=f"/admin/news/{post_id}/edit",
            post=post,
            errors={},
        ),
    )


@router.post("/admin/news/{post_id}/edit")
async def admin_news_update(request: Request, post_id: int):
    form = await read_form_data(request)
    admin = require_admin_csrf(request, form)
    existing = news_service.get_admin_post(post_id)
    if not existing:
        raise HTTPException(status_code=404, detail="news post not found")

    data, errors = news_service.build_post_data(form, existing=existing)
    if errors:
        post = dict(existing)
        post.update(data)
        return templates.TemplateResponse(
            request,
            "news/admin_form.html",
            admin_context(
                request,
                admin,
                mode="edit",
                page_title="뉴스 수정",
                form_action=f"/admin/news/{post_id}/edit",
                post=post,
                errors=errors,
            ),
            status_code=400,
        )

    news_service.update_post(post_id, data)
    return RedirectResponse(url="/admin/news", status_code=303)


@router.post("/admin/news/{post_id}/delete")
async def admin_news_delete(request: Request, post_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    news_service.delete_post(post_id)
    return RedirectResponse(url="/admin/news", status_code=303)


@router.post("/admin/news/{post_id}/toggle-public")
async def admin_news_toggle_public(request: Request, post_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    news_service.toggle_public(post_id)
    return RedirectResponse(url="/admin/news", status_code=303)


@router.post("/admin/news/{post_id}/toggle-pin")
async def admin_news_toggle_pin(request: Request, post_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    news_service.toggle_pin(post_id)
    return RedirectResponse(url="/admin/news", status_code=303)


@router.post("/admin/news/comments/{comment_id}/hide")
async def admin_comment_hide(request: Request, comment_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    news_service.set_comment_hidden(comment_id, True)
    return RedirectResponse(url="/admin/news#comments", status_code=303)


@router.post("/admin/news/comments/{comment_id}/unhide")
async def admin_comment_unhide(request: Request, comment_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    news_service.set_comment_hidden(comment_id, False)
    return RedirectResponse(url="/admin/news#comments", status_code=303)


@router.post("/admin/news/comments/{comment_id}/delete")
async def admin_comment_delete(request: Request, comment_id: int):
    form = await read_form_data(request)
    require_admin_csrf(request, form)
    news_service.delete_comment(comment_id)
    return RedirectResponse(url="/admin/news#comments", status_code=303)
