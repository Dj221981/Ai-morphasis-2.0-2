"""
Smoke and configuration tests for src/ modules.

These tests cover the configuration surface that is importable without
optional heavy dependencies (TensorFlow, NumPy, etc.).  ML model tests
that require TensorFlow are intentionally excluded from the default CI
suite because TensorFlow is not a required runtime dependency.
"""

import copy

import pytest

from src.config.model_config import CONFIG_REGISTRY, get_config, list_configs


class TestListConfigs:
    def test_returns_list(self) -> None:
        result = list_configs()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_expected_configs_present(self) -> None:
        names = list_configs()
        for expected in ("dqn", "policy", "small", "large", "continuous", "multi_agent"):
            assert expected in names, f"Config '{expected}' missing from registry"


class TestGetConfig:
    def test_returns_dict(self) -> None:
        cfg = get_config("dqn")
        assert isinstance(cfg, dict)

    def test_dqn_has_required_keys(self) -> None:
        cfg = get_config("dqn")
        for key in ("model", "environment", "training", "data", "evaluation"):
            assert key in cfg, f"Key '{key}' missing from dqn config"

    def test_returns_copy_not_reference(self) -> None:
        cfg1 = get_config("dqn")
        cfg2 = get_config("dqn")
        cfg1["model"]["state_size"] = 9999
        assert cfg2["model"]["state_size"] != 9999, "get_config must return an independent copy"

    def test_boolean_values_are_python_bools(self) -> None:
        for name in list_configs():
            cfg = get_config(name)
            data = cfg.get("data", {})
            aug = data.get("augmentation", {})
            assert isinstance(data.get("reward_normalization"), bool), (
                f"{name}: reward_normalization should be bool"
            )
            assert isinstance(aug.get("enabled"), bool), (
                f"{name}: augmentation.enabled should be bool"
            )

    def test_unknown_config_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown configuration"):
            get_config("does_not_exist")

    @pytest.mark.parametrize("name", ["dqn", "policy", "small", "large", "continuous", "multi_agent"])
    def test_all_configs_loadable(self, name: str) -> None:
        cfg = get_config(name)
        assert cfg["model"]["type"] in ("dqn", "policy_gradient")


class TestConfigRegistry:
    def test_registry_is_dict(self) -> None:
        assert isinstance(CONFIG_REGISTRY, dict)

    def test_registry_not_mutated_by_get_config(self) -> None:
        original = copy.deepcopy(CONFIG_REGISTRY["dqn"]["model"]["state_size"])
        cfg = get_config("dqn")
        cfg["model"]["state_size"] = 9999
        assert CONFIG_REGISTRY["dqn"]["model"]["state_size"] == original


class TestConfigValueInvariants:
    @pytest.mark.parametrize("name", ["dqn", "policy", "small", "large", "continuous", "multi_agent"])
    def test_learning_rate_is_positive(self, name: str) -> None:
        cfg = get_config(name)
        lr = cfg["model"]["learning_rate"]
        assert isinstance(lr, float), f"{name}: learning_rate must be a float"
        assert lr > 0, f"{name}: learning_rate must be positive, got {lr}"

    @pytest.mark.parametrize("name", ["dqn", "policy", "small", "large", "continuous", "multi_agent"])
    def test_gamma_in_valid_range(self, name: str) -> None:
        cfg = get_config(name)
        gamma = cfg["model"]["gamma"]
        assert 0 < gamma <= 1, f"{name}: gamma must be in (0, 1], got {gamma}"
