"""
src/agents/models.py
====================
Core domain models for the super-agentic agent framework.

Contains:
- Enumerations: AgentRole, AgentStatus, TaskPriority, TaskStatus
- Policy dataclasses: RetryPolicy, ExecutionPolicy
- Data dataclasses: AgentCapability, AgentMemory, Task
- Error types: TaskCancelledError
- Constants and transition tables
"""

import uuid
import logging
import random
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# Module-level constants
# ============================================================================

CAPABILITY_MATCH_BASE_SCORE = 2.0
DEFAULT_AGENT_BASE_SCORE = 1.0


# ============================================================================
# Enumerations
# ============================================================================

class AgentRole(Enum):
    """Defines the role/purpose of an agent."""
    ORCHESTRATOR = "orchestrator"
    EXECUTOR = "executor"
    ANALYZER = "analyzer"
    LEARNER = "learner"
    SUPERVISOR = "supervisor"
    SPECIALIZED = "specialized"


class AgentStatus(Enum):
    """Tracks the operational status of an agent."""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    LEARNING = "learning"
    ERROR = "error"
    SUSPENDED = "suspended"


class TaskPriority(Enum):
    """Defines task execution priority levels."""
    CRITICAL = 5
    HIGH = 4
    NORMAL = 3
    LOW = 2
    DEFERRED = 1


class TaskStatus(Enum):
    """Defines valid task lifecycle states."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Guarded state transitions for task lifecycle
TASK_STATUS_TRANSITIONS: Dict[TaskStatus, set] = {
    TaskStatus.PENDING: {TaskStatus.ASSIGNED, TaskStatus.CANCELLED},
    TaskStatus.ASSIGNED: {TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.RETRYING, TaskStatus.CANCELLED},
    TaskStatus.RETRYING: {TaskStatus.ASSIGNED, TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


# ============================================================================
# Error types
# ============================================================================

class TaskCancelledError(RuntimeError):
    """Raised when task execution is cancelled."""


# ============================================================================
# Policy dataclasses (typed execution configuration)
# ============================================================================

@dataclass
class RetryPolicy:
    """Typed retry configuration for tasks."""
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    jitter_seconds: float = 0.5

    def __post_init__(self) -> None:
        if not isinstance(self.max_retries, int) or self.max_retries < 0:
            raise ValueError("RetryPolicy.max_retries must be a non-negative integer")
        if self.base_delay_seconds < 0:
            raise ValueError("RetryPolicy.base_delay_seconds must be non-negative")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError(
                "RetryPolicy.max_delay_seconds must be >= base_delay_seconds"
            )
        if self.jitter_seconds < 0:
            raise ValueError("RetryPolicy.jitter_seconds must be non-negative")

    def calculate_next_retry_at(self, retry_count: int) -> datetime:
        """Calculate the next retry timestamp using bounded exponential backoff + jitter."""
        retry_index = min(max(retry_count, 0), 16)
        backoff = min(self.base_delay_seconds * (2 ** retry_index), self.max_delay_seconds)
        jitter = random.uniform(0.0, max(self.jitter_seconds, 0.0))
        return datetime.now() + timedelta(seconds=backoff + jitter)


@dataclass
class ExecutionPolicy:
    """Typed execution configuration for tasks."""
    timeout_seconds: Optional[float] = None
    allow_forced_status_fallback: bool = False
    required_capabilities: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.timeout_seconds is not None:
            if not isinstance(self.timeout_seconds, (int, float)) or self.timeout_seconds <= 0:
                raise ValueError("ExecutionPolicy.timeout_seconds must be a positive number")
        for cap in self.required_capabilities:
            if not isinstance(cap, str) or not cap.strip():
                raise ValueError(
                    "ExecutionPolicy.required_capabilities must be a list of non-empty strings"
                )


# ============================================================================
# Core data dataclasses
# ============================================================================

@dataclass
class AgentCapability:
    """Represents a capability an agent can perform."""
    name: str
    description: str
    func: Optional[Callable] = None
    confidence_score: float = 1.0
    requires_resources: List[str] = field(default_factory=list)
    version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("AgentCapability name must not be empty")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("AgentCapability description must not be empty")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("AgentCapability version must not be empty")
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(
                f"AgentCapability confidence_score must be in [0.0, 1.0]; got {self.confidence_score}"
            )

    def __repr__(self) -> str:
        return f"<Capability: {self.name} v{self.version} ({self.confidence_score:.2%})>"


@dataclass
class AgentMemory:
    """Represents agent memory with episodic and semantic storage."""
    agent_id: str
    episodic_memory: Dict[str, Any] = field(default_factory=dict)  # Short-term
    semantic_memory: Dict[str, Any] = field(default_factory=dict)  # Long-term
    procedural_memory: Dict[str, Callable] = field(default_factory=dict)  # Skills
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    max_episodes: int = 1000

    def _touch(self, timestamp: Optional[datetime] = None) -> datetime:
        """Update and return last-access timestamp."""
        now = timestamp or datetime.now()
        self.last_accessed = now
        return now

    @staticmethod
    def _entry_timestamp_for_eviction(
        key: str,
        entry: Dict[str, Any],
        fallback_now: datetime,
    ) -> datetime:
        """Resolve a deterministic timestamp used for episodic eviction ordering."""
        timestamp = entry.get("timestamp")
        if isinstance(timestamp, datetime):
            return timestamp
        fallback = entry.get("last_accessed")
        if isinstance(fallback, datetime):
            logger.warning(
                "Episode %s is missing timestamp; using last_accessed fallback",
                key,
            )
            return fallback
        logger.warning(
            "Episode %s is missing timestamp metadata; using current time fallback",
            key,
        )
        return fallback_now

    def store_episode(self, key: str, value: Any) -> None:
        """Store an episode in short-term memory."""
        now = self._touch()
        if key not in self.episodic_memory and len(self.episodic_memory) >= self.max_episodes:
            # Existing-key updates do not increase cardinality, so no eviction is needed.
            # Remove oldest entry by explicit timestamp to make eviction deterministic.
            oldest_key = min(
                self.episodic_memory.items(),
                key=lambda item: self._entry_timestamp_for_eviction(item[0], item[1], now),
            )[0]
            del self.episodic_memory[oldest_key]
        self.episodic_memory[key] = {
            "value": value,
            "timestamp": now,
            "last_accessed": now,
        }

    def store_semantic(self, key: str, value: Any) -> None:
        """Store knowledge in long-term memory."""
        now = self._touch()
        self.semantic_memory[key] = {
            "value": value,
            "timestamp": now,
            "last_accessed": now,
            "access_count": 0,
        }

    def retrieve(self, key: str, memory_type: str = "auto") -> Optional[Any]:
        """Retrieve from memory (auto-selects best source)."""
        if memory_type in ("auto", "episodic") and key in self.episodic_memory:
            now = self._touch()
            self.episodic_memory[key]["last_accessed"] = now
            return self.episodic_memory[key]["value"]
        if memory_type in ("auto", "semantic") and key in self.semantic_memory:
            now = self._touch()
            self.semantic_memory[key]["access_count"] += 1
            self.semantic_memory[key]["last_accessed"] = now
            return self.semantic_memory[key]["value"]
        self._touch()
        return None


@dataclass
class Task:
    """Represents a task for agents to execute."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_to: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    last_retry_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)

    def transition_to(self, new_status: TaskStatus) -> bool:
        """Perform guarded task status transition."""
        allowed = TASK_STATUS_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            logger.warning(
                f"Invalid task status transition for {self.id}: {self.status.value} -> {new_status.value}"
            )
            return False

        self.status = new_status
        now = datetime.now()

        if new_status == TaskStatus.ASSIGNED:
            self.assigned_at = now
        elif new_status == TaskStatus.RUNNING:
            self.started_at = now
        elif new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            self.completed_at = now
        elif new_status == TaskStatus.RETRYING:
            self.last_retry_at = now

        return True

    # ------------------------------------------------------------------
    # Explicit lifecycle helpers (convenience wrappers around transition_to)
    # ------------------------------------------------------------------

    def mark_assigned(self, agent_id: str) -> bool:
        """Transition to ASSIGNED and record the assigned agent."""
        if not self.transition_to(TaskStatus.ASSIGNED):
            return False
        self.assigned_to = agent_id
        return True

    def mark_running(self) -> bool:
        """Transition to RUNNING."""
        return self.transition_to(TaskStatus.RUNNING)

    def mark_retrying(self) -> bool:
        """Transition to RETRYING and increment retry counter."""
        if not self.transition_to(TaskStatus.RETRYING):
            return False
        self.retry_count += 1
        return True

    def mark_completed(self, result: Any = None) -> bool:
        """Transition to COMPLETED and store result."""
        if not self.transition_to(TaskStatus.COMPLETED):
            return False
        self.result = result
        self.error = None
        return True

    def mark_failed(self, error: str = "") -> bool:
        """Transition to FAILED and store error message."""
        if not self.transition_to(TaskStatus.FAILED):
            return False
        self.error = error
        return True

    def mark_cancelled(self, reason: Optional[str] = None) -> bool:
        """Transition to CANCELLED and optionally store reason."""
        if not self.transition_to(TaskStatus.CANCELLED):
            return False
        if reason:
            self.metadata["cancellation_reason"] = reason
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority.name,
            "assigned_to": self.assigned_to,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "execution_metadata": self.execution_metadata,
        }
