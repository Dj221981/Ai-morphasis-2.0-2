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
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import redis
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.pool import QueuePool, StaticPool

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


class SqlEventStore:
    """SQLAlchemy Core-backed durable event store."""

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
            "agent_task_events",
            self._metadata,
            Column("id", Text, primary_key=True),
            Column("task_id", Text, nullable=False),
            Column("event_type", Text, nullable=False),
            Column("agent_id", Text, nullable=True),
            Column("timestamp", DateTime, nullable=False),
            Column("attempt", Integer, nullable=False, default=0),
            Column("error", Text, nullable=True),
            Column("metadata_", Text, nullable=False),
        )
        self._metadata.create_all(self._engine)

    @staticmethod
    def _to_event(row: Dict) -> TaskEvent:
        timestamp = row["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return TaskEvent(
            id=row["id"],
            task_id=row["task_id"],
            event_type=TaskEventType(row["event_type"]),
            agent_id=row.get("agent_id"),
            timestamp=timestamp,
            attempt=int(row["attempt"]),
            error=row.get("error"),
            metadata=json.loads(row["metadata_"] or "{}"),
        )

    def append(self, event: TaskEvent) -> None:
        stmt = self._table.insert().values(
            id=event.id,
            task_id=event.task_id,
            event_type=event.event_type.value,
            agent_id=event.agent_id,
            timestamp=event.timestamp,
            attempt=event.attempt,
            error=event.error,
            metadata_=json.dumps(event.metadata),
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)

    def get_events_for_task(self, task_id: str) -> List[TaskEvent]:
        stmt = (
            select(self._table)
            .where(self._table.c.task_id == task_id)
            .order_by(self._table.c.timestamp.asc())
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [self._to_event(dict(row)) for row in rows]

    def get_all_events(self) -> List[TaskEvent]:
        stmt = select(self._table).order_by(self._table.c.timestamp.asc())
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [self._to_event(dict(row)) for row in rows]

    def filter_by_type(self, event_type: TaskEventType) -> List[TaskEvent]:
        stmt = select(self._table).where(self._table.c.event_type == event_type.value)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [self._to_event(dict(row)) for row in rows]

    def __len__(self) -> int:
        stmt = select(func.count()).select_from(self._table)
        with self._engine.connect() as conn:
            count = conn.execute(stmt).scalar_one()
        return int(count)

    def close(self) -> None:
        self._engine.dispose()

    def __repr__(self) -> str:
        return f"<SqlEventStore: {self._engine.url}>"


class RedisEventStore:
    """Redis-backed durable event store."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "agent:event:",
        max_events: Optional[int] = None,
    ) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix
        self._all_key = f"{key_prefix}all"
        self._task_key_prefix = f"{key_prefix}task:"
        self._max_events = max_events

    def _task_key(self, task_id: str) -> str:
        return f"{self._task_key_prefix}{task_id}"

    @staticmethod
    def _serialize(event: TaskEvent) -> str:
        return json.dumps(event.to_dict())

    @staticmethod
    def _deserialize(payload: str) -> TaskEvent:
        data = json.loads(payload)
        return TaskEvent(
            id=data["id"],
            task_id=data["task_id"],
            event_type=TaskEventType(data["event_type"]),
            agent_id=data.get("agent_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            attempt=int(data.get("attempt", 0)),
            error=data.get("error"),
            metadata=data.get("metadata") or {},
        )

    def append(self, event: TaskEvent) -> None:
        serialized = self._serialize(event)
        task_key = self._task_key(event.task_id)
        with self._client.pipeline() as pipe:
            pipe.rpush(self._all_key, serialized)
            pipe.rpush(task_key, serialized)
            if self._max_events is not None:
                pipe.ltrim(self._all_key, -self._max_events, -1)
            pipe.execute()

    def get_events_for_task(self, task_id: str) -> List[TaskEvent]:
        return [
            self._deserialize(item)
            for item in self._client.lrange(self._task_key(task_id), 0, -1)
        ]

    def get_all_events(self) -> List[TaskEvent]:
        return [self._deserialize(item) for item in self._client.lrange(self._all_key, 0, -1)]

    def filter_by_type(self, event_type: TaskEventType) -> List[TaskEvent]:
        return [e for e in self.get_all_events() if e.event_type == event_type]

    def __len__(self) -> int:
        return int(self._client.llen(self._all_key))

    def close(self) -> None:
        self._client.close()

    def __repr__(self) -> str:
        return f"<RedisEventStore: prefix={self._key_prefix}>"
