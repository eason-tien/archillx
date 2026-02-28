#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${ARCHILLX_BASE_URL:-http://127.0.0.1:8000}"
API_KEY="${API_KEY:-}"
CURL_ARGS=(-fsS -X POST "$BASE_URL/v1/audit/archive")
if [[ -n "$API_KEY" ]]; then
  CURL_ARGS+=(-H "x-api-key: $API_KEY")
fi
curl "${CURL_ARGS[@]}"
echo
