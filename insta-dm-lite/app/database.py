import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
from collections.abc import Iterator

from .config import get_settings

PLAN_SEED_DATA = [
    {
        "code": "free",
        "name": "Free",
        "monthly_price_krw": 0,
        "monthly_credits": 30,
        "automation_account_limit": 1,
        "automation_rule_limit": 1,
        "allow_token_purchase": 0,
        "allow_cta_button": 0,
        "log_retention_days": 7,
        "sort_order": 10,
    },
    {
        "code": "basic",
        "name": "Basic",
        "monthly_price_krw": 2900,
        "monthly_credits": 1000,
        "automation_account_limit": 5,
        "automation_rule_limit": 10,
        "allow_token_purchase": 1,
        "allow_cta_button": 1,
        "log_retention_days": 30,
        "sort_order": 20,
    },
    {
        "code": "plus",
        "name": "Plus",
        "monthly_price_krw": 4900,
        "monthly_credits": 2000,
        "automation_account_limit": 5,
        "automation_rule_limit": 30,
        "allow_token_purchase": 1,
        "allow_cta_button": 1,
        "log_retention_days": 90,
        "sort_order": 30,
    },
    {
        "code": "pro",
        "name": "Pro",
        "monthly_price_krw": 9900,
        "monthly_credits": 5000,
        "automation_account_limit": 5,
        "automation_rule_limit": 100,
        "allow_token_purchase": 1,
        "allow_cta_button": 1,
        "log_retention_days": 180,
        "sort_order": 40,
    },
]

TOKEN_PRODUCT_SEED_DATA = [
    {"code": "tokens_1000", "name": "1,000건", "token_amount": 1000, "price_krw": 3000, "sort_order": 10},
    {"code": "tokens_3000", "name": "3,000건", "token_amount": 3000, "price_krw": 7900, "sort_order": 20},
    {"code": "tokens_5000", "name": "5,000건", "token_amount": 5000, "price_krw": 12000, "sort_order": 30},
    {"code": "tokens_10000", "name": "10,000건", "token_amount": 10000, "price_krw": 19000, "sort_order": 40},
]

SEED_ADMIN_USERNAME = "admin"


def get_database_path() -> Path:
    settings = get_settings()
    prefix = "sqlite:///"

    if not settings.database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// database URLs are supported in step 0.")

    database_path = Path(settings.database_url.removeprefix(prefix))
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path

    return database_path


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    _apply_sqlite_pragmas(connection)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _apply_sqlite_pragmas(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA foreign_keys = ON")


def initialize_database() -> None:
    with get_connection() as connection:
        create_schema(connection)
        migrate_schema(connection)
        seed_reference_data(connection)
        connection.commit()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            monthly_price_krw INTEGER NOT NULL CHECK (monthly_price_krw >= 0),
            monthly_credits INTEGER NOT NULL CHECK (monthly_credits >= 0),
            automation_account_limit INTEGER NOT NULL CHECK (automation_account_limit >= 0),
            automation_rule_limit INTEGER NOT NULL CHECK (automation_rule_limit >= 0),
            allow_token_purchase INTEGER NOT NULL CHECK (allow_token_purchase IN (0, 1)),
            allow_cta_button INTEGER NOT NULL DEFAULT 0 CHECK (allow_cta_button IN (0, 1)),
            log_retention_days INTEGER NOT NULL DEFAULT 0 CHECK (log_retention_days >= 0),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS token_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            token_amount INTEGER NOT NULL CHECK (token_amount > 0),
            price_krw INTEGER NOT NULL CHECK (price_krw >= 0),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            current_plan_id INTEGER NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (current_plan_id) REFERENCES subscription_plans (id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_balances (
            user_id INTEGER PRIMARY KEY,
            current_period TEXT NOT NULL,
            monthly_remaining INTEGER NOT NULL DEFAULT 0 CHECK (monthly_remaining >= 0),
            purchased_remaining INTEGER NOT NULL DEFAULT 0 CHECK (purchased_remaining >= 0),
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS credit_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ref_id TEXT NOT NULL,
            entry_type TEXT NOT NULL CHECK (
                entry_type IN (
                    'monthly_grant',
                    'purchase_grant',
                    'consume_monthly',
                    'consume_purchased',
                    'consume_failed'
                )
            ),
            reason TEXT NOT NULL,
            monthly_delta INTEGER NOT NULL DEFAULT 0,
            purchased_delta INTEGER NOT NULL DEFAULT 0,
            balance_monthly_after INTEGER NOT NULL CHECK (balance_monthly_after >= 0),
            balance_purchased_after INTEGER NOT NULL CHECK (balance_purchased_after >= 0),
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, ref_id, entry_type)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS credit_reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ref_id TEXT NOT NULL,
            source TEXT NOT NULL CHECK (source IN ('monthly', 'purchased')),
            amount INTEGER NOT NULL DEFAULT 1 CHECK (amount > 0),
            status TEXT NOT NULL CHECK (status IN ('reserved', 'committed', 'released')),
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, ref_id)
        )
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_credit_ledger_unique_consume_ref
        ON credit_ledger (user_id, ref_id)
        WHERE entry_type IN ('consume_monthly', 'consume_purchased')
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_product_id INTEGER,
            order_ref TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'failed', 'cancelled')),
            amount_krw INTEGER NOT NULL CHECK (amount_krw >= 0),
            token_amount INTEGER NOT NULL CHECK (token_amount >= 0),
            payment_id TEXT NOT NULL DEFAULT '',
            transaction_id TEXT NOT NULL DEFAULT '',
            failure_reason TEXT NOT NULL DEFAULT '',
            raw_webhook_json TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            paid_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (token_product_id) REFERENCES token_products (id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            event_ref TEXT NOT NULL,
            order_id INTEGER,
            payment_id TEXT NOT NULL DEFAULT '',
            transaction_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            raw_payload_json TEXT NOT NULL,
            error_message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES payment_orders (id) ON DELETE SET NULL,
            UNIQUE (provider, event_ref)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS meta_api_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL,
            method TEXT NOT NULL,
            status_code INTEGER,
            user_message TEXT NOT NULL,
            error_payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS connected_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            page_id TEXT NOT NULL,
            ig_user_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            ig_username TEXT NOT NULL DEFAULT '',
            page_access_token_encrypted TEXT NOT NULL DEFAULT '',
            facebook_user_id TEXT NOT NULL DEFAULT '',
            webhook_subscribed INTEGER NOT NULL DEFAULT 0 CHECK (webhook_subscribed IN (0, 1)),
            webhook_status TEXT NOT NULL DEFAULT '',
            last_error TEXT NOT NULL DEFAULT '',
            token_updated_at TEXT,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, provider, page_id, ig_user_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS automation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target_mode TEXT NOT NULL CHECK (target_mode IN ('all', 'selected')),
            keywords_json TEXT NOT NULL,
            exclude_keywords_json TEXT NOT NULL,
            match_mode TEXT NOT NULL CHECK (match_mode IN ('contains', 'exact')),
            public_reply_text TEXT NOT NULL,
            dm_text TEXT NOT NULL,
            cta_label TEXT NOT NULL DEFAULT '',
            cta_url TEXT NOT NULL DEFAULT '',
            delay_min_seconds INTEGER NOT NULL DEFAULT 0 CHECK (delay_min_seconds >= 0),
            delay_max_seconds INTEGER NOT NULL DEFAULT 0 CHECK (delay_max_seconds >= 0),
            enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES connected_accounts (id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS rule_media_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER NOT NULL,
            media_id TEXT NOT NULL,
            media_caption TEXT NOT NULL DEFAULT '',
            media_permalink TEXT NOT NULL DEFAULT '',
            media_type TEXT NOT NULL DEFAULT '',
            thumbnail_url TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (rule_id) REFERENCES automation_rules (id) ON DELETE CASCADE,
            UNIQUE (rule_id, media_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS job_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            rule_id INTEGER NOT NULL,
            comment_id TEXT NOT NULL UNIQUE,
            media_id TEXT NOT NULL,
            comment_text TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'queued',
                    'processing',
                    'success',
                    'partial_success',
                    'failed',
                    'skipped',
                    'skipped_keyword',
                    'skipped_media',
                    'duplicate',
                    'skipped_rule_conflict',
                    'token_empty',
                    'permission_error',
                    'rate_limited'
                )
            ),
            run_after TEXT NOT NULL,
            attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
            last_error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES connected_accounts (id) ON DELETE CASCADE,
            FOREIGN KEY (rule_id) REFERENCES automation_rules (id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_job_queue_due
        ON job_queue (status, run_after, account_id)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id TEXT NOT NULL UNIQUE,
            media_id TEXT NOT NULL,
            rule_id INTEGER NOT NULL,
            charged INTEGER NOT NULL CHECK (charged IN (0, 1)),
            created_at TEXT NOT NULL,
            FOREIGN KEY (rule_id) REFERENCES automation_rules (id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS automation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            rule_id INTEGER,
            media_id TEXT NOT NULL,
            comment_id TEXT NOT NULL,
            comment_text TEXT NOT NULL,
            matched_keyword TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            public_reply_status TEXT NOT NULL DEFAULT '',
            dm_status TEXT NOT NULL DEFAULT '',
            charged INTEGER NOT NULL DEFAULT 0 CHECK (charged IN (0, 1)),
            charge_amount INTEGER NOT NULL DEFAULT 0 CHECK (charge_amount >= 0),
            error_message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES connected_accounts (id) ON DELETE CASCADE,
            FOREIGN KEY (rule_id) REFERENCES automation_rules (id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_automation_logs_filters
        ON automation_logs (status, rule_id, media_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            event_id TEXT NOT NULL,
            raw_payload_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (provider, event_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS facebook_oauth_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            pages_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'started',
            error_message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def migrate_schema(connection: sqlite3.Connection) -> None:
    _add_column_if_missing(
        connection,
        "subscription_plans",
        "allow_cta_button",
        "ALTER TABLE subscription_plans ADD COLUMN allow_cta_button INTEGER NOT NULL DEFAULT 0 CHECK (allow_cta_button IN (0, 1))",
    )
    _add_column_if_missing(
        connection,
        "subscription_plans",
        "log_retention_days",
        "ALTER TABLE subscription_plans ADD COLUMN log_retention_days INTEGER NOT NULL DEFAULT 0 CHECK (log_retention_days >= 0)",
    )
    _add_column_if_missing(
        connection,
        "connected_accounts",
        "active",
        "ALTER TABLE connected_accounts ADD COLUMN active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))",
    )
    _add_column_if_missing(
        connection,
        "connected_accounts",
        "ig_username",
        "ALTER TABLE connected_accounts ADD COLUMN ig_username TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "connected_accounts",
        "page_access_token_encrypted",
        "ALTER TABLE connected_accounts ADD COLUMN page_access_token_encrypted TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "connected_accounts",
        "facebook_user_id",
        "ALTER TABLE connected_accounts ADD COLUMN facebook_user_id TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "connected_accounts",
        "webhook_subscribed",
        "ALTER TABLE connected_accounts ADD COLUMN webhook_subscribed INTEGER NOT NULL DEFAULT 0 CHECK (webhook_subscribed IN (0, 1))",
    )
    _add_column_if_missing(
        connection,
        "connected_accounts",
        "webhook_status",
        "ALTER TABLE connected_accounts ADD COLUMN webhook_status TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "connected_accounts",
        "last_error",
        "ALTER TABLE connected_accounts ADD COLUMN last_error TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "connected_accounts",
        "token_updated_at",
        "ALTER TABLE connected_accounts ADD COLUMN token_updated_at TEXT",
    )
    _add_column_if_missing(
        connection,
        "payment_orders",
        "payment_id",
        "ALTER TABLE payment_orders ADD COLUMN payment_id TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "payment_orders",
        "transaction_id",
        "ALTER TABLE payment_orders ADD COLUMN transaction_id TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "payment_orders",
        "failure_reason",
        "ALTER TABLE payment_orders ADD COLUMN failure_reason TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "payment_orders",
        "raw_webhook_json",
        "ALTER TABLE payment_orders ADD COLUMN raw_webhook_json TEXT NOT NULL DEFAULT ''",
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_orders_payment_id
        ON payment_orders (payment_id)
        WHERE payment_id != ''
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_orders_transaction_id
        ON payment_orders (transaction_id)
        WHERE transaction_id != ''
        """
    )


def _table_has_column(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    sql: str,
) -> None:
    if not _table_has_column(connection, table_name, column_name):
        connection.execute(sql)


def seed_reference_data(connection: sqlite3.Connection) -> None:
    now = utc_now()
    for plan in PLAN_SEED_DATA:
        connection.execute(
            """
            INSERT INTO subscription_plans (
                code,
                name,
                monthly_price_krw,
                monthly_credits,
                automation_account_limit,
                automation_rule_limit,
                allow_token_purchase,
                allow_cta_button,
                log_retention_days,
                is_active,
                sort_order,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name = excluded.name,
                monthly_price_krw = excluded.monthly_price_krw,
                monthly_credits = excluded.monthly_credits,
                automation_account_limit = excluded.automation_account_limit,
                automation_rule_limit = excluded.automation_rule_limit,
                allow_token_purchase = excluded.allow_token_purchase,
                allow_cta_button = excluded.allow_cta_button,
                log_retention_days = excluded.log_retention_days,
                is_active = excluded.is_active,
                sort_order = excluded.sort_order,
                updated_at = excluded.updated_at
            """,
            (
                plan["code"],
                plan["name"],
                plan["monthly_price_krw"],
                plan["monthly_credits"],
                plan["automation_account_limit"],
                plan["automation_rule_limit"],
                plan["allow_token_purchase"],
                plan["allow_cta_button"],
                plan["log_retention_days"],
                plan["sort_order"],
                now,
                now,
            ),
        )

    _migrate_legacy_lite_plan_to_free(connection, now)

    for product in TOKEN_PRODUCT_SEED_DATA:
        connection.execute(
            """
            INSERT INTO token_products (
                code,
                name,
                token_amount,
                price_krw,
                is_active,
                sort_order,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name = excluded.name,
                token_amount = excluded.token_amount,
                price_krw = excluded.price_krw,
                is_active = excluded.is_active,
                sort_order = excluded.sort_order,
                updated_at = excluded.updated_at
            """,
            (
                product["code"],
                product["name"],
                product["token_amount"],
                product["price_krw"],
                product["sort_order"],
                now,
                now,
            ),
        )

    free_plan = connection.execute(
        "SELECT id FROM subscription_plans WHERE code = ?",
        ("free",),
    ).fetchone()
    if free_plan is None:
        raise RuntimeError("Free plan seed data was not created.")

    connection.execute(
        """
        INSERT INTO users (
            username,
            display_name,
            current_plan_id,
            is_admin,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, 1, ?, ?)
        ON CONFLICT(username) DO NOTHING
        """,
        (SEED_ADMIN_USERNAME, "Seed Admin", free_plan["id"], now, now),
    )


def _migrate_legacy_lite_plan_to_free(connection: sqlite3.Connection, now: str) -> None:
    free_plan = connection.execute(
        "SELECT id FROM subscription_plans WHERE code = ?",
        ("free",),
    ).fetchone()
    legacy_plan = connection.execute(
        "SELECT id FROM subscription_plans WHERE code = ?",
        ("lite",),
    ).fetchone()
    if free_plan is None or legacy_plan is None:
        return

    connection.execute(
        """
        UPDATE users
        SET current_plan_id = ?,
            updated_at = ?
        WHERE current_plan_id = ?
        """,
        (free_plan["id"], now, legacy_plan["id"]),
    )
    connection.execute("DELETE FROM subscription_plans WHERE id = ?", (legacy_plan["id"],))
