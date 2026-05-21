from typing import Dict, Tuple
from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app import community_service


router = APIRouter()
templates = Jinja2Templates(directory=str(community_service.PROJECT_DIR / "templates"))


async def read_form_data(request: Request) -> Dict[str, str]:
    body = await request.body()
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def client_context(request: Request) -> Tuple[str, str, str]:
    raw_session = community_service.session_id_from_cookie(request.cookies.get("community_session", ""))
    client_host = request.client.host if request.client else ""
    ip_hash, _ = community_service.client_identity(request.headers, client_host)
    return raw_session, community_service.session_hash(raw_session), ip_hash


def identity_hashes(request: Request) -> Tuple[str, str]:
    return community_service.client_identity(request.headers, request.client.host if request.client else "")


def with_session_cookie(response: Response, session_id: str) -> Response:
    response.set_cookie(
        key="community_session",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 365,
        path="/community",
    )
    return response


def append_message(url: str, key: str, message: str) -> str:
    anchor = ""
    if "#" in url:
        url, anchor = url.split("#", 1)
        anchor = f"#{anchor}"
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode({key: message})}{anchor}"


@router.get("/news")
def redirect_news():
    return RedirectResponse(url="/community", status_code=302)


@router.get("/admin/news")
def redirect_admin_news():
    return RedirectResponse(url="/admin/community", status_code=302)


@router.get("/community", response_class=HTMLResponse)
def community_home(request: Request):
    community_service.ensure_community_tables()
    session_id, _, _ = client_context(request)
    response = templates.TemplateResponse(
        request,
        "community/home.html",
        {"request": request, **community_service.home_data()},
    )
    return with_session_cookie(response, session_id)


@router.head("/community")
def community_home_head():
    community_service.ensure_community_tables()
    return Response(status_code=200)


@router.get("/community/boards/{board_slug}", response_class=HTMLResponse)
def community_board(request: Request, board_slug: str, q: str = "", sort: str = "latest", offset: int = 0):
    board = community_service.get_board(board_slug)
    if not board:
        raise HTTPException(status_code=404, detail="board not found")
    session_id, _, _ = client_context(request)
    response = templates.TemplateResponse(
        request,
        "community/board.html",
        {
            "request": request,
            "board": board,
            "boards": community_service.boards(),
            "list_base_url": f"/community/boards/{board_slug}?q={q}&sort={sort}",
            **community_service.list_posts(board_slug=board_slug, query=q, sort=sort, offset=offset),
        },
    )
    return with_session_cookie(response, session_id)


@router.get("/community/posts/{post_id}", response_class=HTMLResponse)
def community_post_detail(request: Request, post_id: int):
    post = community_service.get_public_post(post_id, increment_view=True)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    session_id, _, _ = client_context(request)
    response = templates.TemplateResponse(
        request,
        "community/detail.html",
        {
            "request": request,
            "post": post,
            "comments": community_service.get_comments(post_id),
            "report_reasons": community_service.REPORT_REASONS,
            "message": request.query_params.get("message", ""),
            "error": request.query_params.get("error", ""),
        },
    )
    return with_session_cookie(response, session_id)


@router.get("/community/posts/{post_id}/edit", response_class=HTMLResponse)
def community_edit_post(request: Request, post_id: int):
    post = community_service.get_public_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    session_id, _, _ = client_context(request)
    response = templates.TemplateResponse(
        request,
        "community/edit.html",
        {"request": request, "post": post, "error": ""},
    )
    return with_session_cookie(response, session_id)


@router.post("/community/posts/{post_id}/edit")
async def community_update_post(request: Request, post_id: int):
    form = await read_form_data(request)
    session_id, _, _ = client_context(request)
    ok, message = community_service.update_post_with_password(
        post_id,
        form,
        request.headers,
        request.client.host if request.client else "",
        session_id,
    )
    if ok:
        if not community_service.get_public_post(post_id):
            return with_session_cookie(
                RedirectResponse(url=f"/community?{urlencode({'message': message})}", status_code=303),
                session_id,
            )
        return with_session_cookie(
            RedirectResponse(url=f"/community/posts/{post_id}?{urlencode({'message': message})}", status_code=303),
            session_id,
        )
    post = community_service.get_public_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    post.update({"title": form.get("title", ""), "content": form.get("content", "")})
    response = templates.TemplateResponse(
        request,
        "community/edit.html",
        {"request": request, "post": post, "error": message},
        status_code=400,
    )
    return with_session_cookie(response, session_id)


@router.post("/community/posts/{post_id}/delete")
async def community_delete_post(request: Request, post_id: int):
    form = await read_form_data(request)
    session_id, _, _ = client_context(request)
    ok, message = community_service.delete_post_with_password(post_id, form.get("password", ""))
    target = "/community" if ok else f"/community/posts/{post_id}"
    return with_session_cookie(
        RedirectResponse(url=f"{target}?{urlencode({'message' if ok else 'error': message})}", status_code=303),
        session_id,
    )


@router.get("/community/write", response_class=HTMLResponse)
def community_write(request: Request, board: str = ""):
    session_id, _, _ = client_context(request)
    response = templates.TemplateResponse(
        request,
        "community/write.html",
        {
            "request": request,
            "boards": community_service.public_write_boards(),
            "selected_board": board,
            "errors": {},
            "form": {},
        },
    )
    return with_session_cookie(response, session_id)


@router.head("/community/write")
def community_write_head():
    community_service.ensure_community_tables()
    return Response(status_code=200)


@router.post("/community/write")
async def community_create_post(request: Request):
    form = await read_form_data(request)
    session_id, _, _ = client_context(request)
    ok, message, post_id = community_service.create_post(
        form,
        request.headers,
        request.client.host if request.client else "",
        session_id,
    )
    if ok and post_id:
        if "검토" in message:
            return with_session_cookie(
                RedirectResponse(url=f"/community?{urlencode({'message': message})}", status_code=303),
                session_id,
            )
        return with_session_cookie(
            RedirectResponse(url=f"/community/posts/{post_id}?{urlencode({'message': message})}", status_code=303),
            session_id,
        )
    response = templates.TemplateResponse(
        request,
        "community/write.html",
        {
            "request": request,
            "boards": community_service.public_write_boards(),
            "selected_board": form.get("board_slug", ""),
            "errors": {"form": message},
            "form": form,
        },
        status_code=400,
    )
    return with_session_cookie(response, session_id)


@router.post("/community/posts/{post_id}/comments")
async def community_add_comment(request: Request, post_id: int):
    form = await read_form_data(request)
    session_id, _, _ = client_context(request)
    ok, message = community_service.add_comment(
        post_id,
        form.get("content", ""),
        form.get("password", ""),
        request.headers,
        request.client.host if request.client else "",
        session_id,
    )
    key = "message" if ok else "error"
    return with_session_cookie(
        RedirectResponse(url=f"/community/posts/{post_id}?{urlencode({key: message})}#comments", status_code=303),
        session_id,
    )


@router.post("/community/comments/{comment_id}/edit")
async def community_edit_comment(request: Request, comment_id: int):
    form = await read_form_data(request)
    session_id, _, _ = client_context(request)
    ok, message, post_id = community_service.update_comment_with_password(
        comment_id,
        form.get("content", ""),
        form.get("password", ""),
        request.headers,
        request.client.host if request.client else "",
        session_id,
    )
    target = f"/community/posts/{post_id}#comments" if post_id else request.headers.get("referer", "/community")
    return with_session_cookie(
        RedirectResponse(url=append_message(target, "message" if ok else "error", message), status_code=303),
        session_id,
    )


@router.post("/community/comments/{comment_id}/delete")
async def community_delete_comment(request: Request, comment_id: int):
    form = await read_form_data(request)
    session_id, _, _ = client_context(request)
    ok, message, post_id = community_service.delete_comment_with_password(comment_id, form.get("password", ""))
    target = f"/community/posts/{post_id}#comments" if post_id else request.headers.get("referer", "/community")
    return with_session_cookie(
        RedirectResponse(url=append_message(target, "message" if ok else "error", message), status_code=303),
        session_id,
    )


@router.post("/community/posts/{post_id}/react")
async def community_react_post(request: Request, post_id: int):
    session_id, session_hash, ip_hash = client_context(request)
    _, user_agent_hash = identity_hashes(request)
    ok, message = community_service.react("post", post_id, ip_hash, user_agent_hash, session_hash)
    return with_session_cookie(
        RedirectResponse(url=f"/community/posts/{post_id}?{urlencode({'message' if ok else 'error': message})}", status_code=303),
        session_id,
    )


@router.post("/community/comments/{comment_id}/react")
async def community_react_comment(request: Request, comment_id: int):
    session_id, session_hash, ip_hash = client_context(request)
    _, user_agent_hash = identity_hashes(request)
    ok, message = community_service.react("comment", comment_id, ip_hash, user_agent_hash, session_hash)
    target = request.headers.get("referer", "/community")
    return with_session_cookie(
        RedirectResponse(url=append_message(target, "message" if ok else "error", message), status_code=303),
        session_id,
    )


@router.post("/community/posts/{post_id}/report")
async def community_report_post(request: Request, post_id: int):
    form = await read_form_data(request)
    session_id, session_hash, ip_hash = client_context(request)
    _, user_agent_hash = identity_hashes(request)
    ok, message = community_service.report(
        "post", post_id, form.get("reason", ""), form.get("detail", ""), ip_hash, user_agent_hash, session_hash
    )
    return with_session_cookie(
        RedirectResponse(url=f"/community/posts/{post_id}?{urlencode({'message' if ok else 'error': message})}", status_code=303),
        session_id,
    )


@router.post("/community/comments/{comment_id}/report")
async def community_report_comment(request: Request, comment_id: int):
    form = await read_form_data(request)
    session_id, session_hash, ip_hash = client_context(request)
    _, user_agent_hash = identity_hashes(request)
    ok, message = community_service.report(
        "comment", comment_id, form.get("reason", ""), form.get("detail", ""), ip_hash, user_agent_hash, session_hash
    )
    target = request.headers.get("referer", "/community")
    return with_session_cookie(
        RedirectResponse(url=append_message(target, "message" if ok else "error", message), status_code=303),
        session_id,
    )


@router.get("/community/search", response_class=HTMLResponse)
def community_search(request: Request, q: str = "", board: str = "", sort: str = "latest", offset: int = 0):
    session_id, _, _ = client_context(request)
    response = templates.TemplateResponse(
        request,
        "community/search.html",
        {
            "request": request,
            "boards": community_service.boards(),
            "selected_board": board,
            "list_base_url": f"/community/search?q={q}&board={board}&sort={sort}",
            **community_service.list_posts(board_slug=board, query=q, sort=sort, offset=offset),
        },
    )
    return with_session_cookie(response, session_id)


@router.get("/community/rules", response_class=HTMLResponse)
def community_rules(request: Request):
    session_id, _, _ = client_context(request)
    response = templates.TemplateResponse(request, "community/rules.html", {"request": request})
    return with_session_cookie(response, session_id)


@router.get("/community/privacy", response_class=HTMLResponse)
def community_privacy(request: Request):
    session_id, _, _ = client_context(request)
    response = templates.TemplateResponse(request, "community/privacy.html", {"request": request})
    return with_session_cookie(response, session_id)
