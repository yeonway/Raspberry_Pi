from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URL = f"sqlite:///{(BASE_DIR / 'data' / 'mathgen.sqlite3').as_posix()}"


class Settings(BaseSettings):
    app_name: str = "mathgen-web"
    environment: str = "development"
    database_url: str = DEFAULT_DATABASE_URL
    default_problem_count: int = Field(default=5, ge=1, le=10)
    sympy_validation_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    gemini_api_keys: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEYS", "MATHGEN_GEMINI_API_KEYS"),
    )
    gemini_model_default: str = Field(
        default="gemini-2.5-flash-lite",
        validation_alias=AliasChoices("GEMINI_MODEL_DEFAULT", "MATHGEN_GEMINI_MODEL_DEFAULT"),
    )
    ai_request_timeout_seconds: float = Field(
        default=45.0,
        gt=0,
        validation_alias=AliasChoices("AI_REQUEST_TIMEOUT_SECONDS", "MATHGEN_AI_REQUEST_TIMEOUT_SECONDS"),
    )
    ai_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        validation_alias=AliasChoices("AI_MAX_RETRIES", "MATHGEN_AI_MAX_RETRIES"),
    )
    ai_key_cooldown_seconds: int = Field(
        default=3600,
        ge=1,
        validation_alias=AliasChoices("AI_KEY_COOLDOWN_SECONDS", "MATHGEN_AI_KEY_COOLDOWN_SECONDS"),
    )
    max_problems_per_generation: int = Field(
        default=10,
        ge=1,
        le=20,
        validation_alias=AliasChoices("MAX_PROBLEMS_PER_GENERATION", "MATHGEN_MAX_PROBLEMS_PER_GENERATION"),
    )
    validation_timeout_seconds: float = Field(
        default=3.0,
        gt=0,
        le=10,
        validation_alias=AliasChoices("VALIDATION_TIMEOUT_SECONDS", "MATHGEN_VALIDATION_TIMEOUT_SECONDS"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MATHGEN_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
