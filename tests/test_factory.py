"""
Unit tests for AgentFactory: agent creation and team building.
"""

import pytest

from src.agents.super_agentic_agents import (
    AgentFactory,
    AgentSystem,
    ExecutorAgent,
    AnalyzerAgent,
    LearnerAgent,
    OrchestratorAgent,
    AgentRole,
)


class TestAgentFactoryCreateAgent:
    def test_create_executor_agent(self):
        agent = AgentFactory.create_agent("executor", "MyExecutor")
        assert isinstance(agent, ExecutorAgent)
        assert agent.name == "MyExecutor"

    def test_create_analyzer_agent(self):
        agent = AgentFactory.create_agent("analyzer", "MyAnalyzer")
        assert isinstance(agent, AnalyzerAgent)
        assert agent.name == "MyAnalyzer"

    def test_create_learner_agent(self):
        agent = AgentFactory.create_agent("learner", "MyLearner")
        assert isinstance(agent, LearnerAgent)
        assert agent.name == "MyLearner"

    def test_create_orchestrator_agent(self):
        agent = AgentFactory.create_agent("orchestrator", "MyOrchestrator")
        assert isinstance(agent, OrchestratorAgent)
        assert agent.name == "MyOrchestrator"

    def test_create_unknown_agent_type_returns_none(self):
        agent = AgentFactory.create_agent("unknown_type", "X")
        assert agent is None

    def test_create_agent_type_is_case_insensitive(self):
        agent_lower = AgentFactory.create_agent("executor", "E1")
        agent_upper = AgentFactory.create_agent("EXECUTOR", "E2")
        agent_mixed = AgentFactory.create_agent("Executor", "E3")
        assert isinstance(agent_lower, ExecutorAgent)
        assert isinstance(agent_upper, ExecutorAgent)
        assert isinstance(agent_mixed, ExecutorAgent)

    def test_created_agent_has_unique_id(self):
        a1 = AgentFactory.create_agent("executor", "E")
        a2 = AgentFactory.create_agent("executor", "E")
        assert a1.id != a2.id

    def test_created_agent_role_matches_type(self):
        executor = AgentFactory.create_agent("executor", "E")
        analyzer = AgentFactory.create_agent("analyzer", "A")
        learner = AgentFactory.create_agent("learner", "L")
        orchestrator = AgentFactory.create_agent("orchestrator", "O")
        assert executor.role == AgentRole.EXECUTOR
        assert analyzer.role == AgentRole.ANALYZER
        assert learner.role == AgentRole.LEARNER
        assert orchestrator.role == AgentRole.ORCHESTRATOR


class TestAgentFactoryCreateTeam:
    def test_create_team_returns_agent_system(self):
        system = AgentFactory.create_team({"executor": 1})
        assert isinstance(system, AgentSystem)

    def test_create_team_creates_correct_agent_counts(self):
        config = {"executor": 2, "analyzer": 1}
        system = AgentFactory.create_team(config)
        # 3 agents + the system's built-in orchestrator = 4 total in agents dict
        # system_metrics["total_agents"] starts at 1 and increments by add_agent
        assert system.system_metrics["total_agents"] == 4  # 1 orchestrator + 3

    def test_create_team_single_executor(self):
        system = AgentFactory.create_team({"executor": 1})
        assert system.system_metrics["total_agents"] == 2  # 1 orch + 1 exec

    def test_create_team_ignores_unknown_agent_types(self):
        # Unknown types produce None agents and are skipped
        system = AgentFactory.create_team({"unknown": 3})
        # Only the built-in orchestrator should remain
        assert system.system_metrics["total_agents"] == 1

    def test_create_team_mixed_config(self):
        config = {"executor": 1, "analyzer": 1, "learner": 1, "orchestrator": 1}
        system = AgentFactory.create_team(config)
        assert system.system_metrics["total_agents"] == 5  # 1 orch + 4

    def test_create_team_has_orchestrator(self):
        system = AgentFactory.create_team({"executor": 1})
        assert system.orchestrator is not None
        assert isinstance(system.orchestrator, OrchestratorAgent)

    def test_create_team_agents_registered_with_orchestrator(self):
        system = AgentFactory.create_team({"executor": 2})
        # Both executors should be in orchestrator's managed_agents
        assert len(system.orchestrator.managed_agents) == 2
