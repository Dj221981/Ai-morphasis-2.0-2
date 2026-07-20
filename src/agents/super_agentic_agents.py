"""
Super Agentic Agents Framework
===============================

A sophisticated multi-agent system architecture for Ai-morphasis 2.0.
This module provides the core infrastructure for creating, managing,
and orchestrating intelligent agentic agents with evolved capabilities.

Features:
    - Hierarchical agent architecture
    - Agent memory and state management
    - Inter-agent communication
    - Distributed task execution
    - Dynamic capability evolution
    - Agent reasoning and decision-making
"""

import uuid
import logging
import threading
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)
CAPABILITY_MATCH_BASE_SCORE = 2.0
DEFAULT_AGENT_BASE_SCORE = 1.0


# ============================================================================
# Agent Enums and Data Models
# ============================================================================

class AgentRole(Enum):
    """Defines the role/purpose of an agent."""
    ORCHESTRATOR = "orchestrator"
    EXECUTOR = "executor"
    ANALYZER = "analyzer"
    LEARNER = "learner"
    SUPERVISOR = "supervisor"
    SPECIALIZED = "specialized"


class AgentStatus(Enum):
    """Tracks the operational status of an agent."""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    LEARNING = "learning"
    ERROR = "error"
    SUSPENDED = "suspended"


class TaskPriority(Enum):
    """Defines task execution priority levels."""
    CRITICAL = 5
    HIGH = 4
    NORMAL = 3
    LOW = 2
    DEFERRED = 1


class TaskStatus(Enum):
    """Defines valid task lifecycle states."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Guarded state transitions for task lifecycle
TASK_STATUS_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.ASSIGNED, TaskStatus.CANCELLED},
    TaskStatus.ASSIGNED: {TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.RETRYING, TaskStatus.CANCELLED},
    TaskStatus.RETRYING: {TaskStatus.ASSIGNED, TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


class TaskCancelledError(RuntimeError):
    """Raised when task execution is cancelled."""


@dataclass
class AgentCapability:
    """Represents a capability an agent can perform."""
    name: str
    description: str
    func: Optional[Callable] = None
    confidence_score: float = 1.0
    requires_resources: List[str] = field(default_factory=list)
    version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("AgentCapability name must not be empty")
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(
                f"AgentCapability confidence_score must be in [0.0, 1.0]; got {self.confidence_score}"
            )

    def __repr__(self) -> str:
        return f"<Capability: {self.name} v{self.version} ({self.confidence_score:.2%})>"


@dataclass
class AgentMemory:
    """Represents agent memory with episodic and semantic storage."""
    agent_id: str
    episodic_memory: Dict[str, Any] = field(default_factory=dict)  # Short-term
    semantic_memory: Dict[str, Any] = field(default_factory=dict)  # Long-term
    procedural_memory: Dict[str, Callable] = field(default_factory=dict)  # Skills
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    max_episodes: int = 1000

    def store_episode(self, key: str, value: Any) -> None:
        """Store an episode in short-term memory."""
        if len(self.episodic_memory) >= self.max_episodes:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.episodic_memory))
            del self.episodic_memory[oldest_key]
        self.episodic_memory[key] = {
            "value": value,
            "timestamp": datetime.now()
        }
        self.last_accessed = datetime.now()

    def store_semantic(self, key: str, value: Any) -> None:
        """Store knowledge in long-term memory."""
        self.semantic_memory[key] = {
            "value": value,
            "timestamp": datetime.now(),
            "access_count": 0
        }

    def retrieve(self, key: str, memory_type: str = "auto") -> Optional[Any]:
        """Retrieve from memory (auto-selects best source)."""
        if memory_type in ("auto", "episodic") and key in self.episodic_memory:
            return self.episodic_memory[key]["value"]
        if memory_type in ("auto", "semantic") and key in self.semantic_memory:
            self.semantic_memory[key]["access_count"] += 1
            return self.semantic_memory[key]["value"]
        return None


@dataclass
class Task:
    """Represents a task for agents to execute."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_to: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    last_retry_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)

    def transition_to(self, new_status: TaskStatus) -> bool:
        """Perform guarded task status transition."""
        allowed = TASK_STATUS_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            logger.warning(
                f"Invalid task status transition for {self.id}: {self.status.value} -> {new_status.value}"
            )
            return False

        self.status = new_status
        now = datetime.now()

        if new_status == TaskStatus.ASSIGNED:
            self.assigned_at = now
        elif new_status == TaskStatus.RUNNING:
            self.started_at = now
        elif new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            self.completed_at = now
        elif new_status == TaskStatus.RETRYING:
            self.last_retry_at = now

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority.name,
            "assigned_to": self.assigned_to,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "execution_metadata": self.execution_metadata,
        }


# ============================================================================
# Base Agent Classes
# ============================================================================

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
        self.id = str(uuid.uuid4())
        self.name = name
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
        self.child_agents: Set[str] = set()
        self.peer_agents: Set[str] = set()

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

            self._raise_if_cancelled(task)

            # Think phase
            reasoning = self.think(task.parameters)
            self._raise_if_timed_out(task, start_time)
            self._raise_if_cancelled(task)

            # Act phase
            result = self.act(reasoning)
            self._raise_if_timed_out(task, start_time)

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
        self.telemetry_hook(event, telemetry_payload)

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
        if callable(cancellation_check) and cancellation_check(task):
            raise TaskCancelledError(f"Task {task.id} cancellation hook requested stop")

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


# ============================================================================
# Specialized Agent Classes
# ============================================================================

class OrchestratorAgent(BaseAgent):
    """
    Master orchestrator agent that manages and coordinates other agents.
    Responsible for task distribution, monitoring, and system-level decisions.
    """

    def __init__(self, name: str = "Orchestrator"):
        super().__init__(name, role=AgentRole.ORCHESTRATOR)
        self.managed_agents: Dict[str, BaseAgent] = {}
        self.task_queue: List[Task] = []

    def think(self, input_data: Any) -> Dict[str, Any]:
        """Analyze input and create execution plan."""
        return {
            "analysis": "Task requires orchestration",
            "priority": "high",
            "execution_strategy": "parallel"
        }

    def act(self, decision: Dict[str, Any]) -> Any:
        """Orchestrate agent actions based on decision."""
        logger.info(f"Orchestrator {self.name} executing strategy: {decision.get('execution_strategy')}")
        return {"status": "orchestration_complete"}

    def register_agent(self, agent: BaseAgent) -> bool:
        """Register an agent under this orchestrator."""
        with self._lock:
            self.managed_agents[agent.id] = agent
            agent.parent_agent = self.id
            self.last_activity = datetime.now()
        logger.info(f"Agent {agent.name} registered under orchestrator {self.name}")
        return True

    def distribute_task(self, task: Task, target_agent_id: Optional[str] = None) -> bool:
        """Distribute a task to appropriate agent."""
        if target_agent_id and target_agent_id in self.managed_agents:
            agent = self.managed_agents[target_agent_id]
            return agent.assign_task(task)

        # Auto-select best agent
        best_agent = self._select_best_agent(task)
        if best_agent:
            return best_agent.assign_task(task)

        logger.warning(f"No suitable agent found for task {task.id}")
        return False

    def _select_best_agent(self, task: Task) -> Optional[BaseAgent]:
        """Select best agent for task based on capabilities."""
        available_agents = [
            a for a in self.managed_agents.values()
            if a.status != AgentStatus.SUSPENDED and len(a.active_tasks) < a.max_active_tasks
        ]

        if not available_agents:
            return None

        required_capabilities = task.metadata.get("required_capabilities")
        if required_capabilities is None:
            required_capabilities = task.parameters.get("required_capabilities", [])

        required: Set[str] = set()
        for cap in required_capabilities:
            if isinstance(cap, str):
                normalized = cap.strip()
                if normalized:
                    required.add(normalized)

        scored_agents: List[Tuple[float, BaseAgent]] = []
        for agent in available_agents:
            agent_caps = set(agent.list_capabilities())
            if required and not required.issubset(agent_caps):
                continue
            load_ratio = len(agent.active_tasks) / max(agent.max_active_tasks, 1)
            base_score = CAPABILITY_MATCH_BASE_SCORE if required else DEFAULT_AGENT_BASE_SCORE
            score = base_score - load_ratio
            scored_agents.append((score, agent))

        if not scored_agents:
            return None

        scored_agents.sort(key=lambda item: item[0], reverse=True)
        return scored_agents[0][1]

    def get_system_status(self) -> Dict[str, Any]:
        """Get status of entire agent system."""
        return {
            "orchestrator": self.get_status(),
            "managed_agents": [a.get_status() for a in self.managed_agents.values()],
            "total_agents": len(self.managed_agents),
            "pending_tasks": len(self.task_queue)
        }


class ExecutorAgent(BaseAgent):
    """
    Executor agent that performs specific tasks and operations.
    Specialized for task execution and implementation.
    """

    def __init__(self, name: str = "Executor"):
        super().__init__(name, role=AgentRole.EXECUTOR)
        self.execution_history: List[Dict[str, Any]] = []

    def think(self, input_data: Any) -> Dict[str, Any]:
        """Analyze task parameters and create execution plan."""
        return {
            "action": "execute",
            "parameters": input_data,
            "validation": True
        }

    def act(self, decision: Dict[str, Any]) -> Any:
        """Execute the task based on decision."""
        params = decision.get("parameters", {})
        self.execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "result": "executed"
        })
        return {"execution": "successful", "parameters_processed": params}


class AnalyzerAgent(BaseAgent):
    """
    Analyzer agent that examines data, identifies patterns, and provides insights.
    Specialized for analysis and decision support.
    """

    def __init__(self, name: str = "Analyzer"):
        super().__init__(name, role=AgentRole.ANALYZER)
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}

    def think(self, input_data: Any) -> Dict[str, Any]:
        """Analyze input data and extract insights."""
        analysis = {
            "data_received": bool(input_data),
            "analysis_type": "comprehensive",
            "insights_generated": True
        }
        return analysis

    def act(self, decision: Dict[str, Any]) -> Any:
        """Generate and return analysis results."""
        result = {
            "analysis_complete": True,
            "insights": decision,
            "timestamp": datetime.now().isoformat()
        }
        return result


class LearnerAgent(BaseAgent):
    """
    Learner agent that adapts and improves through experience.
    Specialized for learning, optimization, and capability evolution.
    """

    def __init__(self, name: str = "Learner"):
        super().__init__(name, role=AgentRole.LEARNER)
        self.learned_patterns: Dict[str, Any] = {}
        self.learning_history: List[Dict[str, Any]] = []

    def think(self, input_data: Any) -> Dict[str, Any]:
        """Analyze input for learning opportunities."""
        return {
            "learning_mode": True,
            "input_analyzed": True,
            "patterns_identified": []
        }

    def act(self, decision: Dict[str, Any]) -> Any:
        """Learn from decision and update internal models."""
        self.learning_history.append({
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "patterns_learned": len(self.learned_patterns)
        })
        return {"learning": "in_progress", "patterns": self.learned_patterns}

    def learn_from_experience(self, experience: Dict[str, Any]) -> None:
        """Extract and store learning from an experience."""
        pattern_id = str(uuid.uuid4())
        self.learned_patterns[pattern_id] = {
            "experience": experience,
            "learned_at": datetime.now().isoformat(),
            "confidence": 0.5
        }
        self.memory.store_semantic(f"pattern:{pattern_id}", self.learned_patterns[pattern_id])
        logger.info(f"Learner {self.name} learned pattern: {pattern_id}")


# ============================================================================
# Agent System and Management
# ============================================================================

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
        self.completed_tasks: List[Task] = []
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
    ) -> Task:
        """Create a new task."""
        if not description or not description.strip():
            raise ValueError("Task description must not be empty")
        if not isinstance(parameters, dict):
            raise TypeError("Task parameters must be a dictionary")
        if not isinstance(priority, TaskPriority):
            raise TypeError("Task priority must be a TaskPriority enum value")
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("Task max_retries must be a non-negative integer")

        metadata = parameters.get("metadata", {})
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("Task metadata must be a dictionary")

        timeout_seconds = parameters.get("timeout_seconds")
        if timeout_seconds is not None:
            try:
                timeout_seconds = float(timeout_seconds)
            except (TypeError, ValueError) as exc:
                raise ValueError("Task timeout_seconds must be a positive number") from exc
            if timeout_seconds <= 0:
                raise ValueError("Task timeout_seconds must be greater than 0 when provided")

        required_capabilities = parameters.get("required_capabilities")
        if required_capabilities is not None and (
            not isinstance(required_capabilities, list)
            or len(required_capabilities) == 0
            or any(not isinstance(cap, str) or not cap.strip() for cap in required_capabilities)
        ):
            raise ValueError("Task required_capabilities must be a list of non-empty strings")

        task = Task(
            description=description,
            parameters=parameters,
            priority=priority,
            max_retries=max_retries,
            metadata=dict(metadata) if metadata else {},
        )
        if timeout_seconds is not None:
            task.metadata["timeout_seconds"] = timeout_seconds
        if required_capabilities is not None:
            task.metadata["required_capabilities"] = [cap.strip() for cap in required_capabilities]
        with self._lock:
            self.global_task_queue.append(task)
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
        try:
            result = agent.execute_task(task)
            with self._lock:
                if task.status == TaskStatus.COMPLETED:
                    self.completed_tasks.append(task)
                    self.system_metrics["successful_tasks"] += 1
                self._update_system_task_duration(task, start_time)
                self._persist_task("completed", task)
            return result
        except Exception:
            with self._lock:
                if task.status == TaskStatus.RETRYING:
                    # Requeue for retry dispatch, guarding against duplicates
                    if not any(t.id == task.id for t in self.global_task_queue):
                        self.global_task_queue.append(task)
                    self._persist_task("retry_scheduled", task)
                elif task.status == TaskStatus.CANCELLED:
                    self._persist_task("cancelled", task)
                elif task.status == TaskStatus.FAILED:
                    self.system_metrics["failed_tasks"] += 1
                    self._persist_task("failed", task)
                self._update_system_task_duration(task, start_time)
            raise

    def _remove_from_global_queue(self, task_id: str) -> None:
        """Remove task from global queue if present."""
        with self._lock:
            self.global_task_queue = [t for t in self.global_task_queue if t.id != task_id]

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
            self.persistence_hook(event, task)

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
        self.telemetry_hook(event, event_payload)

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


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    example_usage()
