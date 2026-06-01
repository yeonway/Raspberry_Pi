import asyncio

from app.config import get_settings
from app.kiwoom.token_manager import KiwoomTokenManager


async def main() -> None:
    settings = get_settings()
    manager = KiwoomTokenManager(settings)
    status = await manager.refresh()
    print(
        {
            "has_token": status["has_token"],
            "expires_dt": status["expires_dt"],
            "masked_token": status["masked_token"],
            "mode": status["mode"],
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
