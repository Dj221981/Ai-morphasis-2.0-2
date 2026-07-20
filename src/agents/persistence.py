"""
src/agents/persistence.py
==========================
Persistence abstractions for the super-agentic framework.

Provides:
- TaskRepository protocol (interface for any persistence backend)
- InMemoryTaskRepository (default in-process implementation)

Future implementations can provide:
- SqlTaskRepository (SQLAlchemy / asyncpg backed)
- RedisTaskRepository (Redis-backed with TTL)
"""

import threading
import logging
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .models import Task, TaskStatus

logger = logging.getLogger(__name__)


@runtime_checkable
class TaskRepository(Protocol):
    """Protocol for task persistence backends.

    Implementations must be thread-safe.  The default in-memory
    implementation is provided for development and testing.  Production
    deployments should swap this for a durable backend.
    """

    def save_task(self, task: Task) -> None:
        """Persist or update a task record."""
        ...

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID, or None if not found."""
        ...

    def list_pending_tasks(self) -> List[Task]:
        """Return all tasks in PENDING or RETRYING state."""
        ...

    def list_all_tasks(self) -> List[Task]:
        """Return all tasks regardless of state."""
        ...

    def delete_task(self, task_id: str) -> bool:
        """Delete a task record. Returns True if deleted, False if not found."""
        ...


class InMemoryTaskRepository:
    """Thread-safe in-memory task repository.

    Suitable for single-process deployments, testing, and development.
    Does not survive process restarts.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Task] = {}
        self._lock = threading.RLock()

    def save_task(self, task: Task) -> None:
        """Persist or update a task record."""
        with self._lock:
            self._store[task.id] = task
        logger.debug("InMemoryTaskRepository: saved task_id=%s status=%s", task.id, task.status.value)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID, or None if not found."""
        with self._lock:
            return self._store.get(task_id)

    def list_pending_tasks(self) -> List[Task]:
        """Return all tasks in PENDING or RETRYING state."""
        with self._lock:
            return [
                t for t in self._store.values()
                if t.status in (TaskStatus.PENDING, TaskStatus.RETRYING)
            ]

    def list_all_tasks(self) -> List[Task]:
        """Return all tasks regardless of state."""
        with self._lock:
            return list(self._store.values())

    def delete_task(self, task_id: str) -> bool:
        """Delete a task record. Returns True if deleted, False if not found."""
        with self._lock:
            if task_id in self._store:
                del self._store[task_id]
                logger.debug("InMemoryTaskRepository: deleted task_id=%s", task_id)
                return True
            return False

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __repr__(self) -> str:
        with self._lock:
            return f"<InMemoryTaskRepository: {len(self._store)} tasks>"
