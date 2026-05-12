#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))


def load_env_file(path: Path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def print_json(title: str, payload):
    print(f"\n== {title} ==")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Raspberry Pi -> Android Phone AI Bridge connectivity.")
    parser.add_argument("--env", default=str(PROJECT_DIR / ".env"), help="Path to the dashboard .env file.")
    parser.add_argument("--skip-ask", action="store_true", help="Only call /health and coordinate sync.")
    parser.add_argument("--force-coordinate-sync", action="store_true", help="Force Pi coordinate DB sync to Android.")
    args = parser.parse_args()

    load_env_file(Path(args.env))

    from app.coordinate_sync import sync_coordinates_to_phone
    from app.phone_ai import ask_phone_ai, phone_ai_health

    try:
        print_json("Android /health", phone_ai_health())

        sync_result = sync_coordinates_to_phone(force=args.force_coordinate_sync)
        print_json("Coordinate sync", sync_result)

        if not args.skip_ask:
            response = ask_phone_ai(
                {
                    "player_uuid": "bridge-check",
                    "player_name": "BridgeCheck",
                    "message": "철팜 좌표 알려줘",
                    "server_context": "connectivity_check=true",
                    "coordinate_context": "player_location world=overworld x=0 y=64 z=0",
                    "spark_context": "",
                    "max_tokens": int(os.getenv("PHONE_AI_MAX_TOKENS", "180")),
                }
            )
            print_json("Android /api/ask", response)
        return 0
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
