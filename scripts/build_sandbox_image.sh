#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${ARCHILLX_SANDBOX_DOCKER_IMAGE:-archillx-sandbox:latest}"
docker build -f "$ROOT_DIR/app/security/sandbox.Dockerfile" -t "$IMAGE_NAME" "$ROOT_DIR"
echo "Built sandbox image: $IMAGE_NAME"
