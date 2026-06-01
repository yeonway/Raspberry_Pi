from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import WatchStockCreate, WatchStockResponse
from app.services import watchlist_service

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchStockResponse])
async def list_watchlist(db: Annotated[Session, Depends(get_db)]) -> list[WatchStockResponse]:
    return watchlist_service.list_watchlist(db)


@router.post("", response_model=WatchStockResponse, status_code=status.HTTP_201_CREATED)
async def add_watch_stock(payload: WatchStockCreate, db: Annotated[Session, Depends(get_db)]) -> WatchStockResponse:
    return watchlist_service.add_watch_stock(db, payload)


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watch_stock(code: str, db: Annotated[Session, Depends(get_db)]) -> None:
    deleted = watchlist_service.delete_watch_stock(db, code)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관심종목을 찾을 수 없습니다.")
