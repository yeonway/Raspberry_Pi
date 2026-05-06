import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.security import password_hash


if len(sys.argv) != 2:
    print("usage: python scripts/make_password_hash.py <password>")
    sys.exit(1)

print(password_hash(sys.argv[1]))
