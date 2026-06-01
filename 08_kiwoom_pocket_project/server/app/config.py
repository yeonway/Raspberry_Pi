from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "kiwoom-bridge"
    app_env: str = "local"

    database_url: str = "sqlite:///./kiwoom_bridge.db"

    kiwoom_app_key: str = ""
    kiwoom_secret_key: str = ""
    kiwoom_mode: str = Field(default="mock", pattern="^(mock|real)$")
    kiwoom_base_url: str = "https://mockapi.kiwoom.com"
    kiwoom_ws_url: str = "wss://mockapi.kiwoom.com:10000/api/dostk/websocket"
    kiwoom_mock_fallback: bool = True
    kiwoom_token_refresh_margin_sec: int = 300
    kiwoom_timeout_sec: float = 8.0

    bridge_api_token: str = ""

    log_level: str = "INFO"

    @property
    def is_real_mode(self) -> bool:
        return self.kiwoom_mode == "real"

    @property
    def has_kiwoom_credentials(self) -> bool:
        return bool(self.kiwoom_app_key and self.kiwoom_secret_key)

    @model_validator(mode="after")
    def validate_bridge_api_token(self) -> "Settings":
        weak_tokens = {
            "",
            "dev-bridge-token-change-me",
            "replace-this-with-a-long-random-token",
            "local-dev-token",
        }
        if self.bridge_api_token.strip() in weak_tokens:
            raise ValueError("BRIDGE_API_TOKEN must be set to a non-default secret token.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
