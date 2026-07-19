"""
Unit tests for BaseAgent behavior via the concrete ExecutorAgent subclass.
Covers capability registration, task assignment, execution, and metrics.
"""

import pytest

from src.agents.super_agentic_agents import (
    Task,
    TaskStatus,
    AgentCapability,
    AgentStatus,
    ExecutorAgent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_capability(name: str = "do_something") -> AgentCapability:
    return AgentCapability(name=name, description=f"Capability: {name}")


def make_assigned_task(description: str = "test task") -> Task:
    task = Task(description=description, parameters={"x": 1})
    task.transition_to(TaskStatus.ASSIGNED)
    return task


# ---------------------------------------------------------------------------
# Capability registration
# ---------------------------------------------------------------------------

class TestRegisterCapability:
    def test_register_single_capability_succeeds(self):
        agent = ExecutorAgent("exec")
        cap = make_capability("cap1")
        assert agent.register_capability(cap) is True
        assert "cap1" in agent.capabilities

    def test_register_multiple_distinct_capabilities(self):
        agent = ExecutorAgent("exec")
        agent.register_capability(make_capability("a"))
        agent.register_capability(make_capability("b"))
        assert set(agent.list_capabilities()) == {"a", "b"}

    def test_get_capability_returns_correct_object(self):
        agent = ExecutorAgent("exec")
        cap = make_capability("my_cap")
        agent.register_capability(cap)
        retrieved = agent.get_capability("my_cap")
        assert retrieved is cap

    def test_get_capability_missing_returns_none(self):
        agent = ExecutorAgent("exec")
        assert agent.get_capability("nonexistent") is None

    def test_register_respects_max_capabilities(self):
        agent = ExecutorAgent("exec")
        agent.max_capabilities = 2
        assert agent.register_capability(make_capability("c1")) is True
        assert agent.register_capability(make_capability("c2")) is True
        assert agent.register_capability(make_capability("c3")) is False
        assert len(agent.capabilities) == 2

    def test_list_capabilities_empty_initially(self):
        agent = ExecutorAgent("exec")
        assert agent.list_capabilities() == []

    def test_capability_stored_in_semantic_memory(self):
        agent = ExecutorAgent("exec")
        cap = make_capability("mem_cap")
        agent.register_capability(cap)
        stored = agent.memory.retrieve("capability:mem_cap", "semantic")
        assert stored is cap


# ---------------------------------------------------------------------------
# Task assignment
# ---------------------------------------------------------------------------

class TestAssignTask:
    def test_assign_pending_task_succeeds(self):
        agent = ExecutorAgent("exec")
        task = Task(description="pending task")
        assert agent.assign_task(task) is True
        assert task.id in agent.active_tasks

    def test_assign_pending_task_transitions_to_assigned(self):
        agent = ExecutorAgent("exec")
        task = Task(description="t")
        agent.assign_task(task)
        assert task.status == TaskStatus.ASSIGNED

    def test_assign_task_sets_assigned_to(self):
        agent = ExecutorAgent("exec")
        task = Task(description="t")
        agent.assign_task(task)
        assert task.assigned_to == agent.id

    def test_assign_already_assigned_task_succeeds(self):
        agent = ExecutorAgent("exec")
        task = Task(description="t")
        task.transition_to(TaskStatus.ASSIGNED)
        assert agent.assign_task(task) is True

    def test_assign_retrying_task_succeeds(self):
        agent = ExecutorAgent("exec")
        task = Task(description="t")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RETRYING)
        assert agent.assign_task(task) is True

    def test_assign_completed_task_fails(self):
        agent = ExecutorAgent("exec")
        task = Task(description="t")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.COMPLETED)
        assert agent.assign_task(task) is False
        assert task.id not in agent.active_tasks

    def test_assign_failed_task_fails(self):
        agent = ExecutorAgent("exec")
        task = Task(description="t")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.FAILED)
        assert agent.assign_task(task) is False

    def test_assign_running_task_fails(self):
        agent = ExecutorAgent("exec")
        task = Task(description="t")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        assert agent.assign_task(task) is False

    def test_capacity_limit_is_enforced(self):
        agent = ExecutorAgent("exec")
        agent.max_active_tasks = 2
        task1 = Task(description="t1")
        task2 = Task(description="t2")
        task3 = Task(description="t3")
        assert agent.assign_task(task1) is True
        assert agent.assign_task(task2) is True
        assert agent.assign_task(task3) is False


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------

class TestExecuteTask:
    def test_successful_execution_returns_result(self):
        agent = ExecutorAgent("exec")
        task = Task(description="run", parameters={"x": 42})
        agent.assign_task(task)
        result = agent.execute_task(task)
        assert result["execution"] == "successful"

    def test_successful_execution_transitions_to_completed(self):
        agent = ExecutorAgent("exec")
        task = Task(description="run")
        agent.assign_task(task)
        agent.execute_task(task)
        assert task.status == TaskStatus.COMPLETED

    def test_successful_execution_records_result_on_task(self):
        agent = ExecutorAgent("exec")
        task = Task(description="run")
        agent.assign_task(task)
        agent.execute_task(task)
        assert task.result is not None
        assert task.result["execution"] == "successful"

    def test_successful_execution_updates_completed_tasks(self):
        agent = ExecutorAgent("exec")
        task = Task(description="run")
        agent.assign_task(task)
        agent.execute_task(task)
        assert task in agent.completed_tasks

    def test_successful_execution_updates_task_history(self):
        agent = ExecutorAgent("exec")
        task = Task(description="run")
        agent.assign_task(task)
        agent.execute_task(task)
        assert task in agent.task_history

    def test_successful_execution_increments_tasks_completed_metric(self):
        agent = ExecutorAgent("exec")
        task = Task(description="run")
        agent.assign_task(task)
        agent.execute_task(task)
        assert agent.performance_metrics["tasks_completed"] == 1

    def test_successful_execution_updates_success_rate(self):
        agent = ExecutorAgent("exec")
        task = Task(description="run")
        agent.assign_task(task)
        agent.execute_task(task)
        assert agent.performance_metrics["success_rate"] == 1.0

    def test_active_tasks_cleared_after_successful_execution(self):
        agent = ExecutorAgent("exec")
        task = Task(description="run")
        agent.assign_task(task)
        assert task.id in agent.active_tasks
        agent.execute_task(task)
        assert task.id not in agent.active_tasks

    def test_execute_task_sets_completed_at_timestamp(self):
        agent = ExecutorAgent("exec")
        task = Task(description="run")
        agent.assign_task(task)
        agent.execute_task(task)
        assert task.completed_at is not None

    def test_agent_status_idle_after_successful_execution(self):
        agent = ExecutorAgent("exec")
        task = Task(description="run")
        agent.assign_task(task)
        agent.execute_task(task)
        assert agent.status == AgentStatus.IDLE


class TestExecuteTaskFailureAndRetry:
    """Tests for failing execution with retry and final failure semantics."""

    def _make_failing_agent(self) -> ExecutorAgent:
        """Return an ExecutorAgent whose act() always raises."""
        agent = ExecutorAgent("fail-exec")
        original_act = agent.act

        def failing_act(decision):
            raise RuntimeError("intentional failure")

        agent.act = failing_act
        return agent

    def test_first_failure_retries_and_raises(self):
        agent = self._make_failing_agent()
        task = Task(description="fail", max_retries=2)
        agent.assign_task(task)
        with pytest.raises(RuntimeError):
            agent.execute_task(task)
        assert task.retry_count == 1
        assert task.status == TaskStatus.RETRYING

    def test_last_retry_exceeded_transitions_to_failed(self):
        agent = self._make_failing_agent()
        task = Task(description="fail", max_retries=1)
        agent.assign_task(task)

        # First attempt: retrying
        with pytest.raises(RuntimeError):
            agent.execute_task(task)
        assert task.status == TaskStatus.RETRYING

        # Re-assign for retry (simulate retry dispatch)
        agent.assign_task(task)
        with pytest.raises(RuntimeError):
            agent.execute_task(task)
        assert task.status == TaskStatus.FAILED

    def test_active_tasks_cleared_even_on_exception(self):
        agent = self._make_failing_agent()
        task = Task(description="fail", max_retries=0)
        agent.assign_task(task)
        with pytest.raises(RuntimeError):
            agent.execute_task(task)
        assert task.id not in agent.active_tasks

    def test_failure_increments_retry_count(self):
        agent = self._make_failing_agent()
        task = Task(description="fail", max_retries=3)
        agent.assign_task(task)
        with pytest.raises(RuntimeError):
            agent.execute_task(task)
        assert task.retry_count == 1

    def test_failure_sets_error_on_task(self):
        agent = self._make_failing_agent()
        task = Task(description="fail", max_retries=0)
        agent.assign_task(task)
        with pytest.raises(RuntimeError):
            agent.execute_task(task)
        assert task.error is not None

    def test_failure_updates_tasks_failed_metric(self):
        agent = self._make_failing_agent()
        task = Task(description="fail", max_retries=0)
        agent.assign_task(task)
        with pytest.raises(RuntimeError):
            agent.execute_task(task)
        assert agent.performance_metrics["tasks_failed"] == 1

    def test_failed_task_added_to_task_history(self):
        agent = self._make_failing_agent()
        task = Task(description="fail", max_retries=0)
        agent.assign_task(task)
        with pytest.raises(RuntimeError):
            agent.execute_task(task)
        assert task in agent.task_history
