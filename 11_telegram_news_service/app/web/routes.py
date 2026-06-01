from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import load_settings
from app.database import (
    add_keyword,
    connect,
    dashboard_stats,
    delete_keyword,
    get_article,
    list_articles,
    list_digest_logs,
    list_keywords,
    list_source_runs,
    toggle_keyword,
)
from app.services.ai_client import PhoneAiClient
from app.services.ai_jobs import run_ai_jobs_once
from app.services.collection import run_collectors_once
from app.services.telegram_digest import send_digest_once


templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


def _settings():
    return load_settings()


def _check_admin_token(x_admin_token: str | None) -> None:
    settings = _settings()
    if settings.admin_token and x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="invalid admin token")


@router.get("/")
async def index(request: Request, filter: str = "전체"):
    settings = _settings()
    with connect(settings.database_path) as conn:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "active_filter": filter,
                "filters": ["전체", "미국시장", "AI", "반도체", "Database", "개발/인프라", "AI Research", "SEC", "고점수", "미전송", "AI 실패"],
                "articles": list_articles(conn, filter),
                "stats": dashboard_stats(conn),
            },
        )


@router.get("/articles/{article_id}")
async def article_detail(request: Request, article_id: int):
    settings = _settings()
    with connect(settings.database_path) as conn:
        article = get_article(conn, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article not found")
    return templates.TemplateResponse("article_detail.html", {"request": request, "article": article})


@router.get("/keywords")
async def keywords(request: Request):
    settings = _settings()
    with connect(settings.database_path) as conn:
        rows = list_keywords(conn)
    return templates.TemplateResponse("keywords.html", {"request": request, "keywords": rows})


@router.post("/keywords")
async def create_keyword(
    keyword: Annotated[str, Form()],
    group_name: Annotated[str, Form()],
    weight: Annotated[int, Form()] = 10,
    alert_enabled: Annotated[str | None, Form()] = None,
    enabled: Annotated[str | None, Form()] = None,
    x_admin_token: Annotated[str | None, Header()] = None,
):
    _check_admin_token(x_admin_token)
    settings = _settings()
    with connect(settings.database_path) as conn:
        add_keyword(conn, keyword, group_name, weight, alert_enabled == "on", enabled != "off")
    return RedirectResponse("/keywords", status_code=303)


@router.post("/keywords/{keyword_id}/toggle")
async def keyword_toggle(
    keyword_id: int,
    field: Annotated[str, Form()],
    x_admin_token: Annotated[str | None, Header()] = None,
):
    _check_admin_token(x_admin_token)
    settings = _settings()
    with connect(settings.database_path) as conn:
        toggle_keyword(conn, keyword_id, field)
    return RedirectResponse("/keywords", status_code=303)


@router.post("/keywords/{keyword_id}/delete")
async def keyword_delete(keyword_id: int, x_admin_token: Annotated[str | None, Header()] = None):
    _check_admin_token(x_admin_token)
    settings = _settings()
    with connect(settings.database_path) as conn:
        delete_keyword(conn, keyword_id)
    return RedirectResponse("/keywords", status_code=303)


@router.get("/sources")
async def sources(request: Request):
    settings = _settings()
    with connect(settings.database_path) as conn:
        rows = list_source_runs(conn)
    return templates.TemplateResponse("sources.html", {"request": request, "runs": rows})


@router.get("/digests")
async def digests(request: Request):
    settings = _settings()
    with connect(settings.database_path) as conn:
        logs = list_digest_logs(conn)
    return templates.TemplateResponse("digest_logs.html", {"request": request, "logs": logs})


@router.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "settings": _settings()})


@router.post("/admin/collect-once")
async def admin_collect_once(x_admin_token: Annotated[str | None, Header()] = None):
    _check_admin_token(x_admin_token)
    return await run_collectors_once(_settings())


@router.post("/admin/score-once")
async def admin_score_once(x_admin_token: Annotated[str | None, Header()] = None):
    _check_admin_token(x_admin_token)
    return await run_ai_jobs_once(_settings(), limit=20)


@router.post("/admin/send-digest-once")
async def admin_send_digest_once(x_admin_token: Annotated[str | None, Header()] = None):
    _check_admin_token(x_admin_token)
    return await send_digest_once(_settings())


@router.get("/admin/phone-health")
async def admin_phone_health():
    client = PhoneAiClient(_settings())
    return await client.health()


@router.get("/api/articles")
async def api_articles(filter: str = "전체"):
    settings = _settings()
    with connect(settings.database_path) as conn:
        return {"articles": list_articles(conn, filter)}


@router.get("/api/status")
async def api_status():
    settings = _settings()
    with connect(settings.database_path) as conn:
        stats = dashboard_stats(conn)
    return {"ok": True, "stats": stats, "phone_ai_enabled": settings.phone_ai_enabled}
