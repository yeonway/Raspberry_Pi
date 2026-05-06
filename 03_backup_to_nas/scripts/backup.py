import fnmatch
import hashlib
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
CONFIG_FILE = BASE_DIR / "config" / "backup_config.json"
LOG_FILE = BASE_DIR / "logs" / "backup.log"


def write_log(message: str, level: str = "INFO"):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [{level}] {message}"

    print(line)

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"config not found: {CONFIG_FILE}")

    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def should_exclude(path: Path, exclude_dirs, exclude_files):
    parts = set(path.parts)

    for exclude_dir in exclude_dirs:
        if exclude_dir in parts:
            return True

    for pattern in exclude_files:
        if fnmatch.fnmatch(path.name, pattern):
            return True

    return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def cleanup_backup_files(target_dir: Path, keep_latest: int):
    if not target_dir.exists():
        return []

    backups = sorted(
        target_dir.glob("backup_*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    old_files = backups[keep_latest:]
    deleted = []

    for file in old_files:
        try:
            file.unlink()
            deleted.append(str(file))
            write_log(f"old backup deleted: {file.name}")
        except Exception as e:
            write_log(f"failed to delete old backup {file.name}: {e}", "WARN")

    return deleted


def create_backup():
    config = load_config()

    source_paths = config.get("source_paths", [])
    backup_dir = resolve_path(config.get("backup_dir", "03_backup_to_nas/backups"))
    keep_latest = int(config.get("keep_latest", 5))
    exclude_dirs = config.get("exclude_dirs", [])
    exclude_files = config.get("exclude_files", [])

    backup_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_file = backup_dir / f"backup_{now}.zip"

    existing_sources = []

    for source_text in source_paths:
        source = resolve_path(source_text)

        if source.exists():
            existing_sources.append(source)
        else:
            write_log(f"source not found, skipped: {source}", "WARN")

    if not existing_sources:
        write_log("no valid source paths. backup canceled.", "ERROR")
        return {
            "ok": False,
            "message": "백업할 소스 경로가 없습니다.",
        }

    write_log(f"backup started: {backup_file.name}")

    file_count = 0

    try:
        with zipfile.ZipFile(backup_file, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            manifest = {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "project_root": str(PROJECT_ROOT),
                "sources": [str(p) for p in existing_sources],
                "target_policy": "Synology NAS rsync after local archive verification",
            }

            zipf.writestr(
                "backup_manifest.json",
                json.dumps(manifest, indent=2, ensure_ascii=False),
            )

            for source in existing_sources:
                if source.is_file():
                    if should_exclude(source, exclude_dirs, exclude_files):
                        continue

                    arcname = source.relative_to(PROJECT_ROOT)
                    zipf.write(source, arcname)
                    file_count += 1
                    continue

                for file in source.rglob("*"):
                    if not file.is_file():
                        continue

                    if should_exclude(file, exclude_dirs, exclude_files):
                        continue

                    try:
                        arcname = file.relative_to(PROJECT_ROOT)
                    except ValueError:
                        arcname = file.name

                    zipf.write(file, arcname)
                    file_count += 1

        size_bytes = backup_file.stat().st_size
        sha256 = sha256_file(backup_file)
        sha_file = backup_file.with_suffix(backup_file.suffix + ".sha256")
        sha_file.write_text(f"{sha256}  {backup_file.name}\n", encoding="utf-8")

        write_log(f"backup success: {backup_file.name}, files={file_count}, size={size_bytes}, sha256={sha256}")

        deleted = cleanup_backup_files(backup_dir, keep_latest)

        return {
            "ok": True,
            "backup_file": str(backup_file),
            "sha256_file": str(sha_file),
            "sha256": sha256,
            "size_bytes": size_bytes,
            "file_count": file_count,
            "deleted_old_backups": deleted,
        }

    except Exception as e:
        write_log(f"backup failed: {e}", "ERROR")

        if backup_file.exists():
            try:
                backup_file.unlink()
            except Exception:
                pass

        return {
            "ok": False,
            "message": str(e),
        }


def main():
    result = create_backup()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if not result.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()
