#!/usr/bin/env bash
set -euo pipefail
ENVIRONMENT="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -z "${TF_VAR_db_password:-}" ]]; then
  echo "TF_VAR_db_password must be set for AWS deployment." >&2
  exit 1
fi
cd "$ROOT_DIR/infrastructure/terraform"
terraform init
terraform apply -auto-approve -var-file="../tfvars/${ENVIRONMENT}.tfvars" -var="cloud_provider=aws"
cd "$ROOT_DIR"
kubectl apply -k infrastructure/kubernetes
