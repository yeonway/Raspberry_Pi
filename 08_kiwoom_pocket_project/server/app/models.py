from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class WatchStock(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("code", name="uq_watchlist_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    market: Mapped[str] = mapped_column(String(20), default="KRX")
    memo: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class RecentQuote(Base):
    __tablename__ = "recent_quotes"

    code: Mapped[str] = mapped_column(String(16), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    price: Mapped[int] = mapped_column(Integer, default=0)
    change_price: Mapped[int] = mapped_column(Integer, default=0)
    change_rate: Mapped[str] = mapped_column(String(24), default="0.00")
    volume: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class OrderLog(Base):
    __tablename__ = "order_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mode: Mapped[str] = mapped_column(String(12))
    side: Mapped[str] = mapped_column(String(8))
    code: Mapped[str] = mapped_column(String(16), index=True)
    qty: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    order_type: Mapped[str] = mapped_column(String(24))
    request_json: Mapped[str] = mapped_column(Text)
    response_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
