import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
CONFIG_FILE = BASE_DIR / "config" / "backup_config.json"


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def cleanup_backup_files(target_dir: Path, keep_latest: int):
    if not target_dir.exists():
        print(f"not found: {target_dir}")
        return

    backups = sorted(
        target_dir.glob("backup_*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    old_files = backups[keep_latest:]

    for file in old_files:
        file.unlink()
        print(f"deleted: {file.name}")

    print(f"done. kept latest {keep_latest} files.")


def main():
    config = load_config()

    keep_latest = int(config.get("keep_latest", 5))
    backup_dir = resolve_path(config.get("backup_dir", "03_backup_to_nas/backups"))

    cleanup_backup_files(backup_dir, keep_latest)


if __name__ == "__main__":
    main()
