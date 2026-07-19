"""
Unit tests for src/agents/super_agentic_agents.py
"""

import pytest
from unittest.mock import patch

from src.agents.super_agentic_agents import (
    Task,
    TaskStatus,
    TaskPriority,
    AgentCapability,
    AgentMemory,
    AgentStatus,
    ExecutorAgent,
    OrchestratorAgent,
    AgentSystem,
    AgentFactory,
)


# ---------------------------------------------------------------------------
# Task state-transition tests
# ---------------------------------------------------------------------------

def test_task_valid_transition_pending_to_assigned():
    task = Task(description="test")
    assert task.transition_to(TaskStatus.ASSIGNED) is True
    assert task.status == TaskStatus.ASSIGNED
    assert task.assigned_at is not None


def test_task_invalid_transition_pending_to_completed():
    task = Task(description="test")
    assert task.transition_to(TaskStatus.COMPLETED) is False
    assert task.status == TaskStatus.PENDING


def test_task_transition_sets_started_at():
    task = Task(description="test")
    task.transition_to(TaskStatus.ASSIGNED)
    task.transition_to(TaskStatus.RUNNING)
    assert task.started_at is not None


# ---------------------------------------------------------------------------
# AgentMemory tests
# ---------------------------------------------------------------------------

def test_agent_memory_fifo_eviction():
    memory = AgentMemory(agent_id="a1", max_episodes=2)
    memory.store_episode("k1", "v1")
    memory.store_episode("k2", "v2")
    memory.store_episode("k3", "v3")

    assert memory.retrieve("k1", "episodic") is None
    assert memory.retrieve("k2", "episodic") == "v2"
    assert memory.retrieve("k3", "episodic") == "v3"


def test_agent_memory_semantic_access_count():
    memory = AgentMemory(agent_id="a2")
    memory.store_semantic("fact:x", {"value": 42})

    memory.retrieve("fact:x", "semantic")
    memory.retrieve("fact:x", "semantic")

    entry = memory.semantic_memory.get("fact:x")
    assert entry is not None
    assert entry["access_count"] == 2


# ---------------------------------------------------------------------------
# ExecutorAgent (BaseAgent) tests
# ---------------------------------------------------------------------------

def test_executor_successful_task_execution():
    agent = ExecutorAgent("exec")
    task = Task(description="run", parameters={"x": 1})
    assert agent.assign_task(task) is True

    result = agent.execute_task(task)

    assert task.status == TaskStatus.COMPLETED
    assert result["execution"] == "successful"
    assert agent.performance_metrics["tasks_completed"] == 1


def test_executor_active_task_cleaned_up_after_execution():
    agent = ExecutorAgent("exec-cleanup")
    task = Task(description="cleanup test")
    agent.assign_task(task)
    agent.execute_task(task)

    assert task.id not in agent.active_tasks


def test_executor_assign_task_respects_capacity():
    agent = ExecutorAgent("exec-cap")
    agent.max_active_tasks = 1

    task1 = Task(description="first")
    task2 = Task(description="second")

    assert agent.assign_task(task1) is True
    assert agent.assign_task(task2) is False


# ---------------------------------------------------------------------------
# OrchestratorAgent tests
# ---------------------------------------------------------------------------

def test_orchestrator_select_best_agent_prefers_less_busy():
    orchestrator = OrchestratorAgent("orch")

    busy_agent = ExecutorAgent("busy")
    idle_agent = ExecutorAgent("idle")

    # Give busy_agent an active task without executing it
    filler = Task(description="filler")
    busy_agent.assign_task(filler)

    orchestrator.register_agent(busy_agent)
    orchestrator.register_agent(idle_agent)

    task = Task(description="select-test")
    selected = orchestrator._select_best_agent(task)

    assert selected is idle_agent


def test_orchestrator_select_best_agent_skips_suspended():
    orchestrator = OrchestratorAgent("orch-suspend")
    suspended = ExecutorAgent("suspended")
    suspended.status = AgentStatus.SUSPENDED
    orchestrator.register_agent(suspended)

    task = Task(description="skip-suspended")
    selected = orchestrator._select_best_agent(task)

    assert selected is None


# ---------------------------------------------------------------------------
# AgentFactory tests
# ---------------------------------------------------------------------------

def test_agent_factory_create_team_composition():
    config = {"executor": 2, "analyzer": 1}
    system = AgentFactory.create_team(config)

    # The system includes the built-in orchestrator + 3 created agents
    assert system.system_metrics["total_agents"] == 4


def test_agent_factory_create_agent_unknown_type_returns_none():
    agent = AgentFactory.create_agent("nonexistent", "ghost")
    assert agent is None


# ---------------------------------------------------------------------------
# AgentSystem.execute_task() — retry/failure-path test (new addition)
# ---------------------------------------------------------------------------

def test_agent_system_execute_task_requeues_on_retry():
    """
    When an agent raises during execution and the task still has retries
    remaining, AgentSystem.execute_task() must re-add the task to
    global_task_queue so it can be dispatched again.
    """
    system = AgentSystem("retry-test-system")
    executor = ExecutorAgent("exec-retry")
    system.add_agent(executor)

    # Create task via system so it enters task_registry and global_task_queue
    task = system.create_task("retrying task", {}, max_retries=3)

    # Submit to executor so it is ASSIGNED (removed from global queue)
    submitted = system.submit_task(task, agent_id=executor.id)
    assert submitted is True
    assert task.status == TaskStatus.ASSIGNED
    assert task not in system.global_task_queue

    # Patch act() to raise, triggering the retry path inside BaseAgent.
    # AgentSystem.execute_task() re-raises after requeuing (by design), so we
    # assert on task state outside the raises block once the exception is caught.
    with patch.object(executor, "act", side_effect=RuntimeError("simulated failure")):
        with pytest.raises(RuntimeError, match="simulated failure"):
            system.execute_task(task.id, executor.id)

    # Task should have transitioned to RETRYING and been requeued
    assert task.status == TaskStatus.RETRYING
    assert task.retry_count == 1
    assert task in system.global_task_queue
