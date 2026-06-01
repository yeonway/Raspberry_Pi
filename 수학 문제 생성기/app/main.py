from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import create_db_and_tables
from app.routes import api, web


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    fastapi_app = FastAPI(title=settings.app_name, lifespan=lifespan)
    static_dir = Path(__file__).resolve().parent / "static"
    rendered_dir = Path(__file__).resolve().parent.parent / "data" / "rendered"
    rendered_dir.mkdir(parents=True, exist_ok=True)

    fastapi_app.mount("/static", StaticFiles(directory=static_dir), name="static")
    fastapi_app.mount("/rendered", StaticFiles(directory=rendered_dir), name="rendered")
    fastapi_app.include_router(web.router)
    fastapi_app.include_router(api.router, prefix="/api")
    return fastapi_app


app = create_app()
