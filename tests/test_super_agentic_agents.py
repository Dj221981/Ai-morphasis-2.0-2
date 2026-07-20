"""
Unit tests for src/agents/super_agentic_agents.py

Covers:
- Task state-transition model (valid/invalid transitions, timestamps)
- AgentMemory (store, retrieve, FIFO eviction, semantic access_count)
- BaseAgent behaviour via ExecutorAgent
  - capability registration and limit enforcement
  - task assignment (capacity, state validation)
  - successful task execution path
  - failed task execution path (retry transitions, failure transitions)
  - _force_task_status fallback helper
  - active-task cleanup in finally block
- OrchestratorAgent (register_agent, _select_best_agent, distribute_task)
- AgentSystem
  - add_agent / remove_agent (including relationship cleanup)
  - create_task (validates empty description)
  - submit_task
  - execute_task (success/failure system metrics, retry requeue deduplication)
- AgentFactory (create_agent, create_team)
- AgentCapability validation (__post_init__)
"""

import pytest
import time
from unittest.mock import patch
from datetime import datetime, timedelta

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
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def task():
    return Task(description="test task")


@pytest.fixture
def executor():
    return ExecutorAgent("exec-1")


@pytest.fixture
def system():
    return AgentSystem("test-system")


def _always_cancel(_task):
    return True


# ---------------------------------------------------------------------------
# AgentCapability validation
# ---------------------------------------------------------------------------

class TestAgentCapabilityValidation:
    def test_valid_capability(self):
        cap = AgentCapability(name="cap", description="desc", confidence_score=0.5)
        assert cap.name == "cap"
        assert cap.confidence_score == 0.5

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name must not be empty"):
            AgentCapability(name="", description="desc")

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError, match="name must not be empty"):
            AgentCapability(name="   ", description="desc")

    def test_confidence_score_below_zero_raises(self):
        with pytest.raises(ValueError, match="confidence_score"):
            AgentCapability(name="cap", description="desc", confidence_score=-0.1)

    def test_confidence_score_above_one_raises(self):
        with pytest.raises(ValueError, match="confidence_score"):
            AgentCapability(name="cap", description="desc", confidence_score=1.1)

    def test_confidence_score_boundary_values(self):
        cap_low = AgentCapability(name="c1", description="d", confidence_score=0.0)
        cap_high = AgentCapability(name="c2", description="d", confidence_score=1.0)
        assert cap_low.confidence_score == 0.0
        assert cap_high.confidence_score == 1.0

    def test_empty_description_raises(self):
        with pytest.raises(ValueError, match="description must not be empty"):
            AgentCapability(name="cap", description="")

    def test_empty_version_raises(self):
        with pytest.raises(ValueError, match="version must not be empty"):
            AgentCapability(name="cap", description="desc", version=" ")


# ---------------------------------------------------------------------------
# Task state transitions
# ---------------------------------------------------------------------------

class TestTaskTransitions:
    def test_pending_to_assigned(self, task):
        assert task.transition_to(TaskStatus.ASSIGNED) is True
        assert task.status == TaskStatus.ASSIGNED
        assert task.assigned_at is not None

    def test_assigned_to_running(self, task):
        task.transition_to(TaskStatus.ASSIGNED)
        assert task.transition_to(TaskStatus.RUNNING) is True
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    def test_running_to_completed(self, task):
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        assert task.transition_to(TaskStatus.COMPLETED) is True
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_running_to_retrying(self, task):
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        assert task.transition_to(TaskStatus.RETRYING) is True
        assert task.status == TaskStatus.RETRYING
        assert task.last_retry_at is not None

    def test_running_to_failed(self, task):
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        assert task.transition_to(TaskStatus.FAILED) is True
        assert task.status == TaskStatus.FAILED
        assert task.completed_at is not None

    def test_invalid_pending_to_completed(self, task):
        assert task.transition_to(TaskStatus.COMPLETED) is False
        assert task.status == TaskStatus.PENDING

    def test_invalid_pending_to_running(self, task):
        assert task.transition_to(TaskStatus.RUNNING) is False

    def test_completed_is_terminal(self, task):
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.COMPLETED)
        assert task.transition_to(TaskStatus.RUNNING) is False
        assert task.status == TaskStatus.COMPLETED

    def test_failed_is_terminal(self, task):
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.FAILED)
        assert task.transition_to(TaskStatus.RETRYING) is False

    def test_retrying_to_running(self, task):
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.RETRYING)
        assert task.transition_to(TaskStatus.RUNNING) is True

    def test_pending_to_cancelled(self, task):
        assert task.transition_to(TaskStatus.CANCELLED) is True
        assert task.completed_at is not None

    def test_to_dict_roundtrip(self, task):
        d = task.to_dict()
        assert d["status"] == "pending"
        assert d["description"] == "test task"
        assert d["retry_count"] == 0


# ---------------------------------------------------------------------------
# AgentMemory
# ---------------------------------------------------------------------------

class TestAgentMemory:
    def test_store_and_retrieve_episodic(self):
        mem = AgentMemory(agent_id="a1")
        mem.store_episode("k1", "v1")
        assert mem.retrieve("k1", "episodic") == "v1"

    def test_retrieve_missing_key_returns_none(self):
        mem = AgentMemory(agent_id="a1")
        assert mem.retrieve("nope") is None

    def test_fifo_eviction(self):
        mem = AgentMemory(agent_id="a1", max_episodes=2)
        mem.store_episode("k1", "v1")
        mem.store_episode("k2", "v2")
        mem.store_episode("k3", "v3")

        assert mem.retrieve("k1", "episodic") is None  # evicted
        assert mem.retrieve("k2", "episodic") == "v2"
        assert mem.retrieve("k3", "episodic") == "v3"

    def test_store_semantic(self):
        mem = AgentMemory(agent_id="a1")
        mem.store_semantic("fact1", "Earth is round")
        assert mem.retrieve("fact1", "semantic") == "Earth is round"

    def test_semantic_access_count_increments(self):
        mem = AgentMemory(agent_id="a1")
        mem.store_semantic("fact1", "value")
        mem.retrieve("fact1", "semantic")
        mem.retrieve("fact1", "semantic")
        assert mem.semantic_memory["fact1"]["access_count"] == 2

    def test_auto_mode_prefers_episodic(self):
        mem = AgentMemory(agent_id="a1")
        mem.store_episode("k", "episodic_val")
        mem.store_semantic("k", "semantic_val")
        assert mem.retrieve("k", "auto") == "episodic_val"

    def test_store_and_retrieve_update_access_timestamps(self):
        mem = AgentMemory(agent_id="a1")
        first_access = mem.last_accessed

        mem.store_semantic("fact", "value")
        assert mem.last_accessed >= first_access
        stored_access = mem.semantic_memory["fact"]["last_accessed"]

        time.sleep(0.001)
        mem.retrieve("fact", "semantic")
        assert mem.last_accessed >= stored_access
        assert mem.semantic_memory["fact"]["last_accessed"] >= stored_access


# ---------------------------------------------------------------------------
# BaseAgent / ExecutorAgent
# ---------------------------------------------------------------------------

class TestBaseAgent:
    def test_empty_agent_name_raises(self):
        with pytest.raises(ValueError, match="Agent name must be a non-empty string"):
            ExecutorAgent("   ")

    def test_register_capability(self, executor):
        cap = AgentCapability(name="run", description="run stuff")
        assert executor.register_capability(cap) is True
        assert "run" in executor.capabilities

    def test_capability_limit_enforced(self):
        agent = ExecutorAgent("limited")
        agent.max_capabilities = 2
        agent.register_capability(AgentCapability(name="c1", description="d"))
        agent.register_capability(AgentCapability(name="c2", description="d"))
        assert agent.register_capability(AgentCapability(name="c3", description="d")) is False
        assert len(agent.capabilities) == 2

    def test_assign_pending_task(self, executor, task):
        assert executor.assign_task(task) is True
        assert task.status == TaskStatus.ASSIGNED
        assert task.id in executor.active_tasks

    def test_assign_retrying_task(self, executor, task):
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.RETRYING)
        assert executor.assign_task(task) is True
        assert task.id in executor.active_tasks

    def test_assign_rejected_at_capacity(self):
        agent = ExecutorAgent("capped")
        agent.max_active_tasks = 1
        t1 = Task(description="t1")
        t2 = Task(description="t2")
        agent.assign_task(t1)
        assert agent.assign_task(t2) is False

    def test_assign_rejected_invalid_state(self, executor, task):
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.COMPLETED)
        assert executor.assign_task(task) is False

    def test_get_status_shape(self, executor):
        status = executor.get_status()
        for key in ("id", "name", "role", "status", "capabilities",
                    "active_tasks", "completed_tasks", "performance"):
            assert key in status

    def test_successful_execution(self, executor, task):
        executor.assign_task(task)
        result = executor.execute_task(task)

        assert task.status == TaskStatus.COMPLETED
        assert result["execution"] == "successful"
        assert executor.performance_metrics["tasks_completed"] == 1
        assert executor.performance_metrics["tasks_failed"] == 0
        assert task.id not in executor.active_tasks  # cleaned up

    def test_failed_execution_no_retries(self):
        class BoomAgent(ExecutorAgent):
            def act(self, decision):
                raise RuntimeError("boom")

        agent = BoomAgent("boom")
        t = Task(description="fail", max_retries=0)
        agent.assign_task(t)

        with pytest.raises(RuntimeError, match="boom"):
            agent.execute_task(t)

        assert t.status == TaskStatus.FAILED
        assert t.completed_at is not None
        assert agent.performance_metrics["tasks_failed"] == 1
        assert t.id not in agent.active_tasks  # always cleaned up

    def test_failed_execution_with_retries(self):
        class BoomAgent(ExecutorAgent):
            def act(self, decision):
                raise RuntimeError("transient")

        agent = BoomAgent("retry-agent")
        t = Task(description="retryable", max_retries=3)
        agent.assign_task(t)

        with pytest.raises(RuntimeError):
            agent.execute_task(t)

        assert t.status == TaskStatus.RETRYING
        assert t.retry_count == 1
        assert t.last_retry_at is not None
        assert t.id not in agent.active_tasks

    def test_retry_count_increments_on_repeated_failures(self):
        class BoomAgent(ExecutorAgent):
            def act(self, decision):
                raise RuntimeError("always fails")

        agent = BoomAgent("counter")
        t = Task(description="counter", max_retries=2)

        agent.assign_task(t)
        with pytest.raises(RuntimeError):
            agent.execute_task(t)
        assert t.retry_count == 1
        assert t.status == TaskStatus.RETRYING

        # Re-assign for next retry
        agent.assign_task(t)
        with pytest.raises(RuntimeError):
            agent.execute_task(t)
        assert t.retry_count == 2
        assert t.status == TaskStatus.RETRYING

        # One more — exhausts retries
        agent.assign_task(t)
        with pytest.raises(RuntimeError):
            agent.execute_task(t)
        assert t.retry_count == 2  # not incremented beyond max_retries
        assert t.status == TaskStatus.FAILED

    def test_active_task_cleaned_up_on_success(self, executor, task):
        executor.assign_task(task)
        assert task.id in executor.active_tasks
        executor.execute_task(task)
        assert task.id not in executor.active_tasks

    def test_active_task_cleaned_up_on_failure(self):
        class BoomAgent(ExecutorAgent):
            def act(self, decision):
                raise RuntimeError("cleanup-test")

        agent = BoomAgent("cleanup")
        t = Task(description="cleanup", max_retries=0)
        agent.assign_task(t)
        assert t.id in agent.active_tasks

        with pytest.raises(RuntimeError):
            agent.execute_task(t)

        assert t.id not in agent.active_tasks

    def test_force_task_status_disallowed_by_default(self, executor, task):
        task.transition_to(TaskStatus.ASSIGNED)
        with pytest.raises(RuntimeError, match="Refused forced status transition"):
            executor._force_task_status(task, TaskStatus.RETRYING)

    def test_force_task_status_allowed_when_explicitly_enabled(self, executor, task):
        task.transition_to(TaskStatus.ASSIGNED)
        executor.enable_forced_status_fallback = True
        task.metadata["allow_forced_status_fallback"] = True
        executor._force_task_status(task, TaskStatus.FAILED)
        assert task.status == TaskStatus.FAILED
        assert task.completed_at is not None


# ---------------------------------------------------------------------------
# OrchestratorAgent
# ---------------------------------------------------------------------------

class TestOrchestratorAgent:
    def test_register_agent_sets_parent(self):
        orch = OrchestratorAgent("orch")
        agent = ExecutorAgent("exec")
        orch.register_agent(agent)
        assert agent.id in orch.managed_agents
        assert agent.parent_agent == orch.id

    def test_select_best_agent_prefers_less_busy(self):
        orch = OrchestratorAgent("orch")
        a1 = ExecutorAgent("a1")
        a2 = ExecutorAgent("a2")
        orch.register_agent(a1)
        orch.register_agent(a2)

        # Assign one task to a1 to make it busier
        t = Task(description="busy")
        a1.assign_task(t)

        best = orch._select_best_agent(Task(description="new"))
        assert best is a2

    def test_select_best_agent_respects_required_capabilities(self):
        orch = OrchestratorAgent("orch")
        general = ExecutorAgent("general")
        specialist = ExecutorAgent("specialist")
        specialist.register_capability(
            AgentCapability(name="data_analysis", description="analyze")
        )
        orch.register_agent(general)
        orch.register_agent(specialist)

        task = Task(
            description="analysis",
            parameters={"required_capabilities": ["data_analysis"]},
        )
        best = orch._select_best_agent(task)
        assert best is specialist

    def test_select_best_agent_returns_none_when_capabilities_missing(self):
        orch = OrchestratorAgent("orch")
        agent = ExecutorAgent("general")
        orch.register_agent(agent)

        task = Task(
            description="special",
            parameters={"required_capabilities": ["missing_capability"]},
        )
        best = orch._select_best_agent(task)
        assert best is None

    def test_select_best_agent_skips_suspended(self):
        orch = OrchestratorAgent("orch")
        a1 = ExecutorAgent("a1")
        orch.register_agent(a1)
        a1.status = AgentStatus.SUSPENDED

        best = orch._select_best_agent(Task(description="new"))
        assert best is None

    def test_distribute_task_to_explicit_target(self):
        orch = OrchestratorAgent("orch")
        agent = ExecutorAgent("exec")
        orch.register_agent(agent)
        t = Task(description="explicit")
        result = orch.distribute_task(t, target_agent_id=agent.id)
        assert result is True
        assert t.id in agent.active_tasks

    def test_distribute_task_auto_selects(self):
        orch = OrchestratorAgent("orch")
        agent = ExecutorAgent("exec")
        orch.register_agent(agent)
        t = Task(description="auto")
        result = orch.distribute_task(t)
        assert result is True

    def test_distribute_task_returns_false_when_no_agent(self):
        orch = OrchestratorAgent("orch")
        t = Task(description="no-agent")
        assert orch.distribute_task(t) is False


# ---------------------------------------------------------------------------
# AgentSystem
# ---------------------------------------------------------------------------

class TestAgentSystem:
    def test_add_agent(self, system):
        agent = ExecutorAgent("e1")
        assert system.add_agent(agent) is True
        assert agent.id in system.agents
        assert agent.id in system.orchestrator.managed_agents
        assert system.system_metrics["total_agents"] == 2  # orchestrator + e1

    def test_remove_agent_basic(self, system):
        agent = ExecutorAgent("e1")
        system.add_agent(agent)
        assert system.remove_agent(agent.id) is True
        assert agent.id not in system.agents
        assert system.system_metrics["total_agents"] == 1  # only orchestrator left

    def test_remove_agent_cleans_managed_agents(self, system):
        agent = ExecutorAgent("e1")
        system.add_agent(agent)
        system.remove_agent(agent.id)
        assert agent.id not in system.orchestrator.managed_agents

    def test_remove_agent_clears_parent_reference(self, system):
        agent = ExecutorAgent("e1")
        system.add_agent(agent)
        assert agent.parent_agent == system.orchestrator.id
        system.remove_agent(agent.id)
        assert agent.parent_agent is None

    def test_remove_agent_clears_peer_references(self, system):
        a1 = ExecutorAgent("a1")
        a2 = ExecutorAgent("a2")
        system.add_agent(a1)
        system.add_agent(a2)
        # Manually wire peer relationship
        a1.peer_agents.add(a2.id)
        a2.peer_agents.add(a1.id)

        system.remove_agent(a1.id)

        assert a1.id not in a2.peer_agents
        assert len(a1.peer_agents) == 0

    def test_remove_agent_clears_child_parent_reference(self, system):
        parent = ExecutorAgent("parent")
        child = ExecutorAgent("child")
        system.add_agent(parent)
        system.add_agent(child)
        # Wire parent->child relationship
        parent.child_agents.add(child.id)
        child.parent_agent = parent.id

        system.remove_agent(parent.id)

        assert child.parent_agent is None

    def test_remove_nonexistent_agent(self, system):
        assert system.remove_agent("nonexistent") is False

    def test_create_task(self, system):
        t = system.create_task("do something", {"k": "v"})
        assert t.id in system.task_registry
        assert any(x.id == t.id for x in system.global_task_queue)
        assert system.system_metrics["total_tasks"] == 1

    def test_create_task_empty_description_raises(self, system):
        with pytest.raises(ValueError, match="description must not be empty"):
            system.create_task("", {})

    def test_create_task_whitespace_description_raises(self, system):
        with pytest.raises(ValueError, match="description must not be empty"):
            system.create_task("   ", {})

    def test_create_task_non_dict_parameters_raises(self, system):
        with pytest.raises(TypeError, match="parameters must be a dictionary"):
            system.create_task("bad-params", [])

    def test_create_task_negative_retries_raises(self, system):
        with pytest.raises(ValueError, match="max_retries must be a non-negative integer"):
            system.create_task("bad-retries", {}, max_retries=-1)

    def test_create_task_invalid_required_capabilities_raises(self, system):
        with pytest.raises(ValueError, match="required_capabilities must be a list of non-empty strings"):
            system.create_task("bad-caps", {"required_capabilities": ["", 1]})

    def test_create_task_empty_required_capabilities_raises(self, system):
        with pytest.raises(ValueError, match="required_capabilities must be a list of non-empty strings"):
            system.create_task("bad-caps-empty", {"required_capabilities": []})

    def test_create_task_invalid_timeout_raises(self, system):
        with pytest.raises(ValueError, match="timeout_seconds"):
            system.create_task("bad-timeout", {"timeout_seconds": 0})

    def test_submit_task_removes_from_global_queue(self, system):
        agent = ExecutorAgent("exec")
        system.add_agent(agent)
        t = system.create_task("submit-test", {})
        assert any(x.id == t.id for x in system.global_task_queue)
        system.submit_task(t, agent.id)
        assert not any(x.id == t.id for x in system.global_task_queue)

    def test_execute_task_success_updates_metrics(self, system):
        agent = ExecutorAgent("exec")
        system.add_agent(agent)
        t = system.create_task("run", {})
        system.submit_task(t, agent.id)
        system.execute_task(t.id, agent.id)
        assert system.system_metrics["successful_tasks"] == 1
        assert t in system.completed_tasks

    def test_execute_task_completed_list_deduplicated(self, system):
        agent = ExecutorAgent("exec")
        system.add_agent(agent)
        t = system.create_task("run-once", {})
        system.submit_task(t, agent.id)
        system.execute_task(t.id, agent.id)

        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)

        assert sum(1 for task in system.completed_tasks if task.id == t.id) == 1

    def test_execute_task_failure_updates_metrics(self, system):
        class BoomAgent(ExecutorAgent):
            def act(self, decision):
                raise RuntimeError("fail")

        agent = BoomAgent("boom")
        agent.max_retries = 0
        system.add_agent(agent)
        t = system.create_task("fail-task", {})
        t.max_retries = 0
        system.submit_task(t, agent.id)

        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)

        assert system.system_metrics["failed_tasks"] == 1

    def test_execute_task_retry_requeues(self, system):
        class BoomAgent(ExecutorAgent):
            def act(self, decision):
                raise RuntimeError("retry-me")

        agent = BoomAgent("retry-exec")
        system.add_agent(agent)
        t = system.create_task("retry-task", {})
        t.max_retries = 2
        system.submit_task(t, agent.id)

        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)

        assert t.status == TaskStatus.RETRYING
        assert any(x.id == t.id for x in system.global_task_queue)
        assert t.next_retry_at is not None

    def test_execute_task_retry_no_duplicate_requeue(self, system):
        """Calling execute_task twice on a retrying task must not add duplicates."""
        class BoomAgent(ExecutorAgent):
            def act(self, decision):
                raise RuntimeError("dup-test")

        agent = BoomAgent("dup-agent")
        system.add_agent(agent)
        t = system.create_task("dup-task", {})
        t.max_retries = 5
        system.submit_task(t, agent.id)

        # First failure → requeued
        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)

        queue_count = sum(1 for x in system.global_task_queue if x.id == t.id)
        assert queue_count == 1

        # Second failure without draining the queue → still only one entry
        agent.assign_task(t)
        with pytest.raises(RuntimeError):
            system.execute_task(t.id, agent.id)

        queue_count = sum(1 for x in system.global_task_queue if x.id == t.id)
        assert queue_count == 1

    def test_submit_task_skips_retry_until_due(self, system):
        agent = ExecutorAgent("exec")
        system.add_agent(agent)
        t = system.create_task("delayed", {})
        t.transition_to(TaskStatus.ASSIGNED)
        t.transition_to(TaskStatus.RUNNING)
        t.transition_to(TaskStatus.RETRYING)
        t.next_retry_at = datetime.now() + timedelta(seconds=60)

        assert system.submit_task(t, agent.id) is False
        assert t.id not in agent.active_tasks

        t.next_retry_at = datetime.now() - timedelta(seconds=1)
        assert system.submit_task(t, agent.id) is True

    def test_execute_task_cancellation_hook_sets_cancelled(self, system):
        class CancelAgent(ExecutorAgent):
            def think(self, input_data):
                return input_data

            def act(self, decision):
                return {"ok": True}

        agent = CancelAgent("cancel")
        system.add_agent(agent)
        t = system.create_task(
            "cancel-me",
            {"metadata": {"cancellation_check": _always_cancel}},
        )
        assert callable(t.metadata["cancellation_check"])
        t.max_retries = 3
        system.submit_task(t, agent.id)

        with pytest.raises(RuntimeError, match="cancellation hook requested stop"):
            system.execute_task(t.id, agent.id)

        assert t.status == TaskStatus.CANCELLED
        assert t.retry_count == 0
        assert t.next_retry_at is None

    def test_execute_task_timeout_sets_retry_schedule(self, system):
        class SlowAgent(ExecutorAgent):
            def think(self, input_data):
                return input_data

            def act(self, decision):
                time.sleep(0.02)
                return {"ok": True}

        agent = SlowAgent("slow")
        system.add_agent(agent)
        t = system.create_task(
            "timeout",
            {"timeout_seconds": 0.01, "metadata": {"retry_jitter_seconds": 0}},
        )
        t.max_retries = 1
        system.submit_task(t, agent.id)

        with pytest.raises(TimeoutError):
            system.execute_task(t.id, agent.id)

        assert t.status == TaskStatus.RETRYING
        assert t.next_retry_at is not None

    def test_execute_task_unknown_agent_raises(self, system):
        t = system.create_task("task", {})
        with pytest.raises(ValueError, match="not found"):
            system.execute_task(t.id, "bad-agent-id")

    def test_execute_task_unknown_task_raises(self, system):
        agent = ExecutorAgent("exec")
        system.add_agent(agent)
        with pytest.raises(ValueError, match="not found"):
            system.execute_task("bad-task-id", agent.id)

    def test_get_system_status(self, system):
        status = system.get_system_status()
        assert "agents" in status
        assert "metrics" in status
        assert "pending_tasks" in status


class TestAgentSystemObservabilityHooks:
    def test_persistence_hook_receives_task_events(self, system):
        events = []
        system.set_persistence_hook(lambda event, task: events.append((event, task.id)))

        t = system.create_task("persist-me", {})

        assert events
        assert events[0][0] == "created"
        assert events[0][1] == t.id

    def test_telemetry_hook_receives_structured_events(self, system):
        events = []
        system.set_telemetry_hook(lambda event, payload: events.append((event, payload)))

        t = system.create_task("telemetry", {})

        created_events = [evt for evt in events if evt[0] == "task_created"]
        assert created_events
        payload = created_events[0][1]
        assert payload["task_id"] == t.id
        assert payload["system_id"] == system.id
        assert payload["event"] == "task_created"

    def test_persistence_hook_failures_do_not_crash_core_flow(self, system):
        def bad_persistence(_event, _task):
            raise RuntimeError("hook-failure")

        system.set_persistence_hook(bad_persistence)
        t = system.create_task("safe-create", {})
        assert t.id in system.task_registry

    def test_telemetry_hook_failures_do_not_crash_core_flow(self, system):
        def bad_telemetry(_event, _payload):
            raise RuntimeError("hook-failure")

        system.set_telemetry_hook(bad_telemetry)
        t = system.create_task("safe-telemetry", {})
        assert t.id in system.task_registry


# ---------------------------------------------------------------------------
# AgentFactory
# ---------------------------------------------------------------------------

class TestAgentFactory:
    def test_create_executor(self):
        agent = AgentFactory.create_agent("executor", "Exec-1")
        assert isinstance(agent, ExecutorAgent)
        assert agent.name == "Exec-1"

    def test_create_analyzer(self):
        agent = AgentFactory.create_agent("analyzer", "An-1")
        assert isinstance(agent, AnalyzerAgent)

    def test_create_learner(self):
        agent = AgentFactory.create_agent("learner", "Le-1")
        assert isinstance(agent, LearnerAgent)

    def test_create_orchestrator(self):
        agent = AgentFactory.create_agent("orchestrator", "Orch-1")
        assert isinstance(agent, OrchestratorAgent)

    def test_unknown_type_returns_none(self):
        agent = AgentFactory.create_agent("unknown", "X")
        assert agent is None

    def test_case_insensitive(self):
        agent = AgentFactory.create_agent("EXECUTOR", "E")
        assert isinstance(agent, ExecutorAgent)

    def test_create_team(self):
        config = {"executor": 2, "analyzer": 1}
        system = AgentFactory.create_team(config)
        # orchestrator + 2 executors + 1 analyzer = 4
        assert system.system_metrics["total_agents"] == 4
        roles = [a.role for a in system.agents.values()]
        executor_count = sum(1 for r in roles if r == AgentRole.EXECUTOR)
        analyzer_count = sum(1 for r in roles if r == AgentRole.ANALYZER)
        assert executor_count == 2
        assert analyzer_count == 1


# ---------------------------------------------------------------------------
# Additional tests (10 more)
# ---------------------------------------------------------------------------

class TestBaseAgentCapabilityHelpers:
    def test_get_capability_returns_registered(self, executor):
        cap = AgentCapability(name="search", description="search things")
        executor.register_capability(cap)
        retrieved = executor.get_capability("search")
        assert retrieved is cap

    def test_get_capability_returns_none_for_missing(self, executor):
        assert executor.get_capability("nonexistent") is None

    def test_list_capabilities_reflects_registered(self, executor):
        executor.register_capability(AgentCapability(name="alpha", description="a"))
        executor.register_capability(AgentCapability(name="beta", description="b"))
        names = executor.list_capabilities()
        assert "alpha" in names
        assert "beta" in names
        assert len(names) == 2


class TestAnalyzerAgentBehaviour:
    def test_think_returns_expected_keys(self):
        agent = AnalyzerAgent("an-1")
        result = agent.think({"data": 42})
        assert "data_received" in result
        assert "insights_generated" in result
        assert result["insights_generated"] is True

    def test_think_false_when_no_data(self):
        agent = AnalyzerAgent("an-2")
        result = agent.think(None)
        assert result["data_received"] is False


class TestLearnerAgentBehaviour:
    def test_learn_from_experience_stores_pattern(self):
        agent = LearnerAgent("learner-1")
        agent.learn_from_experience({"event": "success", "reward": 1.0})
        assert len(agent.learned_patterns) == 1

    def test_learn_from_experience_multiple_accumulates(self):
        agent = LearnerAgent("learner-2")
        for i in range(3):
            agent.learn_from_experience({"step": i})
        assert len(agent.learned_patterns) == 3


class TestAgentSystemHelpers:
    def test_get_agent_returns_correct_agent(self, system):
        agent = ExecutorAgent("e-find")
        system.add_agent(agent)
        found = system.get_agent(agent.id)
        assert found is agent

    def test_get_agent_returns_none_for_unknown(self, system):
        assert system.get_agent("does-not-exist") is None

    def test_to_json_is_valid_json(self, system):
        import json as _json
        agent = ExecutorAgent("e-json")
        system.add_agent(agent)
        serialized = system.to_json()
        data = _json.loads(serialized)
        assert "agents" in data
        assert "metrics" in data

    def test_create_task_with_high_priority(self, system):
        t = system.create_task("urgent work", {}, priority=TaskPriority.HIGH)
        assert t.priority == TaskPriority.HIGH
        assert system.task_registry[t.id] is t

    def test_submit_task_without_agent_id_auto_distributes(self, system):
        agent = ExecutorAgent("e-auto")
        system.add_agent(agent)
        t = system.create_task("auto-distribute", {})
        result = system.submit_task(t)
        assert result is True
        assert t.id in agent.active_tasks


# ---------------------------------------------------------------------------
# Second round of hardening tests (10 more)
# ---------------------------------------------------------------------------

class TestTaskDictTimestamps:
    def test_to_dict_timestamps_after_completion(self):
        """to_dict exposes assigned_at/started_at/completed_at after a full run."""
        t = Task(description="lifecycle")
        t.transition_to(TaskStatus.ASSIGNED)
        t.transition_to(TaskStatus.RUNNING)
        t.transition_to(TaskStatus.COMPLETED)
        d = t.to_dict()
        assert d["assigned_at"] is not None
        assert d["started_at"] is not None
        assert d["completed_at"] is not None
        assert d["status"] == "completed"

    def test_to_dict_preserves_parameters_and_metadata(self):
        """to_dict round-trips arbitrary parameters and metadata."""
        t = Task(description="params", parameters={"x": 1}, metadata={"tag": "test"})
        d = t.to_dict()
        assert d["parameters"] == {"x": 1}
        assert d["metadata"] == {"tag": "test"}


class TestTaskCancellation:
    def test_assigned_to_cancelled(self, task):
        task.transition_to(TaskStatus.ASSIGNED)
        assert task.transition_to(TaskStatus.CANCELLED) is True
        assert task.status == TaskStatus.CANCELLED
        assert task.completed_at is not None

    def test_running_to_cancelled(self, task):
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        assert task.transition_to(TaskStatus.CANCELLED) is True
        assert task.status == TaskStatus.CANCELLED

    def test_cancelled_is_terminal(self, task):
        task.transition_to(TaskStatus.CANCELLED)
        assert task.transition_to(TaskStatus.ASSIGNED) is False
        assert task.status == TaskStatus.CANCELLED


class TestAgentCapabilityRepr:
    def test_repr_contains_name_and_version(self):
        cap = AgentCapability(name="compute", description="do math", version="2.0.0")
        r = repr(cap)
        assert "compute" in r
        assert "2.0.0" in r


class TestOrchestratorAgentBehaviour:
    def test_think_returns_expected_keys(self):
        orch = OrchestratorAgent("orch-think")
        result = orch.think({"task": "x"})
        assert "analysis" in result
        assert "execution_strategy" in result

    def test_act_returns_orchestration_complete(self):
        orch = OrchestratorAgent("orch-act")
        result = orch.act({"execution_strategy": "parallel"})
        assert result.get("status") == "orchestration_complete"

    def test_get_system_status_structure(self):
        orch = OrchestratorAgent("orch-status")
        agent = ExecutorAgent("e1")
        orch.register_agent(agent)
        status = orch.get_system_status()
        assert "orchestrator" in status
        assert "managed_agents" in status
        assert "total_agents" in status
        assert status["total_agents"] == 1


class TestExecutorAgentHistory:
    def test_execution_history_grows_after_run(self, executor, task):
        executor.assign_task(task)
        executor.execute_task(task)
        assert len(executor.execution_history) == 1
        entry = executor.execution_history[0]
        assert "timestamp" in entry
        assert entry["result"] == "executed"


class TestLearnerAgentDetails:
    def test_think_returns_learning_mode(self):
        agent = LearnerAgent("l-think")
        result = agent.think({"signal": 1})
        assert result.get("learning_mode") is True
        assert "patterns_identified" in result

    def test_act_populates_learning_history(self):
        agent = LearnerAgent("l-act")
        agent.act({"learning_mode": True})
        assert len(agent.learning_history) == 1
        entry = agent.learning_history[0]
        assert "timestamp" in entry
        assert "decision" in entry


class TestAgentSystemSubmitEdgeCases:
    def test_submit_task_returns_false_for_unknown_agent_id(self, system):
        t = system.create_task("edge", {})
        result = system.submit_task(t, agent_id="no-such-agent")
        assert result is False


# ---------------------------------------------------------------------------
# Third round of hardening tests (5 more)
# ---------------------------------------------------------------------------

class TestBaseAgentRepr:
    def test_repr_contains_name_and_role(self, executor):
        r = repr(executor)
        assert executor.name in r
        assert "executor" in r.lower()


class TestAgentSystemRepr:
    def test_repr_contains_system_name_and_agent_count(self, system):
        agent = ExecutorAgent("e-repr")
        system.add_agent(agent)
        r = repr(system)
        assert system.name in r
        # orchestrator + 1 added agent = 2
        assert "2" in r


class TestTaskDictRetryAt:
    def test_to_dict_includes_last_retry_at_after_retry(self):
        t = Task(description="retry-dict", max_retries=2)
        t.transition_to(TaskStatus.ASSIGNED)
        t.transition_to(TaskStatus.RUNNING)
        t.transition_to(TaskStatus.RETRYING)
        d = t.to_dict()
        assert d["last_retry_at"] is not None
        assert d["status"] == "retrying"


class TestAgentMemoryStrictRetrieval:
    def test_episodic_type_misses_semantic_only_key(self):
        """retrieve(key, 'episodic') must return None if the key only lives in semantic memory."""
        mem = AgentMemory(agent_id="a1")
        mem.store_semantic("fact", "only-in-semantic")
        assert mem.retrieve("fact", "episodic") is None

    def test_semantic_type_misses_episodic_only_key(self):
        """retrieve(key, 'semantic') must return None if the key only lives in episodic memory."""
        mem = AgentMemory(agent_id="a1")
        mem.store_episode("ep", "only-in-episodic")
        assert mem.retrieve("ep", "semantic") is None
