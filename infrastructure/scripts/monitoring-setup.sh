#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl -n monitoring create configmap ai-morphasis-prometheus \
  --from-file="$ROOT_DIR/infrastructure/monitoring/prometheus/prometheus.yml" \
  --dry-run=client -o yaml | kubectl apply -f -
printf "Monitoring config applied in namespace monitoring.\n"
