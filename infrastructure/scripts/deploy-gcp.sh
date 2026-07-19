#!/usr/bin/env bash
set -euo pipefail
ENVIRONMENT="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/infrastructure/terraform"
terraform init
terraform apply -auto-approve -var-file="../tfvars/${ENVIRONMENT}.tfvars" -var="cloud_provider=gcp"
cd "$ROOT_DIR"
kubectl apply -k infrastructure/kubernetes
