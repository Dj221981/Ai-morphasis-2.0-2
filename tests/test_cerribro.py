"""
Unit tests for CerribroAgent.

Tests cover initialisation, mode switching, grounding gates (safety, ambiguity,
confidence), plan building, and AgentFactory integration.
"""

import pytest

from src.agents.super_agentic_agents import (
    AgentCapability,
    AgentFactory,
    AgentRole,
    AgentStatus,
    CerribroAgent,
    Task,
    TaskStatus,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cerribro_default():
    """CerribroAgent in default coding_assistant mode."""
    return CerribroAgent(name="Cerribro-Test", mode="coding_assistant")


@pytest.fixture
def cerribro_app():
    """CerribroAgent in app_builder mode."""
    return CerribroAgent(name="Cerribro-App", mode="app_builder")


@pytest.fixture
def cerribro_game():
    """CerribroAgent in game_builder mode."""
    return CerribroAgent(name="Cerribro-Game", mode="game_builder")


# ============================================================================
# Initialisation tests
# ============================================================================

class TestCerribroInit:
    """Tests for CerribroAgent initialisation."""

    def test_default_mode(self, cerribro_default):
        assert cerribro_default.mode == "coding_assistant"

    def test_role_is_specialized(self, cerribro_default):
        assert cerribro_default.role == AgentRole.SPECIALIZED

    def test_initial_status_idle(self, cerribro_default):
        assert cerribro_default.status == AgentStatus.IDLE

    def test_grounding_flags_present(self, cerribro_default):
        flags = cerribro_default.grounding_flags
        assert flags["retrieval_first"] is True
        assert flags["fabrication_allowed"] is False
        assert flags["confidence_signalling"] is True
        assert flags["unsafe_request_rejection"] is True
        assert flags["minimal_viable_change"] is True
        assert flags["test_alongside"] is True

    def test_default_capabilities_registered(self, cerribro_default):
        caps = cerribro_default.list_capabilities()
        assert "app_scaffolding" in caps
        assert "game_development" in caps
        assert "code_debugging" in caps
        assert "code_refactoring" in caps
        assert "test_generation" in caps
        assert "documentation" in caps
        assert "grounded_retrieval" in caps

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="Invalid mode"):
            CerribroAgent(name="Bad", mode="invalid_mode")

    def test_app_builder_mode(self, cerribro_app):
        assert cerribro_app.mode == "app_builder"

    def test_game_builder_mode(self, cerribro_game):
        assert cerribro_game.mode == "game_builder"

    def test_session_history_starts_empty(self, cerribro_default):
        assert cerribro_default.session_history == []

    def test_clarification_queue_starts_empty(self, cerribro_default):
        assert cerribro_default.clarification_queue == []


# ============================================================================
# Mode switching tests
# ============================================================================

class TestCerribroModeSwitch:
    """Tests for runtime mode switching."""

    def test_switch_to_app_builder(self, cerribro_default):
        cerribro_default.set_mode("app_builder")
        assert cerribro_default.mode == "app_builder"

    def test_switch_to_game_builder(self, cerribro_default):
        cerribro_default.set_mode("game_builder")
        assert cerribro_default.mode == "game_builder"

    def test_switch_to_coding_assistant(self, cerribro_app):
        cerribro_app.set_mode("coding_assistant")
        assert cerribro_app.mode == "coding_assistant"

    def test_invalid_mode_switch_raises(self, cerribro_default):
        with pytest.raises(ValueError, match="Invalid mode"):
            cerribro_default.set_mode("unknown_mode")


# ============================================================================
# Grounding — safety gate tests
# ============================================================================

class TestCerribroSafetyGate:
    """Tests for unsafe request rejection."""

    @pytest.mark.parametrize("unsafe_term", [
        "malware", "exploit", "ransomware", "backdoor",
        "keylogger", "rootkit", "phishing", "shellcode",
    ])
    def test_unsafe_keyword_rejected(self, cerribro_default, unsafe_term):
        params = {"description": f"Write a {unsafe_term} for Windows"}
        reasoning = cerribro_default.think(params)
        assert reasoning["decision"] == "reject"
        assert reasoning["confidence"] == 0.0

    def test_rejected_action_returns_rejected_status(self, cerribro_default):
        params = {"description": "Create a keylogger"}
        reasoning = cerribro_default.think(params)
        result = cerribro_default.act(reasoning)
        assert result["status"] == "rejected"
        assert result["confidence"] == 0.0

    def test_safe_request_not_rejected(self, cerribro_default):
        params = {
            "description": "Add input validation to the login form",
            "language": "python",
        }
        reasoning = cerribro_default.think(params)
        assert reasoning["decision"] != "reject"


# ============================================================================
# Grounding — ambiguity gate tests
# ============================================================================

class TestCerribroAmbiguityGate:
    """Tests for clarification requests on ambiguous inputs."""

    def test_empty_description_triggers_clarification(self, cerribro_default):
        params = {"description": ""}
        reasoning = cerribro_default.think(params)
        assert reasoning["decision"] == "clarify"

    def test_short_description_triggers_clarification(self, cerribro_default):
        params = {"description": "fix it"}
        reasoning = cerribro_default.think(params)
        assert reasoning["decision"] == "clarify"

    def test_no_description_key_triggers_clarification(self, cerribro_default):
        params = {}
        reasoning = cerribro_default.think(params)
        assert reasoning["decision"] == "clarify"

    def test_clarification_queued(self, cerribro_default):
        params = {"description": ""}
        cerribro_default.think(params)
        assert len(cerribro_default.clarification_queue) >= 1

    def test_clarification_action_returns_awaiting_status(self, cerribro_default):
        params = {"description": ""}
        reasoning = cerribro_default.think(params)
        result = cerribro_default.act(reasoning)
        assert result["status"] == "awaiting_clarification"

    def test_sufficient_description_proceeds(self, cerribro_default):
        params = {"description": "Refactor the login function to remove duplicate SQL queries"}
        reasoning = cerribro_default.think(params)
        assert reasoning["decision"] not in ("clarify", "reject")


# ============================================================================
# Plan building tests
# ============================================================================

class TestCerribroPlanBuilding:
    """Tests for mode-specific plan construction."""

    def test_coding_assistant_plan_steps(self, cerribro_default):
        params = {"description": "Fix the off-by-one error in the pagination helper"}
        reasoning = cerribro_default.think(params)
        assert reasoning["workflow"] == "coding_assistant"
        assert "understand_context" in reasoning["steps"]
        assert "identify_problem" in reasoning["steps"]
        assert "run_or_suggest_tests" in reasoning["steps"]

    def test_app_builder_plan_steps(self, cerribro_app):
        params = {"description": "Build a REST API for a task management application"}
        reasoning = cerribro_app.think(params)
        assert reasoning["workflow"] == "app_builder"
        assert "scaffold_project_structure" in reasoning["steps"]
        assert "write_tests" in reasoning["steps"]

    def test_game_builder_plan_steps(self, cerribro_game):
        params = {"description": "Create a 2D side-scrolling platformer in Godot"}
        reasoning = cerribro_game.think(params)
        assert reasoning["workflow"] == "game_builder"
        assert "design_game_loop" in reasoning["steps"]
        assert "test_gameplay" in reasoning["steps"]

    def test_confidence_included_in_plan(self, cerribro_default):
        params = {"description": "Refactor the authentication module for better testability"}
        reasoning = cerribro_default.think(params)
        assert "confidence" in reasoning
        assert 0.0 <= reasoning["confidence"] <= 1.0

    def test_grounding_flags_in_plan(self, cerribro_default):
        params = {"description": "Write unit tests for the payment gateway integration"}
        reasoning = cerribro_default.think(params)
        assert "grounding_flags" in reasoning
        assert reasoning["grounding_flags"]["fabrication_allowed"] is False

    def test_mode_in_plan(self, cerribro_default):
        params = {"description": "Improve error handling in the API layer"}
        reasoning = cerribro_default.think(params)
        assert reasoning["mode"] == "coding_assistant"


# ============================================================================
# Act / execution tests
# ============================================================================

class TestCerribroAct:
    """Tests for act() output structure."""

    def test_completed_result_structure(self, cerribro_default):
        params = {"description": "Add docstrings to all public functions in utils.py"}
        reasoning = cerribro_default.think(params)
        result = cerribro_default.act(reasoning)
        assert result["status"] == "completed"
        assert "confidence" in result
        assert "output" in result
        assert result["mode"] == "coding_assistant"

    def test_session_history_updated_after_act(self, cerribro_default):
        params = {"description": "Implement caching for the database query layer"}
        reasoning = cerribro_default.think(params)
        cerribro_default.act(reasoning)
        assert len(cerribro_default.session_history) == 1

    def test_session_history_accumulates(self, cerribro_default):
        for i in range(3):
            params = {"description": f"Task number {i} — refactor module {i} for clarity"}
            reasoning = cerribro_default.think(params)
            cerribro_default.act(reasoning)
        assert len(cerribro_default.session_history) == 3

    def test_output_contains_workflow(self, cerribro_app):
        params = {"description": "Scaffold a GraphQL API with user authentication support"}
        reasoning = cerribro_app.think(params)
        result = cerribro_app.act(reasoning)
        assert result["output"]["workflow"] == "app_builder"

    def test_output_contains_steps_planned(self, cerribro_default):
        params = {"description": "Write integration tests for the checkout endpoint"}
        reasoning = cerribro_default.think(params)
        result = cerribro_default.act(reasoning)
        assert isinstance(result["output"]["steps_planned"], list)
        assert len(result["output"]["steps_planned"]) > 0


# ============================================================================
# Confidence scoring tests
# ============================================================================

class TestCerribroConfidence:
    """Tests for confidence assessment heuristics."""

    def test_short_description_low_confidence(self, cerribro_default):
        # Below ambiguity threshold — will clarify, confidence = 0.5
        params = {"description": "fix bug"}
        reasoning = cerribro_default.think(params)
        assert reasoning["confidence"] <= 0.5

    def test_detailed_description_higher_confidence(self, cerribro_default):
        params = {
            "description": (
                "Refactor the authentication module to use constructor-based dependency "
                "injection so that tests can inject a mock JWT validator without "
                "patching module globals. This will improve testability and reduce "
                "coupling between the auth layer and the JWT library implementation."
            )
        }
        reasoning = cerribro_default.think(params)
        assert reasoning["confidence"] >= 0.8


# ============================================================================
# Capability registration tests
# ============================================================================

class TestCerribroCapabilities:
    """Tests for dynamic capability registration."""

    def test_register_additional_capability(self, cerribro_default):
        cap = AgentCapability(
            name="database_design",
            description="Design relational and document database schemas.",
            confidence_score=0.89,
        )
        success = cerribro_default.register_capability(cap)
        assert success is True
        assert "database_design" in cerribro_default.list_capabilities()

    def test_capability_confidence_score(self, cerribro_default):
        cap_name = "code_debugging"
        cap = cerribro_default.get_capability(cap_name)
        assert cap is not None
        assert cap.confidence_score == 0.95


# ============================================================================
# AgentFactory integration tests
# ============================================================================

class TestCerribroFactory:
    """Tests for AgentFactory integration."""

    def test_factory_creates_cerribro(self):
        agent = AgentFactory.create_agent("cerribro", "Cerribro-Factory")
        assert agent is not None
        assert isinstance(agent, CerribroAgent)

    def test_factory_cerribro_default_mode(self):
        agent = AgentFactory.create_agent("cerribro", "Cerribro-Factory")
        assert agent.mode == "coding_assistant"

    def test_factory_cerribro_name(self):
        agent = AgentFactory.create_agent("cerribro", "MyCerribro")
        assert agent.name == "MyCerribro"


# ============================================================================
# Task execution integration tests
# ============================================================================

class TestCerribroTaskExecution:
    """End-to-end task lifecycle tests using the BaseAgent infrastructure."""

    def test_assign_and_execute_task(self, cerribro_default):
        from src.agents.super_agentic_agents import Task, TaskPriority

        task = Task(
            description="Add type hints to the data processing module",
            parameters={
                "description": "Add type hints to the data processing module",
                "language": "python",
            },
        )
        assert cerribro_default.assign_task(task)
        result = cerribro_default.execute_task(task)
        assert task.status == TaskStatus.COMPLETED
        assert result["status"] == "completed"

    def test_task_history_updated_after_execution(self, cerribro_default):
        from src.agents.super_agentic_agents import Task

        task = Task(
            description="Document the public API of the analytics module",
            parameters={
                "description": "Document the public API of the analytics module",
                "language": "python",
            },
        )
        cerribro_default.assign_task(task)
        cerribro_default.execute_task(task)
        assert len(cerribro_default.task_history) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
