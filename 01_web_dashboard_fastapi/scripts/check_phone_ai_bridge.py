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


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def is_trueish(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Raspberry Pi -> Android Phone AI Bridge connectivity.")
    parser.add_argument("--env", default=str(PROJECT_DIR / ".env"), help="Path to the dashboard .env file.")
    parser.add_argument("--skip-ask", action="store_true", help="Only call /health and coordinate sync.")
    parser.add_argument("--force-coordinate-sync", action="store_true", help="Force Pi coordinate DB sync to Android.")
    parser.add_argument("--timeout", type=float, help="Override PHONE_AI_TIMEOUT_SECONDS for this check run.")
    parser.add_argument("--ask-max-tokens", type=int, help="Max tokens for the optional /api/ask check.")
    parser.add_argument(
        "--allow-model-load-on-ask",
        action="store_true",
        help="Call /api/ask even when /health says the model is not loaded. Use this for first-load testing.",
    )
    args = parser.parse_args()

    load_env_file(Path(args.env))
    if args.timeout is not None:
        os.environ["PHONE_AI_TIMEOUT_SECONDS"] = str(args.timeout)

    from app.coordinate_sync import sync_coordinates_to_phone
    from app.phone_ai import ask_phone_ai, phone_ai_health

    try:
        health = phone_ai_health()
        print_json("Android /health", health)

        sync_result = sync_coordinates_to_phone(force=args.force_coordinate_sync)
        print_json("Coordinate sync", sync_result)

        if not args.skip_ask:
            model_selected = is_trueish(health.get("modelSelected") or health.get("model_selected"))
            model_loaded = is_trueish(health.get("modelLoaded") or health.get("model_loaded"))
            if not model_selected:
                print_json(
                    "Android /api/ask",
                    {
                        "ok": False,
                        "skipped": True,
                        "error": "MODEL_NOT_SELECTED",
                        "message": "No GGUF model is selected in the Android app.",
                    },
                )
                return 1

            if not model_loaded and not args.allow_model_load_on_ask:
                print_json(
                    "Android /api/ask",
                    {
                        "ok": False,
                        "skipped": True,
                        "error": "MODEL_NOT_LOADED",
                        "message": (
                            "The GGUF model is selected but not loaded. Tap Load Model in the Android app, "
                            "then rerun this check. To test first-load behavior, rerun with "
                            "--allow-model-load-on-ask --timeout 180."
                        ),
                    },
                )
                return 1

            if not model_loaded:
                current_timeout = env_float("PHONE_AI_TIMEOUT_SECONDS", 30.0)
                if current_timeout < 180:
                    os.environ["PHONE_AI_TIMEOUT_SECONDS"] = "180"

            response = ask_phone_ai(
                {
                    "player_uuid": "bridge-check",
                    "player_name": "BridgeCheck",
                    "message": "철팜 좌표 알려줘",
                    "server_context": "connectivity_check=true",
                    "coordinate_context": "player_location world=overworld x=0 y=64 z=0",
                    "spark_context": "",
                    "max_tokens": args.ask_max_tokens or env_int("PHONE_AI_CHECK_MAX_TOKENS", 48),
                }
            )
            print_json("Android /api/ask", response)
        return 0
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
