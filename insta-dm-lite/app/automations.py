from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .config import get_settings
from .database import get_connection, utc_now

MATCH_MODES = {"contains", "exact"}
TARGET_MODES = {"all", "selected"}


@dataclass
class AutomationValidationError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def get_or_create_connected_account(user_id: int) -> dict[str, Any]:
    settings = get_settings()
    page_id = settings.meta_page_id.strip() or "local_page"
    ig_user_id = settings.meta_ig_user_id.strip() or "local_ig_user"
    display_name = "테스트 Meta 계정"
    now = utc_now()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO connected_accounts (
                user_id,
                provider,
                page_id,
                ig_user_id,
                display_name,
                active,
                created_at,
                updated_at
            )
            VALUES (?, 'meta', ?, ?, ?, 1, ?, ?)
            ON CONFLICT(user_id, provider, page_id, ig_user_id) DO UPDATE SET
                display_name = excluded.display_name,
                active = 1,
                updated_at = excluded.updated_at
            """,
            (user_id, page_id, ig_user_id, display_name, now, now),
        )
        row = connection.execute(
            """
            SELECT id, user_id, provider, page_id, ig_user_id, display_name, active
            FROM connected_accounts
            WHERE user_id = ?
              AND provider = 'meta'
              AND page_id = ?
              AND ig_user_id = ?
            """,
            (user_id, page_id, ig_user_id),
        ).fetchone()
    if row is None:
        raise RuntimeError("Connected account was not created.")
    return _account_to_dict(row)


def list_automation_rules(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                automation_rules.*,
                connected_accounts.display_name AS account_display_name,
                connected_accounts.page_id,
                connected_accounts.ig_user_id,
                COUNT(rule_media_targets.id) AS media_target_count
            FROM automation_rules
            JOIN connected_accounts ON connected_accounts.id = automation_rules.account_id
            LEFT JOIN rule_media_targets ON rule_media_targets.rule_id = automation_rules.id
            WHERE connected_accounts.user_id = ?
            GROUP BY automation_rules.id
            ORDER BY automation_rules.id DESC
            """,
            (user_id,),
        ).fetchall()
    return [_rule_to_dict(row) for row in rows]


def create_automation_rule(
    *,
    user_id: int,
    name: str,
    target_mode: str,
    keywords_text: str,
    exclude_keywords_text: str,
    match_mode: str,
    public_reply_text: str,
    dm_text: str,
    cta_label: str,
    cta_url: str,
    delay_min_seconds: int,
    delay_max_seconds: int,
    selected_media: list[dict[str, str]],
) -> int:
    account = get_or_create_connected_account(user_id)
    cleaned = _validate_rule_input(
        name=name,
        target_mode=target_mode,
        keywords_text=keywords_text,
        exclude_keywords_text=exclude_keywords_text,
        match_mode=match_mode,
        public_reply_text=public_reply_text,
        dm_text=dm_text,
        cta_label=cta_label,
        cta_url=cta_url,
        delay_min_seconds=delay_min_seconds,
        delay_max_seconds=delay_max_seconds,
        selected_media=selected_media,
    )
    now = utc_now()
    with get_connection() as connection:
        _enforce_plan_limits(connection, user_id, cleaned)
        cursor = connection.execute(
            """
            INSERT INTO automation_rules (
                account_id,
                name,
                target_mode,
                keywords_json,
                exclude_keywords_json,
                match_mode,
                public_reply_text,
                dm_text,
                cta_label,
                cta_url,
                delay_min_seconds,
                delay_max_seconds,
                enabled,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                account["id"],
                cleaned["name"],
                cleaned["target_mode"],
                json.dumps(cleaned["keywords"], ensure_ascii=False),
                json.dumps(cleaned["exclude_keywords"], ensure_ascii=False),
                cleaned["match_mode"],
                cleaned["public_reply_text"],
                cleaned["dm_text"],
                cleaned["cta_label"],
                cleaned["cta_url"],
                cleaned["delay_min_seconds"],
                cleaned["delay_max_seconds"],
                now,
                now,
            ),
        )
        rule_id = int(cursor.lastrowid)
        if cleaned["target_mode"] == "selected":
            for media in cleaned["selected_media"]:
                connection.execute(
                    """
                    INSERT INTO rule_media_targets (
                        rule_id,
                        media_id,
                        media_caption,
                        media_permalink,
                        media_type,
                        thumbnail_url,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rule_id,
                        media["media_id"],
                        media["media_caption"],
                        media["media_permalink"],
                        media["media_type"],
                        media["thumbnail_url"],
                        now,
                    ),
                )
    return rule_id


def _enforce_plan_limits(connection, user_id: int, cleaned_rule: dict[str, Any]) -> None:
    plan = connection.execute(
        """
        SELECT
            subscription_plans.automation_rule_limit,
            subscription_plans.allow_cta_button
        FROM users
        JOIN subscription_plans ON subscription_plans.id = users.current_plan_id
        WHERE users.id = ?
        """,
        (user_id,),
    ).fetchone()
    if plan is None:
        raise AutomationValidationError("User plan does not exist.")

    rule_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM automation_rules
        JOIN connected_accounts ON connected_accounts.id = automation_rules.account_id
        WHERE connected_accounts.user_id = ?
        """,
        (user_id,),
    ).fetchone()[0]
    if int(rule_count) >= int(plan["automation_rule_limit"]):
        raise AutomationValidationError("Current plan automation rule limit has been reached.")
    if (cleaned_rule["cta_label"] or cleaned_rule["cta_url"]) and not bool(plan["allow_cta_button"]):
        raise AutomationValidationError("Current plan does not allow CTA buttons.")


def set_rule_enabled(user_id: int, rule_id: int, enabled: bool) -> None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT automation_rules.id
            FROM automation_rules
            JOIN connected_accounts ON connected_accounts.id = automation_rules.account_id
            WHERE automation_rules.id = ?
              AND connected_accounts.user_id = ?
            """,
            (rule_id, user_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"Automation rule does not exist: {rule_id}")
        connection.execute(
            """
            UPDATE automation_rules
            SET enabled = ?, updated_at = ?
            WHERE id = ?
            """,
            (1 if enabled else 0, utc_now(), rule_id),
        )


def get_rule_media_targets(rule_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT media_id, media_caption, media_permalink, media_type, thumbnail_url
            FROM rule_media_targets
            WHERE rule_id = ?
            ORDER BY id
            """,
            (rule_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def parse_keywords(value: str) -> list[str]:
    normalized = value.replace("\r", "\n").replace(",", "\n")
    keywords = []
    seen = set()
    for item in normalized.split("\n"):
        keyword = item.strip()
        if keyword and keyword not in seen:
            keywords.append(keyword)
            seen.add(keyword)
    return keywords


def _validate_rule_input(
    *,
    name: str,
    target_mode: str,
    keywords_text: str,
    exclude_keywords_text: str,
    match_mode: str,
    public_reply_text: str,
    dm_text: str,
    cta_label: str,
    cta_url: str,
    delay_min_seconds: int,
    delay_max_seconds: int,
    selected_media: list[dict[str, str]],
) -> dict[str, Any]:
    name = name.strip()
    target_mode = target_mode.strip()
    match_mode = match_mode.strip()
    public_reply_text = public_reply_text.strip()
    dm_text = dm_text.strip()
    cta_label = cta_label.strip()
    cta_url = cta_url.strip()
    keywords = parse_keywords(keywords_text)
    exclude_keywords = parse_keywords(exclude_keywords_text)

    if not name:
        raise AutomationValidationError("자동화 이름을 입력하세요.")
    if target_mode not in TARGET_MODES:
        raise AutomationValidationError("적용 대상을 선택하세요.")
    if match_mode not in MATCH_MODES:
        raise AutomationValidationError("키워드 매칭 방식을 선택하세요.")
    if not keywords:
        raise AutomationValidationError("키워드를 하나 이상 입력하세요.")
    if not public_reply_text:
        raise AutomationValidationError("공개 답글 문구를 입력하세요.")
    if not dm_text:
        raise AutomationValidationError("DM 문구를 입력하세요.")
    if bool(cta_label) != bool(cta_url):
        raise AutomationValidationError("CTA 버튼명과 CTA 링크는 함께 입력해야 합니다.")
    if cta_url and not (cta_url.startswith("http://") or cta_url.startswith("https://")):
        raise AutomationValidationError("CTA 링크는 http:// 또는 https://로 시작해야 합니다.")
    if delay_min_seconds < 0 or delay_max_seconds < 0:
        raise AutomationValidationError("발송 지연 시간은 0 이상이어야 합니다.")
    if delay_min_seconds > delay_max_seconds:
        raise AutomationValidationError("최소 지연 시간은 최대 지연 시간보다 클 수 없습니다.")

    cleaned_media = _clean_selected_media(selected_media)
    if target_mode == "selected" and not cleaned_media:
        raise AutomationValidationError("선택한 게시물만 적용하려면 게시물을 하나 이상 선택하세요.")

    return {
        "name": name,
        "target_mode": target_mode,
        "keywords": keywords,
        "exclude_keywords": exclude_keywords,
        "match_mode": match_mode,
        "public_reply_text": public_reply_text,
        "dm_text": dm_text,
        "cta_label": cta_label,
        "cta_url": cta_url,
        "delay_min_seconds": delay_min_seconds,
        "delay_max_seconds": delay_max_seconds,
        "selected_media": cleaned_media,
    }


def _clean_selected_media(selected_media: list[dict[str, str]]) -> list[dict[str, str]]:
    cleaned = []
    seen = set()
    for media in selected_media:
        media_id = media.get("media_id", "").strip()
        if not media_id or media_id in seen:
            continue
        cleaned.append(
            {
                "media_id": media_id,
                "media_caption": media.get("media_caption", "").strip(),
                "media_permalink": media.get("media_permalink", "").strip(),
                "media_type": media.get("media_type", "").strip(),
                "thumbnail_url": media.get("thumbnail_url", "").strip(),
            }
        )
        seen.add(media_id)
    return cleaned


def _account_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "user_id": int(row["user_id"]),
        "provider": row["provider"],
        "page_id": row["page_id"],
        "ig_user_id": row["ig_user_id"],
        "display_name": row["display_name"],
        "active": bool(row["active"]),
    }


def _rule_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "account_id": int(row["account_id"]),
        "account_display_name": row["account_display_name"],
        "page_id": row["page_id"],
        "ig_user_id": row["ig_user_id"],
        "name": row["name"],
        "target_mode": row["target_mode"],
        "keywords": json.loads(row["keywords_json"]),
        "exclude_keywords": json.loads(row["exclude_keywords_json"]),
        "match_mode": row["match_mode"],
        "public_reply_text": row["public_reply_text"],
        "dm_text": row["dm_text"],
        "cta_label": row["cta_label"],
        "cta_url": row["cta_url"],
        "delay_min_seconds": int(row["delay_min_seconds"]),
        "delay_max_seconds": int(row["delay_max_seconds"]),
        "enabled": bool(row["enabled"]),
        "media_target_count": int(row["media_target_count"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
