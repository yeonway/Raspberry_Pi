import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.billing import (
    get_seed_user_id,
    get_usage_balance,
    grant_monthly_credits,
    grant_purchased_tokens,
)
from app.database import initialize_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed billing data and grant test tokens.")
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument("--grant-monthly", action="store_true")
    parser.add_argument("--grant-tokens", type=int, default=0)
    parser.add_argument("--ref-id", default="")
    args = parser.parse_args()

    initialize_database()
    user_id = args.user_id if args.user_id is not None else get_seed_user_id()
    results = []

    if args.grant_monthly or args.grant_tokens == 0:
        results.append(grant_monthly_credits(user_id))

    if args.grant_tokens:
        ref_id = args.ref_id.strip() or _build_seed_ref_id(args.grant_tokens)
        results.append(grant_purchased_tokens(user_id, args.grant_tokens, ref_id))

    payload = {
        "user_id": user_id,
        "results": results,
        "balance": get_usage_balance(user_id),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _build_seed_ref_id(amount: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"seed:tokens:{amount}:{stamp}"


if __name__ == "__main__":
    main()
