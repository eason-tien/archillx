#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup-tar.gz> [--execute]" >&2
  exit 1
fi

ARCHIVE="$1"
MODE="dry-run"
if [[ "${2:-}" == "--execute" ]]; then
  MODE="execute"
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFY_SCRIPT="$ROOT_DIR/scripts/verify_backup_archive.py"
RESTORE_SCRIPT="$ROOT_DIR/scripts/restore_stack.sh"
BASE_URL="${ARCHILLX_BASE_URL:-http://127.0.0.1:8000}"
READY_URL="${READY_URL:-$BASE_URL/v1/ready}"
STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_DIR="${DRILL_REPORT_DIR:-$ROOT_DIR/evidence/drills}"
REPORT_FILE="$REPORT_DIR/restore_drill_${STAMP}.json"
mkdir -p "$REPORT_DIR"

VERIFY_JSON="$(python3 "$VERIFY_SCRIPT" "$ARCHIVE" --json)"
VERIFY_OK="$(printf '%s' "$VERIFY_JSON" | python3 -c 'import sys,json; print("true" if json.load(sys.stdin)["ok"] else "false")')"
if [[ "$VERIFY_OK" != "true" ]]; then
  echo "backup archive verification failed" >&2
  exit 2
fi

STATUS="verified"
READY_STATUS="skipped"
if [[ "$MODE" == "execute" ]]; then
  if [[ "${RUN_RESTORE_DRILL:-false}" != "true" ]]; then
    echo "Refusing execute mode without RUN_RESTORE_DRILL=true" >&2
    exit 3
  fi
  "$RESTORE_SCRIPT" "$ARCHIVE"
  STATUS="restored"
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS "$READY_URL" >/dev/null 2>&1; then
      READY_STATUS="ok"
    else
      READY_STATUS="failed"
      STATUS="warning"
    fi
  fi
fi

python3 - "$VERIFY_JSON" "$STATUS" "$MODE" "$READY_STATUS" "$REPORT_FILE" <<'PY'
import json, sys
verify = json.loads(sys.argv[1])
status = sys.argv[2]
mode = sys.argv[3]
ready = sys.argv[4]
report_file = sys.argv[5]
payload = {
    'mode': mode,
    'status': status,
    'ready_status': ready,
    'backup': verify,
}
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
print(f'OK_RESTORE_DRILL_REPORT={report_file}')
PY
