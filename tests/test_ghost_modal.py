import json
from pathlib import Path

from agents.cerribro.ghost_modal import GhostModal, GhostMode


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ghost_modal_defaults_to_normal_mode() -> None:
    gm = GhostModal(agent_name="cerribro")
    state = gm.get_state()
    assert state["mode"] == "normal"
    assert state["threat_score"] == 0


def test_ghost_modal_switches_to_security_on_threat() -> None:
    gm = GhostModal(agent_name="cerribro", threshold=2)
    state = gm.evaluate("Possible malware exploit and token exposure")
    assert state["mode"] == "security"
    assert state["threat_score"] >= 2
    assert state["reasons"]


def test_ghost_modal_restricts_tools_by_mode() -> None:
    gm = GhostModal(agent_name="cerribro")
    gm.evaluate("normal request without threats")
    out = gm.execute("summarize", "hello")
    assert out["tool"] == "summarize"

    gm.evaluate("sql injection malware token")
    assert gm.get_state()["mode"] == "security"

    try:
        gm.execute("summarize", "blocked in security mode")
        assert False, "Expected ValueError for unavailable tool in security mode"
    except ValueError:
        pass


def test_ghost_modal_can_register_custom_tools_for_cerribrobaddan() -> None:
    gm = GhostModal(agent_name="cerribrobaddan")

    def defense_review(payload: str) -> dict:
        return {"tool": "defense_review", "payload": payload, "status": "ok"}

    gm.register_tool(GhostMode.SECURITY, "defense_review", defense_review)
    gm.evaluate("ransomware payload and secret leak", context={"agent": "cerribrobaddan"})
    result = gm.execute("defense_review", "check release candidate")
    assert result["status"] == "ok"


def test_cerribro_agent_config_includes_ghost_modal() -> None:
    config_path = REPO_ROOT / "agents" / "cerribro" / "agent_config.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))

    assert "ghost_modal" in data
    gm = data["ghost_modal"]
    assert gm["enabled"] is True
    assert gm["shared_with"] == ["cerribro", "cerribrobaddan"]
    assert gm["default_mode"] == "normal"
    assert gm["security_mode"] == "security"
    assert isinstance(gm["threat_threshold"], int)
    assert gm["threat_threshold"] >= 1
