import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app.logs import write_log
from app.security import env_bool


SERVICE_STATE = {
    "minecraft_server": "unknown",
    "last_backup_request": None,
    "last_backup_file": None,
}


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_CONTROL_SCRIPT = PROJECT_ROOT / "02_autorun_monitor_recovery" / "scripts" / "service_control.py"
BACKUP_SCRIPT = PROJECT_ROOT / "03_backup_to_nas" / "scripts" / "backup.py"

SERVICE_COMMANDS = {
    "minecraft_start": ("Minecraft 서버 시작", "minecraft", "start"),
    "minecraft_stop": ("Minecraft 서버 중지", "minecraft", "stop"),
    "minecraft_restart": ("Minecraft 서버 재시작", "minecraft", "restart"),
    "minecraft_status": ("Minecraft 서버 상태 확인", "minecraft", "status"),
}


def get_service_state():
    refresh_minecraft_state()
    return dict(SERVICE_STATE)


def command_enabled(name: str, default: bool = False) -> bool:
    return env_bool(name, default)


def can_use_systemctl() -> bool:
    return os.name != "nt" and shutil.which("systemctl") is not None


def parse_json_from_stdout(stdout: str):
    text = (stdout or "").strip()

    if not text:
        return {}

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        return {}

    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}


def run_python_script(script: Path, args, timeout: int):
    if not script.exists():
        return {
            "ok": False,
            "message": f"script not found: {script}",
            "stdout": "",
            "stderr": "",
        }

    try:
        result = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=str(script.parent.parent),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as e:
        return {
            "ok": False,
            "message": str(e),
            "stdout": "",
            "stderr": str(e),
        }

    parsed = parse_json_from_stdout(result.stdout)
    if parsed:
        parsed.setdefault("ok", result.returncode == 0)
        parsed.setdefault("stdout", result.stdout.strip())
        parsed.setdefault("stderr", result.stderr.strip())
        return parsed

    return {
        "ok": result.returncode == 0,
        "message": result.stdout.strip() or result.stderr.strip(),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def state_from_systemctl_result(result):
    state = result.get("state")

    if state == "active":
        return "running"

    if state == "inactive":
        return "stopped"

    if state:
        return state

    if result.get("active") is True:
        return "running"

    if result.get("active") is False:
        return "stopped"

    return "unknown"


def refresh_minecraft_state():
    if not command_enabled("DASHBOARD_ENABLE_SYSTEMCTL", False):
        return

    if not can_use_systemctl():
        return

    result = run_python_script(SERVICE_CONTROL_SCRIPT, ["minecraft", "status"], timeout=20)

    if result.get("ok") or result.get("state"):
        SERVICE_STATE["minecraft_server"] = state_from_systemctl_result(result)


def handle_minecraft_command(command: str, username: str):
    label, service_key, action = SERVICE_COMMANDS[command]

    if not command_enabled("DASHBOARD_ENABLE_SYSTEMCTL", False):
        if action == "start":
            SERVICE_STATE["minecraft_server"] = "start_requested"
        elif action == "stop":
            SERVICE_STATE["minecraft_server"] = "stop_requested"
        elif action == "restart":
            SERVICE_STATE["minecraft_server"] = "restart_requested"

        write_log(f"command received: {command} / {label} / user={username} / real_execution=false")

        return {
            "ok": True,
            "message": f"{label} 요청 기록됨. 실제 systemd 제어는 비활성화되어 있습니다.",
            "command": command,
            "services": get_service_state(),
            "real_execution": False,
        }

    if not can_use_systemctl():
        write_log(f"systemctl unavailable for command: {command} / user={username}", "WARN")
        return {
            "ok": False,
            "message": "현재 환경에서 systemctl을 사용할 수 없습니다.",
            "command": command,
            "services": get_service_state(),
            "real_execution": False,
        }

    result = run_python_script(SERVICE_CONTROL_SCRIPT, [service_key, action], timeout=30)
    SERVICE_STATE["minecraft_server"] = state_from_systemctl_result(result)

    if result.get("ok"):
        write_log(f"command executed: {command} / {label} / user={username}")
    else:
        write_log(f"command failed: {command} / {label} / user={username} / {result.get('stderr')}", "WARN")

    return {
        "ok": result.get("ok", False),
        "message": f"{label} 완료" if result.get("ok") else f"{label} 실패",
        "command": command,
        "services": get_service_state(),
        "real_execution": True,
        "result": result,
    }


def handle_backup_command(username: str):
    SERVICE_STATE["last_backup_request"] = datetime.now().isoformat(timespec="seconds")

    if not command_enabled("DASHBOARD_ENABLE_BACKUP", True):
        write_log(f"backup command blocked by config / user={username}", "WARN")
        return {
            "ok": False,
            "message": "백업 실행이 설정에서 비활성화되어 있습니다.",
            "command": "backup_run",
            "services": get_service_state(),
            "real_execution": False,
        }

    result = run_python_script(BACKUP_SCRIPT, [], timeout=600)

    if result.get("ok"):
        SERVICE_STATE["last_backup_file"] = result.get("backup_file")
        write_log(f"backup command executed / user={username} / file={result.get('backup_file')}")
    else:
        write_log(f"backup command failed / user={username} / {result.get('message')}", "WARN")

    return {
        "ok": result.get("ok", False),
        "message": "NAS 백업 초안 실행 완료" if result.get("ok") else "NAS 백업 초안 실행 실패",
        "command": "backup_run",
        "services": get_service_state(),
        "real_execution": True,
        "result": result,
    }


def handle_command(command: str, username: str = "unknown"):
    command = (command or "").strip()

    if command in SERVICE_COMMANDS:
        return handle_minecraft_command(command, username)

    if command == "backup_run":
        return handle_backup_command(username)

    write_log(f"unknown command received: {command} / user={username}", "WARN")
    return {
        "ok": False,
        "message": "알 수 없는 명령입니다.",
        "command": command,
    }
