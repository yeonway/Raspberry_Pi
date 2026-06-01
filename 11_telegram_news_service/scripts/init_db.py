from __future__ import annotations

import _bootstrap  # noqa: F401

from app.config import load_settings
from app.database import initialize_database


def main() -> None:
    settings = load_settings()
    initialize_database(settings.database_path)
    print(f"initialized database: {settings.database_path}")


if __name__ == "__main__":
    main()
