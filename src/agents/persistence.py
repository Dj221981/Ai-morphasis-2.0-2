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
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import redis
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    delete,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.pool import QueuePool, StaticPool

from .models import Task, TaskPriority, TaskStatus

logger = logging.getLogger(__name__)


def _to_priority(value: Any) -> TaskPriority:
    if isinstance(value, TaskPriority):
        return value
    if value in TaskPriority.__members__:
        return TaskPriority[str(value)]
    try:
        return TaskPriority(int(value))
    except (TypeError, ValueError):
        return TaskPriority.NORMAL


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


class SqlTaskRepository:
    """SQLAlchemy Core-backed durable task repository."""

    _DATETIME_FIELDS = (
        "created_at",
        "assigned_at",
        "started_at",
        "completed_at",
        "last_retry_at",
        "next_retry_at",
    )

    def __init__(
        self,
        database_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> None:
        if database_url.startswith("sqlite"):
            self._engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self._engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        self._metadata = MetaData()
        self._table = Table(
            "agent_tasks",
            self._metadata,
            Column("id", Text, primary_key=True),
            Column("description", Text, nullable=False),
            Column("priority", Text, nullable=False),
            Column("status", Text, nullable=False),
            Column("assigned_to", Text, nullable=True),
            Column("parameters", Text, nullable=False),
            Column("dependencies", Text, nullable=False),
            Column("metadata_", Text, nullable=False),
            Column("retry_count", Integer, nullable=False, default=0),
            Column("max_retries", Integer, nullable=False, default=3),
            Column("error", Text, nullable=True),
            Column("result", Text, nullable=True),
            Column("execution_metadata", Text, nullable=False),
            Column("created_at", DateTime, nullable=False),
            Column("assigned_at", DateTime, nullable=True),
            Column("started_at", DateTime, nullable=True),
            Column("completed_at", DateTime, nullable=True),
            Column("last_retry_at", DateTime, nullable=True),
            Column("next_retry_at", DateTime, nullable=True),
        )
        self._create_table()

    def _create_table(self) -> None:
        self._metadata.create_all(self._engine)

    @staticmethod
    def _to_iso(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    @staticmethod
    def _from_iso(value: Any) -> Optional[datetime]:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    def _serialize(self, task: Task) -> Dict[str, Any]:
        return {
            "id": task.id,
            "description": task.description,
            "priority": task.priority.name,
            "status": task.status.value,
            "assigned_to": task.assigned_to,
            "parameters": json.dumps(task.parameters),
            "dependencies": json.dumps(task.dependencies),
            "metadata_": json.dumps(task.metadata),
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "error": task.error,
            "result": (
                json.dumps(task.result) if task.result is not None else None
            ),
            "execution_metadata": json.dumps(task.execution_metadata),
            "created_at": self._to_iso(task.created_at),
            "assigned_at": self._to_iso(task.assigned_at),
            "started_at": self._to_iso(task.started_at),
            "completed_at": self._to_iso(task.completed_at),
            "last_retry_at": self._to_iso(task.last_retry_at),
            "next_retry_at": self._to_iso(task.next_retry_at),
        }

    def _normalize_for_sql(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(payload)
        for field in self._DATETIME_FIELDS:
            normalized[field] = self._from_iso(normalized[field])
        return normalized

    def _deserialize(self, row: Any) -> Task:
        data = dict(row)
        return Task(
            id=data["id"],
            description=data["description"],
            priority=_to_priority(data["priority"]),
            assigned_to=data.get("assigned_to"),
            status=TaskStatus(data["status"]),
            created_at=self._from_iso(data.get("created_at")) or datetime.now(),
            assigned_at=self._from_iso(data.get("assigned_at")),
            started_at=self._from_iso(data.get("started_at")),
            completed_at=self._from_iso(data.get("completed_at")),
            result=json.loads(data["result"]) if data.get("result") is not None else None,
            error=data.get("error"),
            parameters=json.loads(data.get("parameters") or "{}"),
            dependencies=json.loads(data.get("dependencies") or "[]"),
            metadata=json.loads(data.get("metadata_") or "{}"),
            retry_count=int(data.get("retry_count") or 0),
            max_retries=int(data.get("max_retries") or 3),
            last_retry_at=self._from_iso(data.get("last_retry_at")),
            next_retry_at=self._from_iso(data.get("next_retry_at")),
            execution_metadata=json.loads(data.get("execution_metadata") or "{}"),
        )

    def save_task(self, task: Task) -> None:
        payload = self._normalize_for_sql(self._serialize(task))
        dialect = self._engine.dialect.name
        with self._engine.begin() as conn:
            if dialect == "sqlite":
                stmt = self._table.insert().values(**payload).prefix_with("OR REPLACE")
                conn.execute(stmt)
            elif dialect in ("postgresql", "postgres"):
                stmt = pg_insert(self._table).values(**payload)
                update_cols = {
                    key: getattr(stmt.excluded, key)
                    for key in payload.keys()
                    if key != "id"
                }
                conn.execute(
                    stmt.on_conflict_do_update(
                        index_elements=[self._table.c.id],
                        set_=update_cols,
                    )
                )
            else:
                conn.execute(delete(self._table).where(self._table.c.id == task.id))
                conn.execute(self._table.insert().values(**payload))

    def get_task(self, task_id: str) -> Optional[Task]:
        stmt = select(self._table).where(self._table.c.id == task_id)
        with self._engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
        return self._deserialize(row) if row else None

    def list_pending_tasks(self) -> List[Task]:
        stmt = select(self._table).where(
            self._table.c.status.in_(
                [TaskStatus.PENDING.value, TaskStatus.RETRYING.value]
            )
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [self._deserialize(row) for row in rows]

    def list_all_tasks(self) -> List[Task]:
        stmt = select(self._table)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [self._deserialize(row) for row in rows]

    def delete_task(self, task_id: str) -> bool:
        stmt = delete(self._table).where(self._table.c.id == task_id)
        with self._engine.begin() as conn:
            result = conn.execute(stmt)
        return result.rowcount > 0

    def close(self) -> None:
        self._engine.dispose()

    def __repr__(self) -> str:
        return f"<SqlTaskRepository: {self._engine.url}>"


class RedisTaskRepository:
    """Redis-backed durable task repository."""

    _TERMINAL_STATUSES = {
        TaskStatus.COMPLETED.value,
        TaskStatus.FAILED.value,
        TaskStatus.CANCELLED.value,
    }

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "agent:task:",
        ttl_seconds: Optional[int] = None,
    ) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix
        self._index_key = f"{key_prefix}index"
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _to_iso(value: Optional[datetime]) -> str:
        return value.isoformat() if value else ""

    @staticmethod
    def _from_iso(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        return datetime.fromisoformat(value)

    def _task_key(self, task_id: str) -> str:
        return f"{self._key_prefix}{task_id}"

    def _serialize(self, task: Task) -> Dict[str, str]:
        return {
            "id": task.id,
            "description": task.description,
            "priority": task.priority.name,
            "status": task.status.value,
            "assigned_to": task.assigned_to or "",
            "parameters": json.dumps(task.parameters),
            "dependencies": json.dumps(task.dependencies),
            "metadata_": json.dumps(task.metadata),
            "retry_count": str(task.retry_count),
            "max_retries": str(task.max_retries),
            "error": task.error or "",
            "result": (
                json.dumps(task.result) if task.result is not None else ""
            ),
            "execution_metadata": json.dumps(task.execution_metadata),
            "created_at": self._to_iso(task.created_at),
            "assigned_at": self._to_iso(task.assigned_at),
            "started_at": self._to_iso(task.started_at),
            "completed_at": self._to_iso(task.completed_at),
            "last_retry_at": self._to_iso(task.last_retry_at),
            "next_retry_at": self._to_iso(task.next_retry_at),
        }

    def _deserialize(self, data: Dict[str, str]) -> Task:
        return Task(
            id=data["id"],
            description=data.get("description", ""),
            priority=_to_priority(data.get("priority")),
            assigned_to=data.get("assigned_to") or None,
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            created_at=self._from_iso(data.get("created_at")) or datetime.now(),
            assigned_at=self._from_iso(data.get("assigned_at")),
            started_at=self._from_iso(data.get("started_at")),
            completed_at=self._from_iso(data.get("completed_at")),
            result=(
                json.loads(data.get("result", "null"))
                if data.get("result")
                else None
            ),
            error=data.get("error") or None,
            parameters=json.loads(data.get("parameters", "{}")),
            dependencies=json.loads(data.get("dependencies", "[]")),
            metadata=json.loads(data.get("metadata_", "{}")),
            retry_count=int(data.get("retry_count", "0")),
            max_retries=int(data.get("max_retries", "3")),
            last_retry_at=self._from_iso(data.get("last_retry_at")),
            next_retry_at=self._from_iso(data.get("next_retry_at")),
            execution_metadata=json.loads(data.get("execution_metadata", "{}")),
        )

    def save_task(self, task: Task) -> None:
        payload = self._serialize(task)
        task_key = self._task_key(task.id)
        with self._client.pipeline() as pipe:
            pipe.hset(task_key, mapping=payload)
            created_at = self._from_iso(payload["created_at"]) or datetime.now()
            pipe.zadd(self._index_key, {task.id: created_at.timestamp()})
            if self._ttl_seconds and payload["status"] in self._TERMINAL_STATUSES:
                pipe.expire(task_key, self._ttl_seconds)
            elif self._ttl_seconds and self._client.ttl(task_key) > 0:
                pipe.persist(task_key)
            pipe.execute()

    def get_task(self, task_id: str) -> Optional[Task]:
        data = self._client.hgetall(self._task_key(task_id))
        return self._deserialize(data) if data else None

    def list_pending_tasks(self) -> List[Task]:
        tasks: List[Task] = []
        for task_id in self._client.zrange(self._index_key, 0, -1):
            task = self.get_task(task_id)
            if task and task.status in (TaskStatus.PENDING, TaskStatus.RETRYING):
                tasks.append(task)
        return tasks

    def list_all_tasks(self) -> List[Task]:
        tasks: List[Task] = []
        for task_id in self._client.zrange(self._index_key, 0, -1):
            task = self.get_task(task_id)
            if task is not None:
                tasks.append(task)
        return tasks

    def delete_task(self, task_id: str) -> bool:
        task_key = self._task_key(task_id)
        with self._client.pipeline() as pipe:
            pipe.delete(task_key)
            pipe.zrem(self._index_key, task_id)
            deleted, _ = pipe.execute()
        return bool(deleted)

    def close(self) -> None:
        self._client.close()

    def __repr__(self) -> str:
        return f"<RedisTaskRepository: prefix={self._key_prefix}>"
