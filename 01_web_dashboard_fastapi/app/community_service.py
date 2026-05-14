import hashlib
import hmac
import html
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from starlette.datastructures import Headers

from app.community_moderation import CommunityModerationService, input_hash
from app.security import get_session_secret, password_hash, verify_password_hash


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DEFAULT_DB_PATH = PROJECT_DIR / "dashboard.db"
REPORT_THRESHOLD_DEFAULT = 3

DEFAULT_BOARDS = [
    ("notice", "공지", "운영자가 전하는 커뮤니티 안내", 10, 1),
    ("free", "자유게시판", "학교생활과 일상을 자유롭게 나누는 공간", 20, 0),
    ("anonymous", "익명게시판", "이름 없이 편하게 이야기하는 공간", 30, 0),
    ("question", "질문게시판", "수업, 생활, 진로 질문을 나누는 공간", 40, 0),
    ("lost", "분실물게시판", "잃어버린 물건과 습득물을 공유하는 공간", 50, 0),
    ("suggestion", "건의함", "학교생활 개선 아이디어를 남기는 공간", 60, 0),
]

REPORT_REASONS = [
    ("abuse", "욕설/비방"),
    ("privacy", "개인정보 노출"),
    ("harassment", "성희롱"),
    ("hate", "혐오/차별"),
    ("spam", "도배/스팸"),
    ("other", "기타"),
]

STATUS_LABELS = {
    "visible": "공개",
    "pending_review": "검토 대기",
    "auto_hidden": "자동 숨김",
    "admin_hidden": "관리자 숨김",
    "deleted_by_user": "작성자 삭제",
    "deleted_by_admin": "관리자 삭제",
    "open": "접수됨",
    "resolved": "처리 완료",
    "dismissed": "기각",
    "allow": "허용",
    "pending_review_action": "검토 대기",
    "auto_hide": "자동 숨김",
    "like": "좋아요",
    "unlike": "좋아요 취소",
}

TARGET_TYPE_LABELS = {"post": "게시글", "comment": "댓글"}

MODERATION_REASON_LABELS = {
    "blocked_term": "금칙어 의심",
    "empty": "빈 내용",
    "too_long_for_moderation": "검토 길이 초과",
    "personal_info_email": "이메일 형태 개인정보 의심",
    "personal_info_phone": "전화번호 형태 개인정보 의심",
    "personal_info_identifier": "식별번호 형태 개인정보 의심",
    "personal_info_long_number": "긴 숫자열 개인정보 의심",
    "too_many_urls": "URL 과다 포함",
    "repeated_characters": "반복 문자 과다",
    "repeated_pattern": "반복 패턴 과다",
    "excessive_symbols": "특수문자 과다",
}


def community_db_path() -> Path:
    explicit = os.getenv("COMMUNITY_DB_PATH", "").strip() or os.getenv("NEWS_DB_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    return DEFAULT_DB_PATH


def now_text() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def connect() -> sqlite3.Connection:
    path = community_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_community_tables() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS community_boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                admin_only_write INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS community_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author_label TEXT DEFAULT '익명',
                password_hash TEXT,
                is_notice INTEGER DEFAULT 0,
                is_hidden INTEGER DEFAULT 0,
                hidden_reason TEXT DEFAULT '',
                moderation_status TEXT DEFAULT 'visible',
                moderation_score INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                report_count INTEGER DEFAULT 0,
                ip_hash TEXT,
                user_agent_hash TEXT,
                session_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(board_id) REFERENCES community_boards(id)
            );

            CREATE TABLE IF NOT EXISTS community_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                parent_id INTEGER,
                content TEXT NOT NULL,
                author_label TEXT DEFAULT '익명',
                password_hash TEXT,
                is_hidden INTEGER DEFAULT 0,
                hidden_reason TEXT DEFAULT '',
                moderation_status TEXT DEFAULT 'visible',
                moderation_score INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                report_count INTEGER DEFAULT 0,
                ip_hash TEXT,
                user_agent_hash TEXT,
                session_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
                FOREIGN KEY(parent_id) REFERENCES community_comments(id)
            );

            CREATE TABLE IF NOT EXISTS community_reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                reaction_type TEXT DEFAULT 'like',
                session_hash TEXT,
                ip_hash TEXT,
                user_agent_hash TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS community_reaction_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                session_hash TEXT,
                ip_hash TEXT,
                user_agent_hash TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS community_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                detail TEXT DEFAULT '',
                status TEXT DEFAULT 'open',
                reporter_session_hash TEXT,
                reporter_ip_hash TEXT,
                reporter_user_agent_hash TEXT,
                created_at TEXT NOT NULL,
                handled_at TEXT,
                handler_note TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS community_post_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                old_title TEXT NOT NULL,
                old_content TEXT NOT NULL,
                new_title TEXT NOT NULL,
                new_content TEXT NOT NULL,
                editor_type TEXT NOT NULL,
                ip_hash TEXT,
                user_agent_hash TEXT,
                session_hash TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS community_comment_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id INTEGER NOT NULL,
                old_content TEXT NOT NULL,
                new_content TEXT NOT NULL,
                editor_type TEXT NOT NULL,
                ip_hash TEXT,
                user_agent_hash TEXT,
                session_hash TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS community_activity_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_type TEXT NOT NULL,
                subject_value TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS community_moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_id INTEGER,
                input_hash TEXT NOT NULL,
                rule_flag INTEGER DEFAULT 0,
                ai_flag INTEGER DEFAULT 0,
                final_flag INTEGER DEFAULT 0,
                final_action TEXT NOT NULL,
                reason TEXT DEFAULT '',
                model_name TEXT DEFAULT '',
                latency_ms INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS community_bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ban_type TEXT NOT NULL,
                ban_value TEXT NOT NULL,
                reason TEXT DEFAULT '',
                expires_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS community_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_community_posts_board_created
                ON community_posts(board_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_community_posts_hidden_created
                ON community_posts(is_hidden, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_community_comments_post_created
                ON community_comments(post_id, created_at ASC);
            CREATE INDEX IF NOT EXISTS idx_community_reports_status_created
                ON community_reports(status, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_community_reactions_target
                ON community_reactions(target_type, target_id);
            CREATE INDEX IF NOT EXISTS idx_community_moderation_logs_created
                ON community_moderation_logs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_community_reaction_logs_target
                ON community_reaction_logs(target_type, target_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_community_activity_notes_subject
                ON community_activity_notes(subject_type, subject_value);
            """
        )
        ensure_column(conn, "community_posts", "deleted_at", "TEXT")
        ensure_column(conn, "community_posts", "is_edited", "INTEGER DEFAULT 0")
        ensure_column(conn, "community_posts", "session_hash", "TEXT")
        ensure_column(conn, "community_comments", "deleted_at", "TEXT")
        ensure_column(conn, "community_comments", "is_edited", "INTEGER DEFAULT 0")
        ensure_column(conn, "community_comments", "session_hash", "TEXT")
        ensure_column(conn, "community_reactions", "user_agent_hash", "TEXT")
        ensure_column(conn, "community_reactions", "is_active", "INTEGER DEFAULT 1")
        ensure_column(conn, "community_reports", "reporter_user_agent_hash", "TEXT")
        for slug, name, description, sort_order, admin_only in DEFAULT_BOARDS:
            conn.execute(
                """
                INSERT INTO community_boards
                    (slug, name, description, sort_order, is_active, admin_only_write, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    sort_order = excluded.sort_order,
                    admin_only_write = excluded.admin_only_write
                """,
                (slug, name, description, sort_order, admin_only, now_text()),
            )
        seed_settings(conn)


def seed_settings(conn: sqlite3.Connection) -> None:
    defaults = {
        "moderation_enabled": os.getenv("COMMUNITY_MODERATION_ENABLED", "true"),
        "auto_hide_enabled": os.getenv("COMMUNITY_MODERATION_AUTO_HIDE", "true"),
        "report_threshold": os.getenv("COMMUNITY_REPORT_THRESHOLD", str(REPORT_THRESHOLD_DEFAULT)),
        "max_post_length": os.getenv("COMMUNITY_MAX_POST_LENGTH", "3000"),
        "max_comment_length": os.getenv("COMMUNITY_MAX_COMMENT_LENGTH", "800"),
        "fail_mode": os.getenv("COMMUNITY_MODERATION_FAIL_MODE", "pending_review"),
        "maintenance_notice": "",
        "blocked_terms": os.getenv("COMMUNITY_BLOCKED_TERMS", ""),
    }
    current_time = now_text()
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO community_settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, current_time),
        )


def setting(key: str, default: str = "") -> str:
    ensure_community_tables()
    with connect() as conn:
        row = conn.execute("SELECT value FROM community_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def moderation_service() -> CommunityModerationService:
    return CommunityModerationService(blocked_terms=setting("blocked_terms", ""))


def bool_setting(key: str, default: bool = False) -> bool:
    value = setting(key, "true" if default else "false")
    return value.lower() in {"1", "true", "yes", "on"}


def int_setting(key: str, default: int) -> int:
    try:
        return int(setting(key, str(default)))
    except ValueError:
        return default


def update_settings(values: Dict[str, str]) -> None:
    ensure_community_tables()
    allowed = {
        "moderation_enabled",
        "auto_hide_enabled",
        "report_threshold",
        "max_post_length",
        "max_comment_length",
        "fail_mode",
        "maintenance_notice",
        "blocked_terms",
    }
    with connect() as conn:
        for key in allowed:
            if key in values:
                conn.execute(
                    """
                    INSERT INTO community_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                    """,
                    (key, values.get(key, ""), now_text()),
                )


def sign_hash(value: str) -> str:
    secret = os.getenv("COMMUNITY_HASH_SECRET", "").strip() or os.getenv("NEWS_SESSION_SECRET", "").strip() or get_session_secret()
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def client_identity(headers: Headers, client_host: str) -> Tuple[str, str]:
    user_agent = headers.get("user-agent", "")
    return sign_hash(f"ip:{client_host}"), sign_hash(f"ua:{user_agent}")


def session_id_from_cookie(cookie_value: str = "") -> str:
    return cookie_value if cookie_value else secrets.token_urlsafe(24)


def session_hash(session_id: str) -> str:
    return sign_hash(f"session:{session_id}")


def is_banned(ip_hash: str, session_hash_value: str) -> bool:
    ensure_community_tables()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id FROM community_bans
            WHERE (ban_type = 'ip_hash' AND ban_value = ?)
               OR (ban_type = 'session_hash' AND ban_value = ?)
            LIMIT 1
            """,
            (ip_hash, session_hash_value),
        ).fetchone()
    return bool(row)


def render_content(content: str) -> str:
    escaped = html.escape(content.strip())
    paragraphs = [p.strip() for p in escaped.split("\n\n") if p.strip()]
    if not paragraphs:
        return ""
    return "\n".join(f"<p>{p.replace(chr(10), '<br />')}</p>" for p in paragraphs)


def format_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%Y.%m.%d %H:%M")
    except ValueError:
        return value[:16]


def decorate_post(row: sqlite3.Row) -> Dict[str, Any]:
    post = dict(row)
    post["created_display"] = format_date(post.get("created_at", ""))
    post["updated_display"] = format_date(post.get("updated_at", ""))
    post["content_html"] = render_content(post.get("content", ""))
    post["is_review"] = post.get("moderation_status") in {"pending_review", "auto_hidden"}
    post["status_label"] = STATUS_LABELS.get(post.get("moderation_status", ""), post.get("moderation_status", ""))
    post["is_deleted"] = post.get("moderation_status") in {"deleted_by_user", "deleted_by_admin"}
    if "final_action" in post:
        post["final_action_label"] = STATUS_LABELS.get(post.get("final_action", ""), post.get("final_action", ""))
    if "moderation_reason" in post:
        post["moderation_reason_label"] = label_moderation_reasons(post.get("moderation_reason", ""))
    return post


def decorate_comment(row: sqlite3.Row) -> Dict[str, Any]:
    comment = dict(row)
    comment["created_display"] = format_date(comment.get("created_at", ""))
    comment["updated_display"] = format_date(comment.get("updated_at", ""))
    comment["content_html"] = render_content(comment.get("content", ""))
    comment["status_label"] = STATUS_LABELS.get(comment.get("moderation_status", ""), comment.get("moderation_status", ""))
    comment["is_deleted"] = comment.get("moderation_status") in {"deleted_by_user", "deleted_by_admin"}
    if "final_action" in comment:
        comment["final_action_label"] = STATUS_LABELS.get(comment.get("final_action", ""), comment.get("final_action", ""))
    if "moderation_reason" in comment:
        comment["moderation_reason_label"] = label_moderation_reasons(comment.get("moderation_reason", ""))
    return comment


def label_moderation_reasons(raw: str) -> str:
    labels = []
    for item in str(raw or "").split(","):
        key = item.strip()
        if not key:
            continue
        if key.startswith("ai_error"):
            labels.append("AI 호출 실패")
        else:
            labels.append(MODERATION_REASON_LABELS.get(key, key))
    return ", ".join(labels)


def boards(active_only: bool = True) -> List[Dict[str, Any]]:
    ensure_community_tables()
    where = "WHERE is_active = 1" if active_only else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT b.*,
                   (SELECT COUNT(*) FROM community_posts p
                    WHERE p.board_id = b.id AND p.is_hidden = 0 AND p.moderation_status = 'visible') AS post_count
            FROM community_boards b
            {where}
            ORDER BY b.sort_order ASC, b.id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def public_write_boards() -> List[Dict[str, Any]]:
    return [board for board in boards() if not int(board.get("admin_only_write", 0))]


def get_board(slug: str) -> Optional[Dict[str, Any]]:
    ensure_community_tables()
    with connect() as conn:
        row = conn.execute("SELECT * FROM community_boards WHERE slug = ? AND is_active = 1", (slug,)).fetchone()
    return dict(row) if row else None


def home_data() -> Dict[str, Any]:
    ensure_community_tables()
    with connect() as conn:
        latest = conn.execute(
            """
            SELECT p.*, b.slug AS board_slug, b.name AS board_name
            FROM community_posts p
            JOIN community_boards b ON b.id = p.board_id
            WHERE p.is_hidden = 0 AND p.moderation_status = 'visible'
            ORDER BY p.is_notice DESC, p.created_at DESC
            LIMIT 10
            """
        ).fetchall()
        notices = conn.execute(
            """
            SELECT p.*, b.slug AS board_slug, b.name AS board_name
            FROM community_posts p
            JOIN community_boards b ON b.id = p.board_id
            WHERE p.is_hidden = 0 AND p.moderation_status = 'visible' AND p.is_notice = 1
            ORDER BY p.created_at DESC
            LIMIT 5
            """
        ).fetchall()
        popular = conn.execute(
            """
            SELECT p.*, b.slug AS board_slug, b.name AS board_name
            FROM community_posts p
            JOIN community_boards b ON b.id = p.board_id
            WHERE p.is_hidden = 0 AND p.moderation_status = 'visible'
            ORDER BY (p.like_count + p.comment_count + p.view_count / 10) DESC, p.created_at DESC
            LIMIT 8
            """
        ).fetchall()
    return {
        "boards": boards(),
        "notice_posts": [decorate_post(row) for row in notices],
        "latest_posts": [decorate_post(row) for row in latest],
        "popular_posts": [decorate_post(row) for row in popular],
        "maintenance_notice": setting("maintenance_notice", ""),
    }


def list_posts(board_slug: str = "", query: str = "", sort: str = "latest", limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    ensure_community_tables()
    params: List[Any] = []
    limit = max(1, min(int(limit or 10), 30))
    offset = max(0, int(offset or 0))
    where = ["p.is_hidden = 0", "p.moderation_status = 'visible'"]
    if board_slug:
        where.append("b.slug = ?")
        params.append(board_slug)
    clean_query = query.strip()[:80]
    if clean_query:
        where.append("(p.title LIKE ? OR p.content LIKE ?)")
        params.extend([f"%{clean_query}%", f"%{clean_query}%"])
    order = "p.created_at DESC"
    if sort == "popular":
        order = "(p.like_count + p.comment_count + p.view_count / 10) DESC, p.created_at DESC"
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*, b.slug AS board_slug, b.name AS board_name
            FROM community_posts p
            JOIN community_boards b ON b.id = p.board_id
            WHERE {' AND '.join(where)}
            ORDER BY p.is_notice DESC, {order}
            LIMIT ? OFFSET ?
            """,
            params + [limit + 1, offset],
        ).fetchall()
    has_more = len(rows) > limit
    visible_rows = rows[:limit]
    return {
        "posts": [decorate_post(row) for row in visible_rows],
        "query": clean_query,
        "sort": sort,
        "limit": limit,
        "offset": offset,
        "next_offset": offset + limit,
        "has_more": has_more,
    }


def get_public_post(post_id: int, increment_view: bool = False) -> Optional[Dict[str, Any]]:
    ensure_community_tables()
    with connect() as conn:
        if increment_view:
            conn.execute(
                "UPDATE community_posts SET view_count = view_count + 1 WHERE id = ? AND is_hidden = 0 AND moderation_status = 'visible'",
                (post_id,),
            )
        row = conn.execute(
            """
            SELECT p.*, b.slug AS board_slug, b.name AS board_name
            FROM community_posts p
            JOIN community_boards b ON b.id = p.board_id
            WHERE p.id = ? AND p.is_hidden = 0 AND p.moderation_status = 'visible'
            """,
            (post_id,),
        ).fetchone()
    return decorate_post(row) if row else None


def get_post_for_password_action(post_id: int) -> Optional[Dict[str, Any]]:
    ensure_community_tables()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT p.*, b.slug AS board_slug, b.name AS board_name
            FROM community_posts p JOIN community_boards b ON b.id = p.board_id
            WHERE p.id = ?
            """,
            (post_id,),
        ).fetchone()
    return decorate_post(row) if row else None


def verify_post_password(post_id: int, password: str) -> bool:
    post = get_post_for_password_action(post_id)
    if not post or not post.get("password_hash"):
        return False
    return verify_password_hash(password, post["password_hash"])


def get_comments(post_id: int, include_hidden: bool = False) -> List[Dict[str, Any]]:
    ensure_community_tables()
    where = "post_id = ?"
    if not include_hidden:
        where += " AND is_hidden = 0 AND moderation_status = 'visible'"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM community_comments WHERE {where} ORDER BY created_at ASC, id ASC",
            (post_id,),
        ).fetchall()
    return [decorate_comment(row) for row in rows]


def validate_post_form(form: Dict[str, str], admin: bool = False) -> Tuple[Dict[str, Any], Dict[str, str]]:
    title = form.get("title", "").strip()
    content = form.get("content", "").strip()
    board_slug = form.get("board_slug", "").strip()
    password = form.get("password", "")
    errors: Dict[str, str] = {}
    max_length = int_setting("max_post_length", 3000)
    if len(title) < 2 or len(title) > 80:
        errors["title"] = "제목은 2~80자로 입력하세요."
    if len(content) < 2 or len(content) > max_length:
        errors["content"] = f"내용은 2~{max_length}자로 입력하세요."
    if not admin and (len(password) < 4 or len(password) > 32):
        errors["password"] = "비밀번호는 4~32자로 입력하세요."
    board = get_board(board_slug)
    if not board:
        errors["board_slug"] = "게시판을 선택하세요."
    elif board["admin_only_write"] and not admin:
        errors["board_slug"] = "공지 게시판은 관리자만 작성할 수 있습니다."
    return {
        "title": title,
        "content": content,
        "board": board,
        "password": password,
        "is_notice": 1 if (board and board["slug"] == "notice") else 0,
    }, errors


def moderation_to_status(action: str) -> Tuple[int, str, str]:
    if action == "allow":
        return 0, "visible", ""
    if action == "auto_hide":
        return 1, "auto_hidden", "자동 안전 필터 검토 대기"
    return 0, "pending_review", "관리자 검토 대기"


def log_moderation(
    conn: sqlite3.Connection,
    target_type: str,
    target_id: Optional[int],
    content: str,
    decision: Any,
) -> None:
    conn.execute(
        """
        INSERT INTO community_moderation_logs
            (target_type, target_id, input_hash, rule_flag, ai_flag, final_flag,
             final_action, reason, model_name, latency_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            target_type,
            target_id,
            input_hash(content),
            decision.rule_flag,
            decision.ai_flag,
            decision.final_flag,
            decision.action,
            ",".join(decision.reasons[:8]),
            decision.model_name,
            decision.latency_ms,
            now_text(),
        ),
    )


def create_post(form: Dict[str, str], headers: Headers, client_host: str, session_id: str, admin: bool = False) -> Tuple[bool, str, Optional[int]]:
    ensure_community_tables()
    data, errors = validate_post_form(form, admin=admin)
    if errors:
        return False, next(iter(errors.values())), None

    ip_hash, user_agent_hash = client_identity(headers, client_host)
    session_hash_value = session_hash(session_id)
    if is_banned(ip_hash, session_hash_value):
        return False, "현재 작성이 제한된 상태입니다.", None
    decision = moderation_service().moderate(f"{data['title']}\n{data['content']}")
    is_hidden, moderation_status, hidden_reason = moderation_to_status(decision.action)
    if admin:
        is_hidden, moderation_status, hidden_reason = 0, "visible", ""
    stored_password = password_hash(data["password"]) if data["password"] else ""
    current_time = now_text()

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO community_posts
                (board_id, title, content, author_label, password_hash, is_notice,
                 is_hidden, hidden_reason, moderation_status, moderation_score,
                 ip_hash, user_agent_hash, session_hash, created_at, updated_at)
            VALUES (?, ?, ?, '익명', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["board"]["id"],
                data["title"],
                data["content"],
                stored_password,
                data["is_notice"],
                is_hidden,
                hidden_reason,
                moderation_status,
                decision.final_flag,
                ip_hash,
                user_agent_hash,
                session_hash_value,
                current_time,
                current_time,
            ),
        )
        post_id = int(cursor.lastrowid)
        log_moderation(conn, "post", post_id, f"{data['title']}\n{data['content']}", decision)

    if moderation_status == "visible":
        return True, "게시되었습니다.", post_id
    if moderation_status == "auto_hidden":
        return True, "작성 내용이 커뮤니티 운영 기준에 따라 검토 대기 상태로 전환되었습니다.", post_id
    return True, "게시물이 관리자 검토 후 표시됩니다.", post_id


def update_post_with_password(post_id: int, form: Dict[str, str], headers: Headers, client_host: str, session_id: str) -> Tuple[bool, str]:
    if not verify_post_password(post_id, form.get("password", "")):
        return False, "비밀번호가 올바르지 않습니다."
    existing = get_post_for_password_action(post_id)
    if not existing:
        return False, "게시글을 찾을 수 없습니다."
    if existing.get("is_deleted"):
        return False, "삭제된 게시글은 수정할 수 없습니다."
    data, errors = validate_post_form(
        {
            "board_slug": existing["board_slug"],
            "title": form.get("title", ""),
            "content": form.get("content", ""),
            "password": "1234",
        },
        admin=False,
    )
    if errors:
        return False, next(iter(errors.values()))
    ip_hash, user_agent_hash = client_identity(headers, client_host)
    session_hash_value = session_hash(session_id)
    if is_banned(ip_hash, session_hash_value):
        return False, "현재 댓글 작성이 제한된 상태입니다."
    decision = moderation_service().moderate(f"{data['title']}\n{data['content']}")
    is_hidden, moderation_status, hidden_reason = moderation_to_status(decision.action)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO community_post_revisions
                (post_id, old_title, old_content, new_title, new_content, editor_type,
                 ip_hash, user_agent_hash, session_hash, created_at)
            VALUES (?, ?, ?, ?, ?, 'author', ?, ?, ?, ?)
            """,
            (
                post_id,
                existing["title"],
                existing["content"],
                data["title"],
                data["content"],
                ip_hash,
                user_agent_hash,
                session_hash_value,
                now_text(),
            ),
        )
        conn.execute(
            """
            UPDATE community_posts
            SET title = ?, content = ?, is_hidden = ?, hidden_reason = ?,
                moderation_status = ?, moderation_score = ?, is_edited = 1, updated_at = ?
            WHERE id = ?
            """,
            (
                data["title"],
                data["content"],
                is_hidden,
                hidden_reason,
                moderation_status,
                decision.final_flag,
                now_text(),
                post_id,
            ),
        )
        log_moderation(conn, "post", post_id, f"{data['title']}\n{data['content']}", decision)
    if moderation_status == "visible":
        return True, "수정되었습니다."
    return True, "수정 내용이 관리자 검토 후 표시됩니다."


def delete_post_with_password(post_id: int, password: str) -> Tuple[bool, str]:
    if not verify_post_password(post_id, password):
        return False, "비밀번호가 올바르지 않습니다."
    soft_delete_post(post_id, "deleted_by_user")
    return True, "게시글이 삭제 처리되었습니다."


def add_comment(post_id: int, content: str, password: str, headers: Headers, client_host: str, session_id: str) -> Tuple[bool, str]:
    ensure_community_tables()
    content = content.strip()
    max_length = int_setting("max_comment_length", 800)
    if not content:
        return False, "댓글 내용을 입력하세요."
    if len(content) > max_length:
        return False, f"댓글은 {max_length}자 이하로 입력하세요."
    if len(password) < 4 or len(password) > 32:
        return False, "댓글 비밀번호는 4~32자로 입력하세요."
    post = get_public_post(post_id)
    if not post:
        return False, "게시글을 찾을 수 없습니다."

    ip_hash, user_agent_hash = client_identity(headers, client_host)
    session_hash_value = session_hash(session_id)
    decision = moderation_service().moderate(content)
    is_hidden, moderation_status, hidden_reason = moderation_to_status(decision.action)
    stored_password = password_hash(password) if password else ""
    current_time = now_text()

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO community_comments
                (post_id, content, author_label, password_hash, is_hidden, hidden_reason,
                 moderation_status, moderation_score, ip_hash, user_agent_hash, session_hash, created_at, updated_at)
            VALUES (?, ?, '익명', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post_id,
                content,
                stored_password,
                is_hidden,
                hidden_reason,
                moderation_status,
                decision.final_flag,
                ip_hash,
                user_agent_hash,
                session_hash_value,
                current_time,
                current_time,
            ),
        )
        comment_id = int(cursor.lastrowid)
        if moderation_status == "visible":
            conn.execute("UPDATE community_posts SET comment_count = comment_count + 1 WHERE id = ?", (post_id,))
        log_moderation(conn, "comment", comment_id, content, decision)

    if moderation_status == "visible":
        return True, "댓글이 등록되었습니다."
    return True, "댓글이 관리자 검토 후 표시됩니다."


def get_comment_for_password_action(comment_id: int) -> Optional[Dict[str, Any]]:
    ensure_community_tables()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT c.*, p.title AS post_title
            FROM community_comments c
            JOIN community_posts p ON p.id = c.post_id
            WHERE c.id = ?
            """,
            (comment_id,),
        ).fetchone()
    return decorate_comment(row) if row else None


def verify_comment_password(comment_id: int, password: str) -> bool:
    comment = get_comment_for_password_action(comment_id)
    if not comment or not comment.get("password_hash"):
        return False
    return verify_password_hash(password, comment["password_hash"])


def update_comment_with_password(comment_id: int, content: str, password: str, headers: Headers, client_host: str, session_id: str) -> Tuple[bool, str, Optional[int]]:
    if not verify_comment_password(comment_id, password):
        return False, "비밀번호가 올바르지 않습니다.", None
    existing = get_comment_for_password_action(comment_id)
    if not existing:
        return False, "댓글을 찾을 수 없습니다.", None
    if existing.get("is_deleted"):
        return False, "삭제된 댓글은 수정할 수 없습니다.", existing.get("post_id")
    content = content.strip()
    max_length = int_setting("max_comment_length", 800)
    if not content:
        return False, "댓글 내용을 입력하세요.", existing.get("post_id")
    if len(content) > max_length:
        return False, f"댓글은 {max_length}자 이하로 입력하세요.", existing.get("post_id")
    ip_hash, user_agent_hash = client_identity(headers, client_host)
    session_hash_value = session_hash(session_id)
    decision = moderation_service().moderate(content)
    is_hidden, moderation_status, hidden_reason = moderation_to_status(decision.action)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO community_comment_revisions
                (comment_id, old_content, new_content, editor_type, ip_hash, user_agent_hash, session_hash, created_at)
            VALUES (?, ?, ?, 'author', ?, ?, ?, ?)
            """,
            (comment_id, existing["content"], content, ip_hash, user_agent_hash, session_hash_value, now_text()),
        )
        conn.execute(
            """
            UPDATE community_comments
            SET content = ?, is_hidden = ?, hidden_reason = ?, moderation_status = ?,
                moderation_score = ?, is_edited = 1, updated_at = ?
            WHERE id = ?
            """,
            (content, is_hidden, hidden_reason, moderation_status, decision.final_flag, now_text(), comment_id),
        )
        log_moderation(conn, "comment", comment_id, content, decision)
        refresh_comment_count(conn, int(existing["post_id"]))
    if moderation_status == "visible":
        return True, "댓글이 수정되었습니다.", existing.get("post_id")
    return True, "수정한 댓글이 관리자 검토 후 표시됩니다.", existing.get("post_id")


def delete_comment_with_password(comment_id: int, password: str) -> Tuple[bool, str, Optional[int]]:
    if not verify_comment_password(comment_id, password):
        return False, "비밀번호가 올바르지 않습니다.", None
    comment = get_comment_for_password_action(comment_id)
    if not comment:
        return False, "댓글을 찾을 수 없습니다.", None
    soft_delete_comment(comment_id, "deleted_by_user")
    return True, "댓글이 삭제 처리되었습니다.", comment.get("post_id")


def react(target_type: str, target_id: int, ip_hash: str, user_agent_hash: str, session_hash_value: str) -> Tuple[bool, str]:
    ensure_community_tables()
    if target_type not in {"post", "comment"}:
        return False, "잘못된 대상입니다."
    if is_banned(ip_hash, session_hash_value):
        return False, "현재 반응이 제한된 상태입니다."
    with connect() as conn:
        table = "community_posts" if target_type == "post" else "community_comments"
        target = conn.execute(
            f"SELECT id FROM {table} WHERE id = ? AND is_hidden = 0 AND moderation_status = 'visible'",
            (target_id,),
        ).fetchone()
        if not target:
            return False, "대상을 찾을 수 없습니다."
        existing = conn.execute(
            """
            SELECT id, is_active FROM community_reactions
            WHERE target_type = ? AND target_id = ? AND reaction_type = 'like'
              AND (session_hash = ? OR (ip_hash = ? AND user_agent_hash = ?))
            ORDER BY id DESC LIMIT 1
            """,
            (target_type, target_id, session_hash_value, ip_hash, user_agent_hash),
        ).fetchone()
        current_time = now_text()
        if existing and int(existing["is_active"] or 0) == 1:
            conn.execute("UPDATE community_reactions SET is_active = 0 WHERE id = ?", (existing["id"],))
            conn.execute(
                """
                INSERT INTO community_reaction_logs
                    (target_type, target_id, action, session_hash, ip_hash, user_agent_hash, created_at)
                VALUES (?, ?, 'unlike', ?, ?, ?, ?)
                """,
                (target_type, target_id, session_hash_value, ip_hash, user_agent_hash, current_time),
            )
            conn.execute(f"UPDATE {table} SET like_count = MAX(like_count - 1, 0) WHERE id = ?", (target_id,))
            return True, "좋아요를 취소했습니다."
        if existing:
            conn.execute(
                "UPDATE community_reactions SET is_active = 1, created_at = ?, user_agent_hash = ? WHERE id = ?",
                (current_time, user_agent_hash, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO community_reactions
                    (target_type, target_id, reaction_type, session_hash, ip_hash, user_agent_hash, is_active, created_at)
                VALUES (?, ?, 'like', ?, ?, ?, 1, ?)
                """,
                (target_type, target_id, session_hash_value, ip_hash, user_agent_hash, current_time),
            )
        conn.execute(
            """
            INSERT INTO community_reaction_logs
                (target_type, target_id, action, session_hash, ip_hash, user_agent_hash, created_at)
            VALUES (?, ?, 'like', ?, ?, ?, ?)
            """,
            (target_type, target_id, session_hash_value, ip_hash, user_agent_hash, current_time),
        )
        conn.execute(f"UPDATE {table} SET like_count = like_count + 1 WHERE id = ?", (target_id,))
    return True, "좋아요를 눌렀습니다."


def report(target_type: str, target_id: int, reason: str, detail: str, ip_hash: str, user_agent_hash: str, session_hash_value: str) -> Tuple[bool, str]:
    ensure_community_tables()
    valid_reasons = {item[0] for item in REPORT_REASONS}
    if target_type not in {"post", "comment"}:
        return False, "잘못된 대상입니다."
    if reason not in valid_reasons:
        return False, "신고 사유를 선택하세요."
    if is_banned(ip_hash, session_hash_value):
        return False, "현재 신고 기능이 제한된 상태입니다."
    report_threshold = int_setting("report_threshold", REPORT_THRESHOLD_DEFAULT)
    with connect() as conn:
        existing = conn.execute(
            """
            SELECT id FROM community_reports
            WHERE target_type = ? AND target_id = ? AND status = 'open'
              AND (reporter_session_hash = ? OR (reporter_ip_hash = ? AND reporter_user_agent_hash = ?))
            """,
            (target_type, target_id, session_hash_value, ip_hash, user_agent_hash),
        ).fetchone()
        if existing:
            return False, "이미 신고가 접수되었습니다."
        conn.execute(
            """
            INSERT INTO community_reports
                (target_type, target_id, reason, detail, reporter_session_hash,
                 reporter_ip_hash, reporter_user_agent_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (target_type, target_id, reason, detail.strip()[:500], session_hash_value, ip_hash, user_agent_hash, now_text()),
        )
        table = "community_posts" if target_type == "post" else "community_comments"
        conn.execute(f"UPDATE {table} SET report_count = report_count + 1 WHERE id = ?", (target_id,))
        report_count = conn.execute(f"SELECT report_count FROM {table} WHERE id = ?", (target_id,)).fetchone()
        if report_count and int(report_count["report_count"]) >= report_threshold:
            conn.execute(
                f"""
                UPDATE {table}
                SET is_hidden = 1, moderation_status = 'pending_review', hidden_reason = '신고 누적 검토 대기'
                WHERE id = ?
                """,
                (target_id,),
            )
    return True, "신고가 접수되었습니다."


def admin_dashboard_data() -> Dict[str, Any]:
    ensure_community_tables()
    with connect() as conn:
        stats = {
            "post_count": conn.execute("SELECT COUNT(*) AS c FROM community_posts").fetchone()["c"],
            "hidden_post_count": conn.execute("SELECT COUNT(*) AS c FROM community_posts WHERE is_hidden = 1 OR moderation_status != 'visible'").fetchone()["c"],
            "comment_count": conn.execute("SELECT COUNT(*) AS c FROM community_comments").fetchone()["c"],
            "open_report_count": conn.execute("SELECT COUNT(*) AS c FROM community_reports WHERE status = 'open'").fetchone()["c"],
            "ai_flag_count": conn.execute("SELECT COUNT(*) AS c FROM community_moderation_logs WHERE final_flag = 1").fetchone()["c"],
        }
        pending_posts = conn.execute(
            """
            SELECT p.*, b.name AS board_name, b.slug AS board_slug
            FROM community_posts p JOIN community_boards b ON b.id = p.board_id
            WHERE p.is_hidden = 1 OR p.moderation_status != 'visible'
            ORDER BY p.created_at DESC LIMIT 8
            """
        ).fetchall()
        pending_comments = conn.execute(
            """
            SELECT c.*, p.title AS post_title, p.id AS post_id
            FROM community_comments c JOIN community_posts p ON p.id = c.post_id
            WHERE c.moderation_status IN ('pending_review', 'auto_hidden')
               OR c.moderation_score > 0
            ORDER BY c.created_at DESC LIMIT 8
            """
        ).fetchall()
        board_counts = conn.execute(
            """
            SELECT b.name, b.slug, COUNT(p.id) AS post_count
            FROM community_boards b
            LEFT JOIN community_posts p ON p.board_id = b.id
            GROUP BY b.id
            ORDER BY b.sort_order ASC
            """
        ).fetchall()
    return {
        "stats": stats,
        "recent_reports": admin_reports("open")[:8],
        "pending_posts": [decorate_post(row) for row in pending_posts],
        "pending_comments": [decorate_comment(row) for row in pending_comments],
        "board_counts": [dict(row) for row in board_counts],
        "settings": admin_settings(),
    }


def admin_settings() -> Dict[str, str]:
    ensure_community_tables()
    with connect() as conn:
        rows = conn.execute("SELECT key, value FROM community_settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def admin_posts(status: str = "") -> List[Dict[str, Any]]:
    ensure_community_tables()
    where = []
    if status == "hidden":
        where.append("(p.is_hidden = 1 OR p.moderation_status != 'visible')")
    sql_where = f"WHERE {' AND '.join(where)}" if where else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*, b.name AS board_name, b.slug AS board_slug
            FROM community_posts p JOIN community_boards b ON b.id = p.board_id
            {sql_where}
            ORDER BY p.created_at DESC LIMIT 100
            """
        ).fetchall()
    return [decorate_post(row) for row in rows]


def admin_comments(status: str = "") -> List[Dict[str, Any]]:
    ensure_community_tables()
    where = []
    if status == "hidden":
        where.append("(c.is_hidden = 1 OR c.moderation_status != 'visible')")
    sql_where = f"WHERE {' AND '.join(where)}" if where else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT c.*, p.title AS post_title, p.id AS post_id
            FROM community_comments c JOIN community_posts p ON p.id = c.post_id
            {sql_where}
            ORDER BY c.created_at DESC LIMIT 100
            """
        ).fetchall()
    return [decorate_comment(row) for row in rows]


def admin_reports(status: str = "open") -> List[Dict[str, Any]]:
    ensure_community_tables()
    params: List[Any] = []
    where = ""
    if status:
        where = "WHERE status = ?"
        params.append(status)
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM community_reports {where} ORDER BY created_at DESC LIMIT 100",
            params,
        ).fetchall()
        reports = []
        for row in rows:
            report_item = dict(row)
            report_item["status_label"] = STATUS_LABELS.get(report_item.get("status", ""), report_item.get("status", ""))
            report_item["reason_label"] = dict(REPORT_REASONS).get(report_item.get("reason", ""), report_item.get("reason", ""))
            report_item["target_type_label"] = TARGET_TYPE_LABELS.get(report_item.get("target_type", ""), report_item.get("target_type", ""))
            report_item["created_display"] = format_date(report_item.get("created_at", ""))
            if report_item["target_type"] == "post":
                target = conn.execute(
                    """
                    SELECT p.id, p.title, p.content, p.moderation_status, p.is_hidden, b.name AS board_name
                    FROM community_posts p JOIN community_boards b ON b.id = p.board_id
                    WHERE p.id = ?
                    """,
                    (report_item["target_id"],),
                ).fetchone()
                if target:
                    report_item.update(
                        {
                            "target_title": target["title"],
                            "target_snippet": target["content"][:140],
                            "target_status_label": STATUS_LABELS.get(target["moderation_status"], target["moderation_status"]),
                            "target_url": f"/community/posts/{target['id']}",
                            "board_name": target["board_name"],
                        }
                    )
            else:
                target = conn.execute(
                    """
                    SELECT c.id, c.content, c.moderation_status, c.is_hidden,
                           p.id AS post_id, p.title AS post_title, b.name AS board_name
                    FROM community_comments c
                    JOIN community_posts p ON p.id = c.post_id
                    JOIN community_boards b ON b.id = p.board_id
                    WHERE c.id = ?
                    """,
                    (report_item["target_id"],),
                ).fetchone()
                if target:
                    report_item.update(
                        {
                            "target_title": target["post_title"],
                            "target_snippet": target["content"][:140],
                            "target_status_label": STATUS_LABELS.get(target["moderation_status"], target["moderation_status"]),
                            "target_url": f"/community/posts/{target['post_id']}#comment-{target['id']}",
                            "board_name": target["board_name"],
                        }
                    )
            reports.append(report_item)
    return reports


def admin_review_items() -> Dict[str, List[Dict[str, Any]]]:
    ensure_community_tables()
    with connect() as conn:
        posts = conn.execute(
            """
            SELECT p.*, b.name AS board_name, b.slug AS board_slug,
                   (SELECT l.rule_flag FROM community_moderation_logs l
                    WHERE l.target_type = 'post' AND l.target_id = p.id
                    ORDER BY l.created_at DESC LIMIT 1) AS rule_flag,
                   (SELECT l.ai_flag FROM community_moderation_logs l
                    WHERE l.target_type = 'post' AND l.target_id = p.id
                    ORDER BY l.created_at DESC LIMIT 1) AS ai_flag,
                   (SELECT l.final_flag FROM community_moderation_logs l
                    WHERE l.target_type = 'post' AND l.target_id = p.id
                    ORDER BY l.created_at DESC LIMIT 1) AS final_flag,
                   (SELECT l.final_action FROM community_moderation_logs l
                    WHERE l.target_type = 'post' AND l.target_id = p.id
                    ORDER BY l.created_at DESC LIMIT 1) AS final_action,
                   (SELECT l.reason FROM community_moderation_logs l
                    WHERE l.target_type = 'post' AND l.target_id = p.id
                    ORDER BY l.created_at DESC LIMIT 1) AS moderation_reason
            FROM community_posts p JOIN community_boards b ON b.id = p.board_id
            WHERE p.moderation_status IN ('pending_review', 'auto_hidden', 'admin_hidden')
               OR p.moderation_score > 0
               OR EXISTS (
                    SELECT 1 FROM community_moderation_logs l
                    WHERE l.target_type = 'post' AND l.target_id = p.id
                      AND (l.rule_flag = 1 OR l.ai_flag = 1 OR l.final_flag = 1)
               )
            ORDER BY p.updated_at DESC, p.created_at DESC
            LIMIT 100
            """
        ).fetchall()
        comments = conn.execute(
            """
            SELECT c.*, p.title AS post_title, p.id AS post_id, b.name AS board_name,
                   (SELECT l.rule_flag FROM community_moderation_logs l
                    WHERE l.target_type = 'comment' AND l.target_id = c.id
                    ORDER BY l.created_at DESC LIMIT 1) AS rule_flag,
                   (SELECT l.ai_flag FROM community_moderation_logs l
                    WHERE l.target_type = 'comment' AND l.target_id = c.id
                    ORDER BY l.created_at DESC LIMIT 1) AS ai_flag,
                   (SELECT l.final_flag FROM community_moderation_logs l
                    WHERE l.target_type = 'comment' AND l.target_id = c.id
                    ORDER BY l.created_at DESC LIMIT 1) AS final_flag,
                   (SELECT l.final_action FROM community_moderation_logs l
                    WHERE l.target_type = 'comment' AND l.target_id = c.id
                    ORDER BY l.created_at DESC LIMIT 1) AS final_action,
                   (SELECT l.reason FROM community_moderation_logs l
                    WHERE l.target_type = 'comment' AND l.target_id = c.id
                    ORDER BY l.created_at DESC LIMIT 1) AS moderation_reason
            FROM community_comments c
            JOIN community_posts p ON p.id = c.post_id
            JOIN community_boards b ON b.id = p.board_id
            WHERE c.moderation_status IN ('pending_review', 'auto_hidden', 'admin_hidden')
               OR c.moderation_score > 0
               OR EXISTS (
                    SELECT 1 FROM community_moderation_logs l
                    WHERE l.target_type = 'comment' AND l.target_id = c.id
                      AND (l.rule_flag = 1 OR l.ai_flag = 1 OR l.final_flag = 1)
               )
            ORDER BY c.updated_at DESC, c.created_at DESC
            LIMIT 100
            """
        ).fetchall()
    return {"review_posts": [decorate_post(row) for row in posts], "review_comments": [decorate_comment(row) for row in comments]}


def admin_moderation_logs() -> List[Dict[str, Any]]:
    ensure_community_tables()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM community_moderation_logs ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
    logs = []
    for row in rows:
        item = dict(row)
        item["target_type_label"] = TARGET_TYPE_LABELS.get(item.get("target_type", ""), item.get("target_type", ""))
        item["final_action_label"] = STATUS_LABELS.get(item.get("final_action", ""), item.get("final_action", ""))
        item["reason_label"] = label_moderation_reasons(item.get("reason", ""))
        item["created_display"] = format_date(item.get("created_at", ""))
        logs.append(item)
    return logs


def admin_bans() -> List[Dict[str, Any]]:
    ensure_community_tables()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM community_bans ORDER BY created_at DESC LIMIT 100").fetchall()
    return [dict(row) for row in rows]


def refresh_comment_count(conn: sqlite3.Connection, post_id: int) -> None:
    visible_count = conn.execute(
        """
        SELECT COUNT(*) AS c FROM community_comments
        WHERE post_id = ? AND is_hidden = 0 AND moderation_status = 'visible'
        """,
        (post_id,),
    ).fetchone()["c"]
    conn.execute("UPDATE community_posts SET comment_count = ? WHERE id = ?", (visible_count, post_id))


def set_post_hidden(post_id: int, hidden: bool, reason: str = "") -> None:
    ensure_community_tables()
    with connect() as conn:
        current = conn.execute("SELECT moderation_status FROM community_posts WHERE id = ?", (post_id,)).fetchone()
        if current and not hidden and current["moderation_status"] in {"deleted_by_user", "deleted_by_admin"}:
            return
        conn.execute(
            """
            UPDATE community_posts
            SET is_hidden = ?, hidden_reason = ?, moderation_status = ?
            WHERE id = ?
            """,
            (1 if hidden else 0, reason if hidden else "", "admin_hidden" if hidden else "visible", post_id),
        )


def set_comment_hidden(comment_id: int, hidden: bool, reason: str = "") -> None:
    ensure_community_tables()
    with connect() as conn:
        row = conn.execute("SELECT post_id, moderation_status FROM community_comments WHERE id = ?", (comment_id,)).fetchone()
        if row and not hidden and row["moderation_status"] in {"deleted_by_user", "deleted_by_admin"}:
            return
        conn.execute(
            """
            UPDATE community_comments
            SET is_hidden = ?, hidden_reason = ?, moderation_status = ?
            WHERE id = ?
            """,
            (1 if hidden else 0, reason if hidden else "", "admin_hidden" if hidden else "visible", comment_id),
        )
        if row:
            refresh_comment_count(conn, row["post_id"])


def soft_delete_post(post_id: int, status: str = "deleted_by_admin") -> None:
    ensure_community_tables()
    if status not in {"deleted_by_user", "deleted_by_admin"}:
        status = "deleted_by_admin"
    with connect() as conn:
        conn.execute(
            """
            UPDATE community_posts
            SET is_hidden = 1, moderation_status = ?, hidden_reason = ?, deleted_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, STATUS_LABELS[status], now_text(), now_text(), post_id),
        )


def soft_delete_comment(comment_id: int, status: str = "deleted_by_admin") -> None:
    ensure_community_tables()
    if status not in {"deleted_by_user", "deleted_by_admin"}:
        status = "deleted_by_admin"
    with connect() as conn:
        row = conn.execute("SELECT post_id FROM community_comments WHERE id = ?", (comment_id,)).fetchone()
        conn.execute(
            """
            UPDATE community_comments
            SET is_hidden = 1, moderation_status = ?, hidden_reason = ?, deleted_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, STATUS_LABELS[status], now_text(), now_text(), comment_id),
        )
        if row:
            refresh_comment_count(conn, row["post_id"])


def delete_post(post_id: int) -> None:
    soft_delete_post(post_id, "deleted_by_admin")


def delete_comment(comment_id: int) -> None:
    soft_delete_comment(comment_id, "deleted_by_admin")


def handle_report(report_id: int, status: str, note: str = "") -> None:
    ensure_community_tables()
    if status not in {"resolved", "dismissed"}:
        return
    with connect() as conn:
        conn.execute(
            "UPDATE community_reports SET status = ?, handled_at = ?, handler_note = ? WHERE id = ?",
            (status, now_text(), note.strip()[:500], report_id),
        )


def act_on_report_target(report_id: int, action: str) -> None:
    ensure_community_tables()
    with connect() as conn:
        row = conn.execute("SELECT target_type, target_id FROM community_reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        return
    if row["target_type"] == "post":
        if action == "hide":
            set_post_hidden(row["target_id"], True, "신고 검토 후 숨김")
        elif action == "restore":
            set_post_hidden(row["target_id"], False)
        elif action == "delete":
            soft_delete_post(row["target_id"], "deleted_by_admin")
    elif row["target_type"] == "comment":
        if action == "hide":
            set_comment_hidden(row["target_id"], True, "신고 검토 후 숨김")
        elif action == "restore":
            set_comment_hidden(row["target_id"], False)
        elif action == "delete":
            soft_delete_comment(row["target_id"], "deleted_by_admin")


def add_ban(ban_type: str, ban_value: str, reason: str = "") -> None:
    ensure_community_tables()
    if ban_type not in {"ip_hash", "session_hash"} or not ban_value.strip():
        return
    with connect() as conn:
        conn.execute(
            "INSERT INTO community_bans (ban_type, ban_value, reason, created_at) VALUES (?, ?, ?, ?)",
            (ban_type, ban_value.strip(), reason.strip()[:300], now_text()),
        )


def admin_activity(subject_type: str = "", subject_value: str = "") -> Dict[str, Any]:
    ensure_community_tables()
    subject_type = subject_type if subject_type in {"ip_hash", "session_hash"} else ""
    subject_value = subject_value.strip()
    data: Dict[str, Any] = {
        "subject_type": subject_type,
        "subject_value": subject_value,
        "posts": [],
        "comments": [],
        "reports_made": [],
        "reports_received": [],
        "reactions": [],
        "notes": [],
    }
    if not subject_type or not subject_value:
        return data
    post_where = "p.ip_hash = ?" if subject_type == "ip_hash" else "p.session_hash = ?"
    comment_where = "c.ip_hash = ?" if subject_type == "ip_hash" else "c.session_hash = ?"
    report_where = "r.reporter_ip_hash = ?" if subject_type == "ip_hash" else "r.reporter_session_hash = ?"
    reaction_where = "rl.ip_hash = ?" if subject_type == "ip_hash" else "rl.session_hash = ?"
    with connect() as conn:
        data["posts"] = [
            decorate_post(row)
            for row in conn.execute(
                f"""
                SELECT p.*, b.name AS board_name, b.slug AS board_slug
                FROM community_posts p JOIN community_boards b ON b.id = p.board_id
                WHERE {post_where}
                ORDER BY p.created_at DESC LIMIT 100
                """,
                (subject_value,),
            ).fetchall()
        ]
        data["comments"] = [
            decorate_comment(row)
            for row in conn.execute(
                f"""
                SELECT c.*, p.title AS post_title, p.id AS post_id
                FROM community_comments c JOIN community_posts p ON p.id = c.post_id
                WHERE {comment_where}
                ORDER BY c.created_at DESC LIMIT 100
                """,
                (subject_value,),
            ).fetchall()
        ]
        data["reports_made"] = admin_reports_for_subject(conn, report_where, subject_value)
        data["reports_received"] = reports_received_for_subject(conn, subject_type, subject_value)
        data["reactions"] = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT rl.*, p.title AS post_title, c.content AS comment_content
                FROM community_reaction_logs rl
                LEFT JOIN community_posts p ON rl.target_type = 'post' AND p.id = rl.target_id
                LEFT JOIN community_comments c ON rl.target_type = 'comment' AND c.id = rl.target_id
                WHERE {reaction_where}
                ORDER BY rl.created_at DESC LIMIT 100
                """,
                (subject_value,),
            ).fetchall()
        ]
        for item in data["reactions"]:
            item["action_label"] = STATUS_LABELS.get(item.get("action", ""), item.get("action", ""))
            item["target_type_label"] = TARGET_TYPE_LABELS.get(item.get("target_type", ""), item.get("target_type", ""))
            item["created_display"] = format_date(item.get("created_at", ""))
        data["notes"] = [
            dict(row)
            for row in conn.execute(
                """
                SELECT * FROM community_activity_notes
                WHERE subject_type = ? AND subject_value = ?
                ORDER BY created_at DESC
                """,
                (subject_type, subject_value),
            ).fetchall()
        ]
    return data


def admin_revisions() -> Dict[str, List[Dict[str, Any]]]:
    ensure_community_tables()
    with connect() as conn:
        post_rows = conn.execute(
            """
            SELECT r.*, p.title AS current_title
            FROM community_post_revisions r
            LEFT JOIN community_posts p ON p.id = r.post_id
            ORDER BY r.created_at DESC LIMIT 100
            """
        ).fetchall()
        comment_rows = conn.execute(
            """
            SELECT r.*, c.post_id, p.title AS post_title
            FROM community_comment_revisions r
            LEFT JOIN community_comments c ON c.id = r.comment_id
            LEFT JOIN community_posts p ON p.id = c.post_id
            ORDER BY r.created_at DESC LIMIT 100
            """
        ).fetchall()
    posts = [dict(row) for row in post_rows]
    comments = [dict(row) for row in comment_rows]
    for item in posts + comments:
        item["created_display"] = format_date(item.get("created_at", ""))
    return {"post_revisions": posts, "comment_revisions": comments}


def admin_reports_for_subject(conn: sqlite3.Connection, where_clause: str, subject_value: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        f"SELECT * FROM community_reports r WHERE {where_clause} ORDER BY created_at DESC LIMIT 100",
        (subject_value,),
    ).fetchall()
    reports = []
    for row in rows:
        item = dict(row)
        item["status_label"] = STATUS_LABELS.get(item.get("status", ""), item.get("status", ""))
        item["reason_label"] = dict(REPORT_REASONS).get(item.get("reason", ""), item.get("reason", ""))
        item["target_type_label"] = TARGET_TYPE_LABELS.get(item.get("target_type", ""), item.get("target_type", ""))
        item["created_display"] = format_date(item.get("created_at", ""))
        reports.append(item)
    return reports


def reports_received_for_subject(conn: sqlite3.Connection, subject_type: str, subject_value: str) -> List[Dict[str, Any]]:
    if subject_type != "ip_hash":
        return []
    rows = conn.execute(
        """
        SELECT r.*
        FROM community_reports r
        LEFT JOIN community_posts p ON r.target_type = 'post' AND p.id = r.target_id
        LEFT JOIN community_comments c ON r.target_type = 'comment' AND c.id = r.target_id
        WHERE p.ip_hash = ? OR c.ip_hash = ?
        ORDER BY r.created_at DESC LIMIT 100
        """,
        (subject_value, subject_value),
    ).fetchall()
    reports = []
    for row in rows:
        item = dict(row)
        item["status_label"] = STATUS_LABELS.get(item.get("status", ""), item.get("status", ""))
        item["reason_label"] = dict(REPORT_REASONS).get(item.get("reason", ""), item.get("reason", ""))
        item["target_type_label"] = TARGET_TYPE_LABELS.get(item.get("target_type", ""), item.get("target_type", ""))
        item["created_display"] = format_date(item.get("created_at", ""))
        reports.append(item)
    return reports


def add_activity_note(subject_type: str, subject_value: str, note: str) -> None:
    ensure_community_tables()
    if subject_type not in {"ip_hash", "session_hash"} or not subject_value.strip() or not note.strip():
        return
    current_time = now_text()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO community_activity_notes
                (subject_type, subject_value, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (subject_type, subject_value.strip(), note.strip()[:1000], current_time, current_time),
        )
