#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.prod}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
WORK_DIR="$BACKUP_DIR/$STAMP"
MYSQL_SERVICE="${MYSQL_SERVICE:-mysql}"
APP_SERVICE="${APP_SERVICE:-archillx}"
DB_NAME="${DB_NAME:-archillx}"
DB_USER="${DB_USER:-archillx}"
DB_PASSWORD="${DB_PASSWORD:-}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"

mkdir -p "$WORK_DIR"

if [[ -z "$DB_PASSWORD" && -f "$ENV_FILE" ]]; then
  DB_PASSWORD="$(grep -E '^DB_PASSWORD=' "$ENV_FILE" | tail -n1 | cut -d= -f2- || true)"
fi

if [[ -z "$DB_PASSWORD" ]]; then
  echo "DB_PASSWORD is required (set env or .env.prod)" >&2
  exit 1
fi

ARCHIVE_NAME="archillx_backup_${STAMP}.tar.gz"
SQL_NAME="mysql_${STAMP}.sql"
META_NAME="backup_meta_${STAMP}.txt"

printf 'timestamp=%s\ncompose=%s\n' "$STAMP" "$COMPOSE_FILE" > "$WORK_DIR/$META_NAME"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T "$MYSQL_SERVICE" \
  sh -lc "exec mysqldump -u\"$DB_USER\" -p\"$DB_PASSWORD\" --single-transaction --quick --routines --triggers \"$DB_NAME\"" \
  > "$WORK_DIR/$SQL_NAME"

if docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps "$APP_SERVICE" >/dev/null 2>&1; then
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" cp "$APP_SERVICE":/app/evidence "$WORK_DIR/evidence" >/dev/null 2>&1 || true
fi

tar -C "$WORK_DIR" -czf "$BACKUP_DIR/$ARCHIVE_NAME" .
rm -rf "$WORK_DIR"

find "$BACKUP_DIR" -maxdepth 1 -type f -name 'archillx_backup_*.tar.gz' -mtime +"$KEEP_DAYS" -delete || true

echo "OK_BACKUP_CREATED=$BACKUP_DIR/$ARCHIVE_NAME"
