#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:8015/health}"
response="$(curl -fsS --max-time 5 "$URL")"

if [[ "$response" != *'"ok":true'* && "$response" != *'"ok": true'* ]]; then
    echo "Unexpected health response: $response" >&2
    exit 1
fi

echo "OK $URL"
