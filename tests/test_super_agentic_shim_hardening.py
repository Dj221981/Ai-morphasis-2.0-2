"""Hardening tests for the super_agentic_agents compatibility shim.

These tests enforce:
- Export parity between ``src.agents.super_agentic_agents`` and ``src.agents``
- Import-time backward compatibility for all public shim symbols
- Stable, explicit public API surface expected by legacy imports
"""

from importlib import import_module

import pytest


SHIM_MODULE = import_module("src.agents.super_agentic_agents")
PKG_MODULE = import_module("src.agents")


EXPECTED_EXPORTS = [
    "AgentRole",
    "AgentStatus",
    "TaskPriority",
    "TaskStatus",
    "TASK_STATUS_TRANSITIONS",
    "TaskCancelledError",
    "RetryPolicy",
    "ExecutionPolicy",
    "AgentCapability",
    "AgentMemory",
    "Task",
    "CAPABILITY_MATCH_BASE_SCORE",
    "DEFAULT_AGENT_BASE_SCORE",
    "BaseAgent",
    "OrchestratorAgent",
    "ExecutorAgent",
    "AnalyzerAgent",
    "LearnerAgent",
    "AgentSystem",
    "AgentFactory",
    "TaskRepository",
    "InMemoryTaskRepository",
    "SqlTaskRepository",
    "RedisTaskRepository",
    "TaskEventType",
    "TaskEvent",
    "InMemoryEventStore",
    "SqlEventStore",
    "RedisEventStore",
    "dispatch_pending_tasks",
    "process_retry_queue",
    "run_once",
    "run_forever",
]


def test_shim___all___matches_expected_public_contract():
    assert SHIM_MODULE.__all__ == EXPECTED_EXPORTS


def test_shim_exports_count_is_stable():
    assert len(SHIM_MODULE.__all__) == 33


@pytest.mark.parametrize("symbol", EXPECTED_EXPORTS)
def test_every_expected_symbol_exists_on_shim_module(symbol):
    assert hasattr(SHIM_MODULE, symbol), f"missing shim symbol: {symbol}"


@pytest.mark.parametrize("symbol", EXPECTED_EXPORTS)
def test_every_expected_symbol_exists_on_package_module(symbol):
    assert hasattr(PKG_MODULE, symbol), f"missing package symbol: {symbol}"


@pytest.mark.parametrize("symbol", EXPECTED_EXPORTS)
def test_shim_and_package_exports_point_to_same_object_identity(symbol):
    assert getattr(SHIM_MODULE, symbol) is getattr(PKG_MODULE, symbol)


def test_no_duplicate_entries_in_shim___all__():
    assert len(set(SHIM_MODULE.__all__)) == len(SHIM_MODULE.__all__)


def test_shim_re_exports_are_all_resolvable_via_getattr():
    resolved = [getattr(SHIM_MODULE, name) for name in SHIM_MODULE.__all__]
    assert all(obj is not None for obj in resolved)


def test_expected_callable_exports_remain_callable():
    callable_names = {
        "dispatch_pending_tasks",
        "process_retry_queue",
        "run_once",
        "run_forever",
    }
    for name in callable_names:
        assert callable(getattr(SHIM_MODULE, name))


def test_selected_class_exports_are_types():
    class_names = {
        "Task",
        "BaseAgent",
        "ExecutorAgent",
        "AnalyzerAgent",
        "LearnerAgent",
        "OrchestratorAgent",
        "AgentSystem",
        "AgentFactory",
        "TaskRepository",
        "InMemoryTaskRepository",
        "SqlTaskRepository",
        "RedisTaskRepository",
        "InMemoryEventStore",
        "SqlEventStore",
        "RedisEventStore",
    }
    for name in class_names:
        assert isinstance(getattr(SHIM_MODULE, name), type)


def test_wildcard_import_contract_matches___all__():
    # Simulate "from src.agents.super_agentic_agents import *"
    exported_names = set(SHIM_MODULE.__all__)
    assert exported_names == set(EXPECTED_EXPORTS)
