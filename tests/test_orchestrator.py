"""
Unit tests for OrchestratorAgent: agent registration, best-agent selection,
and task distribution logic.
"""

import pytest

from src.agents.super_agentic_agents import (
    Task,
    TaskStatus,
    AgentStatus,
    ExecutorAgent,
    OrchestratorAgent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_orchestrator() -> OrchestratorAgent:
    return OrchestratorAgent("TestOrchestrator")


def make_executor(name: str = "exec") -> ExecutorAgent:
    return ExecutorAgent(name)


def make_pending_task(description: str = "task") -> Task:
    return Task(description=description)


# ---------------------------------------------------------------------------
# Agent registration
# ---------------------------------------------------------------------------

class TestRegisterAgent:
    def test_register_agent_returns_true(self):
        orch = make_orchestrator()
        agent = make_executor()
        assert orch.register_agent(agent) is True

    def test_registered_agent_in_managed_agents(self):
        orch = make_orchestrator()
        agent = make_executor()
        orch.register_agent(agent)
        assert agent.id in orch.managed_agents

    def test_registration_sets_parent_linkage(self):
        orch = make_orchestrator()
        agent = make_executor()
        orch.register_agent(agent)
        assert agent.parent_agent == orch.id

    def test_register_multiple_agents(self):
        orch = make_orchestrator()
        a1 = make_executor("e1")
        a2 = make_executor("e2")
        orch.register_agent(a1)
        orch.register_agent(a2)
        assert len(orch.managed_agents) == 2

    def test_get_system_status_reflects_registered_agents(self):
        orch = make_orchestrator()
        agent = make_executor()
        orch.register_agent(agent)
        status = orch.get_system_status()
        assert status["total_agents"] == 1


# ---------------------------------------------------------------------------
# Agent selection
# ---------------------------------------------------------------------------

class TestSelectBestAgent:
    def test_no_managed_agents_returns_none(self):
        orch = make_orchestrator()
        task = make_pending_task()
        assert orch._select_best_agent(task) is None

    def test_single_agent_is_selected(self):
        orch = make_orchestrator()
        agent = make_executor()
        orch.register_agent(agent)
        task = make_pending_task()
        assert orch._select_best_agent(task) is agent

    def test_suspended_agent_is_excluded(self):
        orch = make_orchestrator()
        suspended = make_executor("suspended")
        suspended.status = AgentStatus.SUSPENDED
        orch.register_agent(suspended)
        task = make_pending_task()
        assert orch._select_best_agent(task) is None

    def test_prefers_less_busy_agent(self):
        orch = make_orchestrator()
        busy = make_executor("busy")
        idle = make_executor("idle")

        # Give busy agent an active task by assigning without executing
        dummy_task = Task(description="dummy")
        busy.assign_task(dummy_task)

        orch.register_agent(busy)
        orch.register_agent(idle)

        task = make_pending_task()
        selected = orch._select_best_agent(task)
        assert selected is idle

    def test_all_suspended_returns_none(self):
        orch = make_orchestrator()
        for i in range(3):
            agent = make_executor(f"s{i}")
            agent.status = AgentStatus.SUSPENDED
            orch.register_agent(agent)
        task = make_pending_task()
        assert orch._select_best_agent(task) is None


# ---------------------------------------------------------------------------
# Task distribution
# ---------------------------------------------------------------------------

class TestDistributeTask:
    def test_distribute_with_explicit_target(self):
        orch = make_orchestrator()
        agent = make_executor()
        orch.register_agent(agent)
        task = make_pending_task()
        result = orch.distribute_task(task, target_agent_id=agent.id)
        assert result is True
        assert task.id in agent.active_tasks

    def test_distribute_with_invalid_target_tries_auto_select(self):
        orch = make_orchestrator()
        agent = make_executor()
        orch.register_agent(agent)
        task = make_pending_task()
        # Non-existent target_agent_id falls back to auto-selection
        result = orch.distribute_task(task, target_agent_id="nonexistent-id")
        assert result is True

    def test_distribute_auto_selects_available_agent(self):
        orch = make_orchestrator()
        agent = make_executor()
        orch.register_agent(agent)
        task = make_pending_task()
        result = orch.distribute_task(task)
        assert result is True
        assert task.id in agent.active_tasks

    def test_distribute_returns_false_when_no_agent_available(self):
        orch = make_orchestrator()
        task = make_pending_task()
        result = orch.distribute_task(task)
        assert result is False

    def test_distribute_returns_false_when_all_agents_suspended(self):
        orch = make_orchestrator()
        agent = make_executor()
        agent.status = AgentStatus.SUSPENDED
        orch.register_agent(agent)
        task = make_pending_task()
        result = orch.distribute_task(task)
        assert result is False

    def test_distribute_transitions_task_to_assigned(self):
        orch = make_orchestrator()
        agent = make_executor()
        orch.register_agent(agent)
        task = make_pending_task()
        orch.distribute_task(task)
        assert task.status == TaskStatus.ASSIGNED
