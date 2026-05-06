import platform
import subprocess
from datetime import datetime
from pathlib import Path

import psutil


def read_temperature_c():
    thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")

    try:
        if thermal_path.exists():
            raw = thermal_path.read_text().strip()
            return round(int(raw) / 1000, 1)
    except Exception:
        pass

    try:
        output = subprocess.check_output(
            ["vcgencmd", "measure_temp"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return float(output.split("=")[1].split("'")[0])
    except Exception:
        return None


def get_system_status():
    memory = psutil.virtual_memory()

    try:
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent
    except Exception:
        disk_percent = None

    return {
        "time": datetime.now().isoformat(timespec="seconds"),
        "os": platform.system(),
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "ram_percent": memory.percent,
        "ram_used_mb": round(memory.used / 1024 / 1024),
        "ram_total_mb": round(memory.total / 1024 / 1024),
        "disk_percent": disk_percent,
        "temperature_c": read_temperature_c(),
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(timespec="seconds"),
    }
