"""
src/agents/base.py
==================
Abstract base class for all agents in the super-agentic framework.
"""

import uuid
import logging
import threading
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta

from .models import (
    AgentRole,
    AgentStatus,
    AgentCapability,
    AgentMemory,
    Task,
    TaskStatus,
    TaskCancelledError,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        name: str,
        role: AgentRole = AgentRole.EXECUTOR,
        max_capabilities: int = 50,
        max_active_tasks: int = 10,
    ):
        """Initialize a base agent."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Agent name must be a non-empty string")
        self.id = str(uuid.uuid4())
        self.name = name.strip()
        self.role = role
        self.status = AgentStatus.IDLE
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

        self.capabilities: Dict[str, AgentCapability] = {}
        self.max_capabilities = max_capabilities
        self.memory = AgentMemory(agent_id=self.id)

        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: List[Task] = []
        self.task_history: List[Task] = []
        self.max_active_tasks = max_active_tasks

        self.parent_agent: Optional[str] = None
        self.child_agents: set = set()
        self.peer_agents: set = set()

        self.performance_metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_task_time": 0.0,
            "success_rate": 1.0
        }

        self._lock = threading.RLock()
        self.enable_forced_status_fallback = False
        self.telemetry_hook: Optional[Callable[[str, Dict[str, Any]], None]] = None

        logger.info(f"Initialized {self.role.value} agent: {self.name} (ID: {self.id})")

    @abstractmethod
    def think(self, input_data: Any) -> Dict[str, Any]:
        """Core reasoning method - must be implemented by subclasses."""
        pass

    @abstractmethod
    def act(self, decision: Dict[str, Any]) -> Any:
        """Execution method - must be implemented by subclasses."""
        pass

    def register_capability(self, capability: AgentCapability) -> bool:
        """Register a new capability."""
        with self._lock:
            if len(self.capabilities) >= self.max_capabilities:
                logger.warning(f"Agent {self.name} has reached max capabilities limit")
                return False

            self.capabilities[capability.name] = capability
            self.memory.store_semantic(f"capability:{capability.name}", capability)
            self.last_activity = datetime.now()

        logger.info(f"Capability '{capability.name}' registered for {self.name}")
        return True

    def get_capability(self, name: str) -> Optional[AgentCapability]:
        """Retrieve a registered capability."""
        with self._lock:
            return self.capabilities.get(name)

    def list_capabilities(self) -> List[str]:
        """Get list of all capability names."""
        with self._lock:
            return list(self.capabilities.keys())

    def assign_task(self, task: Task) -> bool:
        """Assign a task to this agent."""
        with self._lock:
            if len(self.active_tasks) >= self.max_active_tasks:
                logger.warning(
                    f"Agent {self.name} at capacity ({self.max_active_tasks}); cannot assign task {task.id}"
                )
                return False

            if task.status == TaskStatus.PENDING:
                if not task.transition_to(TaskStatus.ASSIGNED):
                    return False
            elif task.status not in (TaskStatus.RETRYING, TaskStatus.ASSIGNED):
                logger.warning(
                    f"Task {task.id} in invalid state for assignment: {task.status.value}"
                )
                return False

            task.assigned_to = self.id
            self.active_tasks[task.id] = task
            self.memory.store_episode(f"task:{task.id}", task)
            self.last_activity = datetime.now()

        logger.info(f"Task {task.id} assigned to agent {self.name}")
        return True

    def execute_task(self, task: Task) -> Any:
        """Execute an assigned task with retry and safe cleanup semantics."""
        start_time = datetime.now()
        attempt = task.retry_count + 1
        task.execution_metadata["attempt"] = attempt
        task.execution_metadata["agent_id"] = self.id
        task.execution_metadata["started_at"] = start_time.isoformat()

        try:
            with self._lock:
                self.status = AgentStatus.BUSY
                self.last_activity = datetime.now()

                if task.status in (TaskStatus.ASSIGNED, TaskStatus.RETRYING):
                    if not task.transition_to(TaskStatus.RUNNING):
                        raise RuntimeError(
                            f"Task {task.id} cannot transition to running from {task.status.value}"
                        )
                elif task.status != TaskStatus.RUNNING:
                    raise RuntimeError(
                        f"Task {task.id} must be assigned/retrying/running to execute; got {task.status.value}"
                    )

            logger.info(f"Agent {self.name} executing task {task.id}")
            self._emit_telemetry("task_started", task, {"attempt": attempt})

            # Keep checks around each phase boundary to catch cancellation/timeouts
            # that happen between think/act handoffs in long-running tasks.
            self._raise_if_stopped(task, start_time)

            # Think phase
            self._raise_if_stopped(task, start_time)
            reasoning = self.think(task.parameters)
            self._raise_if_stopped(task, start_time)

            # Act phase
            self._raise_if_stopped(task, start_time)
            result = self.act(reasoning)
            self._raise_if_stopped(task, start_time)

            with self._lock:
                if not task.transition_to(TaskStatus.COMPLETED):
                    raise RuntimeError(
                        f"Task {task.id} failed status transition to completed from {task.status.value}"
                    )
                task.result = result
                task.error = None
                self.completed_tasks.append(task)
                self.task_history.append(task)
                self._update_metrics(task, success=True, started_at=start_time)
                self.status = AgentStatus.IDLE
                self.last_activity = datetime.now()
                task.next_retry_at = None
                task.execution_metadata["duration_seconds"] = max(
                    (datetime.now() - start_time).total_seconds(),
                    0.0,
                )
                task.execution_metadata["completed_at"] = datetime.now().isoformat()
                task.execution_metadata["failure_reason"] = None

            logger.info(f"Task {task.id} completed successfully")
            self._emit_telemetry("task_completed", task, {"attempt": attempt})
            return result

        except Exception as e:
            with self._lock:
                task.error = str(e)
                now = datetime.now()
                task.execution_metadata["duration_seconds"] = max(
                    (now - start_time).total_seconds(),
                    0.0,
                )
                task.execution_metadata["completed_at"] = now.isoformat()
                task.execution_metadata["failure_reason"] = type(e).__name__

                is_cancelled = isinstance(e, TaskCancelledError)

                if is_cancelled:
                    if task.status != TaskStatus.CANCELLED and not task.transition_to(TaskStatus.CANCELLED):
                        self._force_task_status(task, TaskStatus.CANCELLED)
                    task.next_retry_at = None
                elif task.retry_count < task.max_retries:
                    task.retry_count += 1
                    # The task may already be in RETRYING state from a prior retry
                    # iteration; skip the transition in that case.
                    if task.status != TaskStatus.RETRYING:
                        if not task.transition_to(TaskStatus.RETRYING):
                            self._force_task_status(task, TaskStatus.RETRYING)
                    task.next_retry_at = self._calculate_next_retry_at(task)
                else:
                    if not task.transition_to(TaskStatus.FAILED) and task.status != TaskStatus.FAILED:
                        self._force_task_status(task, TaskStatus.FAILED)
                    task.next_retry_at = None

                self.task_history.append(task)
                self._update_metrics(task, success=False, started_at=start_time)
                self.status = AgentStatus.ERROR
                self.last_activity = datetime.now()

            logger.error(f"Task {task.id} failed: {str(e)}")
            if task.status == TaskStatus.RETRYING:
                logger.info(
                    f"Task {task.id} marked for retry ({task.retry_count}/{task.max_retries})"
                )
            self._emit_telemetry(
                "task_failed",
                task,
                {"attempt": attempt, "error_type": type(e).__name__, "error": str(e)},
            )
            raise

        finally:
            with self._lock:
                self.active_tasks.pop(task.id, None)
                if self.status not in (AgentStatus.SUSPENDED,):
                    # Avoid permanent ERROR lock-in for recoverable failures
                    self.status = AgentStatus.IDLE
                self.last_activity = datetime.now()

    def _force_task_status(self, task: Task, new_status: TaskStatus) -> None:
        """
        Force-set task status as a last-resort fallback when a guarded
        ``transition_to()`` call returns False and the task must still reach
        a terminal or retry state.

        This method must only be called after ``transition_to()`` has already
        been attempted and failed.  It logs a warning so the bypass is always
        visible in logs and avoids silently hiding model inconsistencies.
        """
        if not (
            self.enable_forced_status_fallback
            and bool(task.metadata.get("allow_forced_status_fallback"))
        ):
            raise RuntimeError(
                f"Refused forced status transition for task {task.id}: "
                f"{task.status.value} -> {new_status.value}"
            )

        logger.warning(
            "Task %s: forced status %s -> %s "
            "(guarded transition unavailable from current state)",
            task.id, task.status.value, new_status.value,
        )
        task.status = new_status
        now = datetime.now()
        if new_status == TaskStatus.RETRYING:
            task.last_retry_at = now
        elif new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.completed_at = now

    def _emit_telemetry(self, event: str, task: Task, payload: Optional[Dict[str, Any]] = None) -> None:
        """Emit a structured telemetry event for observability hooks."""
        if not self.telemetry_hook:
            return
        telemetry_payload = {
            "event": event,
            "agent_id": self.id,
            "agent_name": self.name,
            "task_id": task.id,
            "task_status": task.status.value,
            "timestamp": datetime.now().isoformat(),
        }
        if payload:
            telemetry_payload.update(payload)
        try:
            self.telemetry_hook(event, telemetry_payload)
        except Exception:
            logger.exception(
                "Telemetry hook failed for agent event=%s task_id=%s agent_id=%s",
                event,
                task.id,
                self.id,
            )

    def _calculate_next_retry_at(self, task: Task) -> datetime:
        """Calculate retry schedule using bounded exponential backoff + jitter."""
        metadata = task.metadata
        base_delay = float(metadata.get("retry_backoff_base_seconds", 1.0))
        max_delay = float(metadata.get("retry_backoff_max_seconds", 30.0))
        jitter_max = float(metadata.get("retry_jitter_seconds", 0.5))
        retry_index = min(max(task.retry_count, 0), 16)
        backoff = min(base_delay * (2 ** retry_index), max_delay)
        jitter = random.uniform(0.0, max(jitter_max, 0.0))
        return datetime.now() + timedelta(seconds=backoff + jitter)

    def _raise_if_timed_out(self, task: Task, started_at: datetime) -> None:
        timeout_seconds = task.metadata.get("timeout_seconds")
        if timeout_seconds is None:
            return
        elapsed = (datetime.now() - started_at).total_seconds()
        if elapsed > float(timeout_seconds):
            raise TimeoutError(
                f"Task {task.id} timed out after {elapsed:.3f}s "
                f"(limit: {float(timeout_seconds):.3f}s)"
            )

    def _raise_if_cancelled(self, task: Task) -> None:
        if task.status == TaskStatus.CANCELLED or bool(task.metadata.get("cancel_requested")):
            raise TaskCancelledError(f"Task {task.id} was cancelled before completion")
        cancellation_check = task.metadata.get("cancellation_check")
        if callable(cancellation_check):
            try:
                if cancellation_check(task):
                    raise TaskCancelledError(
                        f"Task {task.id} cancellation hook requested stop"
                    )
            except TaskCancelledError:
                raise
            except Exception as exc:
                logger.exception(
                    "Cancellation check callable failed task_id=%s", task.id
                )
                raise RuntimeError(
                    f"Task {task.id} cancellation check callable failed: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

    def _raise_if_stopped(self, task: Task, started_at: datetime) -> None:
        """Run cooperative timeout/cancellation checks at execution boundaries."""
        self._raise_if_timed_out(task, started_at)
        self._raise_if_cancelled(task)

    def _update_metrics(self, task: Task, success: bool, started_at: Optional[datetime] = None) -> None:
        """Update performance metrics with rolling average duration."""
        if success:
            self.performance_metrics["tasks_completed"] += 1
        else:
            self.performance_metrics["tasks_failed"] += 1

        total = self.performance_metrics["tasks_completed"] + self.performance_metrics["tasks_failed"]
        self.performance_metrics["success_rate"] = (
            self.performance_metrics["tasks_completed"] / total if total > 0 else 0
        )

        # Compute rolling average task duration in seconds
        end_time = task.completed_at or datetime.now()
        ref_start = task.started_at or started_at or task.created_at
        duration = max((end_time - ref_start).total_seconds(), 0.0)

        current_avg = self.performance_metrics.get("avg_task_time", 0.0)
        if total > 0:
            self.performance_metrics["avg_task_time"] = ((current_avg * (total - 1)) + duration) / total

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        with self._lock:
            return {
                "id": self.id,
                "name": self.name,
                "role": self.role.name,
                "status": self.status.name,
                "capabilities": list(self.capabilities.keys()),
                "active_tasks": len(self.active_tasks),
                "completed_tasks": len(self.completed_tasks),
                "performance": dict(self.performance_metrics),
                "created_at": self.created_at.isoformat(),
                "last_activity": self.last_activity.isoformat()
            }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name} ({self.role.value})>"
