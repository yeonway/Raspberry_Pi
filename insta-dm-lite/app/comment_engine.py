from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from . import meta_api
from .billing import commit_reserved_credit, release_reserved_credit, reserve_one_credit
from .database import get_connection, utc_now
from .facebook_oauth import get_account_page_access_token
from .token_crypto import TokenCryptoError

DEFAULT_DELAY_MIN_SECONDS = 5
DEFAULT_DELAY_MAX_SECONDS = 30
MAX_ATTEMPTS = 3
ACCOUNT_MINUTE_LIMIT = 20


def enqueue_comment_for_processing(
    *,
    user_id: int,
    media_id: str,
    comment_id: str,
    comment_text: str,
    delay_override_seconds: int | None = None,
) -> dict[str, Any]:
    media_id = _required(media_id, "media_id")
    comment_id = _required(comment_id, "comment_id")
    comment_text = _required(comment_text, "comment_text")

    with get_connection() as connection:
        account = _get_active_account(connection, user_id)
        if account is None:
            return _skip_without_rule(
                connection,
                user_id=user_id,
                media_id=media_id,
                comment_id=comment_id,
                comment_text=comment_text,
                status="skipped",
                error_message="활성 연결 계정이 없습니다.",
            )

        if _is_duplicate_comment(connection, comment_id):
            _insert_log(
                connection,
                account_id=account["id"],
                rule_id=None,
                media_id=media_id,
                comment_id=comment_id,
                comment_text=comment_text,
                matched_keyword="",
                status="duplicate",
                error_message="이미 처리 중이거나 처리된 댓글입니다.",
            )
            return {"status": "duplicate", "queued": False}

        rules = _get_enabled_rules(connection, account["id"])
        if not rules:
            _insert_log(
                connection,
                account_id=account["id"],
                rule_id=None,
                media_id=media_id,
                comment_id=comment_id,
                comment_text=comment_text,
                matched_keyword="",
                status="skipped",
                error_message="활성 자동화 규칙이 없습니다.",
            )
            return {"status": "skipped", "queued": False}

        last_skip_status = "skipped_keyword"
        matched_rules = []
        for rule in rules:
            media_status = _check_media_target(connection, rule, media_id)
            if media_status != "matched":
                _insert_log(
                    connection,
                    account_id=account["id"],
                    rule_id=rule["id"],
                    media_id=media_id,
                    comment_id=comment_id,
                    comment_text=comment_text,
                    matched_keyword="",
                    status="skipped_media",
                    error_message="규칙 대상 게시물이 아닙니다.",
                )
                last_skip_status = "skipped_media"
                continue

            excluded_keyword = _match_keyword(rule["exclude_keywords"], comment_text, rule["match_mode"])
            if excluded_keyword:
                _insert_log(
                    connection,
                    account_id=account["id"],
                    rule_id=rule["id"],
                    media_id=media_id,
                    comment_id=comment_id,
                    comment_text=comment_text,
                    matched_keyword=excluded_keyword,
                    status="skipped_keyword",
                    error_message="제외 키워드와 일치합니다.",
                )
                last_skip_status = "skipped_keyword"
                continue

            matched_keyword = _match_keyword(rule["keywords"], comment_text, rule["match_mode"])
            if not matched_keyword:
                _insert_log(
                    connection,
                    account_id=account["id"],
                    rule_id=rule["id"],
                    media_id=media_id,
                    comment_id=comment_id,
                    comment_text=comment_text,
                    matched_keyword="",
                    status="skipped_keyword",
                    error_message="키워드가 일치하지 않습니다.",
                )
                last_skip_status = "skipped_keyword"
                continue

            matched_rules.append((rule, matched_keyword))

        if matched_rules:
            rule, matched_keyword = matched_rules[0]
            for skipped_rule, skipped_keyword in matched_rules[1:]:
                _insert_log(
                    connection,
                    account_id=account["id"],
                    rule_id=skipped_rule["id"],
                    media_id=media_id,
                    comment_id=comment_id,
                    comment_text=comment_text,
                    matched_keyword=skipped_keyword,
                    status="skipped_rule_conflict",
                    error_message="같은 댓글에 여러 규칙이 맞아 먼저 만든 규칙만 처리했습니다.",
                )

            run_after = _build_run_after(rule, delay_override_seconds)
            connection.execute(
                """
                INSERT INTO job_queue (
                    account_id,
                    rule_id,
                    comment_id,
                    media_id,
                    comment_text,
                    status,
                    run_after,
                    attempt_count,
                    last_error,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'queued', ?, 0, '', ?, ?)
                """,
                (account["id"], rule["id"], comment_id, media_id, comment_text, run_after, utc_now(), utc_now()),
            )
            _insert_log(
                connection,
                account_id=account["id"],
                rule_id=rule["id"],
                media_id=media_id,
                comment_id=comment_id,
                comment_text=comment_text,
                matched_keyword=matched_keyword,
                status="queued",
            )
            return {
                "status": "queued",
                "queued": True,
                "rule_id": rule["id"],
                "matched_keyword": matched_keyword,
                "run_after": run_after,
            }

        return {"status": last_skip_status, "queued": False}


def process_due_jobs(*, limit: int = 5, now: str | None = None) -> list[dict[str, Any]]:
    now_value = now or utc_now()
    results = []
    for _ in range(limit):
        with get_connection() as connection:
            job = _claim_next_due_job(connection, now_value)
        if job is None:
            break
        results.append(_process_job(job))
    return results


def list_job_queue() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT job_queue.*, automation_rules.name AS rule_name
            FROM job_queue
            JOIN automation_rules ON automation_rules.id = job_queue.rule_id
            ORDER BY job_queue.id DESC
            LIMIT 50
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_automation_logs(
    *,
    status: str = "",
    rule_id: str = "",
    media_id: str = "",
    period: str = "",
) -> list[dict[str, Any]]:
    query = """
        SELECT
            automation_logs.*,
            automation_rules.name AS rule_name
        FROM automation_logs
        LEFT JOIN automation_rules ON automation_rules.id = automation_logs.rule_id
        WHERE 1 = 1
    """
    params: list[Any] = []
    if status:
        query += " AND automation_logs.status = ?"
        params.append(status)
    if rule_id:
        query += " AND automation_logs.rule_id = ?"
        params.append(int(rule_id))
    if media_id:
        query += " AND automation_logs.media_id = ?"
        params.append(media_id)
    since = _period_start(period)
    if since:
        query += " AND automation_logs.created_at >= ?"
        params.append(since)
    query += " ORDER BY automation_logs.id DESC LIMIT 100"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _period_start(period: str) -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if period == "today":
        return now.replace(hour=0, minute=0, second=0).isoformat()
    if period == "7d":
        return (now - timedelta(days=7)).isoformat()
    if period == "30d":
        return (now - timedelta(days=30)).isoformat()
    return ""


def _process_job(job: dict[str, Any]) -> dict[str, Any]:
    public_reply_status = "not_attempted"
    dm_status = "not_attempted"
    errors = []
    rate_limited = False
    permission_error = False
    reservation_ref_id = f"comment:{job['comment_id']}"
    reservation = reserve_one_credit(
        job["user_id"],
        ref_id=reservation_ref_id,
        reason="automation_comment_processed",
    )
    if not reservation.ok:
        error_message = "사용 가능한 토큰이 없습니다."
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE job_queue
                SET status = 'token_empty',
                    last_error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (error_message, utc_now(), job["id"]),
            )
            _insert_log(
                connection,
                account_id=job["account_id"],
                rule_id=job["rule_id"],
                media_id=job["media_id"],
                comment_id=job["comment_id"],
                comment_text=job["comment_text"],
                matched_keyword=job["matched_keyword"],
                status="token_empty",
                public_reply_status=public_reply_status,
                dm_status=dm_status,
                error_message=error_message,
            )
        return {
            "job_id": job["id"],
            "status": "token_empty",
            "public_reply_status": public_reply_status,
            "dm_status": dm_status,
            "charged": False,
        }

    access_token = _get_job_access_token(job)

    try:
        if access_token:
            meta_api.reply_to_comment(job["comment_id"], job["public_reply_text"], access_token=access_token)
        else:
            meta_api.reply_to_comment(job["comment_id"], job["public_reply_text"])
        public_reply_status = "success"
    except meta_api.MetaApiError as exc:
        public_reply_status = _status_from_meta_error(exc)
        rate_limited = rate_limited or public_reply_status == "rate_limited"
        permission_error = permission_error or public_reply_status == "permission_error"
        errors.append(exc.user_message)
    except Exception as exc:
        public_reply_status = "failed"
        errors.append(str(exc))

    try:
        if access_token:
            meta_api.send_private_reply(
                job["page_id"],
                job["comment_id"],
                job["dm_text"],
                cta_label=job["cta_label"] or None,
                cta_url=job["cta_url"] or None,
                access_token=access_token,
            )
        else:
            meta_api.send_private_reply(
                job["page_id"],
                job["comment_id"],
                job["dm_text"],
                cta_label=job["cta_label"] or None,
                cta_url=job["cta_url"] or None,
            )
        dm_status = "success"
    except meta_api.MetaApiError as exc:
        dm_status = _status_from_meta_error(exc)
        rate_limited = rate_limited or dm_status == "rate_limited"
        permission_error = permission_error or dm_status == "permission_error"
        errors.append(exc.user_message)
    except Exception as exc:
        dm_status = "failed"
        errors.append(str(exc))

    any_success = public_reply_status == "success" or dm_status == "success"
    all_success = public_reply_status == "success" and dm_status == "success"
    if all_success:
        final_status = "success"
    elif any_success:
        final_status = "partial_success"
    elif rate_limited:
        final_status = "rate_limited"
    elif permission_error:
        final_status = "permission_error"
    else:
        final_status = "failed"

    charged = False
    charge_amount = 0
    if final_status in {"success", "partial_success"}:
        charged = commit_reserved_credit(
            job["user_id"],
            ref_id=reservation_ref_id,
        )
        charge_amount = 1 if charged else 0
        if not charged:
            final_status = "failed"
            errors.append("예약한 토큰을 확정하지 못했습니다.")
    else:
        release_reserved_credit(
            job["user_id"],
            ref_id=reservation_ref_id,
            reason=f"automation_comment_{final_status}",
        )

    with get_connection() as connection:
        if final_status == "rate_limited" and int(job["attempt_count"]) < MAX_ATTEMPTS:
            retry_after = _seconds_from_now(60 * max(1, int(job["attempt_count"])))
            connection.execute(
                """
                UPDATE job_queue
                SET status = 'queued',
                    run_after = ?,
                    last_error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (retry_after, "; ".join(errors), utc_now(), job["id"]),
            )
        else:
            connection.execute(
                """
                UPDATE job_queue
                SET status = ?,
                    last_error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (final_status, "; ".join(errors), utc_now(), job["id"]),
            )
            _mark_processed_comment(
                connection,
                comment_id=job["comment_id"],
                media_id=job["media_id"],
                rule_id=job["rule_id"],
                charged=charged,
            )
        _insert_log(
            connection,
            account_id=job["account_id"],
            rule_id=job["rule_id"],
            media_id=job["media_id"],
            comment_id=job["comment_id"],
            comment_text=job["comment_text"],
            matched_keyword=job["matched_keyword"],
            status=final_status,
            public_reply_status=public_reply_status,
            dm_status=dm_status,
            charged=charged,
            charge_amount=charge_amount,
            error_message="; ".join(errors),
        )
    return {
        "job_id": job["id"],
        "status": final_status,
        "public_reply_status": public_reply_status,
        "dm_status": dm_status,
        "charged": charged,
    }


def _get_job_access_token(job: dict[str, Any]) -> str:
    try:
        return get_account_page_access_token(int(job["account_id"]))
    except (TokenCryptoError, ValueError, TypeError):
        return ""


def _claim_next_due_job(connection, now_value: str) -> dict[str, Any] | None:
    rows = connection.execute(
        """
        SELECT
            job_queue.*,
            automation_rules.public_reply_text,
            automation_rules.dm_text,
            automation_rules.cta_label,
            automation_rules.cta_url,
            connected_accounts.page_id,
            connected_accounts.user_id
        FROM job_queue
        JOIN automation_rules ON automation_rules.id = job_queue.rule_id
        JOIN connected_accounts ON connected_accounts.id = job_queue.account_id
        WHERE job_queue.status = 'queued'
          AND job_queue.run_after <= ?
          AND automation_rules.enabled = 1
          AND connected_accounts.active = 1
        ORDER BY job_queue.run_after, job_queue.id
        LIMIT 20
        """,
        (now_value,),
    ).fetchall()
    for row in rows:
        if _has_processing_job(connection, row["account_id"]):
            continue
        if _recent_account_attempts(connection, row["account_id"]) >= ACCOUNT_MINUTE_LIMIT:
            continue
        now = utc_now()
        connection.execute(
            """
            UPDATE job_queue
            SET status = 'processing',
                attempt_count = attempt_count + 1,
                updated_at = ?
            WHERE id = ? AND status = 'queued'
            """,
            (now, row["id"]),
        )
        job = dict(row)
        job["attempt_count"] = int(job["attempt_count"]) + 1
        job["matched_keyword"] = _get_matched_keyword_for_job(connection, job)
        return job
    return None


def _get_matched_keyword_for_job(connection, job: dict[str, Any]) -> str:
    row = connection.execute(
        """
        SELECT matched_keyword
        FROM automation_logs
        WHERE rule_id = ?
          AND comment_id = ?
          AND status = 'queued'
        ORDER BY id DESC
        LIMIT 1
        """,
        (job["rule_id"], job["comment_id"]),
    ).fetchone()
    if row is None:
        return ""
    return row["matched_keyword"]


def _get_active_account(connection, user_id: int):
    return connection.execute(
        """
        SELECT id, user_id, page_id, ig_user_id, active
        FROM connected_accounts
        WHERE user_id = ?
          AND provider = 'meta'
          AND active = 1
        ORDER BY id
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()


def _get_enabled_rules(connection, account_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT *
        FROM automation_rules
        WHERE account_id = ?
          AND enabled = 1
        ORDER BY id
        """,
        (account_id,),
    ).fetchall()
    rules = []
    for row in rows:
        rule = dict(row)
        rule["keywords"] = json.loads(rule["keywords_json"])
        rule["exclude_keywords"] = json.loads(rule["exclude_keywords_json"])
        rules.append(rule)
    return rules


def _check_media_target(connection, rule: dict[str, Any], media_id: str) -> str:
    if rule["target_mode"] == "all":
        return "matched"
    row = connection.execute(
        """
        SELECT id
        FROM rule_media_targets
        WHERE rule_id = ? AND media_id = ?
        """,
        (rule["id"], media_id),
    ).fetchone()
    return "matched" if row is not None else "skipped_media"


def _match_keyword(keywords: list[str], comment_text: str, match_mode: str) -> str:
    normalized_text = comment_text.strip().lower()
    for keyword in keywords:
        normalized_keyword = keyword.strip().lower()
        if match_mode == "exact" and normalized_text == normalized_keyword:
            return keyword
        if match_mode == "contains" and normalized_keyword in normalized_text:
            return keyword
    return ""


def _build_run_after(rule: dict[str, Any], delay_override_seconds: int | None) -> str:
    if delay_override_seconds is not None:
        return _seconds_from_now(max(0, delay_override_seconds))
    delay_min = int(rule["delay_min_seconds"]) or DEFAULT_DELAY_MIN_SECONDS
    delay_max = int(rule["delay_max_seconds"]) or DEFAULT_DELAY_MAX_SECONDS
    if delay_min <= 0 and delay_max <= 0:
        delay_min = DEFAULT_DELAY_MIN_SECONDS
        delay_max = DEFAULT_DELAY_MAX_SECONDS
    if delay_max < delay_min:
        delay_max = delay_min
    return _seconds_from_now(random.randint(delay_min, delay_max))


def _seconds_from_now(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).replace(microsecond=0).isoformat()


def _is_duplicate_comment(connection, comment_id: str) -> bool:
    processed = connection.execute(
        "SELECT id FROM processed_comments WHERE comment_id = ?",
        (comment_id,),
    ).fetchone()
    if processed is not None:
        return True
    queued = connection.execute(
        "SELECT id FROM job_queue WHERE comment_id = ?",
        (comment_id,),
    ).fetchone()
    return queued is not None


def _has_processing_job(connection, account_id: int) -> bool:
    row = connection.execute(
        """
        SELECT id
        FROM job_queue
        WHERE account_id = ? AND status = 'processing'
        LIMIT 1
        """,
        (account_id,),
    ).fetchone()
    return row is not None


def _recent_account_attempts(connection, account_id: int) -> int:
    since = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(microsecond=0).isoformat()
    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM automation_logs
        WHERE account_id = ?
          AND status IN ('success', 'partial_success', 'failed', 'permission_error', 'rate_limited')
          AND created_at >= ?
        """,
        (account_id, since),
    ).fetchone()
    return int(row[0])


def _mark_processed_comment(
    connection,
    *,
    comment_id: str,
    media_id: str,
    rule_id: int,
    charged: bool,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO processed_comments (
            comment_id,
            media_id,
            rule_id,
            charged,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (comment_id, media_id, rule_id, 1 if charged else 0, utc_now()),
    )


def _insert_log(
    connection,
    *,
    account_id: int,
    rule_id: int | None,
    media_id: str,
    comment_id: str,
    comment_text: str,
    matched_keyword: str,
    status: str,
    public_reply_status: str = "",
    dm_status: str = "",
    charged: bool = False,
    charge_amount: int = 0,
    error_message: str = "",
) -> None:
    connection.execute(
        """
        INSERT INTO automation_logs (
            account_id,
            rule_id,
            media_id,
            comment_id,
            comment_text,
            matched_keyword,
            status,
            public_reply_status,
            dm_status,
            charged,
            charge_amount,
            error_message,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            account_id,
            rule_id,
            media_id,
            comment_id,
            comment_text,
            matched_keyword,
            status,
            public_reply_status,
            dm_status,
            1 if charged else 0,
            charge_amount,
            error_message,
            utc_now(),
        ),
    )


def _skip_without_rule(
    connection,
    *,
    user_id: int,
    media_id: str,
    comment_id: str,
    comment_text: str,
    status: str,
    error_message: str,
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT id
        FROM connected_accounts
        WHERE user_id = ?
        ORDER BY id
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if row is not None:
        _insert_log(
            connection,
            account_id=row["id"],
            rule_id=None,
            media_id=media_id,
            comment_id=comment_id,
            comment_text=comment_text,
            matched_keyword="",
            status=status,
            error_message=error_message,
        )
    return {"status": status, "queued": False}


def _status_from_meta_error(error: meta_api.MetaApiError) -> str:
    if error.status_code in (401, 403):
        return "permission_error"
    if error.status_code == 429:
        return "rate_limited"
    return "failed"


def _required(value: str, name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value
