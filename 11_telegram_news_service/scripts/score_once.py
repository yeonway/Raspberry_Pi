from __future__ import annotations

import argparse
import asyncio
import json

import _bootstrap  # noqa: F401

from app.config import load_settings
from app.services.ai_jobs import run_ai_jobs_once


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pending AI scoring jobs once.")
    parser.add_argument("--dry-run", action="store_true", help="Do not call the phone AI server or mutate jobs.")
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(run_ai_jobs_once(load_settings(), limit=args.limit, dry_run=args.dry_run))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
