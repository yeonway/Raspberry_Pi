from typing import Dict
from urllib.parse import parse_qs, urlencode, quote_plus

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app import news_service


router = APIRouter()
templates = Jinja2Templates(directory=str(news_service.PROJECT_DIR / "templates"))
templates.env.filters["urlencode"] = quote_plus


async def read_form_data(request: Request) -> Dict[str, str]:
    body = await request.body()
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


@router.get("/news", response_class=HTMLResponse)
def news_list(request: Request, category: str = "", q: str = "", page: int = 1):
    result = news_service.list_public_posts(category=category, query=q, page=page)
    posts = result["posts"]
    featured_post = posts[0] if page == 1 and posts else None
    card_posts = posts[1:] if featured_post else posts

    return templates.TemplateResponse(
        request,
        "news/list.html",
        {
            "request": request,
            **result,
            "today_label": news_service.today_label(),
            "categories": news_service.public_categories(),
            "selected_category": category.strip()[:40],
            "query": q.strip()[:80],
            "featured_post": featured_post,
            "posts": card_posts,
        },
    )


@router.head("/news")
def news_list_head():
    news_service.ensure_news_tables()
    return Response(status_code=200)


@router.get("/news/{slug}", response_class=HTMLResponse)
def news_detail(request: Request, slug: str):
    post = news_service.get_public_post(slug, increment_view=True)
    if not post:
        raise HTTPException(status_code=404, detail="news post not found")

    comments = news_service.get_public_comments(int(post["id"]))
    adjacent = news_service.get_adjacent_public_posts(int(post["id"]))
    return templates.TemplateResponse(
        request,
        "news/detail.html",
        {
            "request": request,
            "post": post,
            "comments": comments,
            "previous_post": adjacent["previous"],
            "next_post": adjacent["next"],
            "comment_error": request.query_params.get("comment_error", ""),
            "comment_success": request.query_params.get("comment_success", ""),
        },
    )


@router.post("/news/{slug}/comments")
async def create_comment(request: Request, slug: str):
    form = await read_form_data(request)
    client_host = request.client.host if request.client else ""
    ip_hash, user_agent_hash = news_service.client_identity(request.headers, client_host)
    ok, message = news_service.add_comment(
        slug=slug,
        author_name=form.get("author_name", ""),
        content=form.get("content", ""),
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
    )
    if not ok:
        return RedirectResponse(
            url=f"/news/{slug}?{urlencode({'comment_error': message})}#comments",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/news/{slug}?{urlencode({'comment_success': message})}#comments",
        status_code=303,
    )
