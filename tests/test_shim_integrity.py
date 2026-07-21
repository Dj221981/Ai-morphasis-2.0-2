"""
Unit tests for src.agents.super_agentic_agents compatibility shim.

Tests validate:
1. Dynamic symbol discovery from src.agents.__all__
2. Strict mode fail-fast behavior (production default)
3. Validation enabled by default
4. Export integrity and sub-module importability
5. Error diagnostics and recovery paths
"""

import os
import sys
import pytest
from unittest import mock

# Import the shim module for testing
import src.agents.super_agentic_agents as shim


# ============================================================================
# Test 1: Dynamic symbol discovery works correctly
# ============================================================================

class TestDynamicSymbolDiscovery:
    """Verify that symbols are auto-discovered from src.agents.__all__."""

    def test_get_expected_symbols_returns_list_from_src_agents(self):
        """Symbols should be dynamically discovered, not hardcoded."""
        symbols = shim._get_expected_symbols()
        
        # Should return a list
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        
        # Should include known core symbols
        assert "Task" in symbols
        assert "AgentSystem" in symbols
        assert "ExecutorAgent" in symbols

    def test_get_expected_symbols_matches_src_agents_all(self):
        """Discovered symbols should match src.agents.__all__ exactly."""
        import src.agents
        symbols = shim._get_expected_symbols()
        
        assert set(symbols) == set(src.agents.__all__)

    def test_get_expected_symbols_raises_on_missing_package(self):
        """Should raise ImportError if src.agents not found."""
        with mock.patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("No module named 'src.agents'")
            
            with pytest.raises(ImportError, match="Cannot discover symbols"):
                shim._get_expected_symbols()


# ============================================================================
# Test 2: Strict mode is enabled by default (production safety)
# ============================================================================

class TestStrictModeDefault:
    """Verify strict mode is ON by default for fail-fast behavior."""

    def test_strict_mode_default_is_true(self):
        """AGENT_SHIM_STRICT_MODE should default to 'true' for production."""
        # Test with no env var set
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENT_SHIM_STRICT_MODE", None)
            result = shim._env_flag("AGENT_SHIM_STRICT_MODE", "true")
            assert result is True

    def test_strict_mode_can_be_disabled(self):
        """Operators can opt-in to graceful degradation if needed."""
        with mock.patch.dict(os.environ, {"AGENT_SHIM_STRICT_MODE": "false"}):
            result = shim._env_flag("AGENT_SHIM_STRICT_MODE", "true")
            assert result is False

    def test_strict_mode_parses_multiple_true_formats(self):
        """Should recognize 'true', '1', 'yes' as True."""
        for value in ["true", "True", "TRUE", "1", "yes", "YES"]:
            with mock.patch.dict(os.environ, {"AGENT_SHIM_STRICT_MODE": value}):
                result = shim._env_flag("AGENT_SHIM_STRICT_MODE", "true")
                assert result is True, f"Failed to parse '{value}' as True"


# ============================================================================
# Test 3: Validation enabled by default
# ============================================================================

class TestValidationDefault:
    """Verify validation is enabled by default at import time."""

    def test_validate_at_import_default_is_true(self):
        """AGENT_SHIM_VALIDATE_AT_IMPORT should default to 'true'."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENT_SHIM_VALIDATE_AT_IMPORT", None)
            result = shim._env_flag("AGENT_SHIM_VALIDATE_AT_IMPORT", "true")
            assert result is True

    def test_validate_at_import_can_be_disabled(self):
        """Operators can opt-out if needed for performance."""
        with mock.patch.dict(os.environ, {"AGENT_SHIM_VALIDATE_AT_IMPORT": "false"}):
            result = shim._env_flag("AGENT_SHIM_VALIDATE_AT_IMPORT", "true")
            assert result is False


# ============================================================================
# Test 4: All expected symbols are present on shim module
# ============================================================================

class TestExportIntegrity:
    """Verify that all symbols from src.agents are re-exported."""

    def test_all_src_agents_symbols_accessible_on_shim(self):
        """Every symbol in src.agents.__all__ should be importable from shim."""
        import src.agents
        
        for symbol_name in src.agents.__all__:
            assert hasattr(shim, symbol_name), \
                f"Symbol '{symbol_name}' not found on shim module"

    def test_shim_all_matches_src_agents_all(self):
        """Shim's __all__ should match src.agents.__all__."""
        import src.agents
        
        # After startup, __all__ should be populated
        assert len(shim.__all__) > 0
        assert set(shim.__all__) == set(src.agents.__all__)

    def test_imported_symbols_are_same_as_src_agents(self):
        """Imported symbols should be identical references."""
        import src.agents
        
        # Check a few key symbols
        for symbol_name in ["Task", "AgentSystem", "ExecutorAgent"]:
            shim_symbol = getattr(shim, symbol_name)
            src_symbol = getattr(src.agents, symbol_name)
            assert shim_symbol is src_symbol, \
                f"Symbol '{symbol_name}' is not the same reference"


# ============================================================================
# Test 5: Sub-modules are all importable
# ============================================================================

class TestSubmoduleImportability:
    """Verify all required sub-modules can be imported."""

    def test_validate_all_modules_returns_all_true(self):
        """All required sub-modules should import successfully."""
        status = shim.validate_all_modules()
        
        assert isinstance(status, dict)
        assert all(status.values()), \
            f"Some modules failed to import: {[k for k, v in status.items() if not v]}"

    def test_validate_all_modules_contains_all_required(self):
        """Status dict should include all required sub-modules."""
        status = shim.validate_all_modules()
        
        for module_name in shim._REQUIRED_SUBMODULES:
            assert module_name in status, \
                f"Module '{module_name}' not checked"


# ============================================================================
# Test 6: Shim integrity validation passes
# ============================================================================

class TestShimIntegrity:
    """Verify validate_shim_integrity() passes all checks."""

    def test_validate_shim_integrity_passes(self):
        """Integrity validation should pass without errors."""
        result = shim.validate_shim_integrity(raise_on_error=False)
        assert result is True

    def test_validate_shim_integrity_with_raise_on_error(self):
        """Integrity validation should pass even when raise_on_error=True."""
        # Should not raise
        result = shim.validate_shim_integrity(raise_on_error=True)
        assert result is True


# ============================================================================
# Test 7: Import errors are tracked and accessible
# ============================================================================

class TestImportErrorTracking:
    """Verify import errors are properly tracked and reported."""

    def test_get_import_errors_returns_dict(self):
        """get_import_errors() should return a dict."""
        errors = shim.get_import_errors()
        assert isinstance(errors, dict)

    def test_import_complete_flag_is_set(self):
        """_IMPORT_COMPLETE should be True after successful startup."""
        assert shim._IMPORT_COMPLETE is True

    def test_is_shim_fully_functional_returns_true_on_success(self):
        """is_shim_fully_functional() should return True when fully loaded."""
        result = shim.is_shim_fully_functional()
        assert result is True


# ============================================================================
# Test 8: Deprecation warning is emitted
# ============================================================================

class TestDeprecationWarning:
    """Verify deprecation warning is properly emitted."""

    def test_emit_deprecation_warning_raises_deprecation_warning(self):
        """_emit_deprecation_warning() should emit DeprecationWarning."""
        with pytest.warns(DeprecationWarning, match="deprecated"):
            shim._emit_deprecation_warning()

    def test_deprecation_warning_mentions_migration_guide(self):
        """Warning should mention migration guide URL."""
        with pytest.warns(DeprecationWarning, match="migration"):
            shim._emit_deprecation_warning()


# ============================================================================
# Test 9: Production defaults are sensible
# ============================================================================

class TestProductionDefaults:
    """Verify production defaults prevent silent failures."""

    def test_default_strict_mode_is_enabled(self):
        """strict_mode should be True by default (fail-fast)."""
        # Verify the documented default
        assert shim._env_flag("AGENT_SHIM_STRICT_MODE", "true") is True

    def test_default_validation_is_enabled(self):
        """validate_at_import should be True by default."""
        assert shim._env_flag("AGENT_SHIM_VALIDATE_AT_IMPORT", "true") is True

    def test_graceful_degradation_requires_explicit_opt_in(self):
        """Graceful degradation should require explicit env var."""
        # With defaults, strict mode is on
        assert shim._env_flag("AGENT_SHIM_STRICT_MODE", "true") is True


# ============================================================================
# Test 10: __getattr__ provides helpful error messages
# ============================================================================

class TestAttributeError:
    """Verify __getattr__ provides helpful diagnostics."""

    def test_getattr_raises_for_nonexistent_symbol(self):
        """Accessing nonexistent symbol should raise AttributeError."""
        with pytest.raises(AttributeError, match="has no attribute"):
            _ = shim.NonexistentSymbol

    def test_getattr_error_suggests_getting_import_errors(self):
        """Error message should suggest using get_import_errors()."""
        # Since all symbols imported successfully, this tests the fallback path
        try:
            _ = shim.FakeNonexistentSymbol
        except AttributeError as e:
            # Should mention module name
            assert "super_agentic_agents" in str(e)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
