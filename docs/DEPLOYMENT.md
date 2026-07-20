# Production Deployment Guide: Hardened Compatibility Shim

## Overview

The `src.agents.super_agentic_agents` module is a backward-compatibility shim that re-exports symbols from the modular `src.agents` package. This guide covers production deployment, configuration, migration, and troubleshooting.

**Status**: ✅ Production-Ready (v1.0.0+)  
**Deprecation Timeline**: v2.0.0 (Q4 2024) → v3.0.0+ (removal)

---

## Quick Start

### Default Behavior (Production-Safe)

By default, the shim operates in **graceful degradation mode**:
- ✅ Imports are non-blocking
- ✅ Partial failures are logged (not fatal)
- ✅ Application can start even if some modules are unavailable
- ✅ Validation is performed at startup but won't crash if it fails

```python
# This will NOT crash even if src.agents has issues
import src.agents.super_agentic_agents as shim

# Check if shim is healthy
if shim.is_shim_fully_functional():
    print("All symbols imported successfully")
else:
    print("Some symbols failed to import")
    errors = shim.get_import_errors()
    for symbol, exc in errors.items():
        print(f"  - {symbol}: {exc}")
```

### Strict Mode (CI/CD, Tests, Development)

For strict validation, enable strict mode:

```bash
export AGENT_SHIM_STRICT_MODE=true
python your_app.py
```

This will cause startup to **fail immediately** if any imports fail, which is useful for:
- CI/CD pipelines (catch errors early)
- Test environments (ensure clean state)
- Development (immediate feedback)

---

## Environment Variables

Configure shim behavior via environment variables:

| Variable | Default | Values | Purpose |
|----------|---------|--------|---------|
| `AGENT_SHIM_STRICT_MODE` | `false` | `true` / `false` | Hard-fail vs. graceful degradation |
| `AGENT_SHIM_VALIDATE_AT_IMPORT` | `true` | `true` / `false` | Run integrity checks on startup |
| `AGENT_SHIM_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Control logging verbosity |

### Example Configurations

**Production (Graceful)**
```bash
export AGENT_SHIM_STRICT_MODE=false
export AGENT_SHIM_VALIDATE_AT_IMPORT=true
export AGENT_SHIM_LOG_LEVEL=INFO
```

**Staging (Strict with Diagnostics)**
```bash
export AGENT_SHIM_STRICT_MODE=true
export AGENT_SHIM_VALIDATE_AT_IMPORT=true
export AGENT_SHIM_LOG_LEVEL=DEBUG
```

**Development (Skip Validation for Speed)**
```bash
export AGENT_SHIM_STRICT_MODE=false
export AGENT_SHIM_VALIDATE_AT_IMPORT=false
export AGENT_SHIM_LOG_LEVEL=DEBUG
```

---

## Health Checks and Monitoring

### Application Startup Health Check

```python
import src.agents.super_agentic_agents as shim

def health_check() -> dict:
    """Check shim health for Kubernetes probes or monitoring."""
    return {
        "functional": shim.is_shim_fully_functional(),
        "modules": shim.validate_all_modules(),
        "integrity": shim.validate_shim_integrity(raise_on_error=False),
        "errors": shim.get_import_errors(),
    }

# In your app initialization
status = health_check()
if not status["functional"]:
    logger.warning(f"Shim health check failed: {status['errors']}")
    # Optional: exit if critical
    if STRICT_MODE:
        raise RuntimeError(f"Shim initialization failed: {status['errors']}")
```

### Kubernetes Liveness/Readiness Probes

```python
from flask import Flask, jsonify
app = Flask(__name__)

@app.route("/health/live")
def liveness():
    """Liveness probe - is app running?"""
    return jsonify({"status": "alive"}), 200

@app.route("/health/ready")
def readiness():
    """Readiness probe - is shim functional?"""
    import src.agents.super_agentic_agents as shim
    
    if shim.is_shim_fully_functional():
        return jsonify({"status": "ready"}), 200
    else:
        return jsonify({
            "status": "not_ready",
            "errors": shim.get_import_errors()
        }), 503
```

### Prometheus Metrics

```python
from prometheus_client import Gauge, Counter

shim_functional = Gauge(
    "agent_shim_functional",
    "Whether shim is fully functional (1=yes, 0=no)"
)

shim_import_errors = Gauge(
    "agent_shim_import_errors_total",
    "Number of failed imports in shim"
)

def update_shim_metrics():
    """Update shim-related metrics."""
    import src.agents.super_agentic_agents as shim
    
    shim_functional.set(1 if shim.is_shim_fully_functional() else 0)
    shim_import_errors.set(len(shim.get_import_errors()))
```

---

## Migration Guide

The shim is **deprecated in v2.0.0** and will be **removed in v3.0.0+**.

### Step 1: Identify Legacy Imports

Find all files importing from the shim:

```bash
# Find all imports from super_agentic_agents
grep -r "from src.agents.super_agentic_agents import" .
grep -r "import src.agents.super_agentic_agents" .
```

### Step 2: Replace with Direct Imports

**Before (Legacy):**
```python
from src.agents.super_agentic_agents import (
    AgentSystem, Task, ExecutorAgent,
    RetryPolicy, TaskStatus
)
```

**After (Modern):**
```python
from src.agents import AgentSystem, Task, ExecutorAgent
from src.agents.models import RetryPolicy, TaskStatus
```

### Step 3: Update Your Code

For most cases, direct imports are a drop-in replacement:

```python
# Old way - still works but deprecated
from src.agents.super_agentic_agents import AgentSystem
system = AgentSystem("my-system")

# New way - recommended
from src.agents import AgentSystem
system = AgentSystem("my-system")
```

### Step 4: Run Tests

```bash
pytest tests/ -v
```

### Step 5: Verify No Deprecation Warnings

```python
import warnings

# Catch deprecation warnings during import
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    
    # Your imports here
    from src.agents import AgentSystem
    
    # Check for DeprecationWarnings
    for warning in w:
        if issubclass(warning.category, DeprecationWarning):
            print(f"❌ Still using deprecated import: {warning.message}")
            
if not any(issubclass(w.category, DeprecationWarning) for w in w):
    print("✅ All imports migrated successfully")
```

---

## Error Handling and Troubleshooting

### Problem: "shim partially loaded" Warning

**Symptoms:**
```
WARNING: Graceful degradation: shim partially loaded.
Use AGENT_SHIM_STRICT_MODE=true to fail fast instead.
```

**Diagnosis:**
```python
import src.agents.super_agentic_agents as shim

if not shim.is_shim_fully_functional():
    errors = shim.get_import_errors()
    for symbol, exc in errors.items():
        print(f"{symbol}: {exc}")
```

**Solutions:**
1. Check if `src.agents` package is installed
2. Verify all sub-modules are present:
   ```bash
   python -c "from src.agents import models, base, specialized, system, persistence, events, runtime"
   ```
3. Check for circular imports in your code
4. Enable debug logging to see detailed error trace

### Problem: "super_agentic_agents (strict mode): failed to import"

**Cause:** One or more symbols failed to import in strict mode.

**Solution:**
```bash
# Enable debug logging to see which symbols failed
export AGENT_SHIM_STRICT_MODE=false
export AGENT_SHIM_LOG_LEVEL=DEBUG
python your_app.py 2>&1 | grep -A 5 "Failed to import"
```

### Problem: DeprecationWarning on Import

**Expected:** This is normal and expected until you migrate away from the shim.

**Suppress (temporary):**
```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="src.agents.super_agentic_agents")

import src.agents.super_agentic_agents  # No warning
```

**Fix (permanent):** Migrate to direct imports (see Migration Guide above).

---

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
pytest tests/test_super_agentic_agents_hardened.py -v

# Specific test class
pytest tests/test_super_agentic_agents_hardened.py::TestHealthCheckHelpers -v

# With coverage
pytest tests/test_super_agentic_agents_hardened.py --cov=src.agents.super_agentic_agents
```

### Integration Tests

Test the shim in context:

```python
# tests/test_shim_integration.py
import os
import pytest

@pytest.mark.parametrize("strict_mode,should_fail", [
    ("true", True),
    ("false", False),
])
def test_shim_startup(strict_mode, should_fail):
    """Test shim behavior with different configurations."""
    os.environ["AGENT_SHIM_STRICT_MODE"] = strict_mode
    
    if should_fail:
        with pytest.raises(ImportError):
            import src.agents.super_agentic_agents
    else:
        import src.agents.super_agentic_agents
        assert src.agents.super_agentic_agents is not None
```

### Health Check Tests

```bash
# Test health endpoints
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/live
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Deploy

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: pip install -e .
      
      - name: Strict mode tests
        env:
          AGENT_SHIM_STRICT_MODE: "true"
          AGENT_SHIM_VALIDATE_AT_IMPORT: "true"
        run: pytest tests/test_super_agentic_agents_hardened.py -v

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy
        env:
          AGENT_SHIM_STRICT_MODE: "false"
          AGENT_SHIM_VALIDATE_AT_IMPORT: "true"
          AGENT_SHIM_LOG_LEVEL: "INFO"
        run: |
          docker build -t my-app .
          docker push my-app:latest
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

# Set production defaults
ENV AGENT_SHIM_STRICT_MODE=false
ENV AGENT_SHIM_VALIDATE_AT_IMPORT=true
ENV AGENT_SHIM_LOG_LEVEL=INFO

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import src.agents.super_agentic_agents as s; exit(0 if s.is_shim_fully_functional() else 1)"

CMD ["python", "-m", "your_app"]
```

---

## Performance Considerations

### Startup Time Impact

The shim adds minimal overhead:
- **Import**: ~5-10ms (one-time cost)
- **Validation**: ~20-50ms (only if `VALIDATE_AT_IMPORT=true`)
- **Total**: <100ms for typical deployments

To minimize impact in development:

```bash
export AGENT_SHIM_VALIDATE_AT_IMPORT=false  # Skip validation
```

### Memory Impact

- **Negligible**: The shim is a thin re-export layer
- **No additional objects**: All symbols point to the actual modules
- **Estimated overhead**: <1KB

---

## Rollout Strategy

### Phase 1: Enable Logging (Week 1)

```bash
export AGENT_SHIM_LOG_LEVEL=DEBUG
# Monitor for any import warnings
```

### Phase 2: Validate in Staging (Week 2-3)

```bash
export AGENT_SHIM_STRICT_MODE=true  # Staging/Dev only
export AGENT_SHIM_VALIDATE_AT_IMPORT=true
```

Verify health checks and monitoring:
```python
python -c "import src.agents.super_agentic_agents as s; print(s.validate_shim_integrity())"
```

### Phase 3: Deploy to Production (Week 4)

```bash
export AGENT_SHIM_STRICT_MODE=false      # Graceful degradation
export AGENT_SHIM_VALIDATE_AT_IMPORT=true # Still validate
export AGENT_SHIM_LOG_LEVEL=INFO          # Standard logging
```

### Phase 4: Monitor and Iterate (Ongoing)

- Track health check metrics
- Watch for any deprecation warnings in logs
- Plan migration timeline for each service
- Remove legacy imports gradually

---

## Checklist for Production Readiness

- [ ] Environment variables configured correctly
- [ ] Health check endpoints implemented
- [ ] Monitoring/metrics integrated
- [ ] Logging configured and tested
- [ ] Tests passing in strict mode
- [ ] Graceful degradation tested
- [ ] Documentation updated
- [ ] Runbooks prepared for on-call
- [ ] Migration plan created
- [ ] Team trained on new patterns

---

## Support and Questions

For issues or questions:

1. **Check the logs**: `AGENT_SHIM_LOG_LEVEL=DEBUG` for detailed diagnostics
2. **Run health checks**: Use `validate_shim_integrity()` to verify state
3. **Review migration guide**: See Migration Guide section above
4. **File an issue**: Include output from `get_import_errors()`

---

## References

- [Deprecation Timeline](#deprecation-timeline)
- [Migration Guide](#migration-guide)
- [GitHub Repository](https://github.com/Dj221981/Ai-morphasis-2.0-2)
- [Test Suite](../tests/test_super_agentic_agents_hardened.py)
