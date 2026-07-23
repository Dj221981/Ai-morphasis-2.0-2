"""
src/agents/__init__.py
======================
Public API for the super-agentic agent framework package.

All public symbols are re-exported here so that callers can import from
either the top-level package::

    from src.agents import AgentSystem, Task, ExecutorAgent

or from specific sub-modules::

    from src.agents.models import RetryPolicy, ExecutionPolicy
    from src.agents.runtime import run_once, run_forever
    from src.agents.persistence import InMemoryTaskRepository
    from src.agents.events import InMemoryEventStore, TaskEvent

Backward compatibility is maintained by the ``super_agentic_agents`` shim
module which re-exports everything from this package.
"""

# Models / domain types
from .models import (
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
)

# Base class
from .base import BaseAgent

# Specialized agents
from .specialized import (
    OrchestratorAgent,
    ExecutorAgent,
    AnalyzerAgent,
    LearnerAgent,
)

# System orchestration
from .system import AgentSystem, AgentFactory

# Persistence layer
from .persistence import (
    TaskRepository,
    InMemoryTaskRepository,
    SqlTaskRepository,
    RedisTaskRepository,
)

# Event journal
from .events import (
    TaskEventType,
    TaskEvent,
    InMemoryEventStore,
    SqlEventStore,
    RedisEventStore,
)

# Runtime / scheduler
from .runtime import dispatch_pending_tasks, process_retry_queue, run_once, run_forever

__all__ = [
    # Enums
    "AgentRole",
    "AgentStatus",
    "TaskPriority",
    "TaskStatus",
    # Constants / tables
    "TASK_STATUS_TRANSITIONS",
    # Errors
    "TaskCancelledError",
    # Policy types
    "RetryPolicy",
    "ExecutionPolicy",
    # Domain models
    "AgentCapability",
    "AgentMemory",
    "Task",
    "CAPABILITY_MATCH_BASE_SCORE",
    "DEFAULT_AGENT_BASE_SCORE",
    # Agent classes
    "BaseAgent",
    "OrchestratorAgent",
    "ExecutorAgent",
    "AnalyzerAgent",
    "LearnerAgent",
    # System
    "AgentSystem",
    "AgentFactory",
    # Persistence
    "TaskRepository",
    "InMemoryTaskRepository",
    "SqlTaskRepository",
    "RedisTaskRepository",
    # Events
    "TaskEventType",
    "TaskEvent",
    "InMemoryEventStore",
    "SqlEventStore",
    "RedisEventStore",
    # Runtime
    "dispatch_pending_tasks",
    "process_retry_queue",
    "run_once",
    "run_forever",
]
