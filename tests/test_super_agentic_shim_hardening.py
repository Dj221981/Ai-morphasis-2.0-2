"""Hardening tests for the super_agentic_agents compatibility shim.

These tests enforce:
- Export parity between ``src.agents.super_agentic_agents`` and ``src.agents``
- Import-time backward compatibility for all public shim symbols
- Stable, explicit public API surface expected by legacy imports
- Import guard and validation function correctness
"""

import sys
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


# ---------------------------------------------------------------------------
# Tests for the new validation helpers
# ---------------------------------------------------------------------------


def test_validate_all_modules_is_importable():
    """validate_all_modules must be a callable attribute of the shim."""
    assert callable(SHIM_MODULE.validate_all_modules)


def test_validate_all_modules_runs_without_error():
    """validate_all_modules() must succeed in a healthy environment."""
    SHIM_MODULE.validate_all_modules()


def test_validate_shim_integrity_is_importable():
    """validate_shim_integrity must be a callable attribute of the shim."""
    assert callable(SHIM_MODULE.validate_shim_integrity)


def test_validate_shim_integrity_runs_without_error():
    """validate_shim_integrity() must succeed in a healthy environment."""
    SHIM_MODULE.validate_shim_integrity()


def test_validate_all_modules_raises_on_missing_submodule(monkeypatch):
    """validate_all_modules() must raise ImportError with a descriptive message
    when a required sub-module cannot be imported."""
    import importlib

    # Remove the target sub-module from the cache so importlib will attempt a
    # fresh import, then replace it with None (which forces ImportError).
    target = "src.agents.runtime"
    monkeypatch.delitem(sys.modules, target, raising=False)
    monkeypatch.setitem(sys.modules, target, None)

    with pytest.raises(ImportError, match=target):
        SHIM_MODULE.validate_all_modules()


def test_validate_shim_integrity_raises_when___all___has_phantom_name():
    """validate_shim_integrity() must raise AssertionError when __all__ contains
    a name that is not actually present on the shim module."""
    original_all = SHIM_MODULE.__all__
    try:
        SHIM_MODULE.__all__ = original_all + ["_NonExistentSymbol_"]
        with pytest.raises(AssertionError, match="_NonExistentSymbol_"):
            SHIM_MODULE.validate_shim_integrity()
    finally:
        SHIM_MODULE.__all__ = original_all


def test_import_guard_error_message_is_informative(monkeypatch):
    """When src.agents is broken, the ImportError must mention 'super_agentic_agents'
    so that the error is clearly attributable to the shim."""
    import importlib
    import types

    shim_name = "src.agents.super_agentic_agents"

    # Remove the shim from the module cache so it will re-execute its import block.
    for k in list(sys.modules.keys()):
        if k == shim_name:
            monkeypatch.delitem(sys.modules, k)

    # Place a stub src.agents with no exported symbols so that
    # "from src.agents import AgentRole ..." raises ImportError.
    broken_pkg = types.ModuleType("src.agents")
    monkeypatch.setitem(sys.modules, "src.agents", broken_pkg)

    with pytest.raises(ImportError, match="super_agentic_agents"):
        importlib.import_module(shim_name)


def test_validate_all_modules_not_in___all__():
    """Validation helpers are implementation details, not public API exports."""
    assert "validate_all_modules" not in SHIM_MODULE.__all__
    assert "validate_shim_integrity" not in SHIM_MODULE.__all__
