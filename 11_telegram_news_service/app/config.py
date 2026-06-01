from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


GDELT_QUERY_GROUPS: dict[str, list[str]] = {
    "미국시장": [
        '"Federal Reserve" OR FOMC OR inflation OR "Treasury yields"',
        'Nasdaq OR "S&P 500" OR "US stocks"',
    ],
    "AI": [
        'OpenAI OR Anthropic OR "Google DeepMind" OR "Meta AI"',
        '"AI chip" OR GPU OR Nvidia OR "large language model"',
    ],
    "반도체": [
        'Nvidia OR AMD OR TSMC OR "SK hynix" OR Micron',
        'semiconductor OR "AI accelerator"',
    ],
    "Database": [
        'PostgreSQL OR MySQL OR SQLite OR MongoDB OR Redis',
        '"vector database" OR Qdrant OR Milvus',
    ],
    "개발/인프라": [
        "Docker OR Kubernetes OR Linux OR Cloudflare OR FastAPI",
    ],
}


FRED_SERIES: dict[str, str] = {
    "FEDFUNDS": "Federal Funds Effective Rate",
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "CPIAUCSL": "Consumer Price Index",
    "PCEPI": "Personal Consumption Expenditures Price Index",
    "UNRATE": "Unemployment Rate",
    "GDP": "Gross Domestic Product",
    "SP500": "S&P 500",
    "NASDAQCOM": "NASDAQ Composite",
}


SEED_KEYWORDS: list[tuple[str, str, int, int, int]] = [
    ("Nasdaq", "미국시장", 15, 1, 1),
    ("S&P 500", "미국시장", 15, 1, 1),
    ("Fed", "미국시장", 12, 1, 1),
    ("FOMC", "미국시장", 18, 1, 1),
    ("CPI", "미국시장", 16, 1, 1),
    ("PCE", "미국시장", 16, 1, 1),
    ("Treasury yield", "미국시장", 14, 1, 1),
    ("rate cut", "미국시장", 14, 1, 1),
    ("inflation", "미국시장", 14, 1, 1),
    ("Nvidia", "반도체", 25, 1, 1),
    ("NVDA", "반도체", 25, 1, 1),
    ("AMD", "반도체", 18, 1, 1),
    ("TSMC", "반도체", 18, 1, 1),
    ("Samsung Electronics", "반도체", 18, 1, 1),
    ("SK hynix", "반도체", 18, 1, 1),
    ("Micron", "반도체", 16, 1, 1),
    ("semiconductor", "반도체", 14, 1, 1),
    ("AI chip", "반도체", 20, 1, 1),
    ("GPU", "반도체", 18, 1, 1),
    ("OpenAI", "AI", 22, 1, 1),
    ("Google DeepMind", "AI", 18, 1, 1),
    ("Anthropic", "AI", 18, 1, 1),
    ("Meta AI", "AI", 14, 1, 1),
    ("Gemini", "AI", 14, 1, 1),
    ("Gemma", "AI", 14, 1, 1),
    ("Llama", "AI", 14, 1, 1),
    ("Qwen", "AI", 12, 1, 1),
    ("Mistral", "AI", 12, 1, 1),
    ("local AI", "AI", 16, 1, 1),
    ("llama.cpp", "AI", 16, 1, 1),
    ("GGUF", "AI", 14, 1, 1),
    ("PostgreSQL", "Database", 14, 1, 1),
    ("MySQL", "Database", 10, 0, 1),
    ("SQLite", "Database", 10, 0, 1),
    ("MongoDB", "Database", 10, 0, 1),
    ("Redis", "Database", 10, 0, 1),
    ("vector database", "Database", 16, 1, 1),
    ("Qdrant", "Database", 14, 1, 1),
    ("Milvus", "Database", 14, 1, 1),
    ("Raspberry Pi", "개발/인프라", 16, 1, 1),
    ("Android", "개발/인프라", 12, 1, 1),
    ("Docker", "개발/인프라", 10, 0, 1),
    ("Kubernetes", "개발/인프라", 12, 0, 1),
    ("Linux", "개발/인프라", 10, 0, 1),
    ("Cloudflare", "개발/인프라", 12, 1, 1),
    ("FastAPI", "개발/인프라", 10, 0, 1),
    ("Caddy", "개발/인프라", 10, 0, 1),
]


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_host: str
    app_port: int
    database_path: Path
    admin_token: str | None
    fred_api_key: str | None
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    sec_user_agent: str
    phone_ai_base_url: str
    phone_ai_token: str | None
    phone_ai_enabled: bool
    phone_ai_timeout_seconds: float
    news_digest_interval_minutes: int
    news_digest_min_score: int
    news_digest_max_items: int
    collector_gdelt_enabled: bool
    collector_fred_enabled: bool
    collector_arxiv_enabled: bool
    collector_hn_enabled: bool
    collector_sec_enabled: bool
    scheduler_enabled: bool


def load_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development")
    database_path = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "news.db")))
    return Settings(
        app_env=app_env,
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=_int_env("APP_PORT", 8020),
        database_path=database_path,
        admin_token=os.getenv("ADMIN_TOKEN") or None,
        fred_api_key=os.getenv("FRED_API_KEY") or None,
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
        sec_user_agent=os.getenv("SEC_USER_AGENT", "pi-news-radar contact@example.com"),
        phone_ai_base_url=os.getenv("PHONE_AI_BASE_URL", "http://127.0.0.1:8765"),
        phone_ai_token=os.getenv("PHONE_AI_TOKEN") or None,
        phone_ai_enabled=_bool_env("PHONE_AI_ENABLED", False),
        phone_ai_timeout_seconds=_float_env("PHONE_AI_TIMEOUT_SECONDS", 45.0),
        news_digest_interval_minutes=_int_env("NEWS_DIGEST_INTERVAL_MINUTES", 30),
        news_digest_min_score=_int_env("NEWS_DIGEST_MIN_SCORE", 80),
        news_digest_max_items=_int_env("NEWS_DIGEST_MAX_ITEMS", 10),
        collector_gdelt_enabled=_bool_env("COLLECTOR_GDELT_ENABLED", True),
        collector_fred_enabled=_bool_env("COLLECTOR_FRED_ENABLED", True),
        collector_arxiv_enabled=_bool_env("COLLECTOR_ARXIV_ENABLED", True),
        collector_hn_enabled=_bool_env("COLLECTOR_HN_ENABLED", True),
        collector_sec_enabled=_bool_env("COLLECTOR_SEC_ENABLED", True),
        scheduler_enabled=_bool_env("SCHEDULER_ENABLED", app_env == "production"),
    )
