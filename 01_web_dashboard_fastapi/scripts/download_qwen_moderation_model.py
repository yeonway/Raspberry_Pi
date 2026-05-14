#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path


DEFAULT_REPO_ID = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
DEFAULT_FILENAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
DEFAULT_LOCAL_DIR = "/home/user/models/qwen2.5-0.5b"


def human_size(size: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{size} B"
        value /= 1024
    return f"{size} B"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download the Qwen moderation GGUF model.")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID, help="Hugging Face repository id.")
    parser.add_argument("--filename", default=DEFAULT_FILENAME, help="GGUF filename in the repository.")
    parser.add_argument("--local-dir", default=DEFAULT_LOCAL_DIR, help="Directory outside the repo for model storage.")
    parser.add_argument("--force", action="store_true", help="Force re-download even when the file already exists.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    local_dir = Path(args.local_dir).expanduser()
    target_path = local_dir / args.filename

    if target_path.exists() and not args.force:
        size = target_path.stat().st_size
        if size > 0:
            print(f"Model already exists: {target_path}")
            print(f"size={human_size(size)}")
            return 0
        print(f"Existing file is empty, downloading again: {target_path}", file=sys.stderr)

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("ERROR: huggingface_hub is not installed. Run: pip install -r requirements.txt", file=sys.stderr)
        return 2

    local_dir.mkdir(parents=True, exist_ok=True)
    try:
        downloaded = hf_hub_download(
            repo_id=args.repo_id,
            filename=args.filename,
            local_dir=str(local_dir),
            force_download=args.force,
        )
    except Exception as exc:
        print(f"ERROR: failed to download {args.repo_id}/{args.filename}: {exc}", file=sys.stderr)
        return 1

    path = Path(downloaded)
    if not path.exists():
        print(f"ERROR: download completed but file was not found: {path}", file=sys.stderr)
        return 1

    print(f"Downloaded model: {path}")
    print(f"size={human_size(path.stat().st_size)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
