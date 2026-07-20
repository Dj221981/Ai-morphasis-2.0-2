"""
src/agents/specialized.py
==========================
Concrete agent implementations for the super-agentic framework.

Contains:
- OrchestratorAgent  — coordinates and distributes work to sub-agents
- ExecutorAgent      — performs concrete task execution
- AnalyzerAgent      — analyzes data and generates insights
- LearnerAgent       — adapts and learns from experience
"""

import uuid
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from datetime import datetime

from .models import (
    AgentRole,
    AgentStatus,
    Task,
    TaskStatus,
    CAPABILITY_MATCH_BASE_SCORE,
    DEFAULT_AGENT_BASE_SCORE,
)
from .base import BaseAgent

logger = logging.getLogger(__name__)


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
