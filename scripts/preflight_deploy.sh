#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env.prod ]]; then
  echo "[ERR] .env.prod not found. Copy .env.prod.example first."
  exit 1
fi

required=(API_KEY ADMIN_TOKEN DB_PASSWORD MYSQL_ROOT_PASSWORD)
for key in "${required[@]}"; do
  if ! grep -qE "^${key}=" .env.prod; then
    echo "[ERR] Missing ${key} in .env.prod"
    exit 1
  fi
done

command -v docker >/dev/null || { echo "[ERR] docker not installed"; exit 1; }
docker compose version >/dev/null || { echo "[ERR] docker compose not available"; exit 1; }

echo "[OK] Docker detected"
docker image inspect archillx-sandbox:latest >/dev/null 2>&1 && echo "[OK] sandbox image exists" || echo "[WARN] sandbox image missing (build if code_exec will be enabled)"

docker compose -f docker-compose.prod.yml config >/dev/null

echo "[OK] compose config valid"

if [[ -x ./scripts/check_migration_state.py || -f ./scripts/check_migration_state.py ]]; then
  if python3 ./scripts/check_migration_state.py .env.prod; then
    echo "[OK] migration state check passed"
  else
    echo "[ERR] migration state check failed"
    exit 1
  fi
else
  echo "[WARN] migration state checker missing"
fi

echo "[OK] preflight complete"
