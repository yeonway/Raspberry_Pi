from __future__ import annotations

import getpass
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import db  # noqa: E402
from app.security import hash_password, validate_password, validate_username  # noqa: E402


def main() -> int:
    db.init_db()
    username = validate_username(input("Admin username: ").strip())
    password = validate_password(getpass.getpass("Admin password: "))
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    password_hash = hash_password(password)
    existing = db.find_user_by_username(username)
    if existing:
        db.update_user_password_and_role(username, password_hash, "admin")
        print(f"Updated admin account: {username}")
    else:
        db.insert_user(username, password_hash, "admin")
        print(f"Created admin account: {username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
