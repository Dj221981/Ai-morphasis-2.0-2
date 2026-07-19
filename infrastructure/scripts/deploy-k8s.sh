#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
kubectl apply -k "$ROOT_DIR/infrastructure/kubernetes"
kubectl -n ai-morphasis rollout status deployment/ai-morphasis --timeout=180s
