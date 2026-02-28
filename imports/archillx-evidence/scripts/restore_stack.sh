#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup-tar.gz>" >&2
  exit 1
fi

ARCHIVE="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.prod}"
TMP_DIR="$(mktemp -d)"
MYSQL_SERVICE="${MYSQL_SERVICE:-mysql}"
APP_SERVICE="${APP_SERVICE:-archillx}"
DB_NAME="${DB_NAME:-archillx}"
DB_USER="${DB_USER:-archillx}"
DB_PASSWORD="${DB_PASSWORD:-}"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

if [[ -z "$DB_PASSWORD" && -f "$ENV_FILE" ]]; then
  DB_PASSWORD="$(grep -E '^DB_PASSWORD=' "$ENV_FILE" | tail -n1 | cut -d= -f2- || true)"
fi

if [[ -z "$DB_PASSWORD" ]]; then
  echo "DB_PASSWORD is required (set env or .env.prod)" >&2
  exit 1
fi

tar -C "$TMP_DIR" -xzf "$ARCHIVE"
SQL_FILE="$(find "$TMP_DIR" -type f -name 'mysql_*.sql' | head -n1)"
EVIDENCE_DIR="$(find "$TMP_DIR" -type d -name evidence | head -n1 || true)"

if [[ -z "$SQL_FILE" ]]; then
  echo "No mysql dump found in archive" >&2
  exit 1
fi

cat "$SQL_FILE" | docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T "$MYSQL_SERVICE" \
  sh -lc "exec mysql -u\"$DB_USER\" -p\"$DB_PASSWORD\" \"$DB_NAME\""

if [[ -n "$EVIDENCE_DIR" ]]; then
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" cp "$EVIDENCE_DIR/." "$APP_SERVICE":/app/evidence >/dev/null 2>&1 || true
fi

echo "OK_BACKUP_RESTORED=$ARCHIVE"
