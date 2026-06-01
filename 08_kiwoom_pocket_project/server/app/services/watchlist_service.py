from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.schemas import WatchStockCreate
from app.services.stock_service import SAMPLE_STOCKS


def list_watchlist(db: Session) -> list[models.WatchStock]:
    return list(db.scalars(select(models.WatchStock).order_by(models.WatchStock.created_at.desc())).all())


def add_watch_stock(db: Session, payload: WatchStockCreate) -> models.WatchStock:
    code = payload.code.strip()
    existing = db.scalar(select(models.WatchStock).where(models.WatchStock.code == code))
    if existing:
        existing.name = payload.name or existing.name
        existing.market = payload.market or existing.market
        existing.memo = payload.memo
        db.commit()
        db.refresh(existing)
        return existing

    sample = SAMPLE_STOCKS.get(code, {})
    item = models.WatchStock(
        code=code,
        name=payload.name or sample.get("name", code),
        market=payload.market or "KRX",
        memo=payload.memo,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_watch_stock(db: Session, code: str) -> bool:
    item = db.scalar(select(models.WatchStock).where(models.WatchStock.code == code))
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True
