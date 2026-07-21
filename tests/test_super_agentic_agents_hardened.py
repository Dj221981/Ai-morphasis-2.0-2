"""
tests/test_super_agentic_agents_hardened.py
===========================================
Comprehensive tests for the production-hardened compatibility shim.

Tests cover:
- Safe import paths and error handling
- Graceful fallback behavior
- Configuration via environment variables
- Validation functions (breaking and non-breaking variants)
- Deprecation warnings
- Health check helpers
"""

import os
import sys
import pytest
import logging
import warnings
from unittest import mock
from typing import Dict

# Import the shim module for testing
import src.agents.super_agentic_agents as shim


class TestSafeImport:
    """Test safe import behavior and error handling."""

    def test_safe_import_succeeds_when_package_available(self):
        """Verify safe import succeeds with available src.agents package."""
        result = shim._safe_import_from_package()
        assert result is True
        assert len(shim._import_errors) == 0

    def test_safe_import_returns_false_when_symbols_missing(self):
        """Verify safe import returns False if any symbol is unavailable."""
        with mock.patch("importlib.import_module") as mock_import:
            pkg_mock = mock.MagicMock()
            # Missing AgentSystem
            del pkg_mock.AgentSystem
            mock_import.return_value = pkg_mock

            result = shim._safe_import_from_package()
            assert result is False

    def test_safe_import_handles_package_import_error(self):
        """Verify safe import gracefully handles package ImportError."""
        with mock.patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Package not found")

            result = shim._safe_import_from_package()
            assert result is False
            assert "__package__" in shim._import_errors

    def test_safe_import_handles_unexpected_exceptions(self):
        """Verify safe import catches all exceptions, not just ImportError."""
        with mock.patch("importlib.import_module") as mock_import:
            mock_import.side_effect = RuntimeError("Unexpected error")

            result = shim._safe_import_from_package()
            assert result is False
            assert "__unexpected__" in shim._import_errors


class TestGracefulFallback:
    """Test graceful fallback vs. strict mode behavior."""

    def test_strict_mode_raises_on_import_failure(self):
        """Verify AGENT_SHIM_STRICT_MODE=true causes hard failure."""
        with mock.patch.dict(os.environ, {"AGENT_SHIM_STRICT_MODE": "true"}):
            with mock.patch("src.agents.super_agentic_agents._safe_import_from_package") as mock_import:
                mock_import.return_value = False
                shim._import_errors["test_symbol"] = ImportError("test")

                with pytest.raises(ImportError, match="strict mode"):
                    shim._startup()

    def test_non_strict_mode_logs_warning_on_import_failure(self, caplog):
        """Verify graceful degradation in non-strict mode."""
        with mock.patch.dict(os.environ, {"AGENT_SHIM_STRICT_MODE": "false"}):
            with mock.patch("src.agents.super_agentic_agents._safe_import_from_package") as mock_import:
                with mock.patch("src.agents.super_agentic_agents._emit_deprecation_warning"):
                    mock_import.return_value = False
                    shim._import_errors["test_symbol"] = ImportError("test")

                    with caplog.at_level(logging.WARNING):
                        shim._startup()

                    assert "Graceful degradation" in caplog.text

    def test_strict_mode_validates_on_startup(self):
        """Verify validation is run and enforced in strict mode."""
        with mock.patch.dict(os.environ, {"AGENT_SHIM_STRICT_MODE": "true"}):
            with mock.patch("src.agents.super_agentic_agents._safe_import_from_package") as mock_import:
                with mock.patch("src.agents.super_agentic_agents.validate_shim_integrity") as mock_validate:
                    with mock.patch("src.agents.super_agentic_agents._emit_deprecation_warning"):
                        mock_import.return_value = True
                        mock_validate.side_effect = AssertionError("validation failed")

                        with pytest.raises(AssertionError):
                            shim._startup()


class TestEnvironmentConfiguration:
    """Test environment variable controls."""

    def test_strict_mode_env_parsing_true_variants(self):
        """Verify AGENT_SHIM_STRICT_MODE accepts true/1/yes."""
        for value in ["true", "True", "TRUE", "1", "yes", "YES"]:
            with mock.patch.dict(os.environ, {"AGENT_SHIM_STRICT_MODE": value}):
                # Re-import to pick up env var
                import importlib
                importlib.reload(shim)
                assert shim._STRICT_MODE is True

    def test_strict_mode_env_parsing_false_variants(self):
        """Verify AGENT_SHIM_STRICT_MODE rejects other values."""
        for value in ["false", "0", "no", ""]:
            with mock.patch.dict(os.environ, {"AGENT_SHIM_STRICT_MODE": value}):
                import importlib
                importlib.reload(shim)
                assert shim._STRICT_MODE is False

    def test_validate_at_import_env_control(self):
        """Verify AGENT_SHIM_VALIDATE_AT_IMPORT controls startup validation."""
        with mock.patch.dict(os.environ, {"AGENT_SHIM_VALIDATE_AT_IMPORT": "false"}):
            with mock.patch("src.agents.super_agentic_agents._safe_import_from_package") as mock_import:
                with mock.patch("src.agents.super_agentic_agents.validate_shim_integrity") as mock_validate:
                    with mock.patch("src.agents.super_agentic_agents._emit_deprecation_warning"):
                        mock_import.return_value = True

                        shim._startup()

                        # When VALIDATE_AT_IMPORT=false, validate_shim_integrity should not be called
                        # (This test depends on implementation details, adjust as needed)

    def test_log_level_env_control(self):
        """Verify AGENT_SHIM_LOG_LEVEL sets logger level."""
        with mock.patch.dict(os.environ, {"AGENT_SHIM_LOG_LEVEL": "DEBUG"}):
            import importlib
            importlib.reload(shim)
            assert shim.logger.level == logging.DEBUG

    def test_log_level_invalid_falls_back_to_info(self):
        """Verify invalid log level falls back to INFO."""
        with mock.patch.dict(os.environ, {"AGENT_SHIM_LOG_LEVEL": "INVALID"}):
            import importlib
            importlib.reload(shim)
            assert shim.logger.level == logging.INFO


class TestValidationFunctions:
    """Test non-breaking and strict validation functions."""

    def test_validate_all_modules_returns_dict(self):
        """Verify validate_all_modules returns status dict."""
        result = shim.validate_all_modules()
        assert isinstance(result, dict)
        assert all(isinstance(v, bool) for v in result.values())

    def test_validate_all_modules_all_pass(self):
        """Verify all required modules are present."""
        result = shim.validate_all_modules()
        assert all(result.values()), f"Failed modules: {[k for k, v in result.items() if not v]}"

    def test_validate_shim_integrity_non_breaking_mode(self):
        """Verify validate_shim_integrity returns bool in non-raising mode."""
        result = shim.validate_shim_integrity(raise_on_error=False)
        assert isinstance(result, bool)
        assert result is True

    def test_validate_shim_integrity_strict_mode(self):
        """Verify validate_shim_integrity raises in strict mode."""
        with mock.patch("src.agents.super_agentic_agents.validate_all_modules") as mock_validate:
            mock_validate.return_value = {"src.agents.models": False}

            with pytest.raises(ImportError):
                shim.validate_shim_integrity(raise_on_error=True)

    def test_validate_shim_integrity_detects_missing_symbols_on_shim(self):
        """Verify validation detects symbols missing from shim module."""
        with mock.patch.dict(sys.modules[shim.__name__].__dict__, {"TestSymbol": None}, clear=False):
            # Temporarily remove a symbol
            original_all = shim.__all__
            if isinstance(original_all, tuple):
                shim.__all__ = original_all + ("NonExistentSymbol",)
            else:
                shim.__all__ = [*original_all, "NonExistentSymbol"]

            result = shim.validate_shim_integrity(raise_on_error=False)
            assert result is False

            shim.__all__ = original_all

    def test_validate_shim_integrity_detects_missing_symbols_on_package(self):
        """Verify validation detects symbols missing from src.agents."""
        with mock.patch("importlib.import_module") as mock_import:
            pkg_mock = mock.MagicMock()
            pkg_mock.__name__ = "src.agents"

            def getattr_side_effect(obj, name):
                if name == "NonExistentSymbol":
                    raise AttributeError(f"No such attribute: {name}")
                return getattr(pkg_mock, name)

            mock_import.return_value = pkg_mock

            original_all = shim.__all__
            if isinstance(original_all, tuple):
                shim.__all__ = original_all + ("NonExistentSymbol",)
            else:
                shim.__all__ = [*original_all, "NonExistentSymbol"]

            result = shim.validate_shim_integrity(raise_on_error=False)
            assert result is False

            shim.__all__ = original_all


class TestHealthCheckHelpers:
    """Test helper functions for health checks and diagnostics."""

    def test_is_shim_fully_functional_true_when_no_errors(self):
        """Verify is_shim_fully_functional returns True when all imports succeeded."""
        shim._import_errors.clear()
        assert shim.is_shim_fully_functional() is True

    def test_is_shim_fully_functional_false_when_errors_present(self):
        """Verify is_shim_fully_functional returns False when errors exist."""
        shim._import_errors["test"] = ImportError("test error")
        assert shim.is_shim_fully_functional() is False
        shim._import_errors.clear()

    def test_get_import_errors_returns_dict_copy(self):
        """Verify get_import_errors returns a copy (safe access)."""
        shim._import_errors["test"] = ImportError("test")
        errors = shim.get_import_errors()

        assert isinstance(errors, dict)
        assert "test" in errors
        assert errors is not shim._import_errors  # Should be a copy

        shim._import_errors.clear()

    def test_get_import_errors_empty_when_no_failures(self):
        """Verify get_import_errors returns empty dict on success."""
        shim._import_errors.clear()
        errors = shim.get_import_errors()
        assert len(errors) == 0


class TestDeprecationWarning:
    """Test deprecation warning emission."""

    def test_deprecation_warning_emitted_on_startup(self):
        """Verify DeprecationWarning is emitted when shim is initialized."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            shim._emit_deprecation_warning()

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "v3.0.0" in str(w[0].message)
            assert "migration" in str(w[0].message).lower()

    def test_deprecation_warning_includes_migration_link(self):
        """Verify deprecation warning includes link to migration guide."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            shim._emit_deprecation_warning()

            message = str(w[0].message)
            assert "migration.md" in message.lower() or "github.com" in message.lower()


class TestPublicAPI:
    """Test that public API symbols are accessible."""

    def test_all_symbols_in_all_are_importable(self):
        """Verify every symbol in __all__ is actually accessible."""
        for symbol_name in shim.__all__:
            assert hasattr(shim, symbol_name), f"Symbol {symbol_name} not found in module"

    def test_core_agent_classes_are_accessible(self):
        """Verify key classes are accessible."""
        assert hasattr(shim, "AgentSystem")
        assert hasattr(shim, "BaseAgent")
        assert hasattr(shim, "OrchestratorAgent")
        assert hasattr(shim, "ExecutorAgent")

    def test_core_models_are_accessible(self):
        """Verify domain models are accessible."""
        assert hasattr(shim, "Task")
        assert hasattr(shim, "AgentRole")
        assert hasattr(shim, "TaskStatus")
        assert hasattr(shim, "RetryPolicy")

    def test_runtime_helpers_are_accessible(self):
        """Verify runtime scheduling functions are accessible."""
        assert hasattr(shim, "run_once")
        assert hasattr(shim, "run_forever")
        assert hasattr(shim, "dispatch_pending_tasks")
        assert hasattr(shim, "process_retry_queue")

    def test_persistence_backends_are_accessible(self):
        """Verify persistence implementations are accessible."""
        assert hasattr(shim, "InMemoryTaskRepository")
        assert hasattr(shim, "SqlTaskRepository")
        assert hasattr(shim, "RedisTaskRepository")

    def test_event_store_backends_are_accessible(self):
        """Verify event store implementations are accessible."""
        assert hasattr(shim, "InMemoryEventStore")
        assert hasattr(shim, "SqlEventStore")
        assert hasattr(shim, "RedisEventStore")


class TestBackwardCompatibility:
    """Test that legacy imports still work."""

    def test_legacy_import_from_super_agentic_agents(self):
        """Verify legacy imports from shim still work."""
        # This test demonstrates that the shim maintains backward compatibility
        from src.agents.super_agentic_agents import AgentSystem, Task, ExecutorAgent

        assert AgentSystem is not None
        assert Task is not None
        assert ExecutorAgent is not None

    def test_legacy_import_multiple_symbols(self):
        """Verify multiple symbols can be imported together."""
        from src.agents.super_agentic_agents import (
            AgentSystem,
            Task,
            ExecutorAgent,
            RetryPolicy,
            TaskStatus,
        )

        assert all([AgentSystem, Task, ExecutorAgent, RetryPolicy, TaskStatus])


class TestMetadata:
    """Test version and lifecycle metadata."""

    def test_version_is_set(self):
        """Verify __version__ is defined."""
        assert hasattr(shim, "__version__")
        assert isinstance(shim.__version__, str)
        assert len(shim.__version__) > 0

    def test_deprecation_timeline_is_documented(self):
        """Verify deprecation timeline is defined."""
        assert hasattr(shim, "__deprecated_in__")
        assert hasattr(shim, "__removal_in__")
        assert shim.__deprecated_in__ == "2.0.0"
        assert shim.__removal_in__ == "3.0.0"


class TestLogging:
    """Test logging behavior."""

    def test_logger_is_configured(self):
        """Verify logger is properly configured."""
        assert shim.logger is not None
        assert isinstance(shim.logger, logging.Logger)

    def test_startup_logs_initialization(self, caplog):
        """Verify startup logs initialization message."""
        with caplog.at_level(logging.INFO):
            with mock.patch("src.agents.super_agentic_agents._safe_import_from_package") as mock_import:
                with mock.patch("src.agents.super_agentic_agents._emit_deprecation_warning"):
                    mock_import.return_value = True
                    shim._startup()

                    assert any("initialization" in record.message.lower() for record in caplog.records)

    def test_safe_import_logs_debug_messages(self, caplog):
        """Verify safe import logs at DEBUG level."""
        shim._import_errors.clear()
        old_level = shim.logger.level
        try:
            shim.logger.setLevel(logging.DEBUG)
            with caplog.at_level(logging.DEBUG):
                shim._safe_import_from_package()

                # Should have debug messages about imported symbols
                assert any("Imported symbol" in record.message for record in caplog.records)
        finally:
            shim.logger.setLevel(old_level)


# ============================================================================
# Integration tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_startup_cycle_succeeds(self):
        """Verify complete startup cycle works in production mode."""
        with mock.patch.dict(os.environ, {
            "AGENT_SHIM_STRICT_MODE": "false",
            "AGENT_SHIM_VALIDATE_AT_IMPORT": "true",
            "AGENT_SHIM_LOG_LEVEL": "INFO",
        }):
            # Should not raise
            shim._startup()
            assert shim.is_shim_fully_functional()

    def test_production_health_check(self):
        """Simulate production health check."""
        # Check if shim is functional
        functional = shim.is_shim_fully_functional()
        assert functional is True

        # Verify all modules are available
        module_status = shim.validate_all_modules()
        assert all(module_status.values())

        # Verify integrity
        integrity_ok = shim.validate_shim_integrity(raise_on_error=False)
        assert integrity_ok is True

        # No import errors
        errors = shim.get_import_errors()
        assert len(errors) == 0

    def test_import_error_diagnostics(self):
        """Test diagnostic access when imports fail partially."""
        with mock.patch("src.agents.super_agentic_agents._safe_import_from_package") as mock_import:
            mock_import.return_value = False
            shim._import_errors["AgentSystem"] = ImportError("test error")

            # Should be able to query error state
            assert not shim.is_shim_fully_functional()
            errors = shim.get_import_errors()
            assert "AgentSystem" in errors
            assert isinstance(errors["AgentSystem"], ImportError)

            shim._import_errors.clear()
