"""Bounded optimizer scaffold; no code application, deployment, or training."""

from dataclasses import dataclass
from math import isfinite
from time import monotonic
from typing import Callable, Generic, Literal, TypeVar


T = TypeVar("T")
StopReason = Literal[
    "max_iterations", "max_evaluations", "stagnation", "deadline",
    "baseline_failed",
]


@dataclass(frozen=True)
class Candidate(Generic[T]):
    value: T


@dataclass(frozen=True)
class Evaluation:
    score: float
    quality: float = 0.0
    valid: bool = True


@dataclass(frozen=True)
class RunResult(Generic[T]):
    best_candidate: Candidate[T]
    baseline_score: float | None
    best_score: float | None
    iterations: int
    evaluations: int
    accepted_count: int
    rejected_count: int
    stop_reason: StopReason


def optimize(
    baseline: Candidate[T],
    proposer: Callable[[Candidate[T], int], Candidate[T]],
    evaluator: Callable[[Candidate[T]], Evaluation],
    *,
    max_iterations: int = 10,
    max_evaluations: int = 11,
    stagnation_limit: int = 3,
    min_improvement: float = 0.0,
    time_limit_seconds: float | None = None,
    fail_fast: bool = False,
) -> RunResult[T]:
    """Maximize score sequentially, retaining only valid, strict improvements.

    Quality must never decrease relative to the incumbent. The baseline uses
    one evaluation; proposal indices start at zero. Rejections (including
    evaluator exceptions and non-finite score/quality) count toward stagnation,
    which resets on acceptance. An unusable baseline stops the run with no
    scores. ``fail_fast`` propagates evaluation errors instead.

    The optional elapsed wall-clock limit uses a monotonic clock and is checked
    before callbacks. It cannot interrupt callbacks: callers must bound their
    execution time. Proposer exceptions propagate. Callbacks must not mutate
    candidates or apply external changes; frozen wrappers do not freeze payloads.
    Without a time limit, deterministic callbacks yield deterministic results.
    """
    for name, value, minimum in (
        ("max_iterations", max_iterations, 0),
        ("max_evaluations", max_evaluations, 1),
        ("stagnation_limit", stagnation_limit, 1),
    ):
        if type(value) is not int or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}")
    for name, value in (
        ("min_improvement", min_improvement),
        ("time_limit_seconds", time_limit_seconds),
    ):
        if value is None and name == "time_limit_seconds":
            continue
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not isfinite(value) or value < 0):
            raise ValueError(f"{name} must be finite and non-negative")
    if not isinstance(fail_fast, bool):
        raise ValueError("fail_fast must be a bool")

    started = monotonic() if time_limit_seconds is not None else None
    best = baseline
    baseline_score = best_score = None
    iterations = evaluations = accepted = rejected = stagnant = 0

    def expired() -> bool:
        return (started is not None
                and monotonic() - started >= time_limit_seconds)

    def result(reason: StopReason) -> RunResult[T]:
        return RunResult(
            best, baseline_score, best_score, iterations, evaluations,
            accepted, rejected, reason,
        )

    def evaluate(candidate: Candidate[T]) -> Evaluation | None:
        nonlocal evaluations
        evaluations += 1
        try:
            evaluation = evaluator(candidate)
            if not (isfinite(evaluation.score) and isfinite(evaluation.quality)):
                raise ValueError("score and quality must be finite")
            return evaluation if evaluation.valid else None
        except Exception:
            if fail_fast:
                raise
            return None

    if expired():
        return result("deadline")
    incumbent = evaluate(baseline)
    if incumbent is None:
        return result("baseline_failed")
    baseline_score = best_score = incumbent.score

    for index in range(max_iterations):
        if expired():
            return result("deadline")
        if evaluations >= max_evaluations:
            return result("max_evaluations")
        if stagnant >= stagnation_limit:
            return result("stagnation")
        candidate = proposer(best, index)
        iterations += 1
        if expired():
            return result("deadline")
        evaluation = evaluate(candidate)
        if (evaluation is not None
                and evaluation.score > incumbent.score
                and evaluation.score - incumbent.score >= min_improvement
                and evaluation.quality >= incumbent.quality):
            best = candidate
            incumbent = evaluation
            best_score = evaluation.score
            accepted += 1
            stagnant = 0
        else:
            rejected += 1
            stagnant += 1
    return result("max_iterations")
