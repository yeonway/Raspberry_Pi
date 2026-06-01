from __future__ import annotations

import argparse
import asyncio
import json

import _bootstrap  # noqa: F401

from app.config import load_settings
from app.services.collection import run_collectors_once


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run news collectors once.")
    parser.add_argument("--dry-run", action="store_true", help="Show enabled collectors without network writes.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(run_collectors_once(load_settings(), dry_run=args.dry_run))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
