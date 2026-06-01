from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str = ""
    database_url: str = "sqlite:///data/app.db"
    meta_graph_version: str = "v25.0"
    meta_page_id: str = ""
    meta_ig_user_id: str = ""
    meta_page_access_token: str = ""
    meta_webhook_verify_token: str = ""
    meta_webhook_verify_signature: bool = True
    portone_store_id: str = ""
    portone_channel_key: str = ""
    portone_api_secret: str = ""
    portone_webhook_secret: str = ""
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_redirect_uri: str = ""
    token_encryption_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
