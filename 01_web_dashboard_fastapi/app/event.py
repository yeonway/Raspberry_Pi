from datetime import datetime
from typing import Any, Dict, List

from app.logs import write_log


EVENTS: List[Dict[str, Any]] = []


def add_event(payload: Dict[str, Any], username: str = "unknown"):
    event = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "payload": payload,
    }

    EVENTS.append(event)

    if len(EVENTS) > 100:
        EVENTS.pop(0)

    event_type = payload.get("type", "event")
    write_log(f"event received: {event_type} / user={username}")

    return {
        "ok": True,
        "message": "이벤트 수신 완료",
        "event": event,
    }


def get_events():
    return EVENTS[-50:]
