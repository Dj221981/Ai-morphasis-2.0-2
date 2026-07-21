"""
src/agents/super_agentic_agents.py
===================================
Backward-compatibility shim for the modular ``src.agents`` package.

MIGRATION TIMELINE (Important for users):
------------------------------------------
This shim will be deprecated in **v2.0.0** (expected Q4 2024).

Timeline:
- **Now - v1.9.x**: Shim maintained, no functional changes.
- **v2.0.0**: DeprecationWarning emitted on import. Shim still functional.
- **v3.0.0+**: Shim removal considered only after 2+ full minor releases.

For migration guidance, see:
  https://github.com/Dj221981/Ai-morphasis-2.0-2/docs/migration.md

USAGE
-----
This module has been refactored into a modular package under ``src/agents/``.
All public symbols are re-exported from here so that existing imports continue
to work without modification::

    # Legacy (still works, not recommended for new code):
    from src.agents.super_agentic_agents import AgentSystem, Task, ExecutorAgent

For new code, prefer importing from the package directly::

    from src.agents import AgentSystem, Task, ExecutorAgent
    from src.agents.models import RetryPolicy, ExecutionPolicy
    from src.agents.runtime import run_once, run_forever
    from src.agents.persistence import InMemoryTaskRepository
    from src.agents.events import InMemoryEventStore, TaskEvent

PRODUCTION DEPLOYMENT NOTES
----------------------------
By default, startup validation is DISABLED to reduce import-time side effects
in production while still allowing graceful degradation. Use these environment
variables to control behavior:

- AGENT_SHIM_STRICT_MODE=true         → Hard-fail on any import error
- AGENT_SHIM_VALIDATE_AT_IMPORT=false → Skip integrity validation on startup
- AGENT_SHIM_LOG_LEVEL=DEBUG          → Enable detailed import diagnostics

Example production settings::

    export AGENT_SHIM_STRICT_MODE=false        # Graceful degradation
    export AGENT_SHIM_VALIDATE_AT_IMPORT=true  # Opt-in startup validation
    export AGENT_SHIM_LOG_LEVEL=INFO           # Standard logging

SECURITY REVIEW
---------------
- This compatibility shim contains no direct input handling, I/O, subprocess,
  network, filesystem, authentication, authorization, or secret-management
  logic.
- Its security posture depends on the safety of the modules re-exported from
  ``src.agents``.
- Keep exports limited to intended public APIs to avoid unintentionally exposing
  internal or privileged functionality.
- Avoid re-exporting experimental, admin-only, or environment-specific helpers
  through this compatibility layer.
- When adding new exports, review whether they enable task execution, code
  execution, persistence access, or event access that should remain internal.
"""

import os
import sys
import logging
import importlib
import warnings
from typing import Dict

# ============================================================================
# Configuration: control shim behavior via environment variables
# ============================================================================

def _env_flag(name: str, default: str = "false") -> bool:
    """Parse an environment boolean flag."""
    return os.getenv(name, default).lower() in ("true", "1", "yes")


_STRICT_MODE = _env_flag("AGENT_SHIM_STRICT_MODE", "false")
_VALIDATE_AT_IMPORT = _env_flag("AGENT_SHIM_VALIDATE_AT_IMPORT", "false")
_LOG_LEVEL = os.getenv("AGENT_SHIM_LOG_LEVEL", "INFO").upper()

# ============================================================================
# Logging setup
# ============================================================================

logger = logging.getLogger(__name__)
try:
    _log_level = getattr(logging, _LOG_LEVEL, logging.INFO)
    logger.setLevel(_log_level)
except (ValueError, AttributeError):
    logger.setLevel(logging.INFO)

# ============================================================================
# Runtime metadata
# ============================================================================

__version__ = "1.0.0"
__deprecated_in__ = "2.0.0"
__removal_in__ = "3.0.0"


def _emit_deprecation_warning() -> None:
    """Emit a deprecation warning with migration guidance."""
    warnings.warn(
        (
            "src.agents.super_agentic_agents is deprecated and will be removed in v3.0.0. "
            "Please migrate to direct imports from src.agents or its submodules. "
            "Migration guide: https://github.com/Dj221981/Ai-morphasis-2.0-2/docs/migration.md"
        ),
        DeprecationWarning,
        stacklevel=3,
    )


# ============================================================================
# Import guard: safe re-export block with graceful fallback
# ============================================================================

_import_errors: Dict[str, Exception] = {}
_IMPORT_COMPLETE = False
_EXPECTED_SYMBOLS = (
    "AgentRole",
    "AgentStatus",
    "TaskPriority",
    "TaskStatus",
    "TASK_STATUS_TRANSITIONS",
    "TaskCancelledError",
    "RetryPolicy",
    "ExecutionPolicy",
    "AgentCapability",
    "AgentMemory",
    "Task",
    "CAPABILITY_MATCH_BASE_SCORE",
    "DEFAULT_AGENT_BASE_SCORE",
    "BaseAgent",
    "OrchestratorAgent",
    "ExecutorAgent",
    "AnalyzerAgent",
    "LearnerAgent",
    "AgentSystem",
    "AgentFactory",
    "TaskRepository",
    "InMemoryTaskRepository",
    "SqlTaskRepository",
    "RedisTaskRepository",
    "TaskEventType",
    "TaskEvent",
    "InMemoryEventStore",
    "SqlEventStore",
    "RedisEventStore",
    "dispatch_pending_tasks",
    "process_retry_queue",
    "run_once",
    "run_forever",
)


def _safe_import_from_package() -> bool:
    """Attempt to import all public symbols from ``src.agents``.

    Returns True if successful, False if any symbol fails to import.
    Populates _import_errors dict with failed imports for diagnostic purposes.
    """
    global _import_errors, _IMPORT_COMPLETE
    _import_errors = {}

    try:
        # Attempt to import the main package first
        pkg = importlib.import_module("src.agents")
        logger.info("src.agents package imported successfully")
        imported = {}

        # Try to get each symbol
        for symbol_name in _EXPECTED_SYMBOLS:
            try:
                imported[symbol_name] = getattr(pkg, symbol_name)
                logger.debug(f"Imported symbol: {symbol_name}")
            except AttributeError as exc:
                _import_errors[symbol_name] = exc
                logger.warning(f"Symbol '{symbol_name}' not found in src.agents: {exc}")

        if _import_errors:
            atomic_failure = ImportError(
                "Not exported because compatibility shim import failed atomically."
            )
            for symbol_name in _EXPECTED_SYMBOLS:
                _import_errors.setdefault(symbol_name, atomic_failure)
            logger.warning(
                f"Failed to import {len(_import_errors)} symbols: {list(_import_errors.keys())}"
            )
            return False

        globals().update(imported)
        _IMPORT_COMPLETE = True
        logger.info("All expected symbols imported successfully from src.agents")
        return True

    except ImportError as exc:
        logger.error(f"Failed to import src.agents package: {exc}", exc_info=True)
        _import_errors["__package__"] = exc
        return False
    except Exception as exc:
        logger.error(f"Unexpected error during import from src.agents: {exc}", exc_info=True)
        _import_errors["__unexpected__"] = exc
        return False


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "AgentRole",
    "AgentStatus",
    "TaskPriority",
    "TaskStatus",
    "TASK_STATUS_TRANSITIONS",
    "TaskCancelledError",
    "RetryPolicy",
    "ExecutionPolicy",
    "AgentCapability",
    "AgentMemory",
    "Task",
    "CAPABILITY_MATCH_BASE_SCORE",
    "DEFAULT_AGENT_BASE_SCORE",
    "BaseAgent",
    "OrchestratorAgent",
    "ExecutorAgent",
    "AnalyzerAgent",
    "LearnerAgent",
    "AgentSystem",
    "AgentFactory",
    "TaskRepository",
    "InMemoryTaskRepository",
    "SqlTaskRepository",
    "RedisTaskRepository",
    "TaskEventType",
    "TaskEvent",
    "InMemoryEventStore",
    "SqlEventStore",
    "RedisEventStore",
    "dispatch_pending_tasks",
    "process_retry_queue",
    "run_once",
    "run_forever",
]


# ============================================================================
# Module validation helpers (for health checks, startup probes, tests)
# ============================================================================

_REQUIRED_SUBMODULES = (
    "src.agents.models",
    "src.agents.base",
    "src.agents.specialized",
    "src.agents.system",
    "src.agents.persistence",
    "src.agents.events",
    "src.agents.runtime",
)


def validate_all_modules() -> Dict[str, bool]:
    """Check that every required sub-module can be imported.

    Returns a dict mapping module name to import success (bool).
    Does not raise; returns status instead for graceful degradation.

    Intended for use in health-checks, startup probes, and test suites.

    Example::

        status = validate_all_modules()
        all_ok = all(status.values())
        if not all_ok:
            failed = [k for k, v in status.items() if not v]
            print(f"Failed modules: {failed}")

    Returns
    -------
    dict[str, bool]
        Mapping of module name to success status.
    """
    result = {}
    for module_name in _REQUIRED_SUBMODULES:
        try:
            importlib.import_module(module_name)
            result[module_name] = True
            logger.debug(f"Sub-module {module_name} imported successfully")
        except ImportError as exc:
            result[module_name] = False
            logger.warning(f"Sub-module {module_name} failed to import: {exc}")
    return result


def validate_shim_integrity(raise_on_error: bool = False) -> bool:
    """Verify that ``__all__`` exports match actual module state.

    Validates that:
    1. Every name in ``__all__`` is present on this module
    2. Every name in ``__all__`` is present on ``src.agents``
    3. Every required sub-module is importable

    Parameters
    ----------
    raise_on_error : bool
        If True, raise AssertionError/ImportError on any validation failure.
        If False, log warnings and return False.

    Returns
    -------
    bool
        True if validation passes, False otherwise.

    Raises
    ------
    AssertionError
        If raise_on_error=True and symbols are missing.
    ImportError
        If raise_on_error=True and sub-modules cannot be imported.
    """
    this_module = sys.modules[__name__]

    # Check symbols on shim module
    missing_from_shim = [name for name in __all__ if not hasattr(this_module, name)]
    if missing_from_shim:
        msg = (
            f"super_agentic_agents.__all__ lists {len(missing_from_shim)} symbols "
            f"not present on shim module: {missing_from_shim}"
        )
        logger.error(msg)
        if raise_on_error:
            raise AssertionError(msg)
        return False

    # Check symbols on src.agents package
    try:
        pkg = importlib.import_module("src.agents")
        missing_from_pkg = [name for name in __all__ if not hasattr(pkg, name)]
        if missing_from_pkg:
            msg = (
                f"super_agentic_agents.__all__ lists {len(missing_from_pkg)} symbols "
                f"not present on src.agents: {missing_from_pkg}"
            )
            logger.error(msg)
            if raise_on_error:
                raise AssertionError(msg)
            return False
    except ImportError as exc:
        msg = f"Could not import src.agents to validate exports: {exc}"
        logger.error(msg)
        if raise_on_error:
            raise
        return False

    # Check sub-modules
    module_status = validate_all_modules()
    if not all(module_status.values()):
        failed = [k for k, v in module_status.items() if not v]
        msg = f"Sub-modules failed to import: {failed}"
        logger.warning(msg)
        if raise_on_error:
            raise ImportError(msg)
        return False

    logger.info("Shim integrity validation passed")
    return True


def get_import_errors() -> Dict[str, Exception]:
    """Return a dict of symbols that failed to import.

    Returns
    -------
    dict[str, Exception]
        Mapping of symbol name to Exception that occurred during import.
        Empty dict if all imports succeeded.

    Example::

        errors = get_import_errors()
        if errors:
            for symbol, exc in errors.items():
                print(f"Failed to import {symbol}: {exc}")
    """
    return dict(_import_errors)


def is_shim_fully_functional() -> bool:
    """Quick check: are all exported symbols available?

    Returns
    -------
    bool
        True if no import errors are present, False otherwise.
    """
    return len(_import_errors) == 0


# ============================================================================
# Startup sequence
# ============================================================================

def _startup() -> None:
    """Perform startup initialization when shim is first imported.

    Attempts safe import, validates on demand, handles fallback gracefully.
    Behavior controlled by environment variables:
    - AGENT_SHIM_STRICT_MODE: hard-fail vs. graceful degradation
    - AGENT_SHIM_VALIDATE_AT_IMPORT: opt-in startup validation in non-strict mode
    - AGENT_SHIM_LOG_LEVEL: set logging verbosity

    Note: strict mode always performs integrity validation.
    """
    # Re-read env flags each startup call so tests and runtime reload scenarios
    # can opt into strict/validation behavior without requiring module reload.
    strict_mode = _env_flag("AGENT_SHIM_STRICT_MODE", "false")
    validate_at_import = _env_flag("AGENT_SHIM_VALIDATE_AT_IMPORT", "false")

    logger.info(
        f"Initializing src.agents.super_agentic_agents "
        f"(version={__version__}, strict_mode={strict_mode})"
    )

    # Step 1: Try safe import
    success = _safe_import_from_package()

    if not success:
        logger.error("Failed to import one or more symbols from src.agents")

        if strict_mode:
            # Hard fail in strict mode
            errors_summary = "; ".join(
                f"{name}: {exc}"
                for name, exc in _import_errors.items()
            )
            raise ImportError(
                f"super_agentic_agents (strict mode): failed to import from src.agents. "
                f"Errors: {errors_summary}"
            )
        else:
            # Graceful degradation in production mode
            logger.warning(
                "Graceful degradation: shim partially loaded. "
                "Use AGENT_SHIM_STRICT_MODE=true to fail fast instead."
            )

    # Step 2: Optionally validate integrity at import
    if strict_mode or validate_at_import:
        try:
            validate_shim_integrity(raise_on_error=strict_mode)
        except (AssertionError, ImportError) as exc:
            if strict_mode:
                raise
            logger.warning(f"Integrity validation failed: {exc}")

    # Step 3: Emit deprecation warning
    _emit_deprecation_warning()

    logger.info("super_agentic_agents initialization complete")


# Run startup once when module is imported
_startup()


def __getattr__(name: str):
    """Provide clearer diagnostics for missing shim exports."""
    if name in _import_errors and not _IMPORT_COMPLETE:
        failed = ", ".join(sorted(_import_errors.keys()))
        raise AttributeError(
            f"Shim export '{name}' is unavailable because compatibility import did not fully "
            f"initialize. Missing/failed symbols: {failed}. "
            f"Use get_import_errors() for details or set AGENT_SHIM_STRICT_MODE=true."
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
