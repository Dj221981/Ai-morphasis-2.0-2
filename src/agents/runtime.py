"""
src/agents/runtime.py
=====================
Scheduler and runtime helpers for the super-agentic framework.

Provides standalone functions that wrap AgentSystem scheduling in a
convenient interface, and a ``run_forever`` loop for continuous operation.

These helpers are intentionally thin; they delegate to AgentSystem methods
so that the core orchestration logic remains testable in isolation.
"""

import logging
import threading
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


def dispatch_pending_tasks(system) -> int:
    """Dispatch all ready pending/retrying tasks from ``system``.

    Convenience wrapper around ``AgentSystem.dispatch_pending_tasks()``.

    Parameters
    ----------
    system:
        An ``AgentSystem`` instance.

    Returns
    -------
    int
        Number of tasks successfully dispatched.
    """
    return system.dispatch_pending_tasks()


def process_retry_queue(system) -> int:
    """Resubmit due retrying tasks from ``system``.

    Convenience wrapper around ``AgentSystem.process_retry_queue()``.

    Parameters
    ----------
    system:
        An ``AgentSystem`` instance.

    Returns
    -------
    int
        Number of tasks resubmitted.
    """
    return system.process_retry_queue()


def run_once(system) -> Dict[str, int]:
    """Perform one scheduling cycle on ``system``.

    Dispatches pending tasks and resubmits due retries in a single call.

    Parameters
    ----------
    system:
        An ``AgentSystem`` instance.

    Returns
    -------
    dict
        ``{"dispatched": int, "retried": int}``
    """
    return system.run_once()


def run_forever(
    system,
    interval_seconds: float = 1.0,
    stop_event: Optional[threading.Event] = None,
    on_cycle: Optional[Callable[[Dict[str, int]], None]] = None,
) -> None:
    """Run the scheduling loop continuously until ``stop_event`` is set.

    Each iteration calls ``run_once()`` and then sleeps for
    ``interval_seconds``.  The loop exits cleanly when ``stop_event`` is
    set or when a ``KeyboardInterrupt`` is received.

    Parameters
    ----------
    system:
        An ``AgentSystem`` instance.
    interval_seconds:
        Seconds to wait between scheduling cycles. Default is 1.0.
    stop_event:
        An optional ``threading.Event``.  When set, the loop exits after the
        current cycle completes.  If not provided, the loop runs until
        interrupted.
    on_cycle:
        Optional callback invoked after each cycle with the cycle summary
        dict ``{"dispatched": int, "retried": int}``.
    """
    if interval_seconds < 0:
        raise ValueError("interval_seconds must be non-negative")

    if stop_event is None:
        stop_event = threading.Event()

    logger.info(
        "run_forever: starting scheduler loop for system=%s interval=%.2fs",
        system.name,
        interval_seconds,
    )
    try:
        while not stop_event.is_set():
            summary = run_once(system)
            if on_cycle is not None:
                try:
                    on_cycle(summary)
                except Exception:
                    logger.exception("run_forever: on_cycle callback raised an exception")
            stop_event.wait(timeout=interval_seconds)
    except KeyboardInterrupt:
        logger.info("run_forever: interrupted by KeyboardInterrupt")
    finally:
        logger.info("run_forever: scheduler loop stopped for system=%s", system.name)
