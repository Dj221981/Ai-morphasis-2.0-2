import pytest

from src.config.model_config import get_config, list_configs


def test_list_configs_returns_known_entries() -> None:
    configs = list_configs()
    assert "dqn" in configs
    assert "policy" in configs


def test_get_config_returns_copy() -> None:
    config = get_config("dqn")
    config["model"]["state_size"] = -1

    fresh = get_config("dqn")
    assert fresh["model"]["state_size"] == 64


def test_get_config_raises_for_unknown_name() -> None:
    with pytest.raises(ValueError):
        get_config("unknown")
