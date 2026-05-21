import asyncio
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from app.logs import write_log
from app.coordinate_sync import coordinate_sync_status, sync_coordinates_to_phone
from app.phone_ai import ask_phone_ai, phone_ai_configured, phone_ai_health
from app.rcon import RconError, rcon_configured, send_chat_lines, send_rcon_command
from app.security import env_bool


AI_PREFIXES = ("!ai", "@ai")
QUEUE: asyncio.Queue[Dict[str, Any]] | None = None
WORKER_TASK: asyncio.Task | None = None
STATE: Dict[str, Any] = {
    "started": False,
    "current_job": None,
    "processed": 0,
    "failed": 0,
    "last_error": None,
    "last_answer": None,
}


def queue_enabled() -> bool:
    return env_bool("DASHBOARD_ENABLE_AI_EVENT_WORKER", True)


async def start_worker():
    global QUEUE, WORKER_TASK
    if not queue_enabled():
        STATE["started"] = False
        write_log("AI event worker disabled by DASHBOARD_ENABLE_AI_EVENT_WORKER", "WARN")
        return

    if QUEUE is None:
        QUEUE = asyncio.Queue()

    if WORKER_TASK is None or WORKER_TASK.done():
        WORKER_TASK = asyncio.create_task(_worker_loop())
        STATE["started"] = True
        write_log("AI event worker started")


async def stop_worker():
    global WORKER_TASK
    if WORKER_TASK is None:
        return

    WORKER_TASK.cancel()
    try:
        await WORKER_TASK
    except asyncio.CancelledError:
        pass
    WORKER_TASK = None
    STATE["started"] = False
    STATE["current_job"] = None
    write_log("AI event worker stopped")


def status(include_phone_health: bool = False) -> Dict[str, Any]:
    data = {
        "ok": True,
        "worker_started": STATE["started"],
        "queue_size": QUEUE.qsize() if QUEUE is not None else 0,
        "current_job": STATE["current_job"],
        "processed": STATE["processed"],
        "failed": STATE["failed"],
        "last_error": STATE["last_error"],
        "last_answer": STATE["last_answer"],
        "phone_ai_configured": phone_ai_configured(),
        "rcon_configured": rcon_configured(),
        "coordinate_sync": coordinate_sync_status(),
    }

    if include_phone_health and phone_ai_configured():
        try:
            data["phone_ai_health"] = phone_ai_health()
        except Exception as e:
            data["phone_ai_health"] = {"ok": False, "error": str(e)}

    return data


async def submit_event(payload: Dict[str, Any], source: str = "event") -> Dict[str, Any]:
    event = normalize_event(payload, source)
    if not should_enqueue(event):
        return {
            "ok": True,
            "queued": False,
            "message": "event recorded",
            "event": event,
        }

    if QUEUE is None:
        return {
            "ok": False,
            "queued": False,
            "message": "AI event queue is not started",
            "event": event,
        }

    await QUEUE.put(event)
    write_log(f"AI event queued: id={event['id']} player={event.get('player_name')} source={source}")
    return {
        "ok": True,
        "queued": True,
        "queue_size": QUEUE.qsize(),
        "event": event,
    }


def normalize_event(payload: Dict[str, Any], source: str) -> Dict[str, Any]:
    message = str(payload.get("message") or payload.get("text") or "").strip()
    question = strip_ai_prefix(message)

    return {
        "id": str(payload.get("id") or uuid.uuid4()),
        "time": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "type": str(payload.get("type") or "event"),
        "category": str(payload.get("category") or classify_message(message)),
        "player_uuid": str(payload.get("player_uuid") or payload.get("uuid") or ""),
        "player_name": str(payload.get("player_name") or payload.get("player") or "unknown"),
        "message": message,
        "question": question,
        "server_context": str(payload.get("server_context") or ""),
        "coordinate_context": str(payload.get("coordinate_context") or ""),
        "spark_context": str(payload.get("spark_context") or ""),
        "max_tokens": int(payload.get("max_tokens") or os.getenv("PHONE_AI_MAX_TOKENS", "180")),
        "raw": payload,
    }


def classify_message(message: str) -> str:
    lowered = message.strip().lower()
    if any(lowered == prefix or lowered.startswith(prefix + " ") for prefix in AI_PREFIXES):
        return "qa"
    if lowered.startswith("!status"):
        return "system"
    if lowered.startswith("!cmd"):
        return "command"
    return "event"


def strip_ai_prefix(message: str) -> str:
    stripped = message.strip()
    lowered = stripped.lower()
    for prefix in AI_PREFIXES:
        if lowered == prefix:
            return ""
        if lowered.startswith(prefix + " "):
            return stripped[len(prefix) :].strip()
    return stripped


def should_enqueue(event: Dict[str, Any]) -> bool:
    if event["category"] == "qa":
        return bool(event["question"])

    event_type = event["type"].lower()
    return event_type in {"chat_ai", "minecraft_ai", "ai"} and bool(event["question"])


async def _worker_loop():
    assert QUEUE is not None

    while True:
        event = await QUEUE.get()
        STATE["current_job"] = {
            "id": event["id"],
            "player_name": event["player_name"],
            "question": event["question"],
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }

        try:
            await _process_ai_event(event)
            STATE["processed"] += 1
            STATE["last_error"] = None
        except Exception as e:
            STATE["failed"] += 1
            STATE["last_error"] = str(e)
            write_log(f"AI event failed: id={event['id']} error={e}", "ERROR")
            await _safe_send_error(event, str(e))
        finally:
            STATE["current_job"] = None
            QUEUE.task_done()


async def _process_ai_event(event: Dict[str, Any]):
    sync_result = await asyncio.to_thread(sync_coordinates_to_phone)
    if sync_result.get("enabled") and not sync_result.get("ok"):
        write_log(f"Coordinate sync before AI ask failed: {sync_result.get('message')}", "WARN")

    ai_payload = {
        "player_uuid": event["player_uuid"],
        "player_name": event["player_name"],
        "message": event["question"],
        "server_context": event["server_context"],
        "coordinate_context": event["coordinate_context"],
        "spark_context": event["spark_context"],
        "max_tokens": event["max_tokens"],
    }
    response = await asyncio.to_thread(ask_phone_ai, ai_payload)
    answer = str(response.get("answer") or "")
    STATE["last_answer"] = {
        "id": event["id"],
        "player_name": event["player_name"],
        "answer": answer[:300],
        "time": datetime.now().isoformat(timespec="seconds"),
    }
    write_log(f"AI answer received: id={event['id']} player={event['player_name']}")

    if rcon_configured():
        await asyncio.to_thread(send_chat_lines, os.getenv("AI_CHAT_PREFIX", "[AI]"), event["player_name"], answer)
    else:
        write_log("RCON not configured; AI answer was not sent to Minecraft chat", "WARN")


async def _safe_send_error(event: Dict[str, Any], error: str):
    if not rcon_configured():
        return
    try:
        await asyncio.to_thread(
            send_chat_lines,
            os.getenv("AI_CHAT_PREFIX", "[AI]"),
            event["player_name"],
            f"AI request failed: {error}",
        )
    except Exception:
        pass


def run_admin_rcon_command(command: str) -> Dict[str, Any]:
    if not env_bool("DASHBOARD_ENABLE_RCON_COMMANDS", False):
        return {
            "ok": False,
            "message": "RCON command execution is disabled",
        }

    command = (command or "").strip()
    if not command:
        return {
            "ok": False,
            "message": "command is empty",
        }

    try:
        output = send_rcon_command(command)
        write_log(f"RCON command executed from dashboard: {command}")
        return {
            "ok": True,
            "command": command,
            "output": output,
        }
    except RconError as e:
        write_log(f"RCON command failed: {command} / {e}", "WARN")
        return {
            "ok": False,
            "command": command,
            "message": str(e),
        }
