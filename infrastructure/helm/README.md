# Helm Chart Guide

Install:
```bash
helm upgrade --install ai-morphasis infrastructure/helm -n ai-morphasis --create-namespace
```

Dev values:
```bash
helm upgrade --install ai-morphasis infrastructure/helm -n ai-morphasis -f infrastructure/helm/values-dev.yaml
```

Prod values:
```bash
helm upgrade --install ai-morphasis infrastructure/helm -n ai-morphasis -f infrastructure/helm/values-prod.yaml
```
