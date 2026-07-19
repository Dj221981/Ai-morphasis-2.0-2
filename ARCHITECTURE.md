# AI-Morphasis 2.0 Architecture and Infrastructure as Code Guide

## 1. Executive Summary

AI-Morphasis 2.0 is an AI system designed around three operational pillars: deep learning model execution, training and retraining workflows, and advanced reasoning capabilities. The repository currently contains core neural model logic under `src/models/neural_network.py`, agent orchestration modules under `src/agents/`, and data/config utility layers under `src/data/` and `src/config/`. This document expands the architecture into a full Infrastructure as Code (IaC) operating model so the platform can move from local execution to production-grade, repeatable deployment across AWS, GCP, and Azure.

The goal of this architecture is to ensure every production capability has an equivalent code-defined infrastructure primitive. Instead of relying on one-off manual setup, the platform now has declarative artifacts for build, runtime, orchestration, scaling, observability, secrets, and delivery. Dockerfiles define runtime images, Kubernetes manifests define in-cluster topology, Terraform defines cloud control-plane resources, Helm defines environment overlays, scripts define operational workflows, CI/CD pipelines define release gates, and monitoring/logging stacks define operational feedback loops.

The architecture is intentionally modular: teams can run only Docker Compose for local development, run Kubernetes-only for private clusters, or run Terraform + Kubernetes + Helm for full cloud production. Every path remains compatible with the same code and environment variable contracts.

## 2. System Overview with IaC Integration Points

### 2.1 Core Runtime Domains

The system is split into these domains:

1. **Inference domain**
   - Primary AI-Morphasis app container exposing API/business logic.
   - TensorFlow Serving sidecar/deployment for model inference throughput.
   - Service and ingress path routing to inference endpoints.

2. **Training domain**
   - Training executable path anchored to `src/training/train.py` integration contract.
   - Periodic retraining through Kubernetes `CronJob`.
   - Artifact persistence to cloud object storage (S3/GCS/Azure Storage).

3. **Model storage domain**
   - Persistent volumes for local/on-cluster model cache.
   - Versioned model artifacts in object storage buckets/containers.

4. **Control and operations domain**
   - Terraform modules provisioning clusters, networking, registries, IAM/RBAC.
   - CI/CD workflows building images, testing code, and promoting releases.
   - Monitoring/logging stacks collecting SLI/SLO metrics and alerts.

5. **Security and compliance domain**
   - Kubernetes `Secret` templates (redacted values).
   - Vault bootstrap template and `.env.example` mapping.
   - Security scan workflow and image signing hooks.

### 2.2 Source-Code-to-Infrastructure Mapping

| Source path | Infrastructure component | Deployment/runtime impact |
|---|---|---|
| `src/models/neural_network.py` | TensorFlow Serving deployment, model PVC/object storage | Defines model runtime dependencies and model path layout |
| `src/training/train.py` | `training-job.yaml`, `train-model.yml`, `scripts/train-model.sh` | Defines retraining cadence and validation flow |
| `tests/test_models.py` | CI test workflow (`run-tests.yml`) | Defines quality gate before image publish/deploy |
| `.env.example` | ConfigMap/Secret templates, compose env_file | Defines shared variable contract across environments |
| `requirements.txt` | Docker build layer, CI dependency installation | Defines deterministic runtime and pipeline deps |

### 2.3 Deployment Topologies

- **Local developer topology**: Docker Compose with app + TensorFlow Serving + PostgreSQL + Prometheus + Grafana.
- **Staging topology**: Single Kubernetes cluster namespace with moderate resource requests, HPA enabled, reduced retention.
- **Production topology**: Managed Kubernetes (EKS/GKE/AKS), autoscaling, cloud load balancing, externalized secrets, observability integrations, and IaC-controlled rollouts.

## 3. Component Architecture

### 3.1 AI-Morphasis Application Service

The app service is the control plane for request handling, orchestration logic, and interaction with model-serving endpoints. In production, it runs as a Deployment with rolling updates, readiness and liveness probes, and resource limits to protect node stability.

Dependencies:
- Config from ConfigMap and Secret references.
- TensorFlow Serving endpoint (`TF_SERVING_URL`).
- Optional relational metadata store.
- Persistent model volume for local fallback model loading.

Scaling behavior:
- Horizontal scaling with CPU and memory thresholds via HPA.
- Stateless process model preferred; state externalized to storage and queue layers.

### 3.2 TensorFlow Serving Tier

TensorFlow Serving is isolated into its own Deployment to scale independently from the core app. This supports asymmetric scaling (many inference replicas with fewer control-plane app replicas) and model hot-swaps without changing application image layers.

Key runtime elements:
- Model volume mount or cloud-backed sync path.
- Optional sidecar for model pull/sync.
- Dedicated service for low-latency in-cluster inference traffic.

### 3.3 Training Pipeline Tier

Training is modeled as scheduled batch compute. A Kubernetes `CronJob` runs periodic retraining and can be manually triggered through scripts and CI workflows.

Training lifecycle:
1. Pull latest code + dependencies from container image.
2. Read data source and feature configuration.
3. Train and validate model.
4. Export model artifact and metadata.
5. Push artifact to object storage.
6. Update serving pointer (model version or alias).

### 3.4 Data and Persistence Dependencies

- **Operational metadata**: PostgreSQL/RDS/Cloud SQL/Azure DB (optional based on maturity).
- **Model artifacts**: S3/GCS/Blob storage buckets with lifecycle policies.
- **Transient/edge storage**: PVC for in-cluster model caching and training scratch space.

### 3.5 Observability Plane

Metrics, logs, and alerts are first-class architecture components:
- Prometheus scrapes app and serving metrics.
- Grafana dashboards expose training, inference, and infrastructure health.
- Alertmanager routes high-severity events.
- Fluent Bit/Filebeat/Loki templates support centralized logs.

## 4. Deep Thinking Engine and Runtime Implications

The repository includes a “Deep thinking” module illustrating chain-of-thought style reasoning primitives, hypothesis evaluation, and metacognitive loops. Even when used as an internal cognitive utility rather than an external endpoint, it drives non-trivial infrastructure behavior.

### 4.1 Compute Characteristics

Deep reasoning workloads often produce bursty CPU usage and occasionally sustained memory pressure depending on context windows and intermediate structures. This requires:
- Conservative memory limits to avoid OOM kills.
- Readiness checks that ensure warm-up completion before routing traffic.
- HPA policies tuned for both average and p95 utilization behavior.

### 4.2 Reliability Requirements

Reasoning tasks may chain multiple operations, so partial failures can compound latency. Infrastructure mitigations:
- PodDisruptionBudget (future hardening) to avoid concurrent evictions.
- Rolling updates with surge/unavailable controls.
- Retry semantics in upstream clients and CI smoke checks.

### 4.3 Security and Auditability

If deep thinking outputs are used in automated workflows, logs and traces become audit artifacts. The logging stack should include:
- Request IDs and correlation IDs.
- Redaction for sensitive payload fragments.
- Separate retention policies for debug vs compliance logs.

## 5. Training Pipeline and Deployment Considerations

### 5.1 Pipeline Stages

1. **Data ingestion** from configured source (bucket, DB, feature store).
2. **Preprocessing** through modules under `src/data/preprocessing.py` contract.
3. **Model training** via `src/training/train.py` entrypoint.
4. **Evaluation** using metric thresholds that gate deployment.
5. **Packaging** into TensorFlow SavedModel or compatible serving format.
6. **Promotion** to staging/production registry paths.

### 5.2 Deployment Coupling Between Training and Serving

Training and serving are decoupled but synchronized through artifact versioning:
- Training emits immutable versioned artifacts.
- Serving consumes by explicit version tag.
- Rollback script resets serving to prior model version without retraining.

### 5.3 Safety Gates

Before promotion:
- CI unit/integration tests pass (`tests/test_models.py`).
- Model validation workflow passes thresholds.
- Security scan workflow passes baseline checks.
- Optional human approval for production deployment.

### 5.4 Cost and Performance Controls

- Schedule retraining off-peak.
- Use lower-cost node pools for batch jobs.
- Tune training resource requests/limits for predictable scheduling.
- Apply bucket/object lifecycle to avoid runaway storage costs.

## 6. Detailed Infrastructure as Code Design

This section maps each required IaC layer to operational concerns and concrete files.

### 6.1 Docker Layer (`infrastructure/docker/`)

- `Dockerfile` defines production image via multi-stage build.
- `Dockerfile.dev` adds debugging, shell tooling, and dev dependencies.
- `docker-compose.yml` provisions local full-stack dependencies.
- `docker-compose.prod.yml` approximates production behavior locally.

Production Docker image principles:
- Minimal final layer footprint.
- Non-root runtime user.
- Health check endpoint validation.
- Explicit runtime env defaults and overridable vars.

### 6.2 Kubernetes Base Manifests (`infrastructure/kubernetes/`)

The Kubernetes base serves as environment-agnostic deployment logic:

- `namespace.yaml`: isolates workloads and policies.
- `configmap.yaml`: non-sensitive app settings.
- `secrets.yaml`: placeholder template; real values injected by secret manager.
- `ai-morphasis-deployment.yaml`: app deployment with probes/resources.
- `tensorflow-serving-deployment.yaml`: inference-serving deployment.
- `training-job.yaml`: scheduled retraining cron.
- `pvc.yaml`: persistent model volume.
- `service.yaml`: stable app endpoint.
- `hpa.yaml`: horizontal autoscaling.
- `kustomization.yaml`: deterministic base composition.

Operational controls included:
- Rolling updates.
- Readiness/liveness probes.
- Resource requests/limits.
- Service accounts and explicit env wiring.

### 6.3 Terraform Multi-Cloud Layer (`infrastructure/terraform/`)

Terraform is split into shared and provider-specific concerns.

Shared:
- `providers.tf` selects active cloud provider configuration.
- `variables.tf` defines environment-level inputs.
- `main.tf` composes modules and baseline resources.
- `outputs.tf` exports operational values.

AWS (`terraform/aws/`):
- EKS cluster and node groups.
- ECR repositories for app/training images.
- S3 artifact bucket with lifecycle and encryption.
- IAM roles and policies for cluster/workloads.
- VPC, subnets, gateways, and security groups.
- ALB for external routing.
- CloudWatch log/metric alarms and dashboards.

GCP (`terraform/gcp/`):
- GKE cluster with node pool policies.
- Artifact Registry repositories.
- GCS bucket for model artifacts.
- Service accounts and IAM bindings.
- Cloud Monitoring alert policies.

Azure (`terraform/azure/`):
- AKS cluster with managed identities.
- ACR repositories.
- Storage accounts/containers for artifacts.
- Key Vault for secret material.
- Application Insights + Monitor alerting.

### 6.4 Helm Layer (`infrastructure/helm/`)

Helm provides release packaging and environment overlays:
- `values.yaml` common defaults.
- `values-dev.yaml`, `values-prod.yaml` environment overrides.
- Templates for deployment/service/configmap/secrets/ingress/hpa.

This allows repeatable promotion with parameterized image tags, replica counts, and hostnames.

### 6.5 Scripted Operations Layer (`infrastructure/scripts/`)

Scripts provide deterministic command wrappers:
- Local setup and image build.
- Kubernetes deployment and rollback.
- Cloud-specific deployment wrappers.
- Monitoring stack bootstrap.
- Training trigger and validation checks.

Scripts are shell-safe (`set -euo pipefail`) and fail fast.

### 6.6 CI/CD Layer (`infrastructure/ci-cd/`)

Dedicated pipeline templates include:
- Build and push image workflow.
- Staging and production deploy workflows.
- Test workflow.
- Model retraining workflow.
- Security scan workflow.

These can be copied or referenced into active `.github/workflows` as teams mature.

### 6.7 Monitoring and Logging Layers

Monitoring:
- Prometheus scrape and recording rules.
- Grafana datasource and dashboard JSONs.
- Alert rules and Alertmanager routing.

Logging:
- Fluent Bit config for Kubernetes/containers.
- Filebeat config for ELK-based deployments.
- Loki config for Grafana-native log aggregation.

### 6.8 Secrets Management Layer

- `vault.hcl` template for Vault dev/prod bootstrap.
- `.env.example` in `secrets-management/` enumerating required vars.
- Kubernetes Secret manifests are placeholders only.

### 6.9 Environment Variable Contracts

Critical variables include:
- `APP_ENV`
- `LOG_LEVEL`
- `MODEL_PATH`
- `TF_SERVING_URL`
- `DATABASE_URL`
- `S3_BUCKET` / `GCS_BUCKET` / `AZURE_STORAGE_CONTAINER`

All environments should expose equivalent keys to keep runtime code portable.

## 7. Kubernetes Workload Design Details

### 7.1 AI-Morphasis Deployment Strategy

The app deployment uses:
- 2+ replicas for high availability.
- Rolling update with controlled surge.
- `readinessProbe` on `/health/ready`.
- `livenessProbe` on `/health/live`.
- Tight CPU/memory requests to improve bin-packing.

### 7.2 TensorFlow Serving Strategy

TensorFlow Serving deployment uses:
- Independent replica scaling.
- Model base path mount from PVC/object-sync path.
- Dedicated service on port 8501.

### 7.3 Training CronJob Strategy

Training CronJob:
- Cron schedule (`0 */6 * * *` by default).
- Concurrency policy `Forbid`.
- Active deadline and restart controls.
- Optional model validation post-step before publish.

### 7.4 HPA Policy

HPA scales app deployment with dual metrics:
- CPU utilization target.
- Memory utilization target.

Future extension:
- Custom metrics (request latency, queue depth, model inference latency).

## 8. Terraform Design by Provider

### 8.1 AWS

AWS deployment pattern:
1. Provision VPC and subnets.
2. Create EKS cluster and managed node groups.
3. Create ECR repositories for app/training.
4. Create S3 bucket for model artifacts.
5. Wire IAM roles/policies for nodes and service accounts.
6. Expose service using ALB controller pattern.
7. Configure CloudWatch log groups and alarms.

Cost profile guidance:
- Dev: 2 small nodes, minimal retention, shared NAT considerations.
- Staging: moderate nodes and 7-14 day logs.
- Prod: multi-AZ nodes, managed add-ons, higher retention.

### 8.2 GCP

GCP deployment pattern:
1. Create GKE cluster.
2. Create Artifact Registry repository.
3. Create GCS bucket with lifecycle and versioning.
4. Create service accounts and least-privileged IAM.
5. Attach Cloud Monitoring alerts.

Cost profile guidance:
- Use preemptible/spot pools for training jobs when tolerant.
- Separate node pools for serving vs batch training.

### 8.3 Azure

Azure deployment pattern:
1. Create resource group and AKS cluster.
2. Create ACR and connect pull permissions.
3. Create Storage Account + blob container.
4. Create Key Vault secrets and access policies.
5. Enable Application Insights.

Cost profile guidance:
- Split prod and non-prod into separate resource groups.
- Enforce budget alerts and diagnostic retention tiers.

## 9. CI/CD and Release Management

### 9.1 Build Workflow

`build-image.yml`:
- Trigger on pushes and PRs.
- Build multi-arch image where supported.
- Tag by commit SHA and semantic tags.
- Push to registry with immutable tags.

### 9.2 Test Workflow

`run-tests.yml`:
- Install dependencies from `requirements.txt`.
- Execute `pytest tests/test_models.py -v` and optional expanded suites.
- Enforce minimum quality gates before deploy workflows.

### 9.3 Deployment Workflows

`deploy-staging.yml`:
- Deploy to staging namespace on main branch merge.
- Run post-deploy smoke checks.

`deploy-production.yml`:
- Manual approval gate.
- Blue/green or rolling strategy.
- Automatic rollback on failed health checks.

### 9.4 Model Training Workflow

`train-model.yml`:
- Trigger by schedule and manual dispatch.
- Execute training with environment-specific datasets.
- Validate metrics and publish artifacts.
- Optionally trigger serving rollout with approved model.

### 9.5 Security Workflow

`security-scan.yml`:
- Run `pip-audit`, `bandit`, and image scanning.
- Generate SARIF or artifact reports.
- Fail on critical/high findings by policy.

## 10. Observability, SLOs, and Operational Readiness

### 10.1 Metrics

Core SLIs:
- Request success rate.
- p50/p95/p99 latency.
- Training success rate.
- Model inference error rate.
- HPA scale events.

### 10.2 Alerting

Critical alerts:
- App pod crash loops.
- Readiness probe failures.
- Training job failures.
- High inference latency sustained.
- Low success-rate burn alerts.

### 10.3 Dashboards

Dashboard groupings:
- **Training metrics**: throughput, epoch time, validation score trend.
- **Inference metrics**: QPS, latency, error ratio, model version split.
- **Infrastructure metrics**: CPU, memory, pod restarts, node saturation.

## 11. Security Architecture

### 11.1 Identity and Access

- Least privilege IAM roles/service accounts.
- Registry pull-only permissions for workloads.
- Separate CI deploy role from runtime workload role.

### 11.2 Secrets Handling

- No plaintext production secrets in git.
- Templates only in manifests and env examples.
- Vault/Key Vault/Secret Manager integration recommended.

### 11.3 Network Security

- Restrictive security groups/firewall rules.
- Private cluster endpoints when possible.
- TLS termination at ingress/load balancer.

### 11.4 Supply Chain Security

- Signed container artifacts.
- Dependency scanning in CI.
- Immutable image tags in deployments.

## 12. Deployment Decision Tree

1. **Need local iteration only?**
   - Use Docker Compose.
2. **Need cluster parity without cloud provisioning?**
   - Use Kubernetes manifests + local K8s (kind/minikube).
3. **Need managed cloud production?**
   - Provision with Terraform (AWS/GCP/Azure), deploy with Helm/Kustomize.
4. **Need frequent environment-specific rollouts?**
   - Use Helm values per environment.
5. **Need strict compliance and secret governance?**
   - Integrate Vault/Key Vault and policy-as-code checks.

## 13. Troubleshooting Guide

### 13.1 Build Failures

- Check `requirements.txt` resolution and pinned versions.
- Validate Docker build context and copy paths.
- Verify platform target compatibility.

### 13.2 Kubernetes Failures

- `kubectl describe pod` for probe/resource failures.
- Confirm Secret and ConfigMap keys exist.
- Check PVC binding and storage class availability.

### 13.3 Training Failures

- Inspect CronJob logs for data path/env var issues.
- Validate model artifact write permissions.
- Ensure batch resources are sufficient.

### 13.4 Terraform Failures

- Confirm cloud credentials and provider region settings.
- Validate state backend lock behavior.
- Plan with `-var-file` matching target environment.

### 13.5 Observability Gaps

- Confirm Prometheus scrape annotations/targets.
- Check Grafana datasource URL and auth.
- Validate alert routing in Alertmanager config.

## 14. Cost Estimation Framework

### 14.1 AWS (Approximate Baseline)

- EKS control plane: fixed monthly fee.
- Worker nodes: dominant compute cost (serving + training pools).
- ALB/NLB: request + hour based.
- S3: storage + request costs.
- CloudWatch: ingest + retention.

### 14.2 GCP (Approximate Baseline)

- GKE control plane (depending on mode).
- Node pools by machine family.
- Artifact Registry storage/egress.
- GCS storage tiers and egress.
- Cloud Monitoring ingest/retention.

### 14.3 Azure (Approximate Baseline)

- AKS management and node costs.
- ACR storage and transfer.
- Blob storage capacity and ops.
- Application Insights data volume.

Optimization levers across clouds:
- Spot/preemptible nodes for training.
- Autoscaling with sane min/max bounds.
- Log retention tuning.
- Artifact lifecycle cleanup.

## 15. Migration and Rollout Plan

1. Land infrastructure templates in repo.
2. Validate local compose flow.
3. Validate Kubernetes manifests in non-prod cluster.
4. Provision one cloud environment through Terraform.
5. Wire CI secrets and deployment roles.
6. Enable monitoring and alerting.
7. Add production approvals and rollback drills.

## 16. Final Notes

This architecture converts AI-Morphasis 2.0 from documentation-only deployment ideas into executable infrastructure. The repository now includes practical building blocks for local development, Kubernetes operations, multi-cloud provisioning, observability, and release automation. Teams can adopt incrementally while preserving deterministic, reviewable, and auditable changes through version-controlled IaC.

## 17. Infrastructure Dependency Matrix

This section provides a practical dependency matrix so operators understand exactly what must exist before each workload can be executed. While the manifests and Terraform definitions are executable, a dependency matrix helps with incident response, provisioning order, and blast-radius analysis.

### 17.1 Application Deployment Dependencies

The AI-Morphasis deployment depends on:

- Namespace existence (`ai-morphasis`).
- ConfigMap keys (`APP_ENV`, `LOG_LEVEL`, `MODEL_PATH`, `TF_SERVING_URL`).
- Secret keys (`DATABASE_URL`, API or integration keys where required).
- Image repository availability and pull access.
- PVC binding if local model cache is required.
- TensorFlow Serving service readiness (unless app supports local inference fallback).

If any dependency is absent, startup should fail quickly so operators can identify missing configuration rather than serving partial or incorrect behavior. This is why configuration is externalized and probes are used aggressively.

### 17.2 TensorFlow Serving Dependencies

TensorFlow Serving depends on:

- Model artifact availability in mounted path.
- Filesystem permissions for serving user.
- In-cluster service discovery (`tensorflow-serving` service).
- Optional sidecar or init container for remote model sync (future enhancement).

This separation allows inference scaling independent from application scaling. It also enables serving version promotion by altering model pointers and restarting only serving pods.

### 17.3 Training Job Dependencies

Training job dependencies include:

- Data access credentials and endpoints.
- Write permissions to artifact storage location.
- Resource quota headroom in cluster namespace.
- Known-good image tag that includes training runtime dependencies.

For production, introduce admission checks to block job execution when required secret keys are missing.

### 17.4 Monitoring Dependencies

Observability components depend on:

- Metrics endpoints exposed by app and serving tier.
- Network access from Prometheus to target services.
- Dashboard datasource connectivity.
- Alertmanager receiver endpoints.

Without these dependencies, teams lose operational visibility and incident detection lag increases significantly.

## 18. Environment Modeling and Promotion Strategy

A robust IaC repository must model environment differences while preserving a single architectural truth. AI-Morphasis uses environment overlays for values and variable files so operators can promote changes with confidence.

### 18.1 Development Environment

Development prioritizes speed and feedback:

- Docker Compose for one-command setup.
- Lower resource requests.
- Optional disabling of HPA.
- Verbose logging and permissive retries.
- Shared local model storage.

This environment is optimized for experimentation and integration testing.

### 18.2 Staging Environment

Staging mirrors production patterns but at reduced scale:

- Kubernetes deployment with production-like probes.
- HPA enabled with lower max replica counts.
- Artifact registry and object storage integration.
- Pre-production observability checks.
- Deployment approvals optional but recommended.

Staging validates both application behavior and deployment process behavior.

### 18.3 Production Environment

Production emphasizes resilience and governance:

- Managed Kubernetes cluster and controlled networking.
- Immutable image tags and approved promotion only.
- Tight RBAC and secrets-manager integration.
- SLO-driven alerting and rollback procedures.
- Change windows and audit logging.

### 18.4 Promotion Flow

Promotion should follow these gates:

1. Unit and static checks pass.
2. Build image and scan image.
3. Deploy to staging and run smoke tests.
4. Validate key metrics and error budgets.
5. Approve production deployment.
6. Run post-deploy verification and monitor burn rates.

Each gate is represented in CI/CD workflow templates and scriptable commands.

## 19. Resilience Engineering and Failure Modes

Production-grade IaC is not just about deployment. It is about predictable behavior under failure. This section maps common failure modes to infrastructure controls.

### 19.1 Pod Crash Loop Failures

Potential causes:
- Missing environment variables.
- Invalid startup command.
- OOM at startup due to model preload.

Mitigations:
- Readiness/liveness probes with meaningful paths.
- Resource request/limit tuning.
- Config validation during app bootstrap.
- Fast rollback command path (`rollback.sh`).

### 19.2 Dependency Outage Failures

Potential causes:
- TensorFlow Serving unavailable.
- Database connectivity interruption.
- Object storage throttling.

Mitigations:
- Circuit-breaker and retry logic in app clients.
- Independent scaling for serving tier.
- Multi-replica deployments.
- Alerting on elevated dependency error rates.

### 19.3 Training Pipeline Failures

Potential causes:
- Data source schema drift.
- Resource starvation on batch nodes.
- Artifact write failures.

Mitigations:
- CronJob concurrency policy `Forbid`.
- Validation checks before promotion.
- Separate node pools for training.
- Cloud storage IAM policy validation in Terraform plans.

### 19.4 Deployment Failures

Potential causes:
- Invalid manifest/templating values.
- Incompatible image/runtime changes.
- Secret or config drift.

Mitigations:
- Kustomize/Helm validation in CI.
- Staging smoke tests.
- Controlled rollout status checks.
- Immediate rollback command wrappers.

## 20. Performance and Capacity Planning

Capacity planning should be embedded into IaC defaults and documented assumptions.

### 20.1 Inference Capacity

Key assumptions:
- Baseline QPS and target p95 latency.
- Model size and cold-start cost.
- CPU vs GPU requirements for serving profile.

Practical strategy:
- Start CPU-only for moderate throughput.
- Introduce GPU nodes when p95 latency cannot be met.
- Use HPA with conservative minimum replicas to avoid cold starts.
- Pin serving resources independently from app resources.

### 20.2 Training Capacity

Training is bursty and batch-oriented:
- Prefer dedicated training resources.
- Use spot/preemptible pools when checkpointing exists.
- Timebox jobs with active deadlines.
- Save intermediate artifacts for resumption.

### 20.3 Storage Capacity

Model artifacts and logs can dominate costs:
- Enable object versioning with lifecycle rules.
- Compress and tier old artifacts.
- Use retention classes by environment.

### 20.4 Network Capacity

For inference-heavy deployments:
- Ensure service and ingress sizing for peak traffic.
- Use cloud load balancer metrics to detect saturation.
- Monitor cross-zone traffic costs and tune topology.

## 21. Security Hardening Roadmap

The repository includes secure defaults and templates, but production hardening is iterative. A staged roadmap helps teams adopt controls without blocking delivery.

### 21.1 Immediate Hardening

- Replace placeholder secret templates with external secret injection.
- Use dedicated service accounts per workload.
- Enforce immutable image tags.
- Enable security scan workflow and fail on critical vulnerabilities.

### 21.2 Short-Term Hardening

- Implement network policies restricting east-west traffic.
- Add Pod Security admission constraints.
- Rotate cloud keys and prefer workload identity.
- Add signed image verification in admission controller.

### 21.3 Medium-Term Hardening

- Add OPA/Gatekeeper policies for manifest compliance.
- Integrate centralized key management workflows.
- Add secret leak detection and policy checks in PR gates.
- Add runtime threat detection hooks.

### 21.4 Governance and Audit

- Keep Terraform state and changes auditable.
- Require review for infrastructure changes.
- Track incident retrospectives and map to IaC updates.

## 22. Data Governance and Artifact Lineage

AI systems require reproducible artifact lineage from dataset to deployed model. Infrastructure should support immutable history and traceability.

### 22.1 Artifact Naming and Versioning

Recommended pattern:
- `model-name/environment/date/build-sha/version`

Each artifact includes metadata:
- Training code revision.
- Data snapshot or reference.
- Hyperparameter summary.
- Validation metrics.

### 22.2 Promotion Metadata

When promoting from staging to production:
- Record approver identity.
- Record metric gate pass/fail evidence.
- Record previous and current serving versions.

This supports rollback confidence and compliance reporting.

### 22.3 Retention Policy

Retain:
- Latest N production artifacts.
- Latest N staging artifacts.
- Evaluation reports for audit windows.

Purge:
- Expired intermediate artifacts.
- Abandoned experiment outputs.

Implement lifecycle rules in cloud storage Terraform resources.

## 23. Operational Runbooks

A production platform needs runbooks aligned with IaC commands. The scripts in `infrastructure/scripts/` provide executable building blocks for these runbooks.

### 23.1 Standard Deployment Runbook

1. Build/pull approved image.
2. Validate cluster context.
3. Apply manifests (or Helm upgrade).
4. Monitor rollout status.
5. Run smoke tests.
6. Confirm dashboards/alerts healthy.

### 23.2 Emergency Rollback Runbook

1. Identify failing deployment revision.
2. Execute rollback script.
3. Confirm readiness and service restoration.
4. Capture logs/events for incident report.
5. Freeze further deploys until root cause is identified.

### 23.3 Training Incident Runbook

1. Inspect failed job logs.
2. Validate data source and credentials.
3. Relaunch one manual training job.
4. Compare metrics with previous baseline.
5. Promote only after threshold pass.

### 23.4 Secret Rotation Runbook

1. Rotate secret in managed secret store.
2. Sync into Kubernetes secret reference path.
3. Restart dependent workloads.
4. Validate app health and dependency connectivity.

## 24. Testing Strategy for Infrastructure Changes

Infrastructure code should be tested with similar discipline as application code.

### 24.1 Static Validation

- `terraform validate` and `terraform plan` checks.
- `kubectl apply --dry-run=client` for manifests.
- `helm lint` and `helm template` checks.
- YAML schema checks in CI.

### 24.2 Runtime Validation

- Deploy to dev/staging namespace.
- Run smoke and health endpoint checks.
- Confirm HPA reacts under synthetic load.
- Trigger training job and verify artifact publication.

### 24.3 Regression Guardrails

- Keep backward-compatible env variable contracts.
- Preserve service names and API routes unless versioned migration exists.
- Introduce deployment changes incrementally.

## 25. Team Operating Model and Change Management

To keep infrastructure reliable, teams should treat IaC as a product with ownership and lifecycle.

### 25.1 Ownership Boundaries

- App team owns runtime configuration contracts.
- Platform team owns cluster and cloud modules.
- Shared ownership for CI/CD and observability templates.

### 25.2 Review Standards

For each infra PR:
- Explain blast radius.
- Include rollback strategy.
- Include test evidence (plan output, template render, dry-run).
- Include security considerations.

### 25.3 Release Cadence

- Batch low-risk infra updates weekly.
- Handle critical security patches immediately.
- Align major infrastructure migrations to explicit release windows.

## 26. Future Evolution Path

AI-Morphasis can evolve this IaC foundation through optional enhancements:

- Add Kustomize overlays per environment.
- Add GPU node pools and scheduling constraints.
- Add service mesh for traffic policy and mTLS.
- Add canary analysis with progressive delivery tools.
- Add policy-as-code admission checks.
- Add centralized feature store and metadata registry.

These are natural extensions and do not invalidate the current structure.

## 27. Comprehensive IaC File Index and Purpose

To make onboarding fast, this index summarizes each major file and why it exists.

- `infrastructure/docker/Dockerfile`: production container baseline.
- `infrastructure/docker/Dockerfile.dev`: local developer runtime.
- `infrastructure/docker/docker-compose.yml`: full local stack with app, serving, db, monitoring.
- `infrastructure/docker/docker-compose.prod.yml`: production-like local run.
- `infrastructure/kubernetes/*.yaml`: base Kubernetes objects for runtime, scaling, storage, and scheduling.
- `infrastructure/terraform/*.tf`: cloud provisioning entrypoints.
- `infrastructure/terraform/aws/*.tf`: AWS platform resources for EKS and related services.
- `infrastructure/terraform/gcp/*.tf`: GCP platform resources for GKE and related services.
- `infrastructure/terraform/azure/*.tf`: Azure platform resources for AKS and related services.
- `infrastructure/helm/*`: charted deployment model with environment values.
- `infrastructure/scripts/*.sh`: operational automation and runbook execution.
- `infrastructure/ci-cd/.github/workflows/*.yml`: pipeline templates for build, test, deploy, train, scan.
- `infrastructure/monitoring/**`: metrics, dashboards, and alerts.
- `infrastructure/logging/*`: log collection templates.
- `infrastructure/database/**`: schema initialization and backups.
- `infrastructure/secrets-management/*`: vault and env contract templates.
- `infrastructure/tfvars/*.tfvars`: environment-specific Terraform variables.

This index allows new contributors to map operational concerns directly to files and reduce onboarding time for production readiness.

## 28. Cloud-Specific Deep-Dive Deployment Paths

This section gives step-by-step provider-focused flows that combine Terraform provisioning and Kubernetes workload deployment. It is designed for operators who need exact procedural understanding.

### 28.1 AWS End-to-End Flow

1. Export AWS credentials (or assume role via SSO/OIDC).
2. Initialize Terraform in `infrastructure/terraform`.
3. Apply with `cloud_provider=aws` and selected tfvars.
4. Retrieve and merge EKS kubeconfig.
5. Build/push image to ECR (or GHCR fallback).
6. Update Kubernetes image tag reference.
7. Apply kustomize/helm manifests.
8. Wait for deployment rollout success.
9. Validate service endpoints and dashboards.
10. Trigger one manual training run and verify S3 artifact output.

Operational checks:
- Ensure IAM roles permit S3 access for training and serving workflows.
- Ensure cluster subnets route outbound traffic where needed.
- Ensure ALB routing policies align with expected ingress behavior.

### 28.2 GCP End-to-End Flow

1. Authenticate with `gcloud auth application-default login`.
2. Enable required APIs (GKE, Artifact Registry, Monitoring, Storage).
3. Apply Terraform with `cloud_provider=gcp`.
4. Fetch GKE credentials into kubeconfig.
5. Build/push image to Artifact Registry.
6. Deploy manifests and verify pod readiness.
7. Configure Grafana datasource and alert channels.
8. Run manual training job and validate GCS artifact versions.

Operational checks:
- Workload service account IAM should be least privilege.
- Node pool sizing should separate serving and batch workloads.
- Alert policy filters should match real metric names in your project.

### 28.3 Azure End-to-End Flow

1. Login with `az login` and select subscription.
2. Apply Terraform with `cloud_provider=azure`.
3. Pull AKS credentials.
4. Build/push image to ACR.
5. Deploy manifests and confirm service routing.
6. Configure Key Vault secret ingestion path.
7. Validate Application Insights telemetry ingestion.
8. Trigger and validate training job artifact writes.

Operational checks:
- Confirm AKS identity access to ACR and Storage.
- Confirm Key Vault access policies are scoped correctly.
- Confirm monitoring retention and cost controls.

## 29. Model Serving Lifecycle Management

Model-serving operations should follow lifecycle discipline similar to software releases.

### 29.1 Version Introduction

- New model version is registered with metadata.
- Version is first deployed to staging-serving environment.
- Canary or shadow traffic validation is executed where available.

### 29.2 Promotion

- Promotion requires threshold pass and approval.
- Serving reference is updated to immutable artifact version.
- Deployment is rolled with health and latency checks.

### 29.3 Rollback

- Previous stable model version is preserved.
- Rollback is pointer-based where possible (faster than retraining).
- Post-rollback checks confirm latency and error ratio normalization.

### 29.4 Decommission

- Expired model versions are archived by retention policy.
- Dependencies and dashboard panels are updated.
- Long-term artifact retention remains available for audit.

## 30. Configuration Governance and Drift Prevention

Configuration drift is one of the largest operational risks in distributed AI systems. IaC must make drift visible and correctable.

### 30.1 Drift Detection

- Use scheduled Terraform plan in read-only mode.
- Use periodic `kubectl diff` or `helm diff` against desired state.
- Alert when unmanaged changes are detected.

### 30.2 Drift Response

- Classify drift as authorized emergency change or unauthorized mutation.
- Reconcile by updating IaC or reverting mutable state.
- Document root cause and process correction.

### 30.3 Contract Stability

Application code should consume stable configuration keys. Any key rename should include:
- Backward-compatible transition period.
- Environment-by-environment rollout instructions.
- Explicit deprecation timeline.

## 31. SLO Framework and Error Budget Policy

Define explicit service-level objectives and operational behavior when objectives are at risk.

### 31.1 Candidate SLOs

- API availability: 99.9% monthly.
- Inference p95 latency: < 800ms under nominal load.
- Training completion success: > 98% scheduled runs.
- Deployment success without rollback: > 95% monthly.

### 31.2 Error Budget Usage

When error budget burn is high:
- Freeze non-critical feature releases.
- Prioritize reliability and scaling fixes.
- Increase observability detail where blind spots exist.

### 31.3 Alert Severity Mapping

- **Critical**: Immediate customer impact or data-loss risk.
- **High**: Degraded service approaching SLO violation.
- **Medium**: Persistent warning requiring near-term remediation.
- **Low**: Informational optimization opportunities.

## 32. Detailed Troubleshooting Decision Trees

### 32.1 Deployment Not Becoming Ready

1. Check pod events for image pull, scheduling, or probe errors.
2. Validate secret and config references.
3. Confirm command/entrypoint exists in image.
4. Check container logs for startup exception.
5. If unresolved, rollback to previous revision.

### 32.2 High Latency in Inference Path

1. Check TensorFlow Serving pod CPU/memory saturation.
2. Check app-to-serving network latency.
3. Confirm model size and loading strategy.
4. Increase serving replicas and retest.
5. Evaluate need for GPU serving pool.

### 32.3 Training Jobs Missing Schedule

1. Confirm CronJob exists and schedule syntax valid.
2. Inspect kube-controller-manager logs/events if available.
3. Ensure concurrency policy does not block due stuck job.
4. Verify namespace resource quotas allow job creation.
5. Manually trigger job to validate runtime path.

### 32.4 Terraform Apply Fails Midway

1. Identify failed resource and provider error.
2. Confirm API quotas and permissions.
3. Re-run `terraform plan` to inspect drift/partial state.
4. Apply targeted fix and then full reconciliation.
5. Document issue in infrastructure incident notes.

## 33. Architecture Principles and Non-Goals

### 33.1 Principles

- **Declarative-first**: operational state should be codified.
- **Least privilege**: runtime and deploy identities are scoped.
- **Repeatability**: dev/staging/prod use same conceptual topology.
- **Observability by default**: metrics/logs/traces are not optional.
- **Safe rollback**: every release should have a quick undo path.

### 33.2 Non-Goals (Current Phase)

- Full service mesh adoption.
- Fully automated canary analysis engine.
- Cross-region active-active serving.
- Multi-tenant policy isolation in a single cluster.

These can be added later without restructuring the baseline IaC layout.

## 34. Contribution Workflow for IaC Changes

When contributing infrastructure updates:

1. Update relevant IaC files with smallest viable change.
2. Validate templates/plan locally.
3. Update architecture or quick-start docs if behavior changes.
4. Include change rationale and rollback notes in PR description.
5. Ensure secrets are not committed.
6. Merge only after required checks and reviews pass.

This keeps the infrastructure codebase clean, auditable, and production-safe.

## 35. Closing Architecture Statement

AI-Morphasis 2.0 now has a complete infrastructure blueprint represented as code. The architecture is intentionally layered so each team can adopt the level of operational maturity it needs: local compose for rapid development, Kubernetes manifests for cluster consistency, Helm for release management, Terraform for cloud provisioning, and CI/CD templates for governance and automation. Monitoring, logging, and secrets-management templates ensure the platform can move beyond “deployable” into “operable.”

By maintaining this IaC structure alongside application code and tests, the project gains a repeatable path from idea to production, with explicit controls for scalability, reliability, and security. The artifacts created in this repository are designed to be executed, reviewed, and evolved—giving AI-Morphasis a durable foundation for production growth.

## Appendix A: Practical Command Reference

The following command reference is included so operators can execute common lifecycle tasks without searching across scripts and docs.

### A.1 Local Commands

```bash
# Start local stack
./infrastructure/scripts/setup-local.sh

# Stop local stack
cd infrastructure/docker && docker compose down

# Build image
./infrastructure/scripts/build-image.sh local
```

### A.2 Kubernetes Commands

```bash
# Deploy base manifests
./infrastructure/scripts/deploy-k8s.sh

# Inspect pods and services
kubectl -n ai-morphasis get pods,svc

# Trigger manual training
./infrastructure/scripts/train-model.sh

# Rollback deployment
./infrastructure/scripts/rollback.sh ai-morphasis ai-morphasis
```

### A.3 Terraform Commands

```bash
cd infrastructure/terraform
terraform init
terraform plan -var-file=../tfvars/dev.tfvars -var='cloud_provider=aws'
terraform apply -var-file=../tfvars/dev.tfvars -var='cloud_provider=aws'
```

### A.4 Helm Commands

```bash
# Install in dev mode
helm upgrade --install ai-morphasis infrastructure/helm -n ai-morphasis --create-namespace -f infrastructure/helm/values-dev.yaml

# Promote with prod values
helm upgrade --install ai-morphasis infrastructure/helm -n ai-morphasis -f infrastructure/helm/values-prod.yaml
```

### A.5 Validation Commands

```bash
# Render Helm templates
helm template ai-morphasis infrastructure/helm

# Client-side manifest validation
kubectl apply --dry-run=client -k infrastructure/kubernetes

# Terraform validate
cd infrastructure/terraform && terraform validate
```

These commands provide an immediate, executable baseline for deployment, troubleshooting, and platform validation.

## Appendix B: Final Production Readiness Checklist

- Infrastructure definitions exist for local, Kubernetes, and multi-cloud provisioning.
- Deployment artifacts include resource limits, probes, autoscaling, and rollback path.
- CI/CD templates include build, test, deploy, training, and security workflows.
- Monitoring and logging templates cover runtime, training, and infrastructure visibility.
- Secrets are template-based and designed for managed secret backends.
- Environment-specific tfvars provide predictable dev/staging/prod provisioning behavior.
- Documentation maps code integration points to runtime and operations workflows.

This checklist should be used during release readiness reviews and post-change audits.
