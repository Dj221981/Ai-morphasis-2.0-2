"""
Unit tests for Task lifecycle transitions and timestamp management.
"""

import pytest
from datetime import datetime

from src.agents.super_agentic_agents import Task, TaskStatus, TaskPriority


class TestTaskTransitions:
    """Tests for Task.transition_to guarded state machine."""

    def test_initial_status_is_pending(self):
        task = Task(description="test")
        assert task.status == TaskStatus.PENDING

    def test_pending_to_assigned_succeeds(self):
        task = Task(description="test")
        result = task.transition_to(TaskStatus.ASSIGNED)
        assert result is True
        assert task.status == TaskStatus.ASSIGNED

    def test_pending_to_cancelled_succeeds(self):
        task = Task(description="test")
        result = task.transition_to(TaskStatus.CANCELLED)
        assert result is True
        assert task.status == TaskStatus.CANCELLED

    def test_pending_to_running_is_invalid(self):
        task = Task(description="test")
        result = task.transition_to(TaskStatus.RUNNING)
        assert result is False
        assert task.status == TaskStatus.PENDING

    def test_pending_to_completed_is_invalid(self):
        task = Task(description="test")
        result = task.transition_to(TaskStatus.COMPLETED)
        assert result is False
        assert task.status == TaskStatus.PENDING

    def test_pending_to_failed_is_invalid(self):
        task = Task(description="test")
        result = task.transition_to(TaskStatus.FAILED)
        assert result is False
        assert task.status == TaskStatus.PENDING

    def test_assigned_to_running_succeeds(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        result = task.transition_to(TaskStatus.RUNNING)
        assert result is True
        assert task.status == TaskStatus.RUNNING

    def test_assigned_to_retrying_succeeds(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        result = task.transition_to(TaskStatus.RETRYING)
        assert result is True
        assert task.status == TaskStatus.RETRYING

    def test_assigned_to_cancelled_succeeds(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        result = task.transition_to(TaskStatus.CANCELLED)
        assert result is True
        assert task.status == TaskStatus.CANCELLED

    def test_running_to_completed_succeeds(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        result = task.transition_to(TaskStatus.COMPLETED)
        assert result is True
        assert task.status == TaskStatus.COMPLETED

    def test_running_to_failed_succeeds(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        result = task.transition_to(TaskStatus.FAILED)
        assert result is True
        assert task.status == TaskStatus.FAILED

    def test_running_to_retrying_succeeds(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        result = task.transition_to(TaskStatus.RETRYING)
        assert result is True
        assert task.status == TaskStatus.RETRYING

    def test_running_to_cancelled_succeeds(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        result = task.transition_to(TaskStatus.CANCELLED)
        assert result is True
        assert task.status == TaskStatus.CANCELLED

    def test_retrying_to_assigned_succeeds(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RETRYING)
        result = task.transition_to(TaskStatus.ASSIGNED)
        assert result is True
        assert task.status == TaskStatus.ASSIGNED

    def test_retrying_to_running_succeeds(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RETRYING)
        result = task.transition_to(TaskStatus.RUNNING)
        assert result is True
        assert task.status == TaskStatus.RUNNING

    def test_retrying_to_failed_succeeds(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RETRYING)
        result = task.transition_to(TaskStatus.FAILED)
        assert result is True
        assert task.status == TaskStatus.FAILED

    def test_completed_is_terminal_no_transitions(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.COMPLETED)
        for target in [TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.RUNNING,
                       TaskStatus.FAILED, TaskStatus.RETRYING, TaskStatus.CANCELLED]:
            result = task.transition_to(target)
            assert result is False
            assert task.status == TaskStatus.COMPLETED

    def test_failed_is_terminal_no_transitions(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.FAILED)
        for target in [TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.RUNNING,
                       TaskStatus.COMPLETED, TaskStatus.RETRYING, TaskStatus.CANCELLED]:
            result = task.transition_to(target)
            assert result is False
            assert task.status == TaskStatus.FAILED

    def test_cancelled_is_terminal_no_transitions(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.CANCELLED)
        for target in [TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.RUNNING,
                       TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.RETRYING]:
            result = task.transition_to(target)
            assert result is False
            assert task.status == TaskStatus.CANCELLED


class TestTaskTimestamps:
    """Tests that transition_to sets the correct timestamp fields."""

    def test_assigned_at_set_on_assigned(self):
        task = Task(description="test")
        assert task.assigned_at is None
        task.transition_to(TaskStatus.ASSIGNED)
        assert task.assigned_at is not None
        assert isinstance(task.assigned_at, datetime)

    def test_started_at_set_on_running(self):
        task = Task(description="test")
        assert task.started_at is None
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        assert task.started_at is not None
        assert isinstance(task.started_at, datetime)

    def test_completed_at_set_on_completed(self):
        task = Task(description="test")
        assert task.completed_at is None
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.COMPLETED)
        assert task.completed_at is not None
        assert isinstance(task.completed_at, datetime)

    def test_completed_at_set_on_failed(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RUNNING)
        task.transition_to(TaskStatus.FAILED)
        assert task.completed_at is not None

    def test_completed_at_set_on_cancelled(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.CANCELLED)
        assert task.completed_at is not None

    def test_last_retry_at_set_on_retrying(self):
        task = Task(description="test")
        assert task.last_retry_at is None
        task.transition_to(TaskStatus.ASSIGNED)
        task.transition_to(TaskStatus.RETRYING)
        assert task.last_retry_at is not None
        assert isinstance(task.last_retry_at, datetime)

    def test_invalid_transition_does_not_mutate_timestamps(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.COMPLETED)  # invalid
        assert task.assigned_at is None
        assert task.started_at is None
        assert task.completed_at is None

    def test_started_at_not_set_on_assigned(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        assert task.started_at is None

    def test_assigned_at_not_set_on_running(self):
        task = Task(description="test")
        task.transition_to(TaskStatus.ASSIGNED)
        assigned_at = task.assigned_at
        task.transition_to(TaskStatus.RUNNING)
        assert task.assigned_at == assigned_at


class TestTaskDefaults:
    """Tests for Task default values and ID generation."""

    def test_task_id_is_generated(self):
        task = Task(description="test")
        assert task.id is not None
        assert len(task.id) > 0

    def test_task_ids_are_unique(self):
        task1 = Task(description="t1")
        task2 = Task(description="t2")
        assert task1.id != task2.id

    def test_task_default_priority_is_normal(self):
        task = Task(description="test")
        assert task.priority == TaskPriority.NORMAL

    def test_task_default_max_retries(self):
        task = Task(description="test")
        assert task.max_retries == 3

    def test_task_to_dict_contains_expected_keys(self):
        task = Task(description="test task", parameters={"k": "v"})
        d = task.to_dict()
        for key in ["id", "description", "priority", "status", "created_at",
                    "assigned_at", "started_at", "completed_at", "result",
                    "error", "parameters", "retry_count", "max_retries"]:
            assert key in d
