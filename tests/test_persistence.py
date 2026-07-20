"""Persistence backend tests for task repositories and event stores."""

from datetime import datetime

import fakeredis
import pytest

from src.agents.events import (
    InMemoryEventStore,
    RedisEventStore,
    SqlEventStore,
    TaskEvent,
    TaskEventType,
)
from src.agents.models import Task, TaskPriority, TaskStatus
from src.agents.persistence import (
    InMemoryTaskRepository,
    RedisTaskRepository,
    SqlTaskRepository,
)
from src.agents.persistence_factory import make_event_store, make_task_repository


def _make_task(task_id: str, status: TaskStatus = TaskStatus.PENDING) -> Task:
    task = Task(
        id=task_id,
        description=f"task-{task_id}",
        priority=TaskPriority.NORMAL,
        status=status,
        parameters={"k": task_id},
        dependencies=["dep-1"],
        metadata={"m": task_id},
        execution_metadata={"x": True},
    )
    if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        task.completed_at = datetime.now()
    return task


@pytest.fixture
def sql_repo():
    repo = SqlTaskRepository("sqlite:///:memory:")
    yield repo
    repo.close()


@pytest.fixture
def sql_events():
    store = SqlEventStore("sqlite:///:memory:")
    yield store
    store.close()


@pytest.fixture
def fake_redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def redis_repo(monkeypatch, fake_redis_client):
    monkeypatch.setattr(
        "src.agents.persistence.redis.Redis.from_url",
        lambda *args, **kwargs: fake_redis_client,
    )
    repo = RedisTaskRepository(redis_url="redis://unused")
    yield repo
    repo.close()


@pytest.fixture
def redis_events(monkeypatch, fake_redis_client):
    monkeypatch.setattr(
        "src.agents.events.redis.Redis.from_url",
        lambda *args, **kwargs: fake_redis_client,
    )
    store = RedisEventStore(redis_url="redis://unused")
    yield store
    store.close()


@pytest.mark.parametrize(
    "repo_factory",
    [
        lambda: InMemoryTaskRepository(),
        lambda: SqlTaskRepository("sqlite:///:memory:"),
    ],
)
def test_task_repository_crud_and_upsert(repo_factory):
    repo = repo_factory()
    t1 = _make_task("t1")
    t2 = _make_task("t2", status=TaskStatus.RETRYING)
    t3 = _make_task("t3", status=TaskStatus.COMPLETED)

    repo.save_task(t1)
    repo.save_task(t2)
    repo.save_task(t3)

    assert repo.get_task("missing") is None
    assert repo.get_task("t1").description == "task-t1"
    assert {t.id for t in repo.list_pending_tasks()} == {"t1", "t2"}
    assert {t.id for t in repo.list_all_tasks()} == {"t1", "t2", "t3"}

    t1.description = "updated"
    repo.save_task(t1)
    assert repo.get_task("t1").description == "updated"

    assert repo.delete_task("t2") is True
    assert repo.delete_task("t2") is False

    if hasattr(repo, "close"):
        repo.close()


def test_sql_task_repository_close(sql_repo):
    sql_repo.close()


def test_redis_task_repository_crud_and_upsert(redis_repo):
    t1 = _make_task("rt1")
    t2 = _make_task("rt2", status=TaskStatus.RETRYING)
    redis_repo.save_task(t1)
    redis_repo.save_task(t2)

    assert redis_repo.get_task("missing") is None
    assert {t.id for t in redis_repo.list_pending_tasks()} == {"rt1", "rt2"}
    assert {t.id for t in redis_repo.list_all_tasks()} == {"rt1", "rt2"}

    t1.description = "updated"
    redis_repo.save_task(t1)
    assert redis_repo.get_task("rt1").description == "updated"

    assert redis_repo.delete_task("rt1") is True
    assert redis_repo.delete_task("rt1") is False


def test_redis_task_repository_applies_ttl(monkeypatch, fake_redis_client):
    monkeypatch.setattr(
        "src.agents.persistence.redis.Redis.from_url",
        lambda *args, **kwargs: fake_redis_client,
    )
    repo = RedisTaskRepository(redis_url="redis://unused", ttl_seconds=300)
    task = _make_task("ttl-task")
    repo.save_task(task)
    assert repo._client.ttl(repo._task_key(task.id)) == -1

    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now()
    repo.save_task(task)
    assert repo._client.ttl(repo._task_key(task.id)) > 0
    repo.close()


@pytest.mark.parametrize(
    "store_factory",
    [
        lambda: InMemoryEventStore(),
        lambda: SqlEventStore("sqlite:///:memory:"),
    ],
)
def test_event_store_interface(store_factory):
    store = store_factory()
    e1 = TaskEvent(task_id="t1", event_type=TaskEventType.CREATED)
    e2 = TaskEvent(task_id="t1", event_type=TaskEventType.COMPLETED)
    e3 = TaskEvent(task_id="t2", event_type=TaskEventType.FAILED)

    store.append(e1)
    store.append(e2)
    store.append(e3)

    assert [e.task_id for e in store.get_events_for_task("t1")] == ["t1", "t1"]
    assert len(store.get_all_events()) == 3
    assert [e.event_type for e in store.filter_by_type(TaskEventType.FAILED)] == [
        TaskEventType.FAILED
    ]
    assert len(store) == 3

    if hasattr(store, "close"):
        store.close()


def test_redis_event_store_interface(redis_events):
    e1 = TaskEvent(task_id="r1", event_type=TaskEventType.CREATED)
    e2 = TaskEvent(task_id="r1", event_type=TaskEventType.COMPLETED)
    e3 = TaskEvent(task_id="r2", event_type=TaskEventType.FAILED)
    redis_events.append(e1)
    redis_events.append(e2)
    redis_events.append(e3)

    assert [e.task_id for e in redis_events.get_events_for_task("r1")] == ["r1", "r1"]
    assert len(redis_events.get_all_events()) == 3
    assert [e.event_type for e in redis_events.filter_by_type(TaskEventType.FAILED)] == [
        TaskEventType.FAILED
    ]
    assert len(redis_events) == 3


def test_redis_event_store_max_events(monkeypatch, fake_redis_client):
    monkeypatch.setattr(
        "src.agents.events.redis.Redis.from_url",
        lambda *args, **kwargs: fake_redis_client,
    )
    store = RedisEventStore(redis_url="redis://unused", max_events=2)
    store.append(TaskEvent(task_id="x", event_type=TaskEventType.CREATED))
    store.append(TaskEvent(task_id="x", event_type=TaskEventType.STARTED))
    store.append(TaskEvent(task_id="x", event_type=TaskEventType.COMPLETED))
    assert len(store.get_all_events()) == 2
    store.close()


@pytest.mark.parametrize(
    "backend, expected_task_repo, expected_event_store",
    [
        ("sqlite", SqlTaskRepository, SqlEventStore),
        ("postgres", SqlTaskRepository, SqlEventStore),
        ("postgresql", SqlTaskRepository, SqlEventStore),
        ("memory", InMemoryTaskRepository, InMemoryEventStore),
    ],
)
def test_factory_backends(monkeypatch, backend, expected_task_repo, expected_event_store):
    monkeypatch.setenv("PERSISTENCE_BACKEND", backend)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    task_repo = make_task_repository()
    event_store = make_event_store()
    assert isinstance(task_repo, expected_task_repo)
    assert isinstance(event_store, expected_event_store)

    if hasattr(task_repo, "close"):
        task_repo.close()
    if hasattr(event_store, "close"):
        event_store.close()


def test_factory_redis(monkeypatch, fake_redis_client):
    monkeypatch.setattr(
        "src.agents.persistence.redis.Redis.from_url",
        lambda *args, **kwargs: fake_redis_client,
    )
    monkeypatch.setattr(
        "src.agents.events.redis.Redis.from_url",
        lambda *args, **kwargs: fake_redis_client,
    )
    monkeypatch.setenv("PERSISTENCE_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://unused")
    monkeypatch.setenv("REDIS_KEY_PREFIX", "agent:test:")
    monkeypatch.setenv("REDIS_TTL_SECONDS", "123")
    monkeypatch.setenv("REDIS_MAX_EVENTS", "42")

    task_repo = make_task_repository()
    event_store = make_event_store()
    assert isinstance(task_repo, RedisTaskRepository)
    assert isinstance(event_store, RedisEventStore)
    task_repo.close()
    event_store.close()
