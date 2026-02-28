#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v alembic >/dev/null 2>&1; then
  ALEMBIC_CMD=("$(command -v alembic)")
elif python3 - <<'PY' >/dev/null 2>&1
import importlib.metadata
import sys
try:
    importlib.metadata.version('alembic')
except importlib.metadata.PackageNotFoundError:
    sys.exit(1)
PY
then
  ALEMBIC_CMD=(python3 -m alembic)
else
  echo "ERROR: alembic not found. Install requirements.txt before running migrations."
  exit 1
fi

ACTION="${1:-upgrade}"
TARGET="${2:-head}"

case "$ACTION" in
  upgrade)
    exec "${ALEMBIC_CMD[@]}" upgrade "$TARGET"
    ;;
  downgrade)
    exec "${ALEMBIC_CMD[@]}" downgrade "$TARGET"
    ;;
  current)
    exec "${ALEMBIC_CMD[@]}" current
    ;;
  history)
    exec "${ALEMBIC_CMD[@]}" history --verbose
    ;;
  stamp)
    exec "${ALEMBIC_CMD[@]}" stamp "$TARGET"
    ;;
  *)
    echo "Usage: $0 [upgrade|downgrade|current|history|stamp] [target]"
    exit 2
    ;;
esac
