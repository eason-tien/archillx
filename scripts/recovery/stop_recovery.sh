#!/usr/bin/env bash
set -euo pipefail
pkill -f "app.recovery.cli" || true
echo "recovery processes (if any) stopped"
