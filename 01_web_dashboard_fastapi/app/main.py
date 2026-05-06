from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

from fastapi import Body, Depends, FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.command import get_service_state, handle_command
from app.event import add_event, get_events
from app.logs import read_logs, write_log
from app.security import (
    clear_session_cookie,
    get_current_user,
    require_auth,
    set_session_cookie,
    verify_login,
)
from app.status import get_system_status


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
STATIC_DIR = PROJECT_DIR / "static"
TEMPLATE_DIR = PROJECT_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    write_log("FastAPI dashboard started")
    yield
    write_log("FastAPI dashboard stopped")


app = FastAPI(
    title="Raspberry Pi Control Dashboard",
    version="0.3.0",
    lifespan=lifespan,
)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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
def api_event(
    payload: Dict[str, Any] = Body(...),
    username: str = Depends(require_auth),
):
    return add_event(payload, username=username)


@app.get("/api/events")
def api_events(username: str = Depends(require_auth)):
    return {
        "ok": True,
        "events": get_events(),
    }
