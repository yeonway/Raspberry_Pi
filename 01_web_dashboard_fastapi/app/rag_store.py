import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.coordinate_sync import coordinate_db_path, coordinate_db_table, load_dashboard_coordinates


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_KNOWLEDGE_DIR = PROJECT_DIR / "ai_knowledge"
WORD_RE = re.compile(r"[0-9A-Za-z_\-\uac00-\ud7a3#]{2,}")


def rag_context_for(question: str) -> Dict[str, Any]:
    return {
        "knowledge_context": knowledge_context_for(question),
        "coordinate_context": saved_coordinate_context_for(question),
    }


def knowledge_context_for(question: str, limit: int = 5) -> str:
    items = _load_knowledge_items()
    if not items:
        return ""

    file_matches = _file_matches(question, items)
    if file_matches:
        return "\n\n".join(_format_file_context(item) for item in file_matches[:limit])

    tokens = _tokens(question)
    scored = _score_items(tokens, items)
    if not scored:
        return ""

    lines = []
    for item in scored[:limit]:
        title = item["title"]
        filename = item.get("filename", "")
        file_hint = f" ({filename})" if filename else ""
        content = _compact(item["content"], 700)
        lines.append(f"- {title}{file_hint}: {content}")
    return "\n".join(lines)


def saved_coordinate_context_for(question: str, limit: int = 10) -> str:
    path = coordinate_db_path()
    if path is None or not path.exists():
        return ""

    try:
        coordinates = load_dashboard_coordinates(path, coordinate_db_table(), 200)
    except Exception:
        return ""

    if not coordinates:
        return ""

    tokens = _tokens(question)
    rows = []
    for coordinate in coordinates:
        text = " ".join(
            [
                coordinate.name,
                coordinate.world,
                coordinate.note,
                coordinate.owner,
            ]
        ).lower()
        score = sum(1 for token in tokens if token in text)
        rows.append((coordinate, score))

    coordinate_question = any(
        word in question for word in ("\uc88c\ud45c", "\uc5b4\ub514", "\uc704\uce58", "\uac00\ub294", "\uae38", "\ucc3d\uace0", "\uc2a4\ud3f0")
    )
    matches = [item for item in rows if item[1] > 0]
    if not matches and coordinate_question:
        matches = rows[:limit]

    lines = []
    for coordinate, _ in sorted(matches, key=lambda item: item[1], reverse=True)[:limit]:
        y_text = "" if coordinate.y is None else f" y={coordinate.y:g}"
        note = f" ({coordinate.note})" if coordinate.note else ""
        lines.append(
            f"- {coordinate.name} [{coordinate.world}] x={coordinate.x:g}{y_text} z={coordinate.z:g}{note}"
        )
    return "\n".join(lines)


def _knowledge_dir() -> Path:
    return Path(os.getenv("AI_KNOWLEDGE_DIR", str(DEFAULT_KNOWLEDGE_DIR))).expanduser()


def _load_knowledge_items() -> List[Dict[str, str]]:
    directory = _knowledge_dir()
    if not directory.exists():
        return []

    items: List[Dict[str, str]] = []
    for path in sorted(_iter_knowledge_files(directory)):
        try:
            raw = path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError:
            raw = path.read_text(encoding="cp949", errors="replace").strip()
        if not raw:
            continue

        lines = [line.strip() for line in raw.splitlines()]
        title = path.stem
        if lines and lines[0].startswith("#"):
            title = lines[0].lstrip("#").strip() or title
            content = "\n".join(lines[1:]).strip()
        else:
            content = raw

        if content:
            items.append(
                {
                    "title": title,
                    "content": content,
                    "raw": raw,
                    "path": str(path),
                    "filename": path.name,
                    "stem": path.stem,
                }
            )
    return items


def _iter_knowledge_files(directory: Path) -> Iterable[Path]:
    for pattern in ("*.md", "*.txt"):
        yield from directory.glob(pattern)


def _score_items(tokens: List[str], items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    scored = []
    for item in items:
        text = f"{item.get('filename', '')} {item.get('stem', '')} {item['title']} {item['content']}".lower()
        score = sum(1 for token in tokens if token in text)
        if score > 0:
            scored.append((item, score))
    return [item for item, _ in sorted(scored, key=lambda row: row[1], reverse=True)]


def _file_matches(question: str, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    lowered = (question or "").lower()
    if not lowered:
        return []

    matches = []
    for item in items:
        filename = item.get("filename", "").lower()
        stem = item.get("stem", "").lower()
        if filename and filename in lowered:
            matches.append(item)
        elif stem and re.search(rf"(?<![0-9a-z_\-]){re.escape(stem)}(?![0-9a-z_\-])", lowered):
            matches.append(item)
    return matches


def _format_file_context(item: Dict[str, str]) -> str:
    max_chars = _file_context_max_chars()
    raw = item.get("raw") or item.get("content") or ""
    content = raw.strip()
    if len(content) > max_chars:
        content = content[:max_chars].rstrip() + "\n...(truncated)"
    return "\n".join(
        [
            f"FILE: {item.get('filename', '')}",
            f"TITLE: {item.get('title', '')}",
            "CONTENT:",
            content,
        ]
    )


def _file_context_max_chars() -> int:
    try:
        return max(500, min(int(os.getenv("AI_KNOWLEDGE_FILE_MAX_CHARS", "6000")), 20000))
    except ValueError:
        return 6000


def _tokens(value: str) -> List[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(value or "")]


def _compact(value: str, max_length: int) -> str:
    return re.sub(r"\s+", " ", value.strip())[:max_length]
