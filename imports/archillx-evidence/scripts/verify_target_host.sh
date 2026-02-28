#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE=".env.prod"
BASE_URL="${ARCHILLX_BASE_URL:-http://127.0.0.1:8000}"
TIMEOUT="${ARCHILLX_CURL_TIMEOUT:-10}"
SKIP_ENDPOINTS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --skip-endpoints)
      SKIP_ENDPOINTS=1
      shift
      ;;
    *)
      echo "Usage: $0 [--env-file .env.prod] [--base-url http://127.0.0.1:8000] [--skip-endpoints]"
      exit 2
      ;;
  esac
done

fail() {
  echo "[ERR] $*"
  exit 1
}

ok() {
  echo "[OK] $*"
}

warn() {
  echo "[WARN] $*"
}

[[ -f "$ENV_FILE" ]] || fail "env file not found: $ENV_FILE"

command -v python3 >/dev/null || fail "python3 not installed"
command -v curl >/dev/null || fail "curl not installed"
command -v docker >/dev/null || fail "docker not installed"
docker compose version >/dev/null || fail "docker compose not available"
ok "host tools detected"

if command -v alembic >/dev/null 2>&1; then
  ok "alembic CLI detected"
elif python3 - <<'PY' >/dev/null 2>&1
import importlib.metadata
import sys
try:
    importlib.metadata.version('alembic')
except importlib.metadata.PackageNotFoundError:
    sys.exit(1)
PY
then
  ok "alembic Python package detected"
else
  fail "alembic not installed; install requirements.txt before migration validation"
fi

bash ./scripts/preflight_deploy.sh
ok "preflight_deploy passed"

bash ./scripts/migrate.sh current
ok "migrate current passed"

bash ./scripts/migrate.sh upgrade head
ok "migrate upgrade head passed"

python3 ./scripts/check_migration_state.py "$ENV_FILE"
ok "check_migration_state passed"

if [[ "$SKIP_ENDPOINTS" -eq 1 ]]; then
  warn "endpoint verification skipped"
  exit 0
fi

for path in /v1/live /v1/ready /v1/metrics /v1/telemetry /v1/audit/summary /v1/migration/state; do
  code="$(curl -sS -m "$TIMEOUT" -o /tmp/archillx_verify_body.$$ -w '%{http_code}' "$BASE_URL$path" || true)"
  if [[ "$code" =~ ^2 ]]; then
    ok "$path -> HTTP $code"
  else
    echo "----- response body for $path -----"
    cat /tmp/archillx_verify_body.$$ 2>/dev/null || true
    echo "-----------------------------------"
    fail "$path returned HTTP $code"
  fi
done

rm -f /tmp/archillx_verify_body.$$ || true
ok "target host verification passed"
