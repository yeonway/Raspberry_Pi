import hashlib
import hmac
import html
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.security import get_session_secret


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_DIR / "dashboard.db"
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 20
COMMENT_RATE_LIMIT_SECONDS = 45

CATEGORY_OPTIONS = [
    {"value": "notice", "label": "공지"},
    {"value": "server", "label": "서버"},
    {"value": "update", "label": "업데이트"},
    {"value": "event", "label": "이벤트"},
    {"value": "devlog", "label": "작업일지"},
    {"value": "incident", "label": "장애안내"},
]
CATEGORY_LABELS = {item["value"]: item["label"] for item in CATEGORY_OPTIONS}
CATEGORY_LABELS.update(
    {
        "general": "일반",
        "maintenance": "점검",
    }
)

_INITIALIZED = False


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today_label() -> str:
    return datetime.now().strftime("%Y.%m.%d")


def news_db_path() -> Path:
    explicit = os.getenv("NEWS_DB_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser()

    coordinate_path = os.getenv("COORDINATE_DB_PATH", "").strip()
    if coordinate_path:
        path = Path(coordinate_path).expanduser()
        if path.exists() or path.parent.exists():
            return path

    if DEFAULT_DB_PATH.exists():
        return DEFAULT_DB_PATH

    production_default = Path("/home/user/server/dashboard/dashboard.db")
    if production_default.exists() or production_default.parent.exists():
        return production_default

    return DEFAULT_DB_PATH


def connect() -> sqlite3.Connection:
    path = news_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_news_tables() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS news_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                summary_bullets TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                cover_image_url TEXT,
                cover_image_caption TEXT NOT NULL DEFAULT '',
                tags TEXT,
                author_name TEXT NOT NULL DEFAULT 'DCOUT News',
                source_label TEXT NOT NULL DEFAULT 'DCOUT News',
                is_public INTEGER NOT NULL DEFAULT 0,
                is_pinned INTEGER NOT NULL DEFAULT 0,
                view_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_news_posts_slug
                ON news_posts(slug);
            CREATE INDEX IF NOT EXISTS idx_news_posts_public_pinned_created
                ON news_posts(is_public, is_pinned, created_at);
            CREATE INDEX IF NOT EXISTS idx_news_posts_category
                ON news_posts(category);

            CREATE TABLE IF NOT EXISTS news_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                content TEXT NOT NULL,
                is_hidden INTEGER NOT NULL DEFAULT 0,
                ip_hash TEXT,
                user_agent_hash TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(post_id) REFERENCES news_posts(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_news_comments_post_id
                ON news_comments(post_id);
            CREATE INDEX IF NOT EXISTS idx_news_comments_created_at
                ON news_comments(created_at);
            CREATE INDEX IF NOT EXISTS idx_news_comments_hidden
                ON news_comments(is_hidden);
            """
        )
        _ensure_column(conn, "news_posts", "summary_bullets", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "news_posts", "cover_image_caption", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "news_posts", "author_name", "TEXT NOT NULL DEFAULT 'DCOUT News'")
        _ensure_column(conn, "news_posts", "source_label", "TEXT NOT NULL DEFAULT 'DCOUT News'")

    _INITIALIZED = True


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def format_datetime(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%Y.%m.%d %H:%M")
    except ValueError:
        return value


def format_date(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%Y.%m.%d")
    except ValueError:
        return value


def category_label(value: Optional[str]) -> str:
    value = (value or "general").strip()
    return CATEGORY_LABELS.get(value, value)


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:80].strip("-") or "news"


def normalize_slug(value: str, fallback_title: str) -> str:
    candidate = value.strip().lower()
    if not candidate:
        return slugify(fallback_title)
    candidate = re.sub(r"\s+", "-", candidate)
    candidate = re.sub(r"[^a-z0-9-]", "", candidate)
    candidate = re.sub(r"-{2,}", "-", candidate).strip("-")
    return candidate[:80].strip("-") or slugify(fallback_title)


def make_unique_slug(conn: sqlite3.Connection, desired_slug: str, post_id: Optional[int] = None) -> str:
    base = desired_slug[:80].strip("-") or "news"
    slug = base
    suffix = 2
    while True:
        params: List[Any] = [slug]
        sql = "SELECT id FROM news_posts WHERE slug = ?"
        if post_id is not None:
            sql += " AND id != ?"
            params.append(post_id)
        row = conn.execute(sql, params).fetchone()
        if not row:
            return slug
        suffix_text = f"-{suffix}"
        slug = f"{base[:80 - len(suffix_text)]}{suffix_text}"
        suffix += 1


def text_excerpt(value: str, length: int = 170) -> str:
    cleaned = re.sub(r"```.*?```", " ", value, flags=re.DOTALL)
    cleaned = re.sub(r"[#>*_`~\[\]\(\)|]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= length:
        return cleaned
    return cleaned[: length - 1].rstrip() + "..."


def normalize_category(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    if not value:
        return "notice"
    value = value[:40]
    return value


def normalize_tags(value: str) -> str:
    tags: List[str] = []
    for raw_tag in value.split(","):
        tag = re.sub(r"\s+", " ", raw_tag.strip().lstrip("#"))
        if tag and tag not in tags:
            tags.append(tag[:30])
    return ", ".join(tags[:10])


def tag_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def bullet_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    bullets: List[str] = []
    for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        item = re.sub(r"^\s*[-*]\s*", "", line).strip()
        if item:
            bullets.append(item[:180])
    return bullets[:6]


def validate_cover_image_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("대표 이미지는 http 또는 https URL만 사용할 수 있습니다.")
    return value[:500]


def checkbox_value(form: Dict[str, str], name: str) -> int:
    return 1 if form.get(name, "").lower() in {"1", "true", "yes", "on"} else 0


def compact_text(value: str, max_length: int) -> str:
    return re.sub(r"\s+", " ", value.strip())[:max_length]


def build_post_data(
    form: Dict[str, str],
    existing: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    title = compact_text(form.get("title", ""), 140)
    content = form.get("content", "").strip()
    summary = compact_text(form.get("summary", ""), 400)
    summary_bullets = "\n".join(bullet_list(form.get("summary_bullets", "")))
    category = normalize_category(form.get("category", "notice"))
    tags = normalize_tags(form.get("tags", ""))
    author_name = compact_text(form.get("author_name", ""), 60) or "DCOUT News"
    source_label = compact_text(form.get("source_label", ""), 80) or "DCOUT News"
    cover_image_caption = compact_text(form.get("cover_image_caption", ""), 180)
    intent = form.get("intent", "save")

    errors: Dict[str, str] = {}
    if not title:
        errors["title"] = "제목을 입력하세요."
    if not content:
        errors["content"] = "본문을 입력하세요."
    if len(content) > 50000:
        errors["content"] = "본문은 50,000자 이내로 입력하세요."

    cover_image_url = ""
    try:
        cover_image_url = validate_cover_image_url(form.get("cover_image_url", ""))
    except ValueError as exc:
        errors["cover_image_url"] = str(exc)

    if not summary and content:
        summary = text_excerpt(content, 220)

    fallback_title = title or (existing or {}).get("title", "news")
    slug = normalize_slug(form.get("slug", ""), fallback_title)
    is_public = checkbox_value(form, "is_public")
    if intent == "publish":
        is_public = 1
    elif intent == "draft":
        is_public = 0

    data = {
        "title": title,
        "slug": slug,
        "summary": summary,
        "summary_bullets": summary_bullets,
        "content": content,
        "category": category,
        "cover_image_url": cover_image_url,
        "cover_image_caption": cover_image_caption,
        "tags": tags,
        "author_name": author_name,
        "source_label": source_label,
        "is_public": is_public,
        "is_pinned": checkbox_value(form, "is_pinned"),
    }
    return data, errors


def empty_post_form() -> Dict[str, Any]:
    return {
        "id": None,
        "title": "",
        "slug": "",
        "summary": "",
        "summary_bullets": "",
        "content": "",
        "category": "notice",
        "cover_image_url": "",
        "cover_image_caption": "",
        "tags": "",
        "author_name": "DCOUT News",
        "source_label": "DCOUT News",
        "is_public": 0,
        "is_pinned": 0,
        "published_at": "",
    }


def decorate_post(row: sqlite3.Row) -> Dict[str, Any]:
    post = dict(row)
    post.setdefault("comment_count", 0)
    post.setdefault("summary_bullets", "")
    post.setdefault("cover_image_caption", "")
    post.setdefault("author_name", "DCOUT News")
    post.setdefault("source_label", "DCOUT News")
    post["created_display"] = format_date(post.get("created_at"))
    post["created_datetime_display"] = format_datetime(post.get("created_at"))
    post["updated_display"] = format_datetime(post.get("updated_at"))
    post["published_display"] = format_datetime(post.get("published_at"))
    post["article_date_display"] = format_datetime(post.get("published_at") or post.get("created_at"))
    post["category_label"] = category_label(post.get("category"))
    post["tag_list"] = tag_list(post.get("tags"))
    post["summary_bullet_list"] = bullet_list(post.get("summary_bullets"))
    post["is_public"] = int(post.get("is_public") or 0)
    post["is_pinned"] = int(post.get("is_pinned") or 0)
    post["view_count"] = int(post.get("view_count") or 0)
    post["comment_count"] = int(post.get("comment_count") or 0)
    return post


def public_categories() -> List[Dict[str, Any]]:
    ensure_news_tables()
    with connect() as conn:
        count_rows = conn.execute(
            """
            SELECT category, COUNT(*) AS count
            FROM news_posts
            WHERE is_public = 1
            GROUP BY category
            """
        ).fetchall()
    counts = {row["category"]: int(row["count"]) for row in count_rows}
    categories = [
        {
            "category": item["value"],
            "label": item["label"],
            "count": counts.get(item["value"], 0),
        }
        for item in CATEGORY_OPTIONS
    ]
    for category, count in sorted(counts.items()):
        if category not in {item["category"] for item in categories}:
            categories.append({"category": category, "label": category_label(category), "count": count})
    return categories


def public_tags(limit: int = 18) -> List[Dict[str, Any]]:
    ensure_news_tables()
    counts: Dict[str, int] = {}
    with connect() as conn:
        rows = conn.execute("SELECT tags FROM news_posts WHERE is_public = 1 AND tags IS NOT NULL").fetchall()
    for row in rows:
        for tag in tag_list(row["tags"]):
            counts[tag] = counts.get(tag, 0) + 1
    return [
        {"tag": tag, "count": count}
        for tag, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))[:limit]
    ]


def list_public_posts(
    category: str = "",
    query: str = "",
    tag: str = "",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    ensure_news_tables()
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    query = query.strip()[:80]
    category = category.strip()[:40]
    tag = tag.strip().lstrip("#")[:30]

    where = ["is_public = 1"]
    params: List[Any] = []
    if category:
        where.append("category = ?")
        params.append(category)
    if tag:
        where.append("(',' || REPLACE(tags, ', ', ',') || ',') LIKE ?")
        params.append(f"%,{tag},%")
    if query:
        like = f"%{query}%"
        where.append("(title LIKE ? OR summary LIKE ? OR content LIKE ? OR tags LIKE ?)")
        params.extend([like, like, like, like])

    where_sql = " AND ".join(where)
    offset = (page - 1) * page_size
    with connect() as conn:
        total = int(conn.execute(f"SELECT COUNT(*) FROM news_posts WHERE {where_sql}", params).fetchone()[0])
        rows = conn.execute(
            f"""
            SELECT p.*,
                   (
                       SELECT COUNT(*)
                       FROM news_comments c
                       WHERE c.post_id = p.id AND c.is_hidden = 0
                   ) AS comment_count
            FROM news_posts p
            WHERE {where_sql}
            ORDER BY p.is_pinned DESC,
                     COALESCE(p.published_at, p.created_at) DESC,
                     p.id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "posts": [decorate_post(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def public_home_sidebar() -> Dict[str, List[Dict[str, Any]]]:
    ensure_news_tables()
    with connect() as conn:
        popular_rows = conn.execute(
            """
            SELECT p.*,
                   (
                       SELECT COUNT(*)
                       FROM news_comments c
                       WHERE c.post_id = p.id AND c.is_hidden = 0
                   ) AS comment_count
            FROM news_posts p
            WHERE p.is_public = 1
            ORDER BY p.view_count DESC, COALESCE(p.published_at, p.created_at) DESC
            LIMIT 5
            """
        ).fetchall()
        commented_rows = conn.execute(
            """
            SELECT p.*,
                   (
                       SELECT COUNT(*)
                       FROM news_comments c
                       WHERE c.post_id = p.id AND c.is_hidden = 0
                   ) AS comment_count
            FROM news_posts p
            WHERE p.is_public = 1
            ORDER BY comment_count DESC, COALESCE(p.published_at, p.created_at) DESC
            LIMIT 5
            """
        ).fetchall()
        recent_rows = conn.execute(
            """
            SELECT p.*,
                   (
                       SELECT COUNT(*)
                       FROM news_comments c
                       WHERE c.post_id = p.id AND c.is_hidden = 0
                   ) AS comment_count
            FROM news_posts p
            WHERE p.is_public = 1
            ORDER BY p.updated_at DESC, p.id DESC
            LIMIT 5
            """
        ).fetchall()
    return {
        "popular_posts": [decorate_post(row) for row in popular_rows],
        "commented_posts": [decorate_post(row) for row in commented_rows],
        "recent_posts": [decorate_post(row) for row in recent_rows],
    }


def get_public_post(slug: str, increment_view: bool = False) -> Optional[Dict[str, Any]]:
    ensure_news_tables()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT p.*,
                   (
                       SELECT COUNT(*)
                       FROM news_comments c
                       WHERE c.post_id = p.id AND c.is_hidden = 0
                   ) AS comment_count
            FROM news_posts p
            WHERE p.slug = ? AND p.is_public = 1
            """,
            (slug,),
        ).fetchone()
        if not row:
            return None
        if increment_view:
            conn.execute("UPDATE news_posts SET view_count = view_count + 1 WHERE id = ?", (row["id"],))
            row = conn.execute(
                """
                SELECT p.*,
                       (
                           SELECT COUNT(*)
                           FROM news_comments c
                           WHERE c.post_id = p.id AND c.is_hidden = 0
                       ) AS comment_count
                FROM news_posts p
                WHERE p.id = ?
                """,
                (row["id"],),
            ).fetchone()

    post = decorate_post(row)
    post["content_html"] = render_markdown(post["content"])
    return post


def get_public_comments(post_id: int) -> List[Dict[str, Any]]:
    ensure_news_tables()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, author_name, content, created_at
            FROM news_comments
            WHERE post_id = ? AND is_hidden = 0
            ORDER BY created_at ASC, id ASC
            """,
            (post_id,),
        ).fetchall()
    comments = [dict(row) for row in rows]
    for comment in comments:
        comment["created_display"] = format_datetime(comment.get("created_at"))
    return comments


def get_adjacent_public_posts(post_id: int) -> Dict[str, Optional[Dict[str, Any]]]:
    ensure_news_tables()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT p.*,
                   (
                       SELECT COUNT(*)
                       FROM news_comments c
                       WHERE c.post_id = p.id AND c.is_hidden = 0
                   ) AS comment_count
            FROM news_posts p
            WHERE p.is_public = 1
            ORDER BY COALESCE(p.published_at, p.created_at) DESC, p.id DESC
            """
        ).fetchall()

    posts = [decorate_post(row) for row in rows]
    index = next((i for i, item in enumerate(posts) if int(item["id"]) == int(post_id)), -1)
    if index == -1:
        return {"previous": None, "next": None}
    return {
        "previous": posts[index - 1] if index > 0 else None,
        "next": posts[index + 1] if index + 1 < len(posts) else None,
    }


def related_public_posts(post_id: int, category: str, limit: int = 3) -> List[Dict[str, Any]]:
    ensure_news_tables()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT p.*,
                   (
                       SELECT COUNT(*)
                       FROM news_comments c
                       WHERE c.post_id = p.id AND c.is_hidden = 0
                   ) AS comment_count
            FROM news_posts p
            WHERE p.is_public = 1 AND p.id != ? AND p.category = ?
            ORDER BY COALESCE(p.published_at, p.created_at) DESC, p.id DESC
            LIMIT ?
            """,
            (post_id, category, limit),
        ).fetchall()
    return [decorate_post(row) for row in rows]


def hash_request_value(value: str) -> str:
    secret = os.getenv("NEWS_SESSION_SECRET", "").strip() or get_session_secret()
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def client_identity(headers: Dict[str, str], client_host: str) -> Tuple[str, str]:
    forwarded_for = headers.get("x-forwarded-for", "")
    ip_value = forwarded_for.split(",", 1)[0].strip() if forwarded_for else client_host
    user_agent = headers.get("user-agent", "")
    return hash_request_value(ip_value or "unknown"), hash_request_value(user_agent or "unknown")


def add_comment(
    slug: str,
    author_name: str,
    content: str,
    ip_hash: str,
    user_agent_hash: str,
) -> Tuple[bool, str]:
    ensure_news_tables()
    author_name = re.sub(r"\s+", " ", author_name.strip())
    content = content.strip()

    if not author_name:
        return False, "작성자명을 입력하세요."
    if not content:
        return False, "댓글 내용을 입력하세요."
    if len(author_name) > 20:
        return False, "작성자명은 20자 이내로 입력하세요."
    if len(content) > 500:
        return False, "댓글은 500자 이내로 입력하세요."

    threshold = (datetime.now() - timedelta(seconds=COMMENT_RATE_LIMIT_SECONDS)).isoformat(timespec="seconds")
    with connect() as conn:
        post = conn.execute(
            "SELECT id FROM news_posts WHERE slug = ? AND is_public = 1",
            (slug,),
        ).fetchone()
        if not post:
            return False, "댓글을 남길 수 없는 글입니다."

        recent = conn.execute(
            """
            SELECT id
            FROM news_comments
            WHERE ip_hash = ? AND created_at >= ?
            LIMIT 1
            """,
            (ip_hash, threshold),
        ).fetchone()
        if recent:
            return False, "잠시 후 다시 댓글을 작성하세요."

        conn.execute(
            """
            INSERT INTO news_comments (
                post_id, author_name, content, is_hidden,
                ip_hash, user_agent_hash, created_at
            )
            VALUES (?, ?, ?, 0, ?, ?, ?)
            """,
            (post["id"], author_name, content, ip_hash, user_agent_hash, now_text()),
        )

    return True, "댓글이 등록되었습니다."


def create_post(data: Dict[str, Any]) -> int:
    ensure_news_tables()
    created_at = now_text()
    published_at = created_at if int(data["is_public"]) else None
    with connect() as conn:
        slug = make_unique_slug(conn, data["slug"])
        cursor = conn.execute(
            """
            INSERT INTO news_posts (
                slug, title, summary, summary_bullets, content, category,
                cover_image_url, cover_image_caption, tags, author_name, source_label,
                is_public, is_pinned, view_count, created_at, updated_at, published_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                slug,
                data["title"],
                data["summary"],
                data["summary_bullets"],
                data["content"],
                data["category"],
                data["cover_image_url"],
                data["cover_image_caption"],
                data["tags"],
                data["author_name"],
                data["source_label"],
                int(data["is_public"]),
                int(data["is_pinned"]),
                created_at,
                created_at,
                published_at,
            ),
        )
        return int(cursor.lastrowid)


def get_admin_post(post_id: int) -> Optional[Dict[str, Any]]:
    ensure_news_tables()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT p.*,
                   (
                       SELECT COUNT(*)
                       FROM news_comments c
                       WHERE c.post_id = p.id
                   ) AS comment_count
            FROM news_posts p
            WHERE p.id = ?
            """,
            (post_id,),
        ).fetchone()
    if not row:
        return None
    return decorate_post(row)


def update_post(post_id: int, data: Dict[str, Any]) -> None:
    ensure_news_tables()
    updated_at = now_text()
    with connect() as conn:
        existing = conn.execute("SELECT id, published_at FROM news_posts WHERE id = ?", (post_id,)).fetchone()
        if not existing:
            raise ValueError("뉴스 글을 찾을 수 없습니다.")
        slug = make_unique_slug(conn, data["slug"], post_id=post_id)
        published_at = existing["published_at"]
        if int(data["is_public"]) and not published_at:
            published_at = updated_at
        conn.execute(
            """
            UPDATE news_posts
            SET slug = ?,
                title = ?,
                summary = ?,
                summary_bullets = ?,
                content = ?,
                category = ?,
                cover_image_url = ?,
                cover_image_caption = ?,
                tags = ?,
                author_name = ?,
                source_label = ?,
                is_public = ?,
                is_pinned = ?,
                updated_at = ?,
                published_at = ?
            WHERE id = ?
            """,
            (
                slug,
                data["title"],
                data["summary"],
                data["summary_bullets"],
                data["content"],
                data["category"],
                data["cover_image_url"],
                data["cover_image_caption"],
                data["tags"],
                data["author_name"],
                data["source_label"],
                int(data["is_public"]),
                int(data["is_pinned"]),
                updated_at,
                published_at,
                post_id,
            ),
        )


def delete_post(post_id: int) -> None:
    ensure_news_tables()
    with connect() as conn:
        conn.execute("DELETE FROM news_comments WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM news_posts WHERE id = ?", (post_id,))


def toggle_public(post_id: int) -> None:
    ensure_news_tables()
    updated_at = now_text()
    with connect() as conn:
        row = conn.execute("SELECT is_public, published_at FROM news_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise ValueError("뉴스 글을 찾을 수 없습니다.")
        next_public = 0 if int(row["is_public"]) else 1
        published_at = row["published_at"] or (updated_at if next_public else None)
        conn.execute(
            """
            UPDATE news_posts
            SET is_public = ?, published_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (next_public, published_at, updated_at, post_id),
        )


def toggle_pin(post_id: int) -> None:
    ensure_news_tables()
    with connect() as conn:
        conn.execute(
            """
            UPDATE news_posts
            SET is_pinned = CASE WHEN is_pinned = 1 THEN 0 ELSE 1 END,
                updated_at = ?
            WHERE id = ?
            """,
            (now_text(), post_id),
        )


def admin_dashboard_data() -> Dict[str, Any]:
    ensure_news_tables()
    recent_threshold = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
    with connect() as conn:
        stats_row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_posts,
                COALESCE(SUM(CASE WHEN is_public = 1 THEN 1 ELSE 0 END), 0) AS public_posts,
                COALESCE(SUM(CASE WHEN is_public = 0 THEN 1 ELSE 0 END), 0) AS private_posts
            FROM news_posts
            """
        ).fetchone()
        comment_count = int(conn.execute("SELECT COUNT(*) FROM news_comments").fetchone()[0])
        recent_comment_count = int(
            conn.execute("SELECT COUNT(*) FROM news_comments WHERE created_at >= ?", (recent_threshold,)).fetchone()[0]
        )
        post_rows = conn.execute(
            """
            SELECT p.*,
                   (
                       SELECT COUNT(*)
                       FROM news_comments c
                       WHERE c.post_id = p.id
                   ) AS comment_count
            FROM news_posts p
            ORDER BY p.is_pinned DESC, p.created_at DESC, p.id DESC
            """
        ).fetchall()
        comment_rows = conn.execute(
            """
            SELECT c.*, p.title AS post_title, p.slug AS post_slug
            FROM news_comments c
            JOIN news_posts p ON p.id = c.post_id
            ORDER BY c.created_at DESC, c.id DESC
            LIMIT 80
            """
        ).fetchall()

    comments = [dict(row) for row in comment_rows]
    for comment in comments:
        comment["created_display"] = format_datetime(comment.get("created_at"))
        comment["content_excerpt"] = text_excerpt(comment.get("content", ""), 100)

    return {
        "stats": {
            "total_posts": int(stats_row["total_posts"]),
            "public_posts": int(stats_row["public_posts"]),
            "private_posts": int(stats_row["private_posts"]),
            "comment_count": comment_count,
            "recent_comment_count": recent_comment_count,
        },
        "posts": [decorate_post(row) for row in post_rows],
        "comments": comments,
    }


def set_comment_hidden(comment_id: int, hidden: bool) -> None:
    ensure_news_tables()
    with connect() as conn:
        conn.execute(
            "UPDATE news_comments SET is_hidden = ? WHERE id = ?",
            (1 if hidden else 0, comment_id),
        )


def delete_comment(comment_id: int) -> None:
    ensure_news_tables()
    with connect() as conn:
        conn.execute("DELETE FROM news_comments WHERE id = ?", (comment_id,))


def inline_format(text: str) -> str:
    escaped = html.escape(text, quote=True)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def render_markdown(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    html_parts: List[str] = []
    in_code = False
    code_lines: List[str] = []
    list_type: Optional[str] = None
    in_table = False

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            html_parts.append(f"</{list_type}>")
            list_type = None

    def close_table() -> None:
        nonlocal in_table
        if in_table:
            html_parts.append("</tbody></table></div>")
            in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            close_table()
            if in_code:
                html_parts.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            close_list()
            close_table()
            continue

        if "|" in stripped and stripped.startswith("|") and stripped.endswith("|"):
            close_list()
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            if not in_table:
                html_parts.append('<div class="news-table-wrap"><table><tbody>')
                in_table = True
            cell_html = "".join(f"<td>{inline_format(cell)}</td>" for cell in cells)
            html_parts.append(f"<tr>{cell_html}</tr>")
            continue

        close_table()

        if stripped.startswith("### "):
            close_list()
            html_parts.append(f"<h3>{inline_format(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            close_list()
            html_parts.append(f"<h2>{inline_format(stripped[3:])}</h2>")
            continue
        if stripped.startswith("> "):
            close_list()
            html_parts.append(f"<blockquote><p>{inline_format(stripped[2:])}</p></blockquote>")
            continue

        unordered = re.match(r"^[-*]\s+(.+)$", stripped)
        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if unordered or ordered:
            wanted_type = "ul" if unordered else "ol"
            if list_type != wanted_type:
                close_list()
                html_parts.append(f"<{wanted_type}>")
                list_type = wanted_type
            item_text = (unordered or ordered).group(1)
            html_parts.append(f"<li>{inline_format(item_text)}</li>")
            continue

        close_list()
        html_parts.append(f"<p>{inline_format(stripped)}</p>")

    close_list()
    close_table()
    if in_code:
        html_parts.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(html_parts)
