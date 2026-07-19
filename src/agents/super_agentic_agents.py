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
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


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


@dataclass
class AgentCapability:
    """Represents a capability an agent can perform."""
    name: str
    description: str
    func: Optional[Callable] = None
    confidence_score: float = 1.0
    requires_resources: List[str] = field(default_factory=list)
    version: str = "1.0.0"

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
        should_retry = False

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

            # Think phase
            reasoning = self.think(task.parameters)

            # Act phase
            result = self.act(reasoning)

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

            logger.info(f"Task {task.id} completed successfully")
            return result

        except Exception as e:
            with self._lock:
                task.error = str(e)

                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    if task.status == TaskStatus.RUNNING:
                        if task.transition_to(TaskStatus.RETRYING):
                            should_retry = True
                    elif task.status != TaskStatus.RETRYING:
                        # Fallback in case status is unexpected due to upstream mutation
                        task.status = TaskStatus.RETRYING
                        task.last_retry_at = datetime.now()
                        should_retry = True
                else:
                    if task.status == TaskStatus.RUNNING:
                        task.transition_to(TaskStatus.FAILED)
                    elif task.status != TaskStatus.FAILED:
                        task.status = TaskStatus.FAILED
                        task.completed_at = datetime.now()

                self.task_history.append(task)
                self._update_metrics(task, success=False, started_at=start_time)
                self.status = AgentStatus.ERROR
                self.last_activity = datetime.now()

            logger.error(f"Task {task.id} failed: {str(e)}")
            if should_retry:
                logger.info(
                    f"Task {task.id} marked for retry ({task.retry_count}/{task.max_retries})"
                )
            raise

        finally:
            with self._lock:
                self.active_tasks.pop(task.id, None)
                if self.status not in (AgentStatus.SUSPENDED,):
                    # Avoid permanent ERROR lock-in for recoverable failures
                    self.status = AgentStatus.IDLE
                self.last_activity = datetime.now()

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
            if a.status != AgentStatus.SUSPENDED
        ]

        if not available_agents:
            return None

        # Simple scoring: prefer less busy agents
        return min(available_agents, key=lambda a: len(a.active_tasks))

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

        logger.info(f"Initialized Agent System: {self.name}")

    def add_agent(self, agent: BaseAgent) -> bool:
        """Add an agent to the system."""
        with self._lock:
            self.agents[agent.id] = agent
            self.orchestrator.register_agent(agent)
            self.system_metrics["total_agents"] += 1
        logger.info(f"Agent {agent.name} added to system")
        return True

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the system."""
        with self._lock:
            if agent_id in self.agents:
                agent = self.agents.pop(agent_id)
                self.system_metrics["total_agents"] -= 1
                logger.info(f"Agent {agent.name} removed from system")
                return True
        return False

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
        task = Task(
            description=description,
            parameters=parameters,
            priority=priority,
            max_retries=max_retries,
        )
        with self._lock:
            self.global_task_queue.append(task)
            self.task_registry[task.id] = task
            self.system_metrics["total_tasks"] += 1
        logger.info(f"Task {task.id} created: {description}")
        return task

    def submit_task(self, task: Task, agent_id: Optional[str] = None) -> bool:
        """Submit a task to an agent for execution."""
        if agent_id:
            agent = self.get_agent(agent_id)
            if agent:
                assigned = agent.assign_task(task)
                if assigned:
                    self._remove_from_global_queue(task.id)
                return assigned
        else:
            assigned = self.orchestrator.distribute_task(task)
            if assigned:
                self._remove_from_global_queue(task.id)
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
            return result
        except Exception:
            with self._lock:
                if task.status == TaskStatus.RETRYING:
                    # Requeue for retry dispatch
                    self.global_task_queue.append(task)
                elif task.status == TaskStatus.FAILED:
                    self.system_metrics["failed_tasks"] += 1
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


class CerribroAgent(BaseAgent):
    """
    Cerribro — Specialist Agentic AI for application building, game development,
    and coding assistance.

    Cerribro operates in three primary modes:
        - ``app_builder``      : Scaffold and architect full applications.
        - ``game_builder``     : Engine-agnostic game development guidance.
        - ``coding_assistant`` : Debug, refactor, test, and document code.

    Grounding policy
    ----------------
    Cerribro enforces a retrieval-evidence-first policy:
        * No fabricated APIs, library names, or citations are emitted.
        * Confidence is signalled explicitly in every response payload.
        * Requests that are ambiguous trigger a clarification request.
        * Unsafe or malicious requests are rejected with a clear reason and safe alternative.
        * All planned changes default to the minimal viable increment.

    Deep upgrade layers (v2.0)
    --------------------------
    Three optional deep modes extend the base grounding policy:
        * ``strict_planning``  : Problem decomposition, assumptions log, decision log,
                                 branching strategy, and confidence scoring.
        * ``deep_research``    : Evidence gathering, source quality ranking, contradiction
                                 detection, synthesis with citations, freshness checks.
        * ``deepmind_loop``    : Hypothesis → experiment → evaluate → learn → iterate cycle.

    Enable/disable each layer via :meth:`enable_deep_mode` /
    :meth:`disable_deep_mode`, or pass ``deep_mode_config`` at init time.
    """

    # Valid operating modes for Cerribro
    VALID_MODES = {"app_builder", "game_builder", "coding_assistant"}

    # Grounding flags — machine-readable policy toggles
    GROUNDING_FLAGS = {
        "retrieval_first": True,
        "fabrication_allowed": False,
        "confidence_signalling": True,
        "source_attribution": True,
        "clarification_on_ambiguity": True,
        "unsafe_request_rejection": True,
        "minimal_viable_change": True,
        "test_alongside": True,
    }

    # Default deep-mode configuration (mirrors agent_config.json deep_modes section)
    DEFAULT_DEEP_MODE_CONFIG: Dict[str, Any] = {
        "strict_planning": {
            "enabled": False,
            "confidence_threshold_auto_proceed": 0.75,
            "require_assumption_verification": True,
            "log_decisions": True,
            "max_subproblem_depth": 2,
        },
        "deep_research": {
            "enabled": False,
            "min_evidence_records": {"simple": 1, "medium": 2, "complex": 3},
            "max_source_age_months": 12,
            "require_tier1_for_high_confidence": True,
            "freshness_penalty": -0.05,
            "contradiction_penalty": -0.05,
        },
        "deepmind_loop": {
            "enabled": False,
            "max_rounds": 5,
            "min_confidence_to_finalise": 0.75,
            "confirmed_delta": 0.10,
            "falsified_delta": -0.15,
            "inconclusive_delta": -0.05,
        },
        "governance": {
            "separate_facts_assumptions_proposals": True,
            "mark_speculative_content": True,
            "require_test_evidence_for_code_changes": True,
            "include_unknowns_section_below_confidence": 0.55,
            "deny_unsafe_with_safe_alternative": True,
        },
    }

    def __init__(
        self,
        name: str = "Cerribro",
        mode: str = "coding_assistant",
        deep_mode_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialise CerribroAgent.

        Parameters
        ----------
        name : str
            Display name for this agent instance.
        mode : str
            Operating mode — one of ``app_builder``, ``game_builder``,
            or ``coding_assistant``.
        deep_mode_config : dict, optional
            Override specific deep-mode settings. Keys that are not provided
            default to :attr:`DEFAULT_DEEP_MODE_CONFIG`. Pass
            ``{"strict_planning": {"enabled": True}}`` to activate strict
            planning mode without changing other defaults.
        """
        super().__init__(name, role=AgentRole.SPECIALIZED)

        if mode not in self.VALID_MODES:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of: {sorted(self.VALID_MODES)}"
            )

        self.mode = mode
        self.grounding_flags: Dict[str, bool] = dict(self.GROUNDING_FLAGS)
        self.session_history: List[Dict[str, Any]] = []
        self.clarification_queue: List[str] = []

        # Build deep-mode config by merging defaults with any user overrides
        self.deep_mode_config: Dict[str, Any] = {}
        for layer, defaults in self.DEFAULT_DEEP_MODE_CONFIG.items():
            override = (deep_mode_config or {}).get(layer, {})
            self.deep_mode_config[layer] = {**defaults, **override}

        # Register built-in capabilities
        self._register_default_capabilities()

        logger.info(
            f"CerribroAgent '{self.name}' initialised in mode='{self.mode}'"
        )

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def think(self, input_data: Any) -> Dict[str, Any]:
        """
        Reason about the incoming request and produce an actionable plan.

        Applies grounding checks before committing to any plan:
          1. Safety gate  — rejects unsafe/malicious requests.
          2. Ambiguity gate — queues clarification for under-specified input.
          3. Confidence assessment — rates certainty; low-confidence paths
             are flagged for human review.
          4. Deep layers (when enabled) — adds intelligence plan, evidence
             bundle stub, and DeepMind loop stub to the plan.
        """
        params: Dict[str, Any] = input_data if isinstance(input_data, dict) else {"raw": input_data}

        # Safety gate
        if self._is_unsafe(params):
            return {
                "decision": "reject",
                "reason": "Request flagged as unsafe or potentially malicious.",
                "safe_alternative": (
                    "If this is for authorised security research, consider using "
                    "established tools such as OWASP ZAP or Burp Suite Community Edition."
                ),
                "confidence": 0.0,
                "mode": self.mode,
            }

        # Ambiguity gate
        if self._is_ambiguous(params):
            clarification = self._build_clarification_request(params)
            self.clarification_queue.append(clarification)
            return {
                "decision": "clarify",
                "clarification": clarification,
                "confidence": 0.5,
                "mode": self.mode,
            }

        # Build mode-specific plan
        plan = self._build_plan(params)
        confidence = self._assess_confidence(params)
        plan["confidence"] = confidence
        plan["confidence_band"] = self._confidence_band(confidence)
        plan["grounding_flags"] = self.grounding_flags
        plan["mode"] = self.mode

        # Deep layers — attach structured metadata when enabled
        if self.deep_mode_config["strict_planning"]["enabled"]:
            plan["deep_intelligence"] = self._build_intelligence_plan(params, confidence)

        if self.deep_mode_config["deep_research"]["enabled"]:
            plan["evidence_bundle"] = self._build_evidence_bundle_stub(params)

        if self.deep_mode_config["deepmind_loop"]["enabled"]:
            plan["deepmind_loop"] = self._build_deepmind_loop_stub()

        # Governance tags
        plan["facts"] = []
        plan["assumptions"] = []
        plan["proposals"] = []
        plan["speculative"] = []

        # Unknowns section if confidence is below threshold
        unknowns_threshold = self.deep_mode_config["governance"][
            "include_unknowns_section_below_confidence"
        ]
        if confidence < unknowns_threshold:
            plan["unknowns_and_next_steps"] = (
                "Confidence is below threshold. Please provide more context to proceed."
            )

        return plan

    def act(self, decision: Dict[str, Any]) -> Any:
        """
        Execute or relay the plan produced by :meth:`think`.

        Returns a structured result dict that always includes:
        ``status``, ``mode``, ``confidence``, ``confidence_band``, and ``output``.
        Unsafe rejections include a ``safe_alternative`` field.
        """
        decision_type = decision.get("decision", "execute")

        if decision_type == "reject":
            result = {
                "status": "rejected",
                "mode": self.mode,
                "confidence": 0.0,
                "confidence_band": "Uncertain",
                "output": decision.get("reason", "Request rejected."),
                "safe_alternative": decision.get("safe_alternative", ""),
            }
        elif decision_type == "clarify":
            result = {
                "status": "awaiting_clarification",
                "mode": self.mode,
                "confidence": decision.get("confidence", 0.5),
                "confidence_band": self._confidence_band(decision.get("confidence", 0.5)),
                "output": decision.get("clarification", "Please clarify your request."),
            }
        else:
            confidence = decision.get("confidence", 0.9)
            result = {
                "status": "completed",
                "mode": self.mode,
                "confidence": confidence,
                "confidence_band": self._confidence_band(confidence),
                "output": self._execute_plan(decision),
                "facts": decision.get("facts", []),
                "assumptions": decision.get("assumptions", []),
                "proposals": decision.get("proposals", []),
                "speculative": decision.get("speculative", []),
            }
            # Propagate deep layer payloads if present
            for key in ("deep_intelligence", "evidence_bundle", "deepmind_loop"):
                if key in decision:
                    result[key] = decision[key]
            if "unknowns_and_next_steps" in decision:
                result["unknowns_and_next_steps"] = decision["unknowns_and_next_steps"]

        # Store session history
        now = datetime.now()
        self.session_history.append({
            "timestamp": now.isoformat(),
            "decision": decision_type,
            "result": result,
        })
        self.last_activity = now

        logger.info(
            f"CerribroAgent '{self.name}' action completed: status={result['status']}"
        )
        return result

    # ------------------------------------------------------------------
    # Mode helpers
    # ------------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        """Switch the operating mode at runtime."""
        if mode not in self.VALID_MODES:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of: {sorted(self.VALID_MODES)}"
            )
        self.mode = mode
        logger.info(f"CerribroAgent '{self.name}' switched to mode='{self.mode}'")

    # ------------------------------------------------------------------
    # Deep mode helpers
    # ------------------------------------------------------------------

    def enable_deep_mode(self, layer: str) -> None:
        """
        Enable a deep upgrade layer at runtime.

        Parameters
        ----------
        layer : str
            One of ``"strict_planning"``, ``"deep_research"``, or ``"deepmind_loop"``.
        """
        allowed_layers = {"strict_planning", "deep_research", "deepmind_loop"}
        if layer not in allowed_layers:
            raise ValueError(
                f"Unknown deep mode layer '{layer}'. Must be one of: {sorted(allowed_layers)}"
            )
        self.deep_mode_config[layer]["enabled"] = True
        logger.info(f"CerribroAgent '{self.name}': deep mode '{layer}' enabled.")

    def disable_deep_mode(self, layer: str) -> None:
        """
        Disable a deep upgrade layer at runtime.

        Parameters
        ----------
        layer : str
            One of ``"strict_planning"``, ``"deep_research"``, or ``"deepmind_loop"``.
        """
        allowed_layers = {"strict_planning", "deep_research", "deepmind_loop"}
        if layer not in allowed_layers:
            raise ValueError(
                f"Unknown deep mode layer '{layer}'. Must be one of: {sorted(allowed_layers)}"
            )
        self.deep_mode_config[layer]["enabled"] = False
        logger.info(f"CerribroAgent '{self.name}': deep mode '{layer}' disabled.")

    def is_deep_mode_enabled(self, layer: str) -> bool:
        """Return True if the specified deep mode layer is currently active."""
        return bool(self.deep_mode_config.get(layer, {}).get("enabled", False))

    # ------------------------------------------------------------------
    # Grounding helpers
    # ------------------------------------------------------------------

    def _is_unsafe(self, params: Dict[str, Any]) -> bool:
        """Return True if the request contains unsafe or malicious signals."""
        unsafe_keywords = {
            "malware", "exploit", "ransomware", "backdoor", "keylogger",
            "rootkit", "phishing", "shellcode",
        }
        payload = json.dumps(params, default=str).lower()
        return any(kw in payload for kw in unsafe_keywords)

    def _is_ambiguous(self, params: Dict[str, Any]) -> bool:
        """Return True if the request is under-specified."""
        # A request is ambiguous if it has no meaningful description
        description = params.get("description", params.get("raw", ""))
        return not description or len(str(description).strip()) < 10

    def _build_clarification_request(self, params: Dict[str, Any]) -> str:
        """Produce a clarifying question for the user."""
        mode_questions = {
            "app_builder": (
                "Please describe the application you want to build, including "
                "its target platform, primary features, and any tech-stack preferences."
            ),
            "game_builder": (
                "Please describe the game concept, target platform, genre, "
                "and any preferred engine or framework."
            ),
            "coding_assistant": (
                "Please provide the code snippet or file, describe what it should do, "
                "and explain the specific problem you need help with."
            ),
        }
        return mode_questions.get(self.mode, "Please provide more details about your request.")

    def _assess_confidence(self, params: Dict[str, Any]) -> float:
        """
        Return a confidence score in [0, 1].

        Higher scores reflect well-specified, familiar requests.
        """
        description = str(params.get("description", params.get("raw", "")))
        word_count = len(description.split())
        # Simple heuristic: score rises with detail up to a cap
        raw_score = min(1.0, 0.5 + (word_count / 40) * 0.5)
        return round(raw_score, 2)

    @staticmethod
    def _confidence_band(score: float) -> str:
        """Map a numeric confidence score to a human-readable band label."""
        if score >= 0.80:
            return "High"
        if score >= 0.55:
            return "Medium"
        if score >= 0.30:
            return "Low"
        return "Uncertain"

    # ------------------------------------------------------------------
    # Deep Intelligence helpers
    # ------------------------------------------------------------------

    def _build_intelligence_plan(
        self, params: Dict[str, Any], confidence: float
    ) -> Dict[str, Any]:
        """
        Build a minimal Deep Intelligence stub attached to the plan.

        In a full integration, this would be populated by the LLM reasoning
        loop. Here it provides the structural scaffold that the LLM/operator
        must fill in, making the expected schema explicit.
        """
        cfg = self.deep_mode_config["strict_planning"]
        return {
            "enabled": True,
            "confidence_threshold_auto_proceed": cfg["confidence_threshold_auto_proceed"],
            "confidence_score": confidence,
            "confidence_band": self._confidence_band(confidence),
            "auto_proceed": confidence >= cfg["confidence_threshold_auto_proceed"],
            "subproblems": [],
            "assumptions": [],
            "decisions": [],
            "branches": {
                "primary": [],
                "fallbacks": [],
            },
            "_note": (
                "Populate subproblems, assumptions, decisions, and branches "
                "following intelligence_framework.md before proceeding."
            ),
        }

    def _build_evidence_bundle_stub(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a minimal Deep Research evidence bundle stub.

        In a full integration, the research pipeline populates this with
        real evidence records. The stub makes the expected schema explicit.
        """
        description = str(params.get("description", params.get("raw", "")))
        word_count = len(description.split())
        if word_count < 15:
            complexity = "simple"
        elif word_count < 40:
            complexity = "medium"
        else:
            complexity = "complex"
        cfg = self.deep_mode_config["deep_research"]
        min_records = cfg["min_evidence_records"].get(complexity, 2)

        return {
            "enabled": True,
            "complexity": complexity,
            "min_evidence_records_required": min_records,
            "research_questions": [],
            "evidence_records": [],
            "contradictions": [],
            "evidence_map": {},
            "freshness_warnings": [],
            "synthesis_confidence": None,
            "insufficient_evidence": True,
            "unverified_claims": [],
            "_note": (
                "Populate research_questions and evidence_records following "
                "deep_research.md before proceeding. Schema: evidence_schema.json."
            ),
        }

    def _build_deepmind_loop_stub(self) -> Dict[str, Any]:
        """
        Build a minimal DeepMind loop tracking stub.

        In a full integration, each round is populated as the agent iterates.
        The stub makes the expected schema explicit.
        """
        cfg = self.deep_mode_config["deepmind_loop"]
        return {
            "enabled": True,
            "mode": self.mode,
            "max_rounds": cfg["max_rounds"],
            "min_confidence_to_finalise": cfg["min_confidence_to_finalise"],
            "total_rounds": 0,
            "rounds": [],
            "final_verdict": None,
            "final_confidence": None,
            "final_confidence_band": None,
            "escalated": False,
            "escalation_reason": None,
            "_note": (
                "Populate rounds following deepmind_loop.md. "
                "Each round must have: hypothesis, success_criteria, experiment, "
                "execution_method, status, confidence_delta, learnings."
            ),
        }

    # ------------------------------------------------------------------
    # Plan builders per mode
    # ------------------------------------------------------------------

    def _build_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the correct mode-specific plan builder."""
        builders = {
            "app_builder": self._plan_app_builder,
            "game_builder": self._plan_game_builder,
            "coding_assistant": self._plan_coding_assistant,
        }
        builder = builders[self.mode]
        return builder(params)

    def _plan_app_builder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a plan for application scaffolding."""
        return {
            "decision": "execute",
            "workflow": "app_builder",
            "steps": [
                "intelligence_plan",
                "research_plan",
                "clarify_requirements",
                "choose_architecture",
                "scaffold_project_structure",
                "implement_core_features",
                "write_tests",
                "document_api",
                "validation_gate",
                "review_and_iterate",
            ],
            "parameters": params,
        }

    def _plan_game_builder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a plan for game development assistance."""
        return {
            "decision": "execute",
            "workflow": "game_builder",
            "steps": [
                "intelligence_plan",
                "research_plan",
                "clarify_game_concept",
                "select_engine_or_framework",
                "design_game_loop",
                "implement_mechanics",
                "add_assets_and_ui",
                "test_gameplay",
                "validation_gate",
                "polish_and_optimize",
            ],
            "parameters": params,
        }

    def _plan_coding_assistant(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a plan for coding assistance."""
        return {
            "decision": "execute",
            "workflow": "coding_assistant",
            "steps": [
                "intelligence_plan",
                "research_plan",
                "understand_context",
                "identify_problem",
                "propose_minimal_fix",
                "apply_change",
                "run_or_suggest_tests",
                "validation_gate",
                "update_docs_if_needed",
            ],
            "parameters": params,
        }

    def _execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Return a structured execution summary for the given plan."""
        return {
            "workflow": plan.get("workflow", self.mode),
            "steps_planned": plan.get("steps", []),
            "steps_completed": [],
            "notes": (
                "Plan produced. Steps are ready for iterative execution. "
                "Grounding policy enforced — no fabricated references included."
            ),
        }

    # ------------------------------------------------------------------
    # Capability registration
    # ------------------------------------------------------------------

    def _register_default_capabilities(self) -> None:
        """Register Cerribro's built-in capabilities."""
        default_capabilities = [
            AgentCapability(
                name="app_scaffolding",
                description="Scaffold and architect full-stack or standalone applications.",
                confidence_score=0.92,
            ),
            AgentCapability(
                name="game_development",
                description="Engine-agnostic game design, mechanics, and implementation guidance.",
                confidence_score=0.88,
            ),
            AgentCapability(
                name="code_debugging",
                description="Identify and fix bugs in existing code with minimal side effects.",
                confidence_score=0.95,
            ),
            AgentCapability(
                name="code_refactoring",
                description="Improve code structure, readability, and maintainability.",
                confidence_score=0.93,
            ),
            AgentCapability(
                name="test_generation",
                description="Generate unit, integration, and end-to-end tests for code.",
                confidence_score=0.90,
            ),
            AgentCapability(
                name="documentation",
                description="Write and update code documentation and API references.",
                confidence_score=0.91,
            ),
            AgentCapability(
                name="grounded_retrieval",
                description="Answer questions using verifiable, cited knowledge only.",
                confidence_score=0.96,
            ),
            AgentCapability(
                name="deep_intelligence",
                description=(
                    "Problem decomposition, assumptions tracking, decision logging, "
                    "and confidence-scored planning."
                ),
                confidence_score=0.90,
            ),
            AgentCapability(
                name="deep_research",
                description=(
                    "Evidence gathering, source quality ranking, contradiction detection, "
                    "and grounded synthesis with citations."
                ),
                confidence_score=0.88,
            ),
            AgentCapability(
                name="deepmind_loop",
                description=(
                    "Iterative hypothesis/experiment/evaluation cycle for rigorous "
                    "validation across all Cerribro modes."
                ),
                confidence_score=0.87,
            ),
        ]
        for cap in default_capabilities:
            self.register_capability(cap)


# ============================================================================
# Factory and Utilities
# ============================================================================

class AgentFactory:
    """Factory for creating agents with standard configurations."""

    _agent_templates = {
        "executor": ExecutorAgent,
        "analyzer": AnalyzerAgent,
        "learner": LearnerAgent,
        "orchestrator": OrchestratorAgent,
        "cerribro": CerribroAgent,
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
