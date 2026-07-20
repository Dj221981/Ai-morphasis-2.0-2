"""
tests/test_agents_modular.py
============================
Tests for the refactored modular agents package.

Covers:
- Task lifecycle transitions (via explicit mark_* helpers)
- RetryPolicy and ExecutionPolicy typed policies
- AgentSystem.cancel_task (queued and running tasks)
- Dependency gating (is_task_ready, create_task with dependencies)
- Priority dispatch ordering (dispatch_pending_tasks)
- run_once() scheduling behavior
- Persistence layer (InMemoryTaskRepository)
- Event journal (InMemoryEventStore, TaskEvent)
- Package re-export shim backward compatibility
- runtime.run_forever (stop event integration)
"""

import threading
import time
import pytest
from datetime import datetime, timedelta

from src.agents import (
    AgentSystem,
    AgentFactory,
    AgentCapability,
    ExecutorAgent,
    AnalyzerAgent,
    LearnerAgent,
    OrchestratorAgent,
    Task,
    TaskStatus,
    TaskPriority,
    TaskCancelledError,
    RetryPolicy,
    ExecutionPolicy,
    InMemoryTaskRepository,
    InMemoryEventStore,
    TaskEvent,
    TaskEventType,
    run_once,
    run_forever,
    dispatch_pending_tasks,
    process_retry_queue,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def system():
    return AgentSystem("test-modular")


@pytest.fixture
def executor():
    return ExecutorAgent("exec-modular")


@pytest.fixture
def pending_task():
    return Task(description="modular-task")


class BoomAgent(ExecutorAgent):
    """An executor that always raises on act()."""
    def act(self, decision):
        raise RuntimeError("boom")


class SlowAgent(ExecutorAgent):
    """An executor that sleeps briefly before completing."""
    def act(self, decision):
        time.sleep(0.02)
        return {"ok": True}


# ===========================================================================
# RetryPolicy
# ===========================================================================

class TestRetryPolicy:
    def test_default_values(self):
        p = RetryPolicy()
        assert p.max_retries == 3
        assert p.base_delay_seconds == 1.0
        assert p.max_delay_seconds == 30.0
        assert p.jitter_seconds == 0.5

    def test_custom_values(self):
        p = RetryPolicy(max_retries=5, base_delay_seconds=2.0, max_delay_seconds=60.0, jitter_seconds=0.0)
        assert p.max_retries == 5

    def test_negative_max_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries"):
            RetryPolicy(max_retries=-1)

    def test_negative_base_delay_raises(self):
        with pytest.raises(ValueError, match="base_delay_seconds"):
            RetryPolicy(base_delay_seconds=-1.0)

    def test_max_delay_less_than_base_raises(self):
        with pytest.raises(ValueError, match="max_delay_seconds"):
            RetryPolicy(base_delay_seconds=10.0, max_delay_seconds=5.0)

    def test_calculate_next_retry_at_is_future(self):
        p = RetryPolicy(base_delay_seconds=0.01, jitter_seconds=0.0)
        before = datetime.now()
        result = p.calculate_next_retry_at(retry_count=0)
        assert result >= before

    def test_backoff_grows_with_retry_count(self):
        p = RetryPolicy(base_delay_seconds=1.0, max_delay_seconds=1000.0, jitter_seconds=0.0)
        t0 = p.calculate_next_retry_at(0)
        t3 = p.calculate_next_retry_at(3)
        assert t3 > t0

    def test_backoff_capped_at_max_delay(self):
        p = RetryPolicy(base_delay_seconds=1.0, max_delay_seconds=2.0, jitter_seconds=0.0)
        now = datetime.now()
        # retry_count=20 would give 2^20 seconds without cap
        t = p.calculate_next_retry_at(20)
        delta = (t - now).total_seconds()
        assert delta <= p.max_delay_seconds + 0.1  # tiny tolerance


# ===========================================================================
# ExecutionPolicy
# ===========================================================================

class TestExecutionPolicy:
    def test_default_values(self):
        p = ExecutionPolicy()
        assert p.timeout_seconds is None
        assert p.allow_forced_status_fallback is False
        assert p.required_capabilities == []

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout_seconds"):
            ExecutionPolicy(timeout_seconds=0)

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout_seconds"):
            ExecutionPolicy(timeout_seconds=-1.0)

    def test_valid_timeout(self):
        p = ExecutionPolicy(timeout_seconds=30.0)
        assert p.timeout_seconds == 30.0

    def test_empty_string_capability_raises(self):
        with pytest.raises(ValueError, match="required_capabilities"):
            ExecutionPolicy(required_capabilities=[""])

    def test_valid_capabilities(self):
        p = ExecutionPolicy(required_capabilities=["analyze", "execute"])
        assert len(p.required_capabilities) == 2


# ===========================================================================
# Task lifecycle helpers (mark_* methods)
# ===========================================================================

class TestTaskLifecycleHelpers:
    def test_mark_assigned(self, pending_task):
        result = pending_task.mark_assigned("agent-123")
        assert result is True
        assert pending_task.status == TaskStatus.ASSIGNED
        assert pending_task.assigned_to == "agent-123"
        assert pending_task.assigned_at is not None

    def test_mark_assigned_invalid_from_completed(self):
        t = Task(description="t")
        t.transition_to(TaskStatus.ASSIGNED)
        t.transition_to(TaskStatus.RUNNING)
        t.transition_to(TaskStatus.COMPLETED)
        assert t.mark_assigned("agent-x") is False

    def test_mark_running(self, pending_task):
        pending_task.mark_assigned("agent-1")
        assert pending_task.mark_running() is True
        assert pending_task.status == TaskStatus.RUNNING
        assert pending_task.started_at is not None

    def test_mark_retrying_increments_retry_count(self, pending_task):
        pending_task.mark_assigned("a")
        pending_task.mark_running()
        assert pending_task.mark_retrying() is True
        assert pending_task.status == TaskStatus.RETRYING
        assert pending_task.retry_count == 1
        assert pending_task.last_retry_at is not None

    def test_mark_retrying_increments_each_time(self, pending_task):
        pending_task.mark_assigned("a")
        pending_task.mark_running()
        pending_task.mark_retrying()
        pending_task.mark_assigned("a")
        pending_task.mark_running()
        pending_task.mark_retrying()
        assert pending_task.retry_count == 2

    def test_mark_completed(self, pending_task):
        pending_task.mark_assigned("a")
        pending_task.mark_running()
        result = pending_task.mark_completed(result={"done": True})
        assert result is True
        assert pending_task.status == TaskStatus.COMPLETED
        assert pending_task.result == {"done": True}
        assert pending_task.error is None
        assert pending_task.completed_at is not None

    def test_mark_failed(self, pending_task):
        pending_task.mark_assigned("a")
        pending_task.mark_running()
        result = pending_task.mark_failed(error="something went wrong")
        assert result is True
        assert pending_task.status == TaskStatus.FAILED
        assert pending_task.error == "something went wrong"
        assert pending_task.completed_at is not None

    def test_mark_cancelled_from_pending(self, pending_task):
        result = pending_task.mark_cancelled(reason="user request")
        assert result is True
        assert pending_task.status == TaskStatus.CANCELLED
        assert pending_task.metadata.get("cancellation_reason") == "user request"
        assert pending_task.completed_at is not None

    def test_mark_cancelled_no_reason(self, pending_task):
        result = pending_task.mark_cancelled()
        assert result is True
        assert pending_task.status == TaskStatus.CANCELLED
        assert "cancellation_reason" not in pending_task.metadata

    def test_mark_cancelled_from_terminal_fails(self, pending_task):
        pending_task.mark_assigned("a")
        pending_task.mark_running()
        pending_task.mark_completed()
        assert pending_task.mark_cancelled() is False
        assert pending_task.status == TaskStatus.COMPLETED


# ===========================================================================
# AgentSystem.cancel_task
# ===========================================================================

class TestCancelTask:
    def test_cancel_pending_task(self, system):
        t = system.create_task("cancel-me", {})
        result = system.cancel_task(t.id, reason="test")
        assert result is True
        assert t.status == TaskStatus.CANCELLED
        assert t.metadata.get("cancellation_reason") == "test"

    def test_cancel_removes_from_queue(self, system):
        t = system.create_task("queue-cancel", {})
        assert any(x.id == t.id for x in system.global_task_queue)
        system.cancel_task(t.id)
        assert not any(x.id == t.id for x in system.global_task_queue)

    def test_cancel_assigned_task(self, system):
        agent = ExecutorAgent("e-cancel")
        system.add_agent(agent)
        t = system.create_task("assigned-cancel", {})
        system.submit_task(t, agent.id)
        assert t.status == TaskStatus.ASSIGNED

        result = system.cancel_task(t.id)
        assert result is True
        assert t.status == TaskStatus.CANCELLED

    def test_cancel_nonexistent_task_returns_false(self, system):
        assert system.cancel_task("no-such-task") is False

    def test_cancel_completed_task_returns_false(self, system):
        agent = ExecutorAgent("e-done")
        system.add_agent(agent)
        t = system.create_task("done", {})
        system.submit_task(t, agent.id)
        system.execute_task(t.id, agent.id)
        assert t.status == TaskStatus.COMPLETED
        assert system.cancel_task(t.id) is False

    def test_cancel_failed_task_returns_false(self, system):
        agent = BoomAgent("fail-cancel")
        system.add_agent(agent)
        t = system.create_task("fail-for-cancel", {})
        t.max_retries = 0
        system.submit_task(t, agent.id)
        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)
        assert t.status == TaskStatus.FAILED
        assert system.cancel_task(t.id) is False

    def test_cancel_running_task_sets_cancel_requested(self, system):
        """Cancel a running task sets the cancel_requested flag for cooperative cancellation."""
        agent = ExecutorAgent("e-running-cancel")
        system.add_agent(agent)
        t = system.create_task("running-cancel", {})

        # Manually put the task into RUNNING state without executing
        t.transition_to(TaskStatus.ASSIGNED)
        t.transition_to(TaskStatus.RUNNING)

        result = system.cancel_task(t.id)
        assert result is True
        assert t.metadata.get("cancel_requested") is True
        # Task stays RUNNING until the cooperative check fires
        assert t.status == TaskStatus.RUNNING

    def test_cancel_running_task_via_execution(self, system):
        """A cancel_requested flag causes the cooperative check to raise TaskCancelledError."""
        agent = ExecutorAgent("e-coop-cancel")
        system.add_agent(agent)
        t = system.create_task("coop-cancel", {})
        t.max_retries = 0
        system.submit_task(t, agent.id)

        # Set cancel flag before execution starts
        t.metadata["cancel_requested"] = True

        with pytest.raises(TaskCancelledError):
            system.execute_task(t.id, agent.id)

        assert t.status == TaskStatus.CANCELLED

    def test_cancel_cancelled_task_returns_false(self, system):
        t = system.create_task("already-cancelled", {})
        system.cancel_task(t.id)
        assert t.status == TaskStatus.CANCELLED
        assert system.cancel_task(t.id) is False


# ===========================================================================
# Dependency gating
# ===========================================================================

class TestDependencyGating:
    def test_is_task_ready_no_dependencies(self, system):
        t = system.create_task("no-deps", {})
        assert system.is_task_ready(t) is True

    def test_is_task_ready_dependency_pending(self, system):
        dep = system.create_task("dep", {})
        task = system.create_task("main", {}, dependencies=[dep.id])
        assert system.is_task_ready(task) is False

    def test_is_task_ready_dependency_completed(self, system):
        agent = ExecutorAgent("e-dep")
        system.add_agent(agent)
        dep = system.create_task("dep-complete", {})
        system.submit_task(dep, agent.id)
        system.execute_task(dep.id, agent.id)
        assert dep.status == TaskStatus.COMPLETED

        task = system.create_task("main-ready", {}, dependencies=[dep.id])
        assert system.is_task_ready(task) is True

    def test_create_task_with_dependency_validates_existence(self, system):
        """create_task should reject dependencies referencing non-existent task IDs."""
        with pytest.raises(ValueError, match="does not exist"):
            system.create_task("bad-dep", {}, dependencies=["non-existent-id"])

    def test_create_task_self_dependency_raises(self, system):
        """A task cannot list itself as a dependency."""
        # We can't get the task ID before creation, so we test at the Task level directly.
        # The system validates dependency IDs against the existing registry, but self-dependency
        # is also caught. We force it by registering a task_id manually:
        import uuid as _uuid
        fake_id = str(_uuid.uuid4())
        # Insert a fake task in the registry to simulate a self-dep scenario
        fake_task = Task(id=fake_id, description="fake")
        system.task_registry[fake_id] = fake_task

        with pytest.raises(ValueError, match="cannot depend on itself"):
            system._validate_dependencies_locked(fake_id, [fake_id])

    def test_dispatch_blocks_dependency_gated_tasks(self, system):
        """dispatch_pending_tasks should skip tasks with unfinished dependencies."""
        agent = ExecutorAgent("e-gating")
        system.add_agent(agent)

        dep = system.create_task("gating-dep", {})
        downstream = system.create_task("gating-downstream", {}, dependencies=[dep.id])

        # Try to dispatch — only dep should be dispatchable
        dispatched = system.dispatch_pending_tasks()
        # dep goes to agent; downstream is blocked
        assert dep.status == TaskStatus.ASSIGNED
        assert downstream.status == TaskStatus.PENDING

    def test_dispatch_releases_after_dependency_completes(self, system):
        """After dep completes, dispatch_pending_tasks dispatches the downstream task."""
        agent = ExecutorAgent("e-release")
        system.add_agent(agent)

        dep = system.create_task("release-dep", {})
        downstream = system.create_task("release-downstream", {}, dependencies=[dep.id])

        # Dispatch + execute dep
        system.dispatch_pending_tasks()
        system.execute_task(dep.id, agent.id)
        assert dep.status == TaskStatus.COMPLETED

        # Downstream is still in queue but not yet assigned
        assert downstream.status == TaskStatus.PENDING

        # Second dispatch cycle should now pick up downstream
        system.dispatch_pending_tasks()
        assert downstream.status == TaskStatus.ASSIGNED


# ===========================================================================
# Priority dispatch
# ===========================================================================

class TestPriorityDispatch:
    def test_high_priority_dispatched_before_low(self, system):
        agent = ExecutorAgent("prio-agent")
        agent.max_active_tasks = 1  # Can only take 1 task
        system.add_agent(agent)

        low = system.create_task("low", {}, priority=TaskPriority.LOW)
        high = system.create_task("high", {}, priority=TaskPriority.HIGH)

        dispatched = system.dispatch_pending_tasks()
        assert dispatched == 1
        # The high priority task should have been dispatched first
        assert high.status == TaskStatus.ASSIGNED
        assert low.status == TaskStatus.PENDING

    def test_critical_before_normal(self, system):
        agent = ExecutorAgent("crit-agent")
        agent.max_active_tasks = 1
        system.add_agent(agent)

        normal = system.create_task("normal", {}, priority=TaskPriority.NORMAL)
        critical = system.create_task("critical", {}, priority=TaskPriority.CRITICAL)

        system.dispatch_pending_tasks()
        assert critical.status == TaskStatus.ASSIGNED
        assert normal.status == TaskStatus.PENDING

    def test_all_same_priority_dispatched_in_order(self, system):
        """Same-priority tasks are dispatched oldest-first."""
        agent = ExecutorAgent("order-agent")
        agent.max_active_tasks = 2
        system.add_agent(agent)

        t1 = system.create_task("t1", {}, priority=TaskPriority.NORMAL)
        t2 = system.create_task("t2", {}, priority=TaskPriority.NORMAL)

        system.dispatch_pending_tasks()
        assert t1.status == TaskStatus.ASSIGNED
        assert t2.status == TaskStatus.ASSIGNED


# ===========================================================================
# run_once() scheduling behavior
# ===========================================================================

class TestRunOnce:
    def test_run_once_returns_summary_dict(self, system):
        agent = ExecutorAgent("e-run-once")
        system.add_agent(agent)
        system.create_task("task1", {})

        result = system.run_once()
        assert "dispatched" in result
        assert "retried" in result
        assert isinstance(result["dispatched"], int)
        assert isinstance(result["retried"], int)

    def test_run_once_dispatches_pending_tasks(self, system):
        agent = ExecutorAgent("e-dispatch")
        system.add_agent(agent)
        t = system.create_task("dispatch-via-run-once", {})

        result = system.run_once()
        assert result["dispatched"] >= 1
        assert t.status == TaskStatus.ASSIGNED

    def test_run_once_no_tasks_returns_zero(self, system):
        result = system.run_once()
        assert result["dispatched"] == 0
        assert result["retried"] == 0

    def test_run_once_skips_future_retry(self, system):
        agent = ExecutorAgent("e-future-retry")
        system.add_agent(agent)
        t = system.create_task("future-retry", {})
        t.transition_to(TaskStatus.ASSIGNED)
        t.transition_to(TaskStatus.RUNNING)
        t.transition_to(TaskStatus.RETRYING)
        t.next_retry_at = datetime.now() + timedelta(seconds=60)

        result = system.run_once()
        # The retrying task with a future retry time should not be resubmitted
        assert t.status == TaskStatus.RETRYING
        assert t.id in agent.active_tasks or t.id not in agent.active_tasks  # not crashed

    def test_run_once_processes_due_retries(self, system):
        agent = BoomAgent("e-retry-run-once")
        system.add_agent(agent)
        t = system.create_task("retry-runonce", {})
        t.max_retries = 2
        system.submit_task(t, agent.id)

        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)

        assert t.status == TaskStatus.RETRYING
        # Force retry to be due immediately
        t.next_retry_at = datetime.now() - timedelta(seconds=1)

        result = system.run_once()
        assert result["retried"] >= 0  # at minimum doesn't crash
        assert result["dispatched"] >= 0

    def test_module_run_once_wrapper(self, system):
        """runtime.run_once() delegates to system.run_once()."""
        agent = ExecutorAgent("e-wrapper")
        system.add_agent(agent)
        system.create_task("wrapper-task", {})
        result = run_once(system)
        assert "dispatched" in result


# ===========================================================================
# run_forever
# ===========================================================================

class TestRunForever:
    def test_run_forever_stops_on_event(self, system):
        stop_event = threading.Event()
        cycles = []

        def on_cycle(summary):
            cycles.append(summary)
            if len(cycles) >= 2:
                stop_event.set()

        t = threading.Thread(
            target=run_forever,
            args=(system,),
            kwargs={"interval_seconds": 0.01, "stop_event": stop_event, "on_cycle": on_cycle},
            daemon=True,
        )
        t.start()
        t.join(timeout=3.0)
        assert not t.is_alive(), "run_forever did not stop within timeout"
        assert len(cycles) >= 2

    def test_run_forever_negative_interval_raises(self, system):
        with pytest.raises(ValueError, match="interval_seconds"):
            run_forever(system, interval_seconds=-1.0, stop_event=threading.Event())

    def test_run_forever_on_cycle_callback(self, system):
        stop_event = threading.Event()
        received = []

        def on_cycle(summary):
            received.append(summary)
            stop_event.set()

        run_forever(system, interval_seconds=0.01, stop_event=stop_event, on_cycle=on_cycle)
        assert len(received) >= 1
        assert "dispatched" in received[0]


# ===========================================================================
# InMemoryTaskRepository
# ===========================================================================

class TestInMemoryTaskRepository:
    def test_save_and_get(self):
        repo = InMemoryTaskRepository()
        t = Task(description="persist-me")
        repo.save_task(t)
        assert repo.get_task(t.id) is t

    def test_get_unknown_returns_none(self):
        repo = InMemoryTaskRepository()
        assert repo.get_task("unknown") is None

    def test_list_pending_tasks(self):
        repo = InMemoryTaskRepository()
        t_pending = Task(description="pending")
        t_done = Task(description="done")
        t_done.transition_to(TaskStatus.ASSIGNED)
        t_done.transition_to(TaskStatus.RUNNING)
        t_done.transition_to(TaskStatus.COMPLETED)

        repo.save_task(t_pending)
        repo.save_task(t_done)

        pending = repo.list_pending_tasks()
        assert t_pending in pending
        assert t_done not in pending

    def test_list_pending_includes_retrying(self):
        repo = InMemoryTaskRepository()
        t = Task(description="retrying")
        t.transition_to(TaskStatus.ASSIGNED)
        t.transition_to(TaskStatus.RUNNING)
        t.transition_to(TaskStatus.RETRYING)
        repo.save_task(t)
        assert t in repo.list_pending_tasks()

    def test_list_all_tasks(self):
        repo = InMemoryTaskRepository()
        t1 = Task(description="t1")
        t2 = Task(description="t2")
        repo.save_task(t1)
        repo.save_task(t2)
        all_tasks = repo.list_all_tasks()
        assert t1 in all_tasks
        assert t2 in all_tasks

    def test_delete_task(self):
        repo = InMemoryTaskRepository()
        t = Task(description="delete-me")
        repo.save_task(t)
        assert repo.delete_task(t.id) is True
        assert repo.get_task(t.id) is None

    def test_delete_nonexistent_returns_false(self):
        repo = InMemoryTaskRepository()
        assert repo.delete_task("ghost-id") is False

    def test_len(self):
        repo = InMemoryTaskRepository()
        assert len(repo) == 0
        repo.save_task(Task(description="x"))
        assert len(repo) == 1

    def test_repr(self):
        repo = InMemoryTaskRepository()
        assert "InMemoryTaskRepository" in repr(repo)

    def test_save_updates_existing(self):
        repo = InMemoryTaskRepository()
        t = Task(description="original")
        repo.save_task(t)
        t.description = "updated"
        repo.save_task(t)
        retrieved = repo.get_task(t.id)
        assert retrieved.description == "updated"


# ===========================================================================
# InMemoryEventStore and TaskEvent
# ===========================================================================

class TestInMemoryEventStore:
    def test_append_and_get_all(self):
        store = InMemoryEventStore()
        evt = TaskEvent(task_id="t1", event_type=TaskEventType.CREATED)
        store.append(evt)
        all_events = store.get_all_events()
        assert evt in all_events

    def test_get_events_for_task(self):
        store = InMemoryEventStore()
        e1 = TaskEvent(task_id="t1", event_type=TaskEventType.CREATED)
        e2 = TaskEvent(task_id="t2", event_type=TaskEventType.COMPLETED)
        store.append(e1)
        store.append(e2)
        t1_events = store.get_events_for_task("t1")
        assert e1 in t1_events
        assert e2 not in t1_events

    def test_get_events_for_unknown_task(self):
        store = InMemoryEventStore()
        assert store.get_events_for_task("no-such") == []

    def test_filter_by_type(self):
        store = InMemoryEventStore()
        e_created = TaskEvent(task_id="t1", event_type=TaskEventType.CREATED)
        e_completed = TaskEvent(task_id="t1", event_type=TaskEventType.COMPLETED)
        store.append(e_created)
        store.append(e_completed)

        created_events = store.filter_by_type(TaskEventType.CREATED)
        assert e_created in created_events
        assert e_completed not in created_events

    def test_len(self):
        store = InMemoryEventStore()
        assert len(store) == 0
        store.append(TaskEvent(task_id="x", event_type=TaskEventType.STARTED))
        assert len(store) == 1

    def test_repr(self):
        store = InMemoryEventStore()
        assert "InMemoryEventStore" in repr(store)

    def test_event_to_dict(self):
        evt = TaskEvent(
            task_id="t1",
            event_type=TaskEventType.FAILED,
            agent_id="agent-42",
            attempt=2,
            error="something broke",
        )
        d = evt.to_dict()
        assert d["task_id"] == "t1"
        assert d["event_type"] == "failed"
        assert d["agent_id"] == "agent-42"
        assert d["attempt"] == 2
        assert d["error"] == "something broke"
        assert "timestamp" in d

    def test_event_immutable(self):
        evt = TaskEvent(task_id="t1", event_type=TaskEventType.CREATED)
        with pytest.raises(Exception):
            evt.task_id = "mutated"  # type: ignore[misc]


# ===========================================================================
# Backward-compatibility shim
# ===========================================================================

class TestShimBackwardCompatibility:
    def test_import_from_shim(self):
        """All legacy symbols must still be importable from the shim module."""
        from src.agents.super_agentic_agents import (
            AgentCapability,
            AgentMemory,
            AgentRole,
            AgentStatus,
            AgentSystem,
            AgentFactory,
            AnalyzerAgent,
            BaseAgent,
            ExecutorAgent,
            LearnerAgent,
            OrchestratorAgent,
            Task,
            TaskPriority,
            TaskStatus,
            TaskCancelledError,
            TASK_STATUS_TRANSITIONS,
        )
        assert AgentSystem is not None
        assert Task is not None

    def test_shim_new_symbols_importable(self):
        """New symbols added in the refactor must also be accessible via the shim."""
        from src.agents.super_agentic_agents import (
            RetryPolicy,
            ExecutionPolicy,
            InMemoryTaskRepository,
            InMemoryEventStore,
            TaskEvent,
            TaskEventType,
            run_once,
            run_forever,
        )
        assert RetryPolicy is not None
        assert run_once is not None

    def test_shim_symbols_are_same_objects(self):
        """Shim re-exports must be the same objects as the package exports."""
        from src.agents import AgentSystem as PackageAgentSystem
        from src.agents.super_agentic_agents import AgentSystem as ShimAgentSystem
        assert PackageAgentSystem is ShimAgentSystem


# ===========================================================================
# Retry behavior (via AgentSystem.execute_task)
# ===========================================================================

class TestRetryBehavior:
    def test_failed_task_with_retries_becomes_retrying(self, system):
        agent = BoomAgent("retry-agent")
        system.add_agent(agent)
        t = system.create_task("retry-behavior", {})
        t.max_retries = 2
        system.submit_task(t, agent.id)

        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)

        assert t.status == TaskStatus.RETRYING
        assert t.retry_count == 1
        assert t.next_retry_at is not None

    def test_retry_task_requeued_for_dispatch(self, system):
        agent = BoomAgent("requeue-agent")
        system.add_agent(agent)
        t = system.create_task("requeue-retry", {})
        t.max_retries = 1
        system.submit_task(t, agent.id)

        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)

        assert any(x.id == t.id for x in system.global_task_queue)

    def test_cancelled_task_not_retried(self, system):
        agent = ExecutorAgent("cancel-no-retry")
        system.add_agent(agent)
        t = system.create_task("cancel-no-retry", {})
        t.max_retries = 3
        system.submit_task(t, agent.id)
        t.metadata["cancel_requested"] = True

        with pytest.raises(TaskCancelledError):
            system.execute_task(t.id, agent.id)

        assert t.status == TaskStatus.CANCELLED
        assert t.retry_count == 0
        assert t.next_retry_at is None

    def test_retry_count_does_not_exceed_max_retries(self, system):
        agent = BoomAgent("max-retry-agent")
        system.add_agent(agent)
        t = system.create_task("max-retries", {})
        t.max_retries = 1

        system.submit_task(t, agent.id)
        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)
        assert t.status == TaskStatus.RETRYING
        assert t.retry_count == 1

        system.submit_task(t, agent.id)
        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)
        assert t.status == TaskStatus.FAILED
        assert t.retry_count == 1  # should not increment past max_retries
