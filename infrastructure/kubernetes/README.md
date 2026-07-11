# Kubernetes Deployment Guide

## Deploy base manifests
```bash
kubectl apply -k infrastructure/kubernetes
```

## Verify
```bash
kubectl -n ai-morphasis get pods,svc,hpa,cronjob
```

## Notes
- `secrets.yaml` is a template only.
- Override image tags and resource sizes per environment with Kustomize overlays or Helm.
