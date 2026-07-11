#!/usr/bin/env bash
set -euo pipefail
TAG="${1:-local}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
docker build -f "$ROOT_DIR/infrastructure/docker/Dockerfile" -t "ai-morphasis:${TAG}" "$ROOT_DIR"
