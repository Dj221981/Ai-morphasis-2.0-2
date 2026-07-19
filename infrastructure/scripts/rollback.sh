#!/usr/bin/env bash
set -euo pipefail
NAMESPACE="${1:-ai-morphasis}"
DEPLOYMENT="${2:-ai-morphasis}"
kubectl -n "$NAMESPACE" rollout undo deployment/"$DEPLOYMENT"
kubectl -n "$NAMESPACE" rollout status deployment/"$DEPLOYMENT"
