from __future__ import annotations

import argparse
import asyncio
import json

import _bootstrap  # noqa: F401

from app.config import load_settings
from app.services.telegram_digest import send_digest_once


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send one Telegram news digest.")
    parser.add_argument("--dry-run", action="store_true", help="Build digest message without sending or mutating DB.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(send_digest_once(load_settings(), dry_run=args.dry_run))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
