import json
import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "service_state.json"


DEFAULT_CONFIG = {
    "dashboard": {
        "service": "dashboard.service",
        "desired": True
    },
    "minecraft": {
        "service": "minecraft.service",
        "desired": True
    }
}


ALLOWED_ACTIONS = {
    "start",
    "stop",
    "restart",
    "status"
}


def ensure_config():
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)


def load_config():
    ensure_config()

    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        sanitized = {}

        for key, value in DEFAULT_CONFIG.items():
            sanitized[key] = data.get(key, value)

        if sanitized != data:
            save_config(sanitized)

        return sanitized

    except Exception:
        return DEFAULT_CONFIG


def save_config(data):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    CONFIG_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20
        )

        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }

    except Exception as e:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": str(e)
        }


def is_root_user():
    geteuid = getattr(os, "geteuid", None)

    if callable(geteuid):
        return geteuid() == 0

    return False


def systemctl_cmd(action: str, service_name: str):
    cmd = ["systemctl", action, service_name]

    if action in {"start", "stop", "restart"} and not is_root_user():
        return ["sudo", "-n"] + cmd

    return cmd


def run_systemctl(service_key: str, action: str):
    config = load_config()

    if service_key not in config:
        return {
            "ok": False,
            "message": "허용되지 않은 서비스입니다.",
            "service_key": service_key
        }

    if action not in ALLOWED_ACTIONS:
        return {
            "ok": False,
            "message": "허용되지 않은 명령입니다.",
            "action": action
        }

    service_name = config[service_key]["service"]

    if action == "status":
        result = run_cmd(["systemctl", "is-active", service_name])
        state = result["stdout"] or "unknown"

        return {
            "ok": result["returncode"] == 0,
            "service_key": service_key,
            "service": service_name,
            "action": action,
            "active": state == "active",
            "state": state,
            "desired": config[service_key].get("desired", False),
            "stderr": result["stderr"]
        }

    if action in {"start", "restart"}:
        config[service_key]["desired"] = True
        save_config(config)

    if action == "stop":
        config[service_key]["desired"] = False
        save_config(config)

    result = run_cmd(systemctl_cmd(action, service_name))

    return {
        "ok": result["returncode"] == 0,
        "service_key": service_key,
        "service": service_name,
        "action": action,
        "desired": config[service_key].get("desired", False),
        "stdout": result["stdout"],
        "stderr": result["stderr"]
    }


def main():
    if len(sys.argv) != 3:
        print("usage: python service_control.py <dashboard|minecraft> <start|stop|restart|status>")
        sys.exit(1)

    service_key = sys.argv[1]
    action = sys.argv[2]

    result = run_systemctl(service_key, action)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
