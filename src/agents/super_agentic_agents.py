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
    example_usage,
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
    "example_usage",
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
