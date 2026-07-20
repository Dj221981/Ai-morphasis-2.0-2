"""
src/agents/super_agentic_agents.py
===================================
Backward-compatibility shim.

This module has been refactored into a modular package under ``src/agents/``.
All public symbols are re-exported from here so that existing imports continue
to work without modification::

    # Still works unchanged:
    from src.agents.super_agentic_agents import AgentSystem, Task, ExecutorAgent

For new code, prefer importing from the package directly::

    from src.agents import AgentSystem, Task, ExecutorAgent
    from src.agents.models import RetryPolicy, ExecutionPolicy
    from src.agents.runtime import run_once, run_forever
    from src.agents.persistence import InMemoryTaskRepository
    from src.agents.events import InMemoryEventStore, TaskEvent

Deprecation and lifecycle policy:
- This shim is maintained for backward compatibility and is not intended for
  feature growth.
- New code SHOULD import from ``src.agents`` (or submodules) directly.
- We MAY emit ``DeprecationWarning`` in a future minor release once migration
  guidance is broadly communicated.
- We SHOULD only consider removal in a future major release after at least one
  full minor-release deprecation window.
- Compatibility-only shims should remain behavior-preserving; changes should be
  limited to documentation and compatibility maintenance.

Security review / security considerations:
- This compatibility shim contains no direct input handling, I/O, subprocess,
  network, filesystem, authentication, authorization, or secret-management
  logic.
- Its security posture depends on the safety of the modules re-exported from
  ``src.agents``.
- Keep exports limited to intended public APIs to avoid unintentionally exposing
  internal or privileged functionality.
- Avoid re-exporting experimental, admin-only, or environment-specific helpers
  through this compatibility layer.
- When adding new exports, review whether they enable task execution, code
  execution, persistence access, or event access that should remain internal.
- Changes to this shim should stay documentation-oriented unless there is a
  deliberate compatibility requirement, so behavior is not altered unexpectedly.
"""

import sys

# ---------------------------------------------------------------------------
# Import guard: wrap the re-export block so that a missing or broken
# ``src.agents`` package produces a clear, actionable error instead of a
# bare ImportError with no context.
# ---------------------------------------------------------------------------
try:
    from src.agents import (  # noqa: F401  (re-export)
        AgentRole,
        AgentStatus,
        TaskPriority,
        TaskStatus,
        TASK_STATUS_TRANSITIONS,
        TaskCancelledError,
        RetryPolicy,
        ExecutionPolicy,
        AgentCapability,
        AgentMemory,
        Task,
        CAPABILITY_MATCH_BASE_SCORE,
        DEFAULT_AGENT_BASE_SCORE,
        BaseAgent,
        OrchestratorAgent,
        ExecutorAgent,
        AnalyzerAgent,
        LearnerAgent,
        AgentSystem,
        AgentFactory,
        TaskRepository,
        InMemoryTaskRepository,
        SqlTaskRepository,
        RedisTaskRepository,
        TaskEventType,
        TaskEvent,
        InMemoryEventStore,
        SqlEventStore,
        RedisEventStore,
        dispatch_pending_tasks,
        process_retry_queue,
        run_once,
        run_forever,
    )
except ImportError as exc:
    raise ImportError(
        "super_agentic_agents: failed to import one or more symbols from "
        "'src.agents'.  This usually means the package is not installed, a "
        "required sub-module is missing, or there is a circular import.  "
        f"Original error: {exc}"
    ) from exc
except Exception as exc:  # pragma: no cover — guards against unforeseen errors
    raise RuntimeError(
        "super_agentic_agents: unexpected error while importing 'src.agents'. "
        f"Original error: {exc}"
    ) from exc

__all__ = [
    "AgentRole",
    "AgentStatus",
    "TaskPriority",
    "TaskStatus",
    "TASK_STATUS_TRANSITIONS",
    "TaskCancelledError",
    "RetryPolicy",
    "ExecutionPolicy",
    "AgentCapability",
    "AgentMemory",
    "Task",
    "CAPABILITY_MATCH_BASE_SCORE",
    "DEFAULT_AGENT_BASE_SCORE",
    "BaseAgent",
    "OrchestratorAgent",
    "ExecutorAgent",
    "AnalyzerAgent",
    "LearnerAgent",
    "AgentSystem",
    "AgentFactory",
    "TaskRepository",
    "InMemoryTaskRepository",
    "SqlTaskRepository",
    "RedisTaskRepository",
    "TaskEventType",
    "TaskEvent",
    "InMemoryEventStore",
    "SqlEventStore",
    "RedisEventStore",
    "dispatch_pending_tasks",
    "process_retry_queue",
    "run_once",
    "run_forever",
]

# ---------------------------------------------------------------------------
# Public validation helpers
# ---------------------------------------------------------------------------

_REQUIRED_SUBMODULES = (
    "src.agents.models",
    "src.agents.base",
    "src.agents.specialized",
    "src.agents.system",
    "src.agents.persistence",
    "src.agents.events",
    "src.agents.runtime",
)


def validate_all_modules() -> None:
    """Check that every sub-module that backs this shim can be imported.

    Raises ``ImportError`` with a descriptive message naming the first
    sub-module that cannot be loaded.  Intended for use in health-checks,
    startup probes, and test suites.
    """
    import importlib

    for module_name in _REQUIRED_SUBMODULES:
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            raise ImportError(
                f"super_agentic_agents: required sub-module '{module_name}' "
                f"could not be imported.  Original error: {exc}"
            ) from exc


def validate_shim_integrity() -> None:
    """Verify that ``__all__`` is in sync with the symbols actually exported.

    Raises ``AssertionError`` if any name listed in ``__all__`` is absent from
    this module's namespace, or if the package (``src.agents``) is missing a
    symbol that the shim advertises.

    Also validates that every sub-module required by the shim is importable.
    """
    import importlib

    this_module = sys.modules[__name__]
    pkg_module = importlib.import_module("src.agents")

    missing_from_shim = [
        name for name in __all__ if not hasattr(this_module, name)
    ]
    if missing_from_shim:
        raise AssertionError(
            "super_agentic_agents.__all__ lists symbols that are not present "
            f"on the shim module: {missing_from_shim}"
        )

    missing_from_pkg = [
        name for name in __all__ if not hasattr(pkg_module, name)
    ]
    if missing_from_pkg:
        raise AssertionError(
            "super_agentic_agents.__all__ lists symbols that are not present "
            f"on src.agents: {missing_from_pkg}"
        )

    validate_all_modules()


# ---------------------------------------------------------------------------
# Startup verification — runs once when the shim is first imported so that
# deployment failures surface immediately rather than at first call-site use.
# ---------------------------------------------------------------------------
validate_shim_integrity()
