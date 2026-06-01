import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.config import Settings, get_settings
from app.security import validate_ws_token
from app.services.stock_service import sample_quote

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/realtime")
async def realtime_ws(websocket: WebSocket, settings: Annotated[Settings, Depends(get_settings)]) -> None:
    auth_header = websocket.headers.get("authorization")
    query_token = websocket.query_params.get("token")
    if not validate_ws_token(auth_header, query_token, settings):
        await websocket.close(code=1008, reason="인증 토큰이 올바르지 않습니다.")
        return

    await websocket.accept()
    await websocket.send_json({"type": "connected", "message": "실시간 시세 중계 서버에 연결되었습니다.", "mode": settings.kiwoom_mode})
    subscribed: list[str] = []
    try:
        while True:
            try:
                payload = await asyncio.wait_for(websocket.receive_json(), timeout=5)
                if payload.get("action") == "subscribe":
                    subscribed = [str(code) for code in payload.get("codes", [])]
                    await websocket.send_json({"type": "subscribed", "codes": subscribed})
            except asyncio.TimeoutError:
                pass

            for code in subscribed[:20]:
                quote = sample_quote(code)
                await websocket.send_json({"type": "quote", "data": quote.model_dump(mode="json")})
    except WebSocketDisconnect:
        return
