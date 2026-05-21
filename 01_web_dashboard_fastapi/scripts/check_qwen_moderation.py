#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.error
import urllib.request


SYSTEM_PROMPT = """너는 학교 익명 커뮤니티의 게시글/댓글 안전 필터다.
입력이 아래 항목 중 하나라도 해당하면 1을 출력한다.
문제가 없으면 0을 출력한다.
반드시 0 또는 1 중 한 글자만 출력한다.
설명, 문장, 따옴표, 마침표, 공백을 출력하지 마라."""


def main() -> int:
    base_url = os.getenv("COMMUNITY_MODERATION_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    model = os.getenv("COMMUNITY_MODERATION_MODEL", "qwen2.5-0.5b-instruct")
    try:
        timeout = int(os.getenv("COMMUNITY_MODERATION_TIMEOUT_SECONDS", "5"))
    except ValueError:
        timeout = 5

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "입력:\n학교 생활 정보를 공유하는 정상 안내문입니다.\n\n출력 규칙:\n0 또는 1만 출력.",
            },
        ],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 1,
        "stop": ["\n"],
    }
    request = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        latency_ms = int((time.perf_counter() - started) * 1000)
        data = json.loads(raw)
        output = str(data["choices"][0]["message"]["content"]).strip()
    except urllib.error.URLError as exc:
        print(f"Qwen moderation server ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Qwen moderation server ERROR: invalid response ({exc})", file=sys.stderr)
        return 1

    if not output or output[0] not in {"0", "1"}:
        print(f"Qwen moderation server ERROR: invalid response: {output!r}", file=sys.stderr)
        return 1

    print("Qwen moderation server OK")
    print(f"response={output[0]}")
    print(f"latency_ms={latency_ms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
