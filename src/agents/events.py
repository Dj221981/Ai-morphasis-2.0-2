"""
src/agents/events.py
====================
Task event journal for the super-agentic framework.

Provides:
- TaskEventType — enumeration of all lifecycle event types
- TaskEvent     — immutable record of a single lifecycle transition
- InMemoryEventStore — append-only in-process event store (dev/test)

The event store is designed to be replaceable with a durable backend
(Postgres table, Kafka topic, etc.) for production deployments.
"""

import uuid
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskEventType(Enum):
    """All observable task lifecycle events."""
    CREATED = "created"
    SUBMITTED = "submitted"
    ASSIGNED = "assigned"
    STARTED = "started"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CANCEL_REQUESTED = "cancel_requested"
    DEPENDENCY_BLOCKED = "dependency_blocked"
    DEPENDENCY_READY = "dependency_ready"


@dataclass(frozen=True)
class TaskEvent:
    """Immutable record of a single task lifecycle event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    event_type: TaskEventType = TaskEventType.CREATED
    agent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    attempt: int = 0
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize event to plain dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "event_type": self.event_type.value,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "attempt": self.attempt,
            "error": self.error,
            "metadata": self.metadata,
        }


class InMemoryEventStore:
    """Thread-safe append-only in-memory event store.

    Suitable for development, testing, and single-process deployments.
    Does not survive process restarts.
    """

    def __init__(self) -> None:
        self._events: List[TaskEvent] = []
        self._index: Dict[str, List[TaskEvent]] = {}  # task_id → events
        self._lock = threading.RLock()

    def append(self, event: TaskEvent) -> None:
        """Append a new event to the store."""
        with self._lock:
            self._events.append(event)
            self._index.setdefault(event.task_id, []).append(event)
        logger.debug(
            "EventStore: appended event_type=%s task_id=%s",
            event.event_type.value,
            event.task_id,
        )

    def get_events_for_task(self, task_id: str) -> List[TaskEvent]:
        """Return all events for a given task, ordered by insertion."""
        with self._lock:
            return list(self._index.get(task_id, []))

    def get_all_events(self) -> List[TaskEvent]:
        """Return all stored events, ordered by insertion."""
        with self._lock:
            return list(self._events)

    def filter_by_type(self, event_type: TaskEventType) -> List[TaskEvent]:
        """Return all events of a given type."""
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)

    def __repr__(self) -> str:
        with self._lock:
            return f"<InMemoryEventStore: {len(self._events)} events>"
