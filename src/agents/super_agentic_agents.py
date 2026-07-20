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

# Re-export everything from the package so that all existing imports continue
# to work without modification.
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
