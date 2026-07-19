import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "agents" / "cerribro" / "agent_config.json"


def load_cerribro_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_cerribro_coding_tools_profile_exists() -> None:
    assert CONFIG_PATH.exists()
    config = load_cerribro_config()
    assert config["agent_name"] == "cerribro"
    assert "coding_tools" in config
    assert isinstance(config["coding_tools"], dict) and config["coding_tools"]


def test_coding_tools_activation_rules_cover_required_modes() -> None:
    activation_rules = load_cerribro_config()["coding_tools"]["activation_rules"]
    assert activation_rules["coding_assistant"] == "always"
    assert activation_rules["app_builder"] == "activate_when_concrete_code_task_present"
    assert activation_rules["game_builder"] == "activate_when_concrete_code_task_present"
    assert activation_rules["conceptual_only"] == "no_tool_execution_unless_requested_for_validation"


def test_coding_pipeline_guardrails_and_output_contract() -> None:
    coding_tools = load_cerribro_config()["coding_tools"]

    assert coding_tools["workflow_pipeline"] == [
        "inspect_context",
        "plan_minimal_changeset",
        "apply_edits",
        "run_quality_gates",
        "verify_acceptance_criteria",
        "produce_grounded_summary",
    ]

    guardrails = coding_tools["guardrails"]
    assert guardrails["read_before_edit"] is True
    assert guardrails["minimal_diff_preferred"] is True
    assert guardrails["deny_large_refactor_without_request"] is True
    assert guardrails["require_verification_evidence_for_code_claims"] is True
    assert guardrails["mark_unverified_assumptions"] is True
    assert guardrails["deny_unsafe_or_malicious_requests"] is True

    assert coding_tools["output_contract"] == [
        "objective",
        "files_changed",
        "diff_summary",
        "tests_checks_run_with_status",
        "known_limitations_or_unknowns",
        "next_recommended_step",
    ]
