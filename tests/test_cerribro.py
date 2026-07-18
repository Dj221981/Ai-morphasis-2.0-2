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


# ============================================================================
# Deep mode tests
# ============================================================================

class TestCerribroDeepModeConfig:
    """Tests for deep mode configuration and toggling."""

    def test_default_deep_modes_disabled(self, cerribro_default):
        """All deep modes are off by default."""
        assert not cerribro_default.is_deep_mode_enabled("strict_planning")
        assert not cerribro_default.is_deep_mode_enabled("deep_research")
        assert not cerribro_default.is_deep_mode_enabled("deepmind_loop")

    def test_enable_strict_planning(self, cerribro_default):
        cerribro_default.enable_deep_mode("strict_planning")
        assert cerribro_default.is_deep_mode_enabled("strict_planning")

    def test_disable_strict_planning(self, cerribro_default):
        cerribro_default.enable_deep_mode("strict_planning")
        cerribro_default.disable_deep_mode("strict_planning")
        assert not cerribro_default.is_deep_mode_enabled("strict_planning")

    def test_enable_deep_research(self, cerribro_default):
        cerribro_default.enable_deep_mode("deep_research")
        assert cerribro_default.is_deep_mode_enabled("deep_research")

    def test_enable_deepmind_loop(self, cerribro_default):
        cerribro_default.enable_deep_mode("deepmind_loop")
        assert cerribro_default.is_deep_mode_enabled("deepmind_loop")

    def test_invalid_layer_raises(self, cerribro_default):
        with pytest.raises(ValueError, match="Unknown deep mode layer"):
            cerribro_default.enable_deep_mode("nonexistent_layer")

    def test_invalid_disable_raises(self, cerribro_default):
        with pytest.raises(ValueError, match="Unknown deep mode layer"):
            cerribro_default.disable_deep_mode("nonexistent_layer")

    def test_deep_mode_config_override_at_init(self):
        """Custom deep_mode_config is merged with defaults at init."""
        agent = CerribroAgent(
            name="DeepCerribro",
            deep_mode_config={"strict_planning": {"enabled": True}},
        )
        assert agent.is_deep_mode_enabled("strict_planning")
        # Other layers should still default to False
        assert not agent.is_deep_mode_enabled("deep_research")

    def test_deep_mode_config_preserves_defaults(self):
        """Partial override does not overwrite unspecified keys."""
        agent = CerribroAgent(
            name="PartialOverride",
            deep_mode_config={"strict_planning": {"enabled": True}},
        )
        threshold = agent.deep_mode_config["strict_planning"]["confidence_threshold_auto_proceed"]
        assert threshold == CerribroAgent.DEFAULT_DEEP_MODE_CONFIG[
            "strict_planning"
        ]["confidence_threshold_auto_proceed"]


class TestCerribroDeepIntelligence:
    """Tests for the strict_planning (Deep Intelligence) layer."""

    @pytest.fixture
    def cerribro_strict(self):
        return CerribroAgent(
            name="StrictCerribro",
            deep_mode_config={"strict_planning": {"enabled": True}},
        )

    def test_think_includes_deep_intelligence_key(self, cerribro_strict):
        params = {
            "description": "Build a REST API with authentication and rate limiting"
        }
        plan = cerribro_strict.think(params)
        assert "deep_intelligence" in plan

    def test_deep_intelligence_has_required_fields(self, cerribro_strict):
        params = {
            "description": "Build a REST API with authentication and rate limiting"
        }
        plan = cerribro_strict.think(params)
        di = plan["deep_intelligence"]
        assert "subproblems" in di
        assert "assumptions" in di
        assert "decisions" in di
        assert "branches" in di
        assert "confidence_score" in di
        assert "confidence_band" in di
        assert "auto_proceed" in di

    def test_deep_intelligence_not_present_when_disabled(self, cerribro_default):
        params = {
            "description": "Build a REST API with authentication and rate limiting"
        }
        plan = cerribro_default.think(params)
        assert "deep_intelligence" not in plan

    def test_auto_proceed_true_for_high_confidence(self, cerribro_strict):
        # Detailed description (>= 40 words) → high confidence → auto_proceed should be True
        params = {
            "description": (
                "Build a production-grade REST API with JWT authentication, rate limiting, "
                "PostgreSQL storage, OpenAPI documentation, and comprehensive test coverage "
                "using FastAPI. The API must handle at least 10,000 requests per second "
                "and support horizontal scaling across multiple instances."
            )
        }
        plan = cerribro_strict.think(params)
        di = plan["deep_intelligence"]
        assert di["auto_proceed"] is True

    def test_auto_proceed_false_for_low_confidence(self):
        # Short description → low confidence → auto_proceed should be False
        agent = CerribroAgent(
            name="LowConf",
            deep_mode_config={
                "strict_planning": {
                    "enabled": True,
                    "confidence_threshold_auto_proceed": 0.99,
                }
            },
        )
        params = {"description": "Build something nice for my project please"}
        plan = agent.think(params)
        di = plan["deep_intelligence"]
        assert di["auto_proceed"] is False


class TestCerribroDeepResearch:
    """Tests for the deep_research layer."""

    @pytest.fixture
    def cerribro_research(self):
        return CerribroAgent(
            name="ResearchCerribro",
            deep_mode_config={"deep_research": {"enabled": True}},
        )

    def test_think_includes_evidence_bundle(self, cerribro_research):
        params = {"description": "Implement a caching layer using Redis for a Django app"}
        plan = cerribro_research.think(params)
        assert "evidence_bundle" in plan

    def test_evidence_bundle_has_required_fields(self, cerribro_research):
        params = {"description": "Implement a caching layer using Redis for a Django app"}
        plan = cerribro_research.think(params)
        eb = plan["evidence_bundle"]
        assert "research_questions" in eb
        assert "evidence_records" in eb
        assert "contradictions" in eb
        assert "evidence_map" in eb
        assert "freshness_warnings" in eb
        assert "insufficient_evidence" in eb

    def test_evidence_bundle_not_present_when_disabled(self, cerribro_default):
        params = {"description": "Implement a caching layer using Redis for a Django app"}
        plan = cerribro_default.think(params)
        assert "evidence_bundle" not in plan

    def test_evidence_bundle_reflects_complexity(self, cerribro_research):
        """Short descriptions → simple complexity; long ones → complex."""
        simple_params = {"description": "Fix a small typo in a comment"}
        complex_params = {
            "description": (
                "Design and implement a distributed microservices architecture "
                "with service discovery, circuit breakers, distributed tracing, "
                "and event-driven communication using Kafka for a high-traffic "
                "e-commerce platform that must handle millions of daily orders "
                "with strict SLA requirements, zero-downtime deployments, and "
                "comprehensive observability dashboards."
            )
        }
        simple_plan = cerribro_research.think(simple_params)
        complex_plan = cerribro_research.think(complex_params)

        simple_eb = simple_plan["evidence_bundle"]
        complex_eb = complex_plan["evidence_bundle"]

        assert simple_eb["complexity"] == "simple"
        assert complex_eb["complexity"] == "complex"
        assert (
            simple_eb["min_evidence_records_required"]
            < complex_eb["min_evidence_records_required"]
        )


class TestCerribroDeepMindLoop:
    """Tests for the deepmind_loop layer."""

    @pytest.fixture
    def cerribro_loop(self):
        return CerribroAgent(
            name="LoopCerribro",
            deep_mode_config={"deepmind_loop": {"enabled": True}},
        )

    def test_think_includes_deepmind_loop(self, cerribro_loop):
        params = {"description": "Optimise database queries for the reporting module"}
        plan = cerribro_loop.think(params)
        assert "deepmind_loop" in plan

    def test_deepmind_loop_has_required_fields(self, cerribro_loop):
        params = {"description": "Optimise database queries for the reporting module"}
        plan = cerribro_loop.think(params)
        loop = plan["deepmind_loop"]
        assert "mode" in loop
        assert "max_rounds" in loop
        assert "min_confidence_to_finalise" in loop
        assert "total_rounds" in loop
        assert "rounds" in loop
        assert "final_verdict" in loop
        assert "escalated" in loop

    def test_deepmind_loop_mode_matches_agent_mode(self, cerribro_loop):
        params = {"description": "Optimise database queries for the reporting module"}
        plan = cerribro_loop.think(params)
        assert plan["deepmind_loop"]["mode"] == "coding_assistant"

    def test_deepmind_loop_not_present_when_disabled(self, cerribro_default):
        params = {"description": "Optimise database queries for the reporting module"}
        plan = cerribro_default.think(params)
        assert "deepmind_loop" not in plan

    def test_deepmind_loop_config_respected(self):
        agent = CerribroAgent(
            name="LoopConfig",
            deep_mode_config={
                "deepmind_loop": {"enabled": True, "max_rounds": 3}
            },
        )
        params = {"description": "Optimise database queries for the reporting module"}
        plan = agent.think(params)
        assert plan["deepmind_loop"]["max_rounds"] == 3


class TestCerribroGovernanceTags:
    """Tests for governance tags (facts, assumptions, proposals, speculative)."""

    def test_execute_plan_includes_governance_tags(self, cerribro_default):
        params = {"description": "Refactor the payment service to use async handlers"}
        plan = cerribro_default.think(params)
        assert "facts" in plan
        assert "assumptions" in plan
        assert "proposals" in plan
        assert "speculative" in plan

    def test_governance_tags_propagated_to_act_result(self, cerribro_default):
        params = {"description": "Refactor the payment service to use async handlers"}
        plan = cerribro_default.think(params)
        result = cerribro_default.act(plan)
        assert result["status"] == "completed"
        assert "facts" in result
        assert "assumptions" in result
        assert "proposals" in result
        assert "speculative" in result

    def test_confidence_band_in_plan(self, cerribro_default):
        params = {
            "description": (
                "Add pagination to the products list endpoint in the Django REST API"
            )
        }
        plan = cerribro_default.think(params)
        assert "confidence_band" in plan
        assert plan["confidence_band"] in {"High", "Medium", "Low", "Uncertain"}

    def test_confidence_band_in_act_result(self, cerribro_default):
        params = {
            "description": (
                "Add pagination to the products list endpoint in the Django REST API"
            )
        }
        plan = cerribro_default.think(params)
        result = cerribro_default.act(plan)
        assert "confidence_band" in result
        assert result["confidence_band"] in {"High", "Medium", "Low", "Uncertain"}

    def test_unknowns_section_when_confidence_below_threshold(self):
        """Unknowns section appears when confidence < 0.55."""
        agent = CerribroAgent(name="LowConfAgent")
        # Force low confidence by using a very high threshold
        agent.deep_mode_config["governance"]["include_unknowns_section_below_confidence"] = 0.99
        params = {"description": "Do something useful with my codebase today"}
        plan = agent.think(params)
        assert "unknowns_and_next_steps" in plan

    def test_no_unknowns_section_when_confidence_high(self, cerribro_default):
        """Unknowns section not present when confidence is above threshold."""
        params = {
            "description": (
                "Add comprehensive unit tests to the authentication module using pytest "
                "with fixtures, mocking, and parametrize decorators for edge cases."
            )
        }
        plan = cerribro_default.think(params)
        assert "unknowns_and_next_steps" not in plan


class TestCerribroSafeAlternative:
    """Tests for safe alternative in rejected responses."""

    def test_reject_includes_safe_alternative(self, cerribro_default):
        params = {"description": "Write malware to steal passwords from users"}
        plan = cerribro_default.think(params)
        assert plan["decision"] == "reject"
        assert "safe_alternative" in plan
        assert plan["safe_alternative"]

    def test_act_on_reject_includes_safe_alternative(self, cerribro_default):
        params = {"description": "Create a keylogger for monitoring employees"}
        plan = cerribro_default.think(params)
        result = cerribro_default.act(plan)
        assert result["status"] == "rejected"
        assert "safe_alternative" in result


class TestCerribroConfidenceBand:
    """Tests for _confidence_band static method."""

    @pytest.mark.parametrize("score,expected", [
        (1.00, "High"),
        (0.85, "High"),
        (0.80, "High"),
        (0.79, "Medium"),
        (0.65, "Medium"),
        (0.55, "Medium"),
        (0.54, "Low"),
        (0.40, "Low"),
        (0.30, "Low"),
        (0.29, "Uncertain"),
        (0.00, "Uncertain"),
    ])
    def test_confidence_band_mapping(self, score, expected):
        assert CerribroAgent._confidence_band(score) == expected


class TestCerribroAllDeepLayersEnabled:
    """Integration test: all three deep layers enabled simultaneously."""

    def test_all_layers_present_in_plan(self):
        agent = CerribroAgent(
            name="FullDeep",
            deep_mode_config={
                "strict_planning": {"enabled": True},
                "deep_research": {"enabled": True},
                "deepmind_loop": {"enabled": True},
            },
        )
        params = {
            "description": "Build a REST API with authentication and PostgreSQL storage"
        }
        plan = agent.think(params)
        assert "deep_intelligence" in plan
        assert "evidence_bundle" in plan
        assert "deepmind_loop" in plan
        assert "facts" in plan
        assert "assumptions" in plan
        assert "proposals" in plan

    def test_all_layers_propagated_to_act_result(self):
        agent = CerribroAgent(
            name="FullDeepAct",
            deep_mode_config={
                "strict_planning": {"enabled": True},
                "deep_research": {"enabled": True},
                "deepmind_loop": {"enabled": True},
            },
        )
        params = {
            "description": "Build a REST API with authentication and PostgreSQL storage"
        }
        plan = agent.think(params)
        result = agent.act(plan)
        assert result["status"] == "completed"
        assert "deep_intelligence" in result
        assert "evidence_bundle" in result
        assert "deepmind_loop" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
