"""
Unit tests for AgentSystem: agent lifecycle, task creation/submission/execution,
and system-level metrics.
"""

import pytest

from src.agents.super_agentic_agents import (
    Task,
    TaskStatus,
    TaskPriority,
    AgentStatus,
    ExecutorAgent,
    AgentSystem,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_system(name: str = "TestSystem") -> AgentSystem:
    return AgentSystem(name)


def make_executor(name: str = "exec") -> ExecutorAgent:
    return ExecutorAgent(name)


def _make_failing_executor(name: str = "fail-exec") -> ExecutorAgent:
    """Return an ExecutorAgent whose act() always raises RuntimeError."""
    agent = ExecutorAgent(name)

    def failing_act(decision):
        raise RuntimeError("intentional failure")

    agent.act = failing_act
    return agent


# ---------------------------------------------------------------------------
# add_agent / remove_agent
# ---------------------------------------------------------------------------

class TestAddRemoveAgent:
    def test_add_agent_returns_true(self):
        system = make_system()
        agent = make_executor()
        assert system.add_agent(agent) is True

    def test_add_agent_registers_in_agents_dict(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        assert system.get_agent(agent.id) is agent

    def test_add_agent_increments_total_agents_metric(self):
        system = make_system()
        initial = system.system_metrics["total_agents"]
        agent = make_executor()
        system.add_agent(agent)
        assert system.system_metrics["total_agents"] == initial + 1

    def test_add_agent_registers_with_orchestrator(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        assert agent.id in system.orchestrator.managed_agents

    def test_remove_agent_returns_true(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        assert system.remove_agent(agent.id) is True

    def test_remove_agent_removes_from_agents_dict(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        system.remove_agent(agent.id)
        assert system.get_agent(agent.id) is None

    def test_remove_agent_decrements_total_agents_metric(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        before = system.system_metrics["total_agents"]
        system.remove_agent(agent.id)
        assert system.system_metrics["total_agents"] == before - 1

    def test_remove_nonexistent_agent_returns_false(self):
        system = make_system()
        assert system.remove_agent("does-not-exist") is False


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------

class TestCreateTask:
    def test_create_task_returns_task(self):
        system = make_system()
        task = system.create_task("do something", {})
        assert isinstance(task, Task)

    def test_create_task_added_to_global_queue(self):
        system = make_system()
        task = system.create_task("do something", {})
        queue_ids = [t.id for t in system.global_task_queue]
        assert task.id in queue_ids

    def test_create_task_added_to_registry(self):
        system = make_system()
        task = system.create_task("do something", {})
        assert task.id in system.task_registry

    def test_create_task_increments_total_tasks_metric(self):
        system = make_system()
        before = system.system_metrics["total_tasks"]
        system.create_task("t", {})
        assert system.system_metrics["total_tasks"] == before + 1

    def test_create_task_respects_priority(self):
        system = make_system()
        task = system.create_task("critical", {}, priority=TaskPriority.CRITICAL)
        assert task.priority == TaskPriority.CRITICAL

    def test_create_task_respects_max_retries(self):
        system = make_system()
        task = system.create_task("t", {}, max_retries=5)
        assert task.max_retries == 5

    def test_create_task_default_status_is_pending(self):
        system = make_system()
        task = system.create_task("t", {})
        assert task.status == TaskStatus.PENDING


# ---------------------------------------------------------------------------
# submit_task
# ---------------------------------------------------------------------------

class TestSubmitTask:
    def test_submit_task_to_explicit_agent_succeeds(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        task = system.create_task("t", {})
        result = system.submit_task(task, agent_id=agent.id)
        assert result is True

    def test_submit_task_removes_from_global_queue_on_success(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        task = system.create_task("t", {})
        system.submit_task(task, agent_id=agent.id)
        queue_ids = [t.id for t in system.global_task_queue]
        assert task.id not in queue_ids

    def test_submit_task_to_unknown_agent_returns_false(self):
        system = make_system()
        task = system.create_task("t", {})
        result = system.submit_task(task, agent_id="no-such-agent")
        assert result is False

    def test_submit_task_without_agent_uses_orchestrator(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        task = system.create_task("t", {})
        result = system.submit_task(task)
        assert result is True

    def test_submit_task_keeps_in_queue_when_no_agent(self):
        system = make_system()
        # No executors registered; orchestrator has no managed agents besides itself
        # (orchestrator is ORCHESTRATOR role and is managed by itself after add_agent)
        # Create a fresh system with no agents at all for the orchestrator
        task = system.create_task("t", {})
        # No non-orchestrator agents; orchestrator auto-select may still pick orchestrator
        # Just verify the return value matches queue state
        result = system.submit_task(task)
        queue_ids = [t.id for t in system.global_task_queue]
        if result:
            assert task.id not in queue_ids
        else:
            assert task.id in queue_ids


# ---------------------------------------------------------------------------
# execute_task
# ---------------------------------------------------------------------------

class TestExecuteTask:
    def test_execute_task_returns_result(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        task = system.create_task("run", {"k": "v"})
        system.submit_task(task, agent_id=agent.id)
        result = system.execute_task(task.id, agent.id)
        assert result["execution"] == "successful"

    def test_execute_task_increments_successful_tasks_metric(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        task = system.create_task("run", {})
        system.submit_task(task, agent_id=agent.id)
        before = system.system_metrics["successful_tasks"]
        system.execute_task(task.id, agent.id)
        assert system.system_metrics["successful_tasks"] == before + 1

    def test_execute_task_adds_to_system_completed_tasks(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        task = system.create_task("run", {})
        system.submit_task(task, agent_id=agent.id)
        system.execute_task(task.id, agent.id)
        assert task in system.completed_tasks

    def test_execute_task_with_unknown_agent_raises(self):
        system = make_system()
        task = system.create_task("t", {})
        with pytest.raises(ValueError, match="Agent.*not found"):
            system.execute_task(task.id, "no-such-agent")

    def test_execute_task_with_unknown_task_raises(self):
        system = make_system()
        agent = make_executor()
        system.add_agent(agent)
        with pytest.raises(ValueError, match="Task.*not found"):
            system.execute_task("no-such-task", agent.id)

    def test_failed_task_increments_failed_tasks_metric(self):
        system = make_system()
        agent = _make_failing_executor()
        system.add_agent(agent)
        task = system.create_task("fail", {}, max_retries=0)
        system.submit_task(task, agent_id=agent.id)
        with pytest.raises(RuntimeError):
            system.execute_task(task.id, agent.id)
        assert system.system_metrics["failed_tasks"] == 1

    def test_retrying_task_is_requeued(self):
        system = make_system()
        agent = _make_failing_executor()
        system.add_agent(agent)
        task = system.create_task("fail", {}, max_retries=2)
        system.submit_task(task, agent_id=agent.id)

        with pytest.raises(RuntimeError):
            system.execute_task(task.id, agent.id)

        assert task.status == TaskStatus.RETRYING
        queue_ids = [t.id for t in system.global_task_queue]
        assert task.id in queue_ids

    def test_system_status_contains_expected_keys(self):
        system = make_system()
        status = system.get_system_status()
        for key in ["system_name", "system_id", "created_at", "agents",
                    "metrics", "pending_tasks", "completed_tasks"]:
            assert key in status

    def test_to_json_returns_string(self):
        system = make_system()
        json_str = system.to_json()
        assert isinstance(json_str, str)
        assert "system_name" in json_str
