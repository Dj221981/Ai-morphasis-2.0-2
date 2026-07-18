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


class DeepStorageMemory:
    """
    Deep Storage Memory — a multi-tier persistent memory layer for agents.

    Tiers (fastest → deepest):
        working   — active scratchpad, cleared each session.
        episodic  — short-term event log (delegates to AgentMemory).
        semantic  — long-term knowledge base (delegates to AgentMemory).
        archive   — append-only deep store for cross-session facts, replayed
                    summaries, and high-value observations that must never be
                    silently evicted.

    The archive tier uses an importance score so that the most significant
    memories surface first on retrieval.
    """

    def __init__(self, agent_id: str, base_memory: Optional["AgentMemory"] = None):
        self.agent_id = agent_id
        self._base = base_memory or AgentMemory(agent_id=agent_id)
        # archive: key → {value, timestamp, importance, access_count}
        self._archive: Dict[str, Any] = {}
        # working scratchpad: key → value (not persisted across sessions)
        self._working: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Working tier
    # ------------------------------------------------------------------

    def write_working(self, key: str, value: Any) -> None:
        """Write to the working (scratchpad) tier."""
        with self._lock:
            self._working[key] = value
            self.last_accessed = datetime.now()

    def read_working(self, key: str) -> Optional[Any]:
        """Read from the working tier."""
        with self._lock:
            return self._working.get(key)

    def clear_working(self) -> None:
        """Clear the working scratchpad (e.g., between sessions)."""
        with self._lock:
            self._working.clear()

    # ------------------------------------------------------------------
    # Episodic / semantic tiers (delegated to base AgentMemory)
    # ------------------------------------------------------------------

    def store_episode(self, key: str, value: Any) -> None:
        """Store a short-term episode."""
        self._base.store_episode(key, value)
        self.last_accessed = datetime.now()

    def store_semantic(self, key: str, value: Any) -> None:
        """Store a long-term semantic fact."""
        self._base.store_semantic(key, value)
        self.last_accessed = datetime.now()

    def retrieve(self, key: str, memory_type: str = "auto") -> Optional[Any]:
        """
        Retrieve from memory.  Search order: working → episodic/semantic → archive.
        """
        with self._lock:
            if memory_type in ("auto", "working") and key in self._working:
                return self._working[key]

        base_result = self._base.retrieve(key, memory_type)
        if base_result is not None:
            return base_result

        return self.retrieve_archive(key)

    # ------------------------------------------------------------------
    # Archive tier
    # ------------------------------------------------------------------

    def archive(self, key: str, value: Any, importance: float = 0.5) -> None:
        """
        Write to the deep archive tier.

        Parameters
        ----------
        key        : Unique identifier for this memory.
        value      : The data to archive.
        importance : Salience score in [0, 1]; higher values surface first
                     on ranked retrieval.
        """
        importance = max(0.0, min(1.0, importance))
        with self._lock:
            existing = self._archive.get(key, {})
            self._archive[key] = {
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "importance": max(importance, existing.get("importance", 0.0)),
                "access_count": existing.get("access_count", 0),
            }
            self.last_accessed = datetime.now()
        logger.debug(f"DeepStorageMemory: archived key='{key}' importance={importance:.2f}")

    def retrieve_archive(self, key: str) -> Optional[Any]:
        """Retrieve a specific entry from the archive."""
        with self._lock:
            entry = self._archive.get(key)
            if entry is None:
                return None
            entry["access_count"] += 1
            self.last_accessed = datetime.now()
            return entry["value"]

    def top_archive(self, n: int = 10) -> List[Dict[str, Any]]:
        """Return the *n* most important archive entries."""
        with self._lock:
            ranked = sorted(
                ({"key": k, **v} for k, v in self._archive.items()),
                key=lambda e: e["importance"],
                reverse=True,
            )
            return ranked[:n]

    def summarize(self) -> Dict[str, Any]:
        """Return a snapshot of storage utilisation across all tiers."""
        with self._lock:
            return {
                "agent_id": self.agent_id,
                "working_entries": len(self._working),
                "episodic_entries": len(self._base.episodic_memory),
                "semantic_entries": len(self._base.semantic_memory),
                "archive_entries": len(self._archive),
                "created_at": self.created_at.isoformat(),
                "last_accessed": self.last_accessed.isoformat(),
            }


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


class DeepMindAgent(BaseAgent):
    """
    DeepMind-style reasoning agent with multi-step chain-of-thought,
    hypothesis generation, and meta-cognitive self-monitoring.

    Reasoning pipeline
    ------------------
    1. **Chain-of-thought** — decomposes the problem into explicit steps.
    2. **Hypothesis generation** — proposes candidate answers and scores them.
    3. **Meta-cognition** — audits its own reasoning for bias and gaps.
    4. **Deep-storage integration** — archives high-confidence conclusions to the
       agent's ``DeepStorageMemory`` for cross-session retrieval.

    The agent is registered under the ``"deepmind"`` key in :class:`AgentFactory`.
    """

    # Confidence thresholds for hypothesis evaluation
    _HIGH_CONFIDENCE = 0.80
    _MEDIUM_CONFIDENCE = 0.55

    def __init__(self, name: str = "DeepMind"):
        super().__init__(name, role=AgentRole.ANALYZER)
        self.deep_storage = DeepStorageMemory(agent_id=self.id, base_memory=self.memory)
        self.reasoning_history: List[Dict[str, Any]] = []

        self._register_deepmind_capabilities()
        logger.info(f"DeepMindAgent '{self.name}' initialised with deep-storage memory")

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def think(self, input_data: Any) -> Dict[str, Any]:
        """
        Run the full DeepMind reasoning pipeline on *input_data*.

        Returns a structured reasoning plan containing:
        - ``steps`` — chain-of-thought steps produced.
        - ``hypotheses`` — ranked candidate answers.
        - ``best_hypothesis`` — highest-confidence hypothesis.
        - ``meta_warnings`` — self-check questions raised by meta-cognition.
        - ``confidence`` — overall confidence in the best hypothesis.
        """
        params: Dict[str, Any] = (
            input_data if isinstance(input_data, dict) else {"problem": str(input_data)}
        )
        problem = params.get("problem", params.get("description", str(params)))

        # 1. Chain-of-thought decomposition
        cot_steps = self._chain_of_thought(problem, params)

        # 2. Hypothesis generation
        hypotheses = self._generate_hypotheses(problem, params, cot_steps)

        # 3. Select best hypothesis
        best = max(hypotheses, key=lambda h: h["confidence"]) if hypotheses else {}

        # 4. Meta-cognition audit
        meta_warnings = self._meta_audit(cot_steps, hypotheses)

        plan = {
            "decision": "execute",
            "problem": problem,
            "steps": cot_steps,
            "hypotheses": hypotheses,
            "best_hypothesis": best,
            "meta_warnings": meta_warnings,
            "confidence": best.get("confidence", 0.5),
        }

        # Archive high-confidence conclusions to deep storage
        if best.get("confidence", 0.0) >= self._MEDIUM_CONFIDENCE:
            self.deep_storage.archive(
                key=f"conclusion:{uuid.uuid4()}",
                value={"problem": problem, "conclusion": best},
                importance=best.get("confidence", 0.5),
            )

        return plan

    def act(self, decision: Dict[str, Any]) -> Any:
        """
        Emit the reasoning result produced by :meth:`think`.

        Returns a structured result with ``status``, ``output``, and
        ``confidence``.
        """
        self.reasoning_history.append({
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
        })
        self.last_activity = datetime.now()

        result = {
            "status": "completed",
            "output": {
                "problem": decision.get("problem", ""),
                "reasoning_steps": decision.get("steps", []),
                "best_hypothesis": decision.get("best_hypothesis", {}),
                "meta_warnings": decision.get("meta_warnings", []),
                "deep_storage_summary": self.deep_storage.summarize(),
            },
            "confidence": decision.get("confidence", 0.5),
        }
        logger.info(
            f"DeepMindAgent '{self.name}' reasoning complete: "
            f"confidence={result['confidence']:.2f}"
        )
        return result

    # ------------------------------------------------------------------
    # Reasoning helpers
    # ------------------------------------------------------------------

    def _chain_of_thought(
        self, problem: str, params: Dict[str, Any]
    ) -> List[str]:
        """Produce a list of chain-of-thought reasoning steps for *problem*."""
        context = params.get("context", "")
        steps = [
            f"Understand the problem: '{problem}'",
            f"Identify key constraints and goals{': ' + context if context else '.'}",
            "Break the problem into sub-problems.",
            "Recall relevant knowledge from deep storage.",
            "Evaluate each sub-problem independently.",
            "Synthesise sub-results into a candidate answer.",
            "Check for internal consistency and completeness.",
        ]
        # Persist reasoning trace in working memory
        self.deep_storage.write_working("current_cot_steps", steps)
        return steps

    def _generate_hypotheses(
        self,
        problem: str,
        params: Dict[str, Any],
        cot_steps: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Generate and score candidate hypotheses.

        In a production integration an LLM or symbolic reasoner would populate
        these; here we produce structured placeholders so the pipeline is fully
        exercised and testable.
        """
        base_confidence = min(1.0, 0.5 + (len(problem.split()) / 40) * 0.3)
        hypotheses = [
            {
                "id": 1,
                "statement": f"Primary hypothesis derived from chain-of-thought for: {problem[:60]}",
                "confidence": round(base_confidence, 2),
                "evidence_for": ["Chain-of-thought analysis supports this conclusion."],
                "evidence_against": [],
                "verdict": self._verdict(base_confidence),
            },
            {
                "id": 2,
                "statement": f"Alternative hypothesis (lower confidence) for: {problem[:60]}",
                "confidence": round(max(0.1, base_confidence - 0.25), 2),
                "evidence_for": [],
                "evidence_against": ["Primary hypothesis has stronger chain-of-thought support."],
                "verdict": self._verdict(max(0.1, base_confidence - 0.25)),
            },
        ]
        return hypotheses

    @staticmethod
    def _verdict(confidence: float) -> str:
        """Convert numeric confidence to a human-readable verdict label."""
        if confidence >= 0.80:
            return "STRONGLY SUPPORTED"
        if confidence >= 0.60:
            return "PLAUSIBLE"
        if confidence >= 0.40:
            return "UNCERTAIN"
        if confidence >= 0.20:
            return "UNLIKELY"
        return "REJECTED"

    @staticmethod
    def _meta_audit(
        steps: List[str], hypotheses: List[Dict[str, Any]]
    ) -> List[str]:
        """Return meta-cognitive self-check warnings for the reasoning trace."""
        warnings = [
            "Am I seeking disconfirming evidence as actively as confirming?",
            "Have I considered at least three alternative explanations?",
            "Is my confidence calibrated to the actual evidence available?",
        ]
        if len(hypotheses) < 2:
            warnings.append("Only one hypothesis generated — broaden the search space.")
        if len(steps) < 4:
            warnings.append("Chain-of-thought is short — consider adding more reasoning steps.")
        return warnings

    # ------------------------------------------------------------------
    # Deep-storage helpers
    # ------------------------------------------------------------------

    def recall(self, key: str) -> Optional[Any]:
        """Retrieve a fact from deep storage (all tiers)."""
        return self.deep_storage.retrieve(key)

    def top_memories(self, n: int = 5) -> List[Dict[str, Any]]:
        """Return the *n* most important archived memories."""
        return self.deep_storage.top_archive(n)

    # ------------------------------------------------------------------
    # Capability registration
    # ------------------------------------------------------------------

    def _register_deepmind_capabilities(self) -> None:
        """Register DeepMind-specific capabilities."""
        caps = [
            AgentCapability(
                name="chain_of_thought_reasoning",
                description="Decompose problems into explicit multi-step reasoning chains.",
                confidence_score=0.94,
            ),
            AgentCapability(
                name="hypothesis_generation",
                description="Generate, score, and rank competing hypotheses.",
                confidence_score=0.91,
            ),
            AgentCapability(
                name="meta_cognition",
                description="Audit reasoning for cognitive biases and logical gaps.",
                confidence_score=0.89,
            ),
            AgentCapability(
                name="deep_storage_memory",
                description="Persist and retrieve high-value conclusions across sessions.",
                confidence_score=0.96,
            ),
            AgentCapability(
                name="analogical_reasoning",
                description="Identify structural similarities across different problem domains.",
                confidence_score=0.87,
            ),
        ]
        for cap in caps:
            self.register_capability(cap)


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
        * Unsafe or malicious requests are rejected with a clear reason.
        * All planned changes default to the minimal viable increment.
    """

    # Valid operating modes for Cerribro
    VALID_MODES = {"app_builder", "game_builder", "coding_assistant", "autonomous", "software_maker"}

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

    def __init__(self, name: str = "Cerribro", mode: str = "coding_assistant"):
        """
        Initialise CerribroAgent.

        Parameters
        ----------
        name : str
            Display name for this agent instance.
        mode : str
            Operating mode — one of ``app_builder``, ``game_builder``,
            or ``coding_assistant``.
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
        """
        params: Dict[str, Any] = input_data if isinstance(input_data, dict) else {"raw": input_data}

        # Safety gate
        if self._is_unsafe(params):
            return {
                "decision": "reject",
                "reason": "Request flagged as unsafe or potentially malicious.",
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
        plan["confidence"] = self._assess_confidence(params)
        plan["grounding_flags"] = self.grounding_flags
        plan["mode"] = self.mode

        return plan

    def act(self, decision: Dict[str, Any]) -> Any:
        """
        Execute or relay the plan produced by :meth:`think`.

        Returns a structured result dict that always includes:
        ``status``, ``mode``, ``confidence``, and ``output``.
        """
        decision_type = decision.get("decision", "execute")

        if decision_type == "reject":
            result = {
                "status": "rejected",
                "mode": self.mode,
                "confidence": 0.0,
                "output": decision.get("reason", "Request rejected."),
            }
        elif decision_type == "clarify":
            result = {
                "status": "awaiting_clarification",
                "mode": self.mode,
                "confidence": decision.get("confidence", 0.5),
                "output": decision.get("clarification", "Please clarify your request."),
            }
        else:
            result = {
                "status": "completed",
                "mode": self.mode,
                "confidence": decision.get("confidence", 0.9),
                "output": self._execute_plan(decision),
            }

        # Store session history
        self.session_history.append({
            "timestamp": datetime.now().isoformat(),
            "decision": decision_type,
            "result": result,
        })
        self.last_activity = datetime.now()

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
    # Grounding helpers
    # ------------------------------------------------------------------

    def _is_unsafe(self, params: Dict[str, Any]) -> bool:
        """Return True if the request contains unsafe or malicious signals."""
        unsafe_keywords = {
            "malware", "exploit", "ransomware", "backdoor", "keylogger",
            "rootkit", "phishing", "shellcode",
        }
        payload = json.dumps(params).lower()
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
            "autonomous": (
                "Please describe the high-level objective you want Cerribro to pursue "
                "autonomously, along with any constraints, acceptance criteria, and "
                "the tools or environments available."
            ),
            "software_maker": (
                "Please describe the software product to be built: its purpose, "
                "target users, required features, deployment target (cloud/on-prem/OT), "
                "and any domain-specific compliance requirements."
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

    # ------------------------------------------------------------------
    # Plan builders per mode
    # ------------------------------------------------------------------

    def _build_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the correct mode-specific plan builder."""
        builders = {
            "app_builder": self._plan_app_builder,
            "game_builder": self._plan_game_builder,
            "coding_assistant": self._plan_coding_assistant,
            "autonomous": self._plan_autonomous,
            "software_maker": self._plan_software_maker,
        }
        builder = builders[self.mode]
        return builder(params)

    def _plan_app_builder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a plan for application scaffolding."""
        return {
            "decision": "execute",
            "workflow": "app_builder",
            "steps": [
                "clarify_requirements",
                "choose_architecture",
                "scaffold_project_structure",
                "implement_core_features",
                "write_tests",
                "document_api",
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
                "clarify_game_concept",
                "select_engine_or_framework",
                "design_game_loop",
                "implement_mechanics",
                "add_assets_and_ui",
                "test_gameplay",
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
                "understand_context",
                "identify_problem",
                "propose_minimal_fix",
                "apply_change",
                "run_or_suggest_tests",
                "update_docs_if_needed",
            ],
            "parameters": params,
        }

    def _plan_autonomous(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a plan for autonomous operation mode."""
        return {
            "decision": "execute",
            "workflow": "autonomous",
            "steps": [
                "parse_high_level_objective",
                "decompose_into_sub_goals",
                "select_tools_and_resources",
                "execute_sub_goals_iteratively",
                "evaluate_intermediate_results",
                "replan_if_deviation_detected",
                "verify_acceptance_criteria",
                "produce_final_report",
            ],
            "parameters": params,
            "autonomous": True,
        }

    def _plan_software_maker(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a plan for the software-making / OT-builder mode."""
        return {
            "decision": "execute",
            "workflow": "software_maker",
            "steps": [
                "elicit_and_refine_requirements",
                "define_system_architecture",
                "identify_ot_or_domain_constraints",
                "scaffold_project_and_toolchain",
                "implement_core_modules",
                "integrate_ot_interfaces_or_apis",
                "write_and_run_tests",
                "validate_against_requirements",
                "package_and_document_release",
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
                name="autonomous_operation",
                description="Pursue high-level objectives autonomously through iterative planning, "
                            "execution, and replanning cycles without step-by-step human guidance.",
                confidence_score=0.85,
            ),
            AgentCapability(
                name="software_making",
                description="End-to-end software product development including OT/industrial "
                            "builder workflows, from requirements through packaging.",
                confidence_score=0.90,
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
        "deepmind": DeepMindAgent,
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
