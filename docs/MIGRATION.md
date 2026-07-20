# Migration Guide: From super_agentic_agents Shim to Direct Imports

## Overview

The `src.agents.super_agentic_agents` module is a **backward-compatibility shim** that will be deprecated in **v2.0.0** and removed in **v3.0.0+**.

This guide helps you migrate your codebase to use direct imports from the `src.agents` package.

**Status**: The shim is fully functional and production-ready, but **new code should not use it**.

---

## Timeline

| Version | Status | Action |
|---------|--------|--------|
| **v1.x** | ✅ Maintained | Shim fully supported, no deprecation warnings (for now) |
| **v2.0.0** | ⚠️ Deprecated | DeprecationWarning emitted on import; shim still works |
| **v3.0.0+** | ❌ Removed | Shim will be deleted; direct imports required |

---

## Why Migrate?

### Benefits

- ✅ **Clearer imports**: Direct import source is explicit
- ✅ **Better IDE support**: Type hints work correctly without indirection
- ✅ **Smaller import chain**: Fewer re-export layers
- ✅ **Future-proof**: No deprecation warnings in v2.0.0+
- ✅ **Performance**: Negligible, but slightly faster startup

### Migration Effort

- **Low effort**: Most imports are drop-in replacements
- **No code changes**: Import statements are the only change needed
- **No breaking changes**: Direct imports have identical APIs
- **Gradual**: Migrate one file/module at a time

---

## Quick Reference: Import Mapping

### Models & Enums

| Shim Import | Direct Import |
|-------------|---------------|
| `from src.agents.super_agentic_agents import AgentRole` | `from src.agents.models import AgentRole` |
| `from src.agents.super_agentic_agents import AgentStatus` | `from src.agents.models import AgentStatus` |
| `from src.agents.super_agentic_agents import TaskPriority` | `from src.agents.models import TaskPriority` |
| `from src.agents.super_agentic_agents import TaskStatus` | `from src.agents.models import TaskStatus` |
| `from src.agents.super_agentic_agents import RetryPolicy` | `from src.agents.models import RetryPolicy` |
| `from src.agents.super_agentic_agents import ExecutionPolicy` | `from src.agents.models import ExecutionPolicy` |
| `from src.agents.super_agentic_agents import AgentCapability` | `from src.agents.models import AgentCapability` |
| `from src.agents.super_agentic_agents import AgentMemory` | `from src.agents.models import AgentMemory` |
| `from src.agents.super_agentic_agents import Task` | `from src.agents.models import Task` |

### Agent Classes

| Shim Import | Direct Import |
|-------------|---------------|
| `from src.agents.super_agentic_agents import BaseAgent` | `from src.agents.base import BaseAgent` |
| `from src.agents.super_agentic_agents import OrchestratorAgent` | `from src.agents.specialized import OrchestratorAgent` |
| `from src.agents.super_agentic_agents import ExecutorAgent` | `from src.agents.specialized import ExecutorAgent` |
| `from src.agents.super_agentic_agents import AnalyzerAgent` | `from src.agents.specialized import AnalyzerAgent` |
| `from src.agents.super_agentic_agents import LearnerAgent` | `from src.agents.specialized import LearnerAgent` |

### System & Factory

| Shim Import | Direct Import |
|-------------|---------------|
| `from src.agents.super_agentic_agents import AgentSystem` | `from src.agents.system import AgentSystem` |
| `from src.agents.super_agentic_agents import AgentFactory` | `from src.agents.system import AgentFactory` |

### Persistence

| Shim Import | Direct Import |
|-------------|---------------|
| `from src.agents.super_agentic_agents import TaskRepository` | `from src.agents.persistence import TaskRepository` |
| `from src.agents.super_agentic_agents import InMemoryTaskRepository` | `from src.agents.persistence import InMemoryTaskRepository` |
| `from src.agents.super_agentic_agents import SqlTaskRepository` | `from src.agents.persistence import SqlTaskRepository` |
| `from src.agents.super_agentic_agents import RedisTaskRepository` | `from src.agents.persistence import RedisTaskRepository` |

### Events

| Shim Import | Direct Import |
|-------------|---------------|
| `from src.agents.super_agentic_agents import TaskEventType` | `from src.agents.events import TaskEventType` |
| `from src.agents.super_agentic_agents import TaskEvent` | `from src.agents.events import TaskEvent` |
| `from src.agents.super_agentic_agents import InMemoryEventStore` | `from src.agents.events import InMemoryEventStore` |
| `from src.agents.super_agentic_agents import SqlEventStore` | `from src.agents.events import SqlEventStore` |
| `from src.agents.super_agentic_agents import RedisEventStore` | `from src.agents.events import RedisEventStore` |

### Runtime

| Shim Import | Direct Import |
|-------------|---------------|
| `from src.agents.super_agentic_agents import dispatch_pending_tasks` | `from src.agents.runtime import dispatch_pending_tasks` |
| `from src.agents.super_agentic_agents import process_retry_queue` | `from src.agents.runtime import process_retry_queue` |
| `from src.agents.super_agentic_agents import run_once` | `from src.agents.runtime import run_once` |
| `from src.agents.super_agentic_agents import run_forever` | `from src.agents.runtime import run_forever` |

### Convenience (Top-level src.agents)

Most common imports are available from `src.agents` directly:

```python
# All of these work:
from src.agents import AgentSystem, Task, ExecutorAgent
from src.agents import RetryPolicy, TaskStatus
from src.agents import InMemoryTaskRepository
from src.agents import run_once, run_forever
```

---

## Migration Checklist

### Step 1: Audit Existing Code

Find all shim imports:

```bash
# Search for shim imports
grep -r "from src.agents.super_agentic_agents import" . --include="*.py"
grep -r "import src.agents.super_agentic_agents" . --include="*.py"

# Count total imports to migrate
grep -r "from src.agents.super_agentic_agents import" . --include="*.py" | wc -l
```

### Step 2: Group Imports by Type

Create a list organized by destination module:

```
Models & Enums (→ src.agents.models):
  - src/myapp/config.py (5 imports)
  - src/myapp/tasks.py (8 imports)

Agent Classes (→ src.agents.{base,specialized}):
  - src/myapp/agents.py (12 imports)

System (→ src.agents.system):
  - src/myapp/main.py (2 imports)

Persistence (→ src.agents.persistence):
  - src/myapp/storage.py (4 imports)

Runtime (→ src.agents.runtime):
  - src/myapp/scheduler.py (3 imports)
```

### Step 3: Migrate by Module

Start with dependencies-first order:

1. **Models** (no dependencies)
2. **Persistence** (depends on models)
3. **Events** (depends on models)
4. **Base agent** (depends on models)
5. **Specialized agents** (depends on base)
6. **System** (depends on agents)
7. **Runtime** (depends on system)
8. **Your app** (depends on all above)

### Step 4: Update Imports

For each file, replace shim imports with direct imports.

### Step 5: Run Tests

```bash
# Run full test suite
pytest tests/ -v

# Check for deprecation warnings
pytest tests/ -W error::DeprecationWarning
```

### Step 6: Verify Clean Slate

```bash
# Should return 0 (no matches)
grep -r "from src.agents.super_agentic_agents import" . --include="*.py" | wc -l
```

---

## Step-by-Step Examples

### Example 1: Simple Single Import

**Before:**
```python
from src.agents.super_agentic_agents import AgentSystem

def create_system():
    return AgentSystem("my-system")
```

**After:**
```python
from src.agents import AgentSystem  # or: from src.agents.system import AgentSystem

def create_system():
    return AgentSystem("my-system")
```

### Example 2: Multiple Related Imports

**Before:**
```python
from src.agents.super_agentic_agents import (
    AgentSystem,
    ExecutorAgent,
    TaskStatus,
    RetryPolicy,
)

def setup():
    system = AgentSystem("my-system")
    agent = ExecutorAgent("executor")
    system.add_agent(agent)
```

**After:**
```python
from src.agents import AgentSystem, ExecutorAgent
from src.agents.models import TaskStatus, RetryPolicy

def setup():
    system = AgentSystem("my-system")
    agent = ExecutorAgent("executor")
    system.add_agent(agent)
```

Or using convenience imports:

```python
from src.agents import (
    AgentSystem,
    ExecutorAgent,
    TaskStatus,
    RetryPolicy,
)

def setup():
    system = AgentSystem("my-system")
    agent = ExecutorAgent("executor")
    system.add_agent(agent)
```

### Example 3: Comprehensive Application

**Before:**
```python
# src/myapp/main.py
from src.agents.super_agentic_agents import (
    AgentSystem,
    ExecutorAgent,
    AnalyzerAgent,
    Task,
    TaskStatus,
    RetryPolicy,
    InMemoryTaskRepository,
    run_forever,
)

def main():
    system = AgentSystem("app")
    repo = InMemoryTaskRepository()
    
    executor = ExecutorAgent("executor")
    analyzer = AnalyzerAgent("analyzer")
    
    system.add_agent(executor)
    system.add_agent(analyzer)
    
    task = Task(description="analyze data")
    # ... rest of app
    
    run_forever(system)

if __name__ == "__main__":
    main()
```

**After:**
```python
# src/myapp/main.py
from src.agents import (
    AgentSystem,
    ExecutorAgent,
    AnalyzerAgent,
    Task,
    run_forever,
)
from src.agents.models import RetryPolicy, TaskStatus
from src.agents.persistence import InMemoryTaskRepository

def main():
    system = AgentSystem("app")
    repo = InMemoryTaskRepository()
    
    executor = ExecutorAgent("executor")
    analyzer = AnalyzerAgent("analyzer")
    
    system.add_agent(executor)
    system.add_agent(analyzer)
    
    task = Task(description="analyze data")
    # ... rest of app
    
    run_forever(system)

if __name__ == "__main__":
    main()
```

---

## Advanced Migration Patterns

### Pattern 1: Gradual Module-by-Module Migration

For large codebases, migrate one module at a time:

```bash
# Migrate storage.py first (fewest dependencies)
# Then agents.py
# Then main.py (everything depends on it)
```

### Pattern 2: Git-Based Workflow

```bash
# Create a migration branch
git checkout -b refactor/remove-shim-imports

# Migrate and test
git add -p                          # Stage by file
pytest tests/

# Create atomic commits per module
git commit -m "Migrate src/myapp/storage.py to direct imports"
git commit -m "Migrate src/myapp/agents.py to direct imports"

# Create PR and get review
git push origin refactor/remove-shim-imports
```

### Pattern 3: Automated Migration (For Large Projects)

Use a search-and-replace script:

```python
#!/usr/bin/env python3
import re
import sys

mapping = {
    # Models
    r'from src\.agents\.super_agentic_agents import (\w+)': 
        lambda m: f'from src.agents.models import {m.group(1)}' if m.group(1) in ['AgentRole', 'AgentStatus', ...] else None,
    # Agents
    r'from src\.agents\.super_agentic_agents import ExecutorAgent': 
        'from src.agents.specialized import ExecutorAgent',
    # System
    r'from src\.agents\.super_agentic_agents import AgentSystem': 
        'from src.agents.system import AgentSystem',
}

for filepath in sys.argv[1:]:
    with open(filepath, 'r') as f:
        content = f.read()
    
    for pattern, replacement in mapping.items():
        if callable(replacement):
            content = re.sub(pattern, replacement, content)
        else:
            content = re.sub(pattern, replacement, content)
    
    with open(filepath, 'w') as f:
        f.write(content)

print("Migration complete!")
```

---

## Testing During Migration

### Pre-Migration

```bash
# Establish baseline
pytest tests/ -v --tb=short
```

### During Migration

After migrating each module:

```bash
# Test just that module
pytest tests/test_myapp_storage.py -v

# Check for import errors
python -c "import src.myapp.storage; print('OK')"

# Check for deprecation warnings
python -W error::DeprecationWarning -c "import src.myapp.storage"
```

### Post-Migration

```bash
# Full regression test
pytest tests/ -v

# Verify no remaining shim imports
grep -r "super_agentic_agents" . --include="*.py" && echo "FAIL: Shim imports remain" || echo "PASS: All imports migrated"

# Check no deprecation warnings
pytest tests/ -W error::DeprecationWarning
```

---

## Troubleshooting

### Problem: ImportError after Migration

**Error**: `ImportError: cannot import name 'X' from 'src.agents.models'`

**Solution**: Check the import mapping table. The symbol might be in a different module.

```bash
# Find where symbol is actually exported
grep -r "def X\|class X" src/agents/ --include="*.py"
```

### Problem: Circular Import After Migration

**Error**: `ImportError: cannot import X (circular import detected)`

**Solution**: Imports from `src.agents` should not create circular imports. If they do, check for:
1. Importing from app-level modules in agent code
2. Creating new circular dependencies in your app

**Fix**: Move imports to function scope or use `TYPE_CHECKING`:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.myapp.models import MyModel
```

### Problem: Type Hints Not Working After Migration

**Cause**: IDE might not have refreshed. Try:

```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Restart IDE/LSP
```

---

## Timeline for Your Team

### Week 1: Planning
- [ ] Audit current codebase
- [ ] Count total imports to migrate
- [ ] Create issue/epic for tracking
- [ ] Assign team members

### Week 2: Tools & Automation
- [ ] Create migration scripts (if needed)
- [ ] Set up testing for migration
- [ ] Document decisions in wiki/PR

### Week 3-4: Execution
- [ ] Migrate dependencies-first (models, persistence)
- [ ] Migrate agent definitions
- [ ] Migrate app code
- [ ] Full test suite passes

### Week 5: Verification
- [ ] All imports migrated
- [ ] No deprecation warnings
- [ ] Full regression testing
- [ ] Code review complete

---

## FAQ

**Q: Will direct imports break my code?**  
A: No. Direct imports have identical APIs and behavior.

**Q: Can I do a gradual migration?**  
A: Yes, absolutely. Migrate one file/module at a time.

**Q: When do I need to migrate?**  
A: Before v3.0.0 is released (estimated late 2024 or 2025).

**Q: What if I forget to migrate?**  
A: Your code will break in v3.0.0 when the shim is removed.

**Q: Can I suppress the deprecation warning for now?**  
A: Yes, but don't. Use it as a reminder to migrate.

```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
```

**Q: Is there performance impact?**  
A: No. Direct imports are slightly faster (no re-export layer).

---

## References

- [Deployment Guide](./DEPLOYMENT.md) - Production deployment and configuration
- [GitHub Repository](https://github.com/Dj221981/Ai-morphasis-2.0-2)
- [Test Suite](../tests/test_super_agentic_agents_hardened.py)

---

## Need Help?

1. **Check this guide** - Most questions answered above
2. **Review test examples** - See how direct imports are used
3. **File an issue** - Include your import statements and error messages
4. **Ask team** - Others have likely migrated similar patterns
