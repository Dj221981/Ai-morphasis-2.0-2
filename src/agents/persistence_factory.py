"""
src/agents/persistence_factory.py
=================================
Factory helpers that instantiate the correct persistence backend
based on environment variables.

Usage::

    from src.agents.persistence_factory import make_task_repository, make_event_store

    repo = make_task_repository()   # reads PERSISTENCE_BACKEND / DATABASE_URL / REDIS_URL
    store = make_event_store()
"""

import os

from .events import InMemoryEventStore, RedisEventStore, SqlEventStore
from .persistence import InMemoryTaskRepository, RedisTaskRepository, SqlTaskRepository


def _get_positive_int_env(name: str):
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def make_task_repository():
    """Return a task repository based on PERSISTENCE_BACKEND."""
    backend = os.getenv("PERSISTENCE_BACKEND", "sqlite").lower()
    if backend in ("sqlite", "postgres", "postgresql"):
        url = os.getenv("DATABASE_URL", "sqlite:///data/tasks.db")
        return SqlTaskRepository(database_url=url)
    if backend == "redis":
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        prefix = os.getenv("REDIS_KEY_PREFIX", "agent:task:")
        return RedisTaskRepository(
            redis_url=url,
            key_prefix=prefix,
            ttl_seconds=_get_positive_int_env("REDIS_TTL_SECONDS"),
        )
    return InMemoryTaskRepository()


def make_event_store():
    """Return an event store based on PERSISTENCE_BACKEND."""
    backend = os.getenv("PERSISTENCE_BACKEND", "sqlite").lower()
    if backend in ("sqlite", "postgres", "postgresql"):
        url = os.getenv("DATABASE_URL", "sqlite:///data/tasks.db")
        return SqlEventStore(database_url=url)
    if backend == "redis":
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        prefix = os.getenv("REDIS_KEY_PREFIX", "agent:event:")
        return RedisEventStore(
            redis_url=url,
            key_prefix=prefix,
            max_events=_get_positive_int_env("REDIS_MAX_EVENTS"),
        )
    return InMemoryEventStore()
