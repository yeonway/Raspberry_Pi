import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "logs" / "watchdog.log"
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


def write_log(message: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{now}] {message}\n")


def ensure_config():
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


def load_config():
    ensure_config()

    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        sanitized = {}

        for key, value in DEFAULT_CONFIG.items():
            sanitized[key] = data.get(key, value)

        if sanitized != data:
            CONFIG_FILE.write_text(
                json.dumps(sanitized, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

        return sanitized

    except Exception as e:
        write_log(f"config load failed: {e}")
        return DEFAULT_CONFIG


def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )

        return result.returncode, result.stdout.strip(), result.stderr.strip()

    except Exception as e:
        return 1, "", str(e)


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


def is_active(service_name: str):
    code, out, err = run_cmd(["systemctl", "is-active", service_name])
    return code == 0 and out == "active"


def restart_service(service_name: str):
    write_log(f"{service_name} is not active. restart requested.")

    code, out, err = run_cmd(systemctl_cmd("restart", service_name))

    if code == 0:
        write_log(f"{service_name} restart success")
    else:
        write_log(f"{service_name} restart failed: {err}")


def main():
    write_log("watchdog started")

    while True:
        config = load_config()

        for key, item in config.items():
            service_name = item.get("service")
            desired = item.get("desired", False)

            if not service_name:
                continue

            if not desired:
                continue

            if not is_active(service_name):
                restart_service(service_name)

        time.sleep(30)


if __name__ == "__main__":
    main()
