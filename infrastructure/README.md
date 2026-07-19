# AI-Morphasis Infrastructure Quick Start

## Prerequisites
- Docker + Docker Compose
- kubectl + access to a Kubernetes cluster
- Terraform >= 1.5
- Helm >= 3.12
- Cloud CLI (aws/gcloud/az) for target provider

## 1) Local Setup (Docker Compose)
```bash
./infrastructure/scripts/setup-local.sh
```

Or run manually:
```bash
cd infrastructure/docker
docker compose up --build
```

## 2) Kubernetes Deployment
```bash
./infrastructure/scripts/deploy-k8s.sh
```

## 3) Cloud Deployment
### AWS
```bash
./infrastructure/scripts/deploy-aws.sh dev
```

### GCP
```bash
./infrastructure/scripts/deploy-gcp.sh dev
```

### Azure
```bash
./infrastructure/scripts/deploy-azure.sh dev
```

## 4) Monitoring + Logging
```bash
./infrastructure/scripts/monitoring-setup.sh
```

## 5) Trigger Training
```bash
./infrastructure/scripts/train-model.sh
```

## 6) CI/CD Pipeline Configuration
Copy or reference files in `infrastructure/ci-cd/.github/workflows/` into repository workflows and set secrets:
- `REGISTRY_USERNAME` / `REGISTRY_PASSWORD`
- `KUBE_CONFIG` or cloud OIDC roles
- `TF_STATE_BACKEND_*`

## 7) Secrets Management
- Use `infrastructure/secrets-management/.env.example` for required keys.
- Use `infrastructure/kubernetes/secrets.yaml` only as template; do not commit real values.
- Optional Vault bootstrap config is in `infrastructure/secrets-management/vault.hcl`.

## 8) Common Operations
### Scale app
```bash
kubectl -n ai-morphasis scale deployment ai-morphasis --replicas=4
```

### Rolling update image
```bash
kubectl -n ai-morphasis set image deployment/ai-morphasis ai-morphasis=ghcr.io/dj221981/ai-morphasis:NEW_TAG
```

### Rollback
```bash
./infrastructure/scripts/rollback.sh
```

### Validate Terraform plan
```bash
cd infrastructure/terraform
terraform init
terraform plan -var-file=../tfvars/dev.tfvars
```
