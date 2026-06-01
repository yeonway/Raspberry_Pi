from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import load_settings
from app.database import initialize_database
from app.services.scheduler import start_scheduler
from app.web.routes import router


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    initialize_database(settings.database_path)
    scheduler = start_scheduler(settings) if settings.scheduler_enabled else None
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(title="AI 뉴스 레이더", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(router)

    @app.get("/health")
    async def health():
        return {"ok": True, "service": "pi-news-radar"}

    return app


app = create_app()
