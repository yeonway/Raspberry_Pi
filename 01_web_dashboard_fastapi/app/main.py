from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

from fastapi import Body, Depends, FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.admin_news import router as admin_news_router
from app.ai_queue import (
    run_admin_rcon_command,
    start_worker,
    status as ai_queue_status,
    stop_worker,
    submit_event,
)
from app.command import get_service_state, handle_command
from app.coordinate_sync import sync_coordinates_to_phone
from app.event import add_event, get_events
from app.logs import read_logs, write_log
from app.news import router as news_router
from app.phone_ai import ask_phone_ai
from app.security import (
    clear_session_cookie,
    get_current_user,
    is_dashboard_auth_public_path,
    require_auth,
    set_session_cookie,
    verify_login,
)
from app.service_auth import require_event_token
from app.status import get_system_status


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
STATIC_DIR = PROJECT_DIR / "static"
TEMPLATE_DIR = PROJECT_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    write_log("FastAPI dashboard started")
    await start_worker()
    yield
    await stop_worker()
    write_log("FastAPI dashboard stopped")


app = FastAPI(
    title="Raspberry Pi Control Dashboard",
    version="0.3.0",
    lifespan=lifespan,
)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


app.include_router(news_router)
app.include_router(admin_news_router)


@app.middleware("http")
async def mark_public_news_paths(request: Request, call_next):
    if is_dashboard_auth_public_path(request.url.path):
        request.scope["dashboard_auth_public"] = True
        request.state.dashboard_auth_public = True
    return await call_next(request)


@app.get("/")
def index():
    return FileResponse(TEMPLATE_DIR / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "message": "dashboard server is running"}


@app.post("/api/auth/login")
def api_login(response: Response, payload: Dict[str, Any] = Body(...)):
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    if not verify_login(username, password):
        write_log(f"login failed: user={username}", "WARN")
        return {"ok": False, "message": "아이디 또는 비밀번호가 올바르지 않습니다."}

    set_session_cookie(response, username)
    write_log(f"login success: user={username}")

    return {"ok": True, "message": "로그인 성공", "username": username}


@app.post("/api/auth/logout")
def api_logout(response: Response, request: Request):
    username = get_current_user(request) or "unknown"
    clear_session_cookie(response)
    write_log(f"logout: user={username}")
    return {"ok": True, "message": "로그아웃 완료"}


@app.get("/api/auth/me")
def api_me(request: Request):
    username = get_current_user(request)
    return {
        "ok": True,
        "authenticated": username is not None,
        "username": username,
    }


@app.get("/api/status")
def api_status(username: str = Depends(require_auth)):
    return {
        "ok": True,
        "user": username,
        "system": get_system_status(),
        "services": get_service_state(),
    }


@app.get("/api/logs")
def api_logs(lines: int = 100, username: str = Depends(require_auth)):
    return {
        "ok": True,
        "logs": read_logs(lines),
    }


@app.post("/api/command")
def api_command(
    payload: Dict[str, Any] = Body(...),
    username: str = Depends(require_auth),
):
    command = payload.get("command", "")
    return handle_command(command, username=username)


@app.post("/api/minecraft/start")
def api_minecraft_start(username: str = Depends(require_auth)):
    return handle_command("minecraft_start", username=username)


@app.post("/api/minecraft/stop")
def api_minecraft_stop(username: str = Depends(require_auth)):
    return handle_command("minecraft_stop", username=username)


@app.post("/api/minecraft/restart")
def api_minecraft_restart(username: str = Depends(require_auth)):
    return handle_command("minecraft_restart", username=username)


@app.get("/api/minecraft/status")
def api_minecraft_status(username: str = Depends(require_auth)):
    return handle_command("minecraft_status", username=username)


@app.post("/api/backup/run")
def api_backup_run(username: str = Depends(require_auth)):
    return handle_command("backup_run", username=username)


@app.post("/api/event")
async def api_event(
    payload: Dict[str, Any] = Body(...),
    username: str = Depends(require_auth),
):
    result = add_event(payload, username=username)
    queue_result = await submit_event(payload, source=f"dashboard:{username}")
    result["queue"] = queue_result
    return result


@app.get("/api/events")
def api_events(username: str = Depends(require_auth)):
    return {
        "ok": True,
        "events": get_events(),
    }


@app.post("/event")
async def event_ingest(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    client: str = Depends(require_event_token),
):
    add_result = add_event(payload, username=client)
    queue_result = await submit_event(payload, source=client)
    return {
        "ok": True,
        "event": add_result["event"],
        "queue": queue_result,
    }


@app.get("/event/status")
def event_status(client: str = Depends(require_event_token)):
    return ai_queue_status(include_phone_health=True)


@app.get("/status")
def service_status(client: str = Depends(require_event_token)):
    return {
        "ok": True,
        "system": get_system_status(),
        "services": get_service_state(),
        "ai": ai_queue_status(include_phone_health=True),
    }


@app.get("/logs")
def service_logs(lines: int = 100, client: str = Depends(require_event_token)):
    return {
        "ok": True,
        "logs": read_logs(lines),
    }


@app.post("/ai-proxy")
def service_ai_proxy(
    payload: Dict[str, Any] = Body(...),
    client: str = Depends(require_event_token),
):
    write_log("AI proxy request from service event token")
    return ask_phone_ai(payload)


@app.post("/coordinate-sync")
def service_coordinate_sync(client: str = Depends(require_event_token)):
    return sync_coordinates_to_phone(force=True)


@app.post("/command")
def service_command(
    payload: Dict[str, Any] = Body(...),
    client: str = Depends(require_event_token),
):
    command = str(payload.get("command", ""))
    return run_admin_rcon_command(command)


@app.get("/api/ai/status")
def api_ai_status(username: str = Depends(require_auth)):
    return ai_queue_status(include_phone_health=True)


@app.post("/api/ai-proxy")
def api_ai_proxy(
    payload: Dict[str, Any] = Body(...),
    username: str = Depends(require_auth),
):
    write_log(f"AI proxy request from dashboard / user={username}")
    return ask_phone_ai(payload)


@app.post("/api/coordinates/sync-phone")
def api_coordinate_sync(username: str = Depends(require_auth)):
    write_log(f"Coordinate sync requested from dashboard / user={username}")
    return sync_coordinates_to_phone(force=True)


@app.post("/api/minecraft/rcon")
def api_minecraft_rcon(
    payload: Dict[str, Any] = Body(...),
    username: str = Depends(require_auth),
):
    command = str(payload.get("command", ""))
    result = run_admin_rcon_command(command)
    result["user"] = username
    return result
