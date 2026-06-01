from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.services.ai_jobs import run_ai_jobs_once
from app.services.collection import run_collectors_once
from app.services.telegram_digest import send_digest_once


logger = logging.getLogger(__name__)


def start_scheduler(settings: Settings):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning("APScheduler is not installed; scheduler disabled")
        return None

    scheduler = BackgroundScheduler(timezone="UTC")

    def run_async(coro):
        asyncio.run(coro)

    scheduler.add_job(lambda: run_async(run_collectors_once(settings, only={"GDELT"})), "interval", minutes=30, id="collect-gdelt", replace_existing=True)
    scheduler.add_job(lambda: run_async(run_collectors_once(settings, only={"Hacker News"})), "interval", hours=1, id="collect-hn", replace_existing=True)
    scheduler.add_job(lambda: run_async(run_collectors_once(settings, only={"arXiv"})), "interval", hours=24, id="collect-arxiv", replace_existing=True)
    scheduler.add_job(lambda: run_async(run_collectors_once(settings, only={"FRED"})), "interval", hours=24, id="collect-fred", replace_existing=True)
    scheduler.add_job(lambda: run_async(run_collectors_once(settings, only={"SEC EDGAR"})), "interval", hours=1, id="collect-sec", replace_existing=True)
    scheduler.add_job(lambda: run_async(run_ai_jobs_once(settings, limit=10)), "interval", minutes=5, id="ai-scoring", replace_existing=True)
    scheduler.add_job(lambda: run_async(send_digest_once(settings)), "interval", minutes=settings.news_digest_interval_minutes, id="telegram-digest", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
