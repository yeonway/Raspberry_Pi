import re
import sys
from pathlib import Path


PATTERNS = [
    (re.compile(r"(NGROK_AUTHTOKEN\s*=\s*)(\S+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(DASHBOARD_PASSWORD\s*=\s*)(\S+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(DASHBOARD_PASSWORD_HASH\s*=\s*)(\S+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(SESSION_SECRET\s*=\s*)(\S+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(API[_-]?KEY\s*[:=]\s*)(\S+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(Authorization\s*:\s*Bearer\s+)(\S+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(password\s*[:=]\s*)(\S+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(token\s*[:=]\s*)(\S+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(secret\s*[:=]\s*)(\S+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(authtoken\s*[:=]\s*)(\S+)", re.I), r"\1[REDACTED]"),
]


def sanitize_text(text: str) -> str:
    for pattern, repl in PATTERNS:
        text = pattern.sub(repl, text)
    return text


def sanitize_file(path: Path):
    if not path.exists():
        print(f"not found: {path}")
        return

    text = path.read_text(encoding="utf-8", errors="replace")
    clean = sanitize_text(text)

    out_path = path.with_suffix(path.suffix + ".sanitized")
    out_path.write_text(clean, encoding="utf-8")

    print(f"created: {out_path}")


def main():
    if len(sys.argv) < 2:
        print("usage: python sanitize_logs.py <log_file1> [log_file2 ...]")
        return

    for item in sys.argv[1:]:
        sanitize_file(Path(item))


if __name__ == "__main__":
    main()
