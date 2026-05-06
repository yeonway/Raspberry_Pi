from pathlib import Path
from datetime import datetime


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "dashboard.log"


def write_log(message: str, level: str = "INFO"):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [{level}] {message}\n"

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)


def read_logs(lines: int = 100):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not LOG_FILE.exists():
        return []

    lines = max(1, min(lines, 500))

    with LOG_FILE.open("r", encoding="utf-8") as f:
        data = f.readlines()

    return data[-lines:]
