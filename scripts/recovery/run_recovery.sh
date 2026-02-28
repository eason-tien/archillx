#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"
shift || true

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

python -m app.recovery.cli "$@"
