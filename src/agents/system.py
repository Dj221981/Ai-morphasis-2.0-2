"""
src/agents/system.py
====================
Central agent management system and factory for the super-agentic framework.

Contains:
- AgentSystem — manages agent lifecycle, task orchestration, and coordination
  with new features: cancel_task, is_task_ready, dependency validation,
  dispatch_pending_tasks, process_retry_queue, run_once
- AgentFactory — factory for creating agents with standard configurations
- example_usage — demonstration function
"""

import uuid
import json
import logging
import threading
from typing import Any, Dict, List, Optional, Callable, Set

from datetime import datetime

from .models import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskCancelledError,
)
from .base import BaseAgent
from .specialized import (
    OrchestratorAgent,
    ExecutorAgent,
    AnalyzerAgent,
    LearnerAgent,
)

logger = logging.getLogger(__name__)


class AgentSystem:
    """
    Central management system for all agents.
    Handles agent lifecycle, orchestration, and inter-agent communication.
    """

    def __init__(self, name: str = "Ai-morphasis"):
        self.name = name
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now()

        self.orchestrator = OrchestratorAgent(f"{name}-Orchestrator")
        self.agents: Dict[str, BaseAgent] = {self.orchestrator.id: self.orchestrator}
        self.global_task_queue: List[Task] = []
        self._queued_task_ids: Set[str] = set()
        self.completed_tasks: List[Task] = []
        self._completed_task_ids: Set[str] = set()
        self.task_registry: Dict[str, Task] = {}

        self.system_metrics = {
            "total_agents": 1,
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "avg_task_duration": 0.0
        }

        self._lock = threading.RLock()
        self.persistence_hook: Optional[Callable[[str, Task], None]] = None
        self.telemetry_hook: Optional[Callable[[str, Dict[str, Any]], None]] = None

        logger.info(f"Initialized Agent System: {self.name}")

    def add_agent(self, agent: BaseAgent) -> bool:
        """Add an agent to the system."""
        with self._lock:
            self.agents[agent.id] = agent
            self.orchestrator.register_agent(agent)
            agent.telemetry_hook = self._emit_telemetry
            self.system_metrics["total_agents"] += 1
        logger.info(f"Agent {agent.name} added to system")
        self._emit_telemetry(
            "agent_added",
            {"agent_id": agent.id, "agent_name": agent.name, "role": agent.role.value},
        )
        return True

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the system and clean up all references.

        Cleans up:
        - ``orchestrator.managed_agents``
        - ``parent_agent`` back-reference on the removed agent
        - peer-agent cross-references (both directions)
        - ``parent_agent`` references on child agents that pointed to the
          removed agent
        """
        with self._lock:
            if agent_id not in self.agents:
                return False

            agent = self.agents.pop(agent_id)
            self.system_metrics["total_agents"] -= 1

            # Remove from orchestrator managed registry
            self.orchestrator.managed_agents.pop(agent_id, None)

            # Clear the agent's own parent back-reference
            agent.parent_agent = None

            # Remove this agent from its peers' peer sets (both directions)
            for peer_id in list(agent.peer_agents):
                peer = self.agents.get(peer_id)
                if peer is not None:
                    peer.peer_agents.discard(agent_id)
            agent.peer_agents.clear()

            # Clear parent reference on child agents that pointed here
            for child_id in list(agent.child_agents):
                child = self.agents.get(child_id)
                if child is not None and child.parent_agent == agent_id:
                    child.parent_agent = None
            agent.child_agents.clear()

            logger.info(f"Agent {agent.name} removed from system")
            self._emit_telemetry(
                "agent_removed",
                {"agent_id": agent.id, "agent_name": agent.name, "role": agent.role.value},
            )
            return True

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Retrieve an agent by ID."""
        with self._lock:
            return self.agents.get(agent_id)

    def create_task(
        self,
        description: str,
        parameters: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        dependencies: Optional[List[str]] = None,
    ) -> Task:
        """Create a new task.

        Parameters
        ----------
        description:
            Human-readable task description. Must not be empty.
        parameters:
            Task payload dictionary. Defensive-copied on creation.
        priority:
            Task scheduling priority.
        max_retries:
            Number of times the task may be retried on failure.
        dependencies:
            Optional list of task IDs that must complete before this task runs.
            Validated against the task registry at creation time.
        """
        if not (isinstance(description, str) and description.strip()):
            raise ValueError("Task description must not be empty")
        cleaned_description = description.strip()
        if not isinstance(parameters, dict):
            raise TypeError("Task parameters must be a dictionary")
        # Defensive copy: isolates task payload from caller-side mutation after creation.
        task_parameters = dict(parameters)
        if not isinstance(priority, TaskPriority):
            raise TypeError("Task priority must be a TaskPriority enum value")
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("Task max_retries must be a non-negative integer")

        metadata = task_parameters.get("metadata", {})
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("Task metadata must be a dictionary")
        task_metadata = dict(metadata) if metadata else {}

        timeout_seconds = task_parameters.get("timeout_seconds")
        if timeout_seconds is not None:
            try:
                timeout_seconds = float(timeout_seconds)
            except (TypeError, ValueError) as exc:
                raise ValueError("Task timeout_seconds must be a positive number") from exc
            if timeout_seconds <= 0:
                raise ValueError("Task timeout_seconds must be greater than 0 when provided")

        required_capabilities = task_parameters.get("required_capabilities")
        if required_capabilities is not None and (
            not isinstance(required_capabilities, list)
            or len(required_capabilities) == 0
            or any(not isinstance(cap, str) or not cap.strip() for cap in required_capabilities)
        ):
            raise ValueError("Task required_capabilities must be a list of non-empty strings")

        task = Task(
            description=cleaned_description,
            parameters=task_parameters,
            priority=priority,
            max_retries=max_retries,
            metadata=task_metadata,
        )
        if timeout_seconds is not None:
            task.metadata["timeout_seconds"] = timeout_seconds
        if required_capabilities is not None:
            task.metadata["required_capabilities"] = [cap.strip() for cap in required_capabilities]

        # Validate and attach dependency IDs
        if dependencies:
            if not isinstance(dependencies, list):
                raise TypeError("dependencies must be a list of task ID strings")
            with self._lock:
                self._validate_dependencies_locked(task.id, dependencies)
            task.dependencies = list(dependencies)

        with self._lock:
            self._queue_task_if_absent(task)
            self.task_registry[task.id] = task
            self.system_metrics["total_tasks"] += 1
            self._persist_task("created", task)
        logger.info(f"Task {task.id} created: {description}")
        self._emit_telemetry(
            "task_created",
            {"task_id": task.id, "priority": task.priority.name, "max_retries": task.max_retries},
        )
        return task

    def submit_task(self, task: Task, agent_id: Optional[str] = None) -> bool:
        """Submit a task to an agent for execution."""
        if task.status == TaskStatus.RETRYING and not self._is_retry_due(task):
            logger.info(
                "Task %s retry is scheduled for %s; skipping immediate assignment",
                task.id,
                task.next_retry_at.isoformat() if task.next_retry_at else "unknown",
            )
            return False

        if agent_id:
            agent = self.get_agent(agent_id)
            if agent:
                assigned = agent.assign_task(task)
                if assigned:
                    self._remove_from_global_queue(task.id)
                    self._persist_task("submitted", task)
                return assigned
        else:
            assigned = self.orchestrator.distribute_task(task)
            if assigned:
                self._remove_from_global_queue(task.id)
                self._persist_task("submitted", task)
            return assigned

        logger.warning(f"Failed to submit task {task.id}")
        return False

    def execute_task(self, task_id: str, agent_id: str) -> Any:
        """Execute a task via a specific agent and aggregate system metrics/state."""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        task = self.task_registry.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        start_time = datetime.now()
        logger.info(
            "System executing task task_id=%s agent_id=%s status=%s retry_count=%s",
            task.id,
            agent.id,
            task.status.value,
            task.retry_count,
        )
        try:
            result = agent.execute_task(task)
            with self._lock:
                if task.status == TaskStatus.COMPLETED:
                    self._add_completed_task(task)
                    self.system_metrics["successful_tasks"] += 1
                self._update_system_task_duration(task, start_time)
                self._persist_task("completed", task)
            return result
        except Exception:
            with self._lock:
                if task.status == TaskStatus.RETRYING:
                    # Requeue for retry dispatch, guarding against duplicates
                    self._queue_task_if_absent(task)
                    self._persist_task("retry_scheduled", task)
                elif task.status == TaskStatus.CANCELLED:
                    self._persist_task("cancelled", task)
                elif task.status == TaskStatus.FAILED:
                    self.system_metrics["failed_tasks"] += 1
                    self._persist_task("failed", task)
                self._update_system_task_duration(task, start_time)
            raise

    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Cancel a task by ID.

        For PENDING/ASSIGNED tasks the transition is immediate.
        For RUNNING tasks, sets ``cancel_requested`` in metadata so the
        cooperative cancellation check inside ``execute_task`` fires on the
        next boundary check.

        Returns True if the task was found and cancellation was initiated,
        False otherwise.
        """
        with self._lock:
            task = self.task_registry.get(task_id)
            if task is None:
                logger.warning("cancel_task: task_id=%s not found", task_id)
                return False

            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                logger.info(
                    "cancel_task: task_id=%s already in terminal state %s; skipping",
                    task_id,
                    task.status.value,
                )
                return False

            if task.status == TaskStatus.RUNNING:
                # Signal cooperative cancellation; the execute_task loop will
                # pick this up at the next _raise_if_stopped boundary.
                task.metadata["cancel_requested"] = True
                if reason:
                    task.metadata["cancellation_reason"] = reason
                logger.info("cancel_task: requested cooperative cancel for running task_id=%s", task_id)
                self._persist_task("cancel_requested", task)
                return True

            # PENDING, ASSIGNED, RETRYING — transition immediately
            if task.mark_cancelled(reason=reason):
                self._remove_from_global_queue(task_id)
                self._persist_task("cancelled", task)
                self._emit_telemetry(
                    "task_cancelled",
                    {"task_id": task_id, "reason": reason or ""},
                )
                logger.info("cancel_task: task_id=%s cancelled", task_id)
                return True

            logger.warning(
                "cancel_task: could not transition task_id=%s from %s to CANCELLED",
                task_id,
                task.status.value,
            )
            return False

    def is_task_ready(self, task: Task) -> bool:
        """Return True if all task dependencies have completed successfully."""
        with self._lock:
            return self._is_task_ready_locked(task)

    def _is_task_ready_locked(self, task: Task) -> bool:
        """Check dependency readiness (caller must hold ``self._lock``)."""
        for dep_id in task.dependencies:
            dep_task = self.task_registry.get(dep_id)
            if dep_task is None or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def _validate_dependencies_locked(self, task_id: str, dep_ids: List[str]) -> None:
        """Validate dependency IDs and reject self-references or unknown IDs.

        Caller must hold ``self._lock``.
        """
        for dep_id in dep_ids:
            if not isinstance(dep_id, str) or not dep_id.strip():
                raise ValueError("Each dependency must be a non-empty task ID string")
            if dep_id == task_id:
                raise ValueError(f"Task {task_id} cannot depend on itself")
            if dep_id not in self.task_registry:
                raise ValueError(
                    f"Dependency task_id={dep_id!r} does not exist in the task registry"
                )

    # ------------------------------------------------------------------
    # Scheduler helpers
    # ------------------------------------------------------------------

    def dispatch_pending_tasks(self) -> int:
        """Submit all ready pending/retrying tasks from the global queue.

        Tasks are dispatched in priority-then-age order (highest priority and
        oldest tasks first).  Dependency-blocked tasks are skipped.

        Returns the number of tasks successfully dispatched.
        """
        with self._lock:
            candidates = [
                t for t in self.global_task_queue
                if t.status in (TaskStatus.PENDING, TaskStatus.RETRYING)
            ]

        # Sort: higher priority value first; then older tasks first (smaller created_at)
        candidates.sort(key=lambda t: (-t.priority.value, t.created_at))

        dispatched = 0
        for task in candidates:
            with self._lock:
                if not self._is_task_ready_locked(task):
                    logger.debug(
                        "dispatch_pending_tasks: task_id=%s blocked by unfinished dependencies",
                        task.id,
                    )
                    continue
            if task.status == TaskStatus.RETRYING and not self._is_retry_due(task):
                continue
            if self.submit_task(task):
                dispatched += 1
        return dispatched

    def process_retry_queue(self) -> int:
        """Resubmit tasks in RETRYING state whose ``next_retry_at`` is past due.

        Returns the number of tasks resubmitted.
        """
        with self._lock:
            retrying = [
                t for t in self.global_task_queue
                if t.status == TaskStatus.RETRYING
            ]

        resubmitted = 0
        for task in retrying:
            if self._is_retry_due(task):
                if self.submit_task(task):
                    resubmitted += 1
        return resubmitted

    def run_once(self) -> Dict[str, int]:
        """Perform one scheduling cycle: dispatch pending tasks and process retries.

        Returns a summary dict with ``dispatched`` and ``retried`` counts.
        """
        dispatched = self.dispatch_pending_tasks()
        retried = self.process_retry_queue()
        logger.info(
            "run_once: dispatched=%d retried=%d system=%s",
            dispatched,
            retried,
            self.name,
        )
        return {"dispatched": dispatched, "retried": retried}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _remove_from_global_queue(self, task_id: str) -> None:
        """Remove task from global queue if present."""
        with self._lock:
            self._assert_lock_held()
            self.global_task_queue = [t for t in self.global_task_queue if t.id != task_id]
            self._queued_task_ids.discard(task_id)

    def _queue_task_if_absent(self, task: Task) -> None:
        """Queue a task once, guarding against duplicate entries.

        Callers must hold ``self._lock``.
        """
        self._assert_lock_held()
        if task.id in self._queued_task_ids:
            logger.debug("Skipped duplicate queue entry for task_id=%s", task.id)
            return
        self.global_task_queue.append(task)
        self._queued_task_ids.add(task.id)
        logger.info("Task queued task_id=%s status=%s", task.id, task.status.value)

    def _add_completed_task(self, task: Task) -> None:
        """Track a completed task once, guarding against duplicate aggregation.

        Callers must hold ``self._lock``.
        """
        self._assert_lock_held()
        if task.id in self._completed_task_ids:
            logger.debug("Skipped duplicate completed task aggregation for task_id=%s", task.id)
            return
        self.completed_tasks.append(task)
        self._completed_task_ids.add(task.id)
        logger.info("Task marked completed in system task_id=%s", task.id)

    def _assert_lock_held(self) -> None:
        """Ensure mutation helpers are called while holding the system lock.

        This is a best-effort check coupled to CPython ``threading.RLock`` via its
        private ``_is_owned`` API; for other lock implementations the check is skipped.
        """
        is_owned = getattr(self._lock, "_is_owned", None)
        if not callable(is_owned):
            return
        if not is_owned():
            raise RuntimeError("AgentSystem internal mutation requires self._lock")

    def _update_system_task_duration(self, task: Task, fallback_start: datetime) -> None:
        """Update system-level rolling average task duration (seconds)."""
        completed = self.system_metrics["successful_tasks"] + self.system_metrics["failed_tasks"]
        if completed <= 0:
            return

        end_time = task.completed_at or datetime.now()
        start_time = task.started_at or fallback_start
        duration = max((end_time - start_time).total_seconds(), 0.0)

        current_avg = self.system_metrics.get("avg_task_duration", 0.0)
        self.system_metrics["avg_task_duration"] = ((current_avg * (completed - 1)) + duration) / completed

    def _is_retry_due(self, task: Task) -> bool:
        """Return True when retry is due; unscheduled retries are treated as immediately due."""
        return task.next_retry_at is None or datetime.now() >= task.next_retry_at

    def set_persistence_hook(self, hook: Optional[Callable[[str, Task], None]]) -> None:
        """Register persistence extension hook invoked on task lifecycle events."""
        self.persistence_hook = hook

    def set_telemetry_hook(self, hook: Optional[Callable[[str, Dict[str, Any]], None]]) -> None:
        """Register structured telemetry extension hook."""
        self.telemetry_hook = hook
        self.orchestrator.telemetry_hook = self._emit_telemetry
        for agent in self.agents.values():
            agent.telemetry_hook = self._emit_telemetry

    def _persist_task(self, event: str, task: Task) -> None:
        """Invoke persistence extension hook, if configured."""
        if self.persistence_hook:
            try:
                self.persistence_hook(event, task)
            except Exception:
                logger.exception(
                    "Persistence hook failed event=%s task_id=%s status=%s",
                    event,
                    task.id,
                    task.status.value,
                )

    def _emit_telemetry(self, event: str, payload: Dict[str, Any]) -> None:
        """Emit structured telemetry event for system-level observability."""
        if not self.telemetry_hook:
            return
        event_payload = {
            "event": event,
            "system_id": self.id,
            "system_name": self.name,
            "timestamp": datetime.now().isoformat(),
        }
        event_payload.update(payload)
        try:
            self.telemetry_hook(event, event_payload)
        except Exception:
            logger.exception(
                "System telemetry hook failed event=%s system_id=%s",
                event,
                self.id,
            )

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        with self._lock:
            return {
                "system_name": self.name,
                "system_id": self.id,
                "created_at": self.created_at.isoformat(),
                "agents": {aid: agent.get_status() for aid, agent in self.agents.items()},
                "metrics": dict(self.system_metrics),
                "pending_tasks": len(self.global_task_queue),
                "completed_tasks": len(self.completed_tasks)
            }

    def to_json(self) -> str:
        """Serialize system status to JSON."""
        return json.dumps(self.get_system_status(), indent=2, default=str)

    def __repr__(self) -> str:
        return f"<AgentSystem: {self.name} ({len(self.agents)} agents)>"


# ============================================================================
# Factory and Utilities
# ============================================================================

class AgentFactory:
    """Factory for creating agents with standard configurations."""

    _agent_templates = {
        "executor": ExecutorAgent,
        "analyzer": AnalyzerAgent,
        "learner": LearnerAgent,
        "orchestrator": OrchestratorAgent
    }

    @classmethod
    def create_agent(cls, agent_type: str, name: str) -> Optional[BaseAgent]:
        """Create an agent from template."""
        agent_class = cls._agent_templates.get(agent_type.lower())
        if agent_class:
            return agent_class(name)
        logger.error(f"Unknown agent type: {agent_type}")
        return None

    @classmethod
    def create_team(cls, team_config: Dict[str, int]) -> AgentSystem:
        """Create a complete agent team from configuration."""
        system = AgentSystem("Ai-morphasis-Team")

        for agent_type, count in team_config.items():
            for i in range(count):
                agent = cls.create_agent(agent_type, f"{agent_type.title()}-{i+1}")
                if agent:
                    system.add_agent(agent)

        logger.info(f"Agent team created with config: {team_config}")
        return system


# ============================================================================
# Example Usage
# ============================================================================

def example_usage():
    """Demonstrate the super agentic agents framework."""
    # Create agent system
    system = AgentSystem("Ai-morphasis-2.0")

    # Create and add agents
    executor = ExecutorAgent("TaskExecutor-1")
    analyzer = AnalyzerAgent("DataAnalyzer-1")
    learner = LearnerAgent("SystemLearner-1")

    system.add_agent(executor)
    system.add_agent(analyzer)
    system.add_agent(learner)

    # Register capabilities
    from .models import AgentCapability
    executor.register_capability(
        AgentCapability(
            name="file_processing",
            description="Process and manipulate files",
            confidence_score=0.95
        )
    )

    analyzer.register_capability(
        AgentCapability(
            name="data_analysis",
            description="Analyze data and generate insights",
            confidence_score=0.88
        )
    )

    # Create and submit tasks
    task1 = system.create_task(
        description="Analyze performance metrics",
        parameters={"metric_type": "performance", "duration": "24h"}
    )

    if system.submit_task(task1, executor.id):
        try:
            system.execute_task(task1.id, executor.id)
        except Exception as exc:
            logger.error(f"Task execution failed in example: {exc}")

    # Print system status
    print("\n" + "="*60)
    print("AGENT SYSTEM STATUS")
    print("="*60)
    print(system.to_json())
