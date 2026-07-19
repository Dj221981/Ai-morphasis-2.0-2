#!/usr/bin/env bash
set -euo pipefail
NAMESPACE="${1:-ai-morphasis}"
kubectl -n "$NAMESPACE" create job --from=cronjob/ai-morphasis-training ai-morphasis-training-manual-"$(date +%s)"
kubectl -n "$NAMESPACE" get jobs
