"""Bounded, proposal-only evaluation of application strategy candidates."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
import math
from numbers import Real
from threading import Lock
from time import monotonic
from types import MappingProxyType
from typing import Callable, Iterable, Mapping, Optional, Tuple, Union


CandidateScalar = Union[str, int, float, bool]
CandidateIdentity = Tuple[str, Tuple[Tuple[str, str, CandidateScalar], ...]]


def _validated_scalar_mapping(
    values: Mapping[str, CandidateScalar], label: str
) -> Mapping[str, CandidateScalar]:
    if not isinstance(values, Mapping):
        raise ValueError(f"{label} must be a mapping")
    copied = {}
    for key, value in values.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{label} keys must be non-empty strings")
        if type(value) not in (str, int, float, bool):
            raise ValueError(f"{label} values must be scalar strings, numbers, or booleans")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{label} values must be finite")
        copied[key] = value
    return MappingProxyType(copied)


@dataclass(frozen=True)
class Candidate:
    """Immutable application-level strategy configuration proposed for evaluation."""

    name: str
    parameters: Mapping[str, CandidateScalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("candidate name must be a non-empty string")
        object.__setattr__(
            self, "parameters", _validated_scalar_mapping(self.parameters, "candidate parameters")
        )

    @property
    def identity(self) -> CandidateIdentity:
        """Return a stable identity including parameter names and scalar types."""
        return (
            self.name,
            tuple(
                (key, type(value).__name__, value)
                for key, value in sorted(self.parameters.items())
            ),
        )


@dataclass(frozen=True)
class Evaluation:
    """Quality and correctness from the fixed evaluator; timing is measured separately."""

    quality_score: float
    correct: bool
    metrics: Mapping[str, CandidateScalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.quality_score, bool) or not isinstance(self.quality_score, Real):
            raise ValueError("quality_score must be a finite number in [0, 1]")
        if not math.isfinite(self.quality_score) or not 0 <= self.quality_score <= 1:
            raise ValueError("quality_score must be a finite number in [0, 1]")
        if type(self.correct) is not bool:
            raise ValueError("correct must be a boolean")
        object.__setattr__(self, "metrics", _validated_scalar_mapping(self.metrics, "metrics"))


@dataclass(frozen=True)
class MeasuredEvaluation:
    """An evaluator result paired with controller-measured elapsed seconds."""

    evaluation: Evaluation
    elapsed_seconds: float


@dataclass(frozen=True)
class CandidateOutcome:
    candidate: Candidate
    measured: Optional[MeasuredEvaluation]
    accepted: bool
    reason: str


class TerminationReason(str, Enum):
    TIME_BUDGET = "time_budget"
    EVALUATION_BUDGET = "evaluation_budget"
    ITERATION_BUDGET = "iteration_budget"
    STAGNATION = "stagnation"
    NO_CANDIDATES = "no_candidates"
    PROPOSAL_FAILURE = "proposal_failure"


@dataclass(frozen=True)
class ResourceCounts:
    iterations: int = 0
    proposals: int = 0
    evaluations: int = 0
    evaluator_failures: int = 0
    proposal_failures: int = 0
    peak_parallelism: int = 1


@dataclass(frozen=True)
class ImprovementResult:
    baseline_candidate: Candidate
    baseline: MeasuredEvaluation
    outcomes: Tuple[CandidateOutcome, ...]
    best_candidate: Candidate
    best_evaluation: MeasuredEvaluation
    termination_reason: TerminationReason
    resources: ResourceCounts
    proposal_only: bool = True
    approval_required: bool = True


@dataclass(frozen=True)
class ImprovementConfig:
    """Hard bounds and acceptance rules for one improvement run."""

    max_iterations: int = 5
    max_evaluations: int = 20
    max_seconds: float = 30.0
    stagnation_limit: int = 2
    max_workers: int = 1
    quality_floor: float = 1.0
    min_speedup: float = 0.01

    def __post_init__(self) -> None:
        integer_fields = (
            ("max_iterations", self.max_iterations, 0),
            ("max_evaluations", self.max_evaluations, 1),
            ("stagnation_limit", self.stagnation_limit, 1),
            ("max_workers", self.max_workers, 1),
        )
        for name, value, minimum in integer_fields:
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        if (
            isinstance(self.max_seconds, bool)
            or not isinstance(self.max_seconds, Real)
            or not math.isfinite(self.max_seconds)
            or self.max_seconds <= 0
        ):
            raise ValueError("max_seconds must be finite and positive")
        if (
            isinstance(self.quality_floor, bool)
            or not isinstance(self.quality_floor, Real)
            or not math.isfinite(self.quality_floor)
            or not 0 <= self.quality_floor <= 1
        ):
            raise ValueError("quality_floor must be finite and in [0, 1]")
        if (
            isinstance(self.min_speedup, bool)
            or not isinstance(self.min_speedup, Real)
            or not math.isfinite(self.min_speedup)
            or not 0 <= self.min_speedup < 1
        ):
            raise ValueError("min_speedup must be finite and in [0, 1)")


Evaluator = Callable[[Candidate], Evaluation]
Proposer = Callable[[Candidate, int], Iterable[Candidate]]
Clock = Callable[[], float]


class ImprovementController:
    """Compare bounded proposals against a fixed evaluator without applying changes."""

    def __init__(
        self,
        evaluator: Evaluator,
        proposer: Proposer,
        config: ImprovementConfig = ImprovementConfig(),
        clock: Clock = monotonic,
    ) -> None:
        if not callable(evaluator) or not callable(proposer) or not callable(clock):
            raise ValueError("evaluator, proposer, and clock must be callable")
        if not isinstance(config, ImprovementConfig):
            raise ValueError("config must be an ImprovementConfig")
        self._evaluator = evaluator
        self._proposer = proposer
        self._config = config
        self._clock = clock

    def _measure(self, candidate: Candidate) -> Tuple[Optional[MeasuredEvaluation], Optional[str]]:
        started = self._clock()
        try:
            evaluation = self._evaluator(candidate)
            elapsed = self._clock() - started
            if not isinstance(evaluation, Evaluation):
                raise ValueError("evaluator must return an Evaluation")
            if (
                isinstance(evaluation.quality_score, bool)
                or not isinstance(evaluation.quality_score, Real)
                or not math.isfinite(evaluation.quality_score)
                or not 0 <= evaluation.quality_score <= 1
                or type(evaluation.correct) is not bool
                or not isinstance(evaluation.metrics, Mapping)
            ):
                raise ValueError("evaluator returned a malformed Evaluation")
            _validated_scalar_mapping(evaluation.metrics, "metrics")
            if not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError("clock must return finite, non-decreasing values")
            return MeasuredEvaluation(evaluation, elapsed), None
        except Exception as exc:
            return None, f"evaluator failed ({type(exc).__name__}): {exc}"

    def run(self, baseline_candidate: Candidate) -> ImprovementResult:
        if not isinstance(baseline_candidate, Candidate):
            raise ValueError("baseline_candidate must be a Candidate")
        started = self._clock()
        baseline, baseline_error = self._measure(baseline_candidate)
        if baseline_error is not None or baseline is None:
            raise ValueError(f"baseline evaluation failed: {baseline_error}")
        if not baseline.evaluation.correct or baseline.evaluation.quality_score < self._config.quality_floor:
            raise ValueError("baseline must be correct and meet quality_floor")

        best_candidate = baseline_candidate
        best_evaluation = baseline
        outcomes = []
        iterations = proposals = failures = proposal_failures = 0
        peak_parallelism = 1
        evaluations = 1
        stagnation = 0
        termination = TerminationReason.ITERATION_BUDGET

        for iteration in range(1, self._config.max_iterations + 1):
            if self._clock() - started >= self._config.max_seconds:
                termination = TerminationReason.TIME_BUDGET
                break
            if evaluations >= self._config.max_evaluations:
                termination = TerminationReason.EVALUATION_BUDGET
                break
            iterations = iteration
            batch_limit = min(
                self._config.max_workers,
                self._config.max_evaluations - evaluations,
            )
            try:
                iterator = iter(self._proposer(best_candidate, iteration))
                candidates = []
                for _ in range(batch_limit):
                    if self._clock() - started >= self._config.max_seconds:
                        break
                    try:
                        candidate = next(iterator)
                    except StopIteration:
                        break
                    proposals += 1
                    if not isinstance(candidate, Candidate):
                        raise ValueError("proposer must yield Candidate instances")
                    candidates.append(candidate)
            except Exception:
                proposal_failures += 1
                termination = TerminationReason.PROPOSAL_FAILURE
                break
            if not candidates:
                termination = (
                    TerminationReason.TIME_BUDGET
                    if self._clock() - started >= self._config.max_seconds
                    else TerminationReason.NO_CANDIDATES
                )
                break

            active = 0
            active_lock = Lock()

            def evaluate(candidate: Candidate):
                nonlocal active, peak_parallelism
                with active_lock:
                    active += 1
                    peak_parallelism = max(peak_parallelism, active)
                try:
                    return self._measure(candidate)
                finally:
                    with active_lock:
                        active -= 1

            if len(candidates) == 1 or self._config.max_workers == 1:
                measured_candidates = [evaluate(candidate) for candidate in candidates]
            else:
                with ThreadPoolExecutor(max_workers=self._config.max_workers) as pool:
                    measured_candidates = list(pool.map(evaluate, candidates))
            evaluations += len(candidates)

            accepted_this_iteration = False
            for candidate, (measured, error) in zip(candidates, measured_candidates):
                if error is not None or measured is None:
                    failures += 1
                    outcomes.append(CandidateOutcome(candidate, None, False, error or "evaluation failed"))
                    continue
                evaluation = measured.evaluation
                if not evaluation.correct:
                    reason = "candidate failed correctness checks"
                elif evaluation.quality_score < self._config.quality_floor:
                    reason = "candidate is below quality_floor"
                elif evaluation.quality_score < best_evaluation.evaluation.quality_score:
                    reason = "candidate regresses quality"
                else:
                    old_time = best_evaluation.elapsed_seconds
                    speedup = (old_time - measured.elapsed_seconds) / old_time if old_time > 0 else 0
                    if measured.elapsed_seconds >= old_time or speedup < self._config.min_speedup:
                        reason = "candidate does not meet minimum speedup"
                    else:
                        reason = "accepted: quality maintained and minimum speedup met"
                        best_candidate = candidate
                        best_evaluation = measured
                        accepted_this_iteration = True
                outcomes.append(CandidateOutcome(candidate, measured, reason.startswith("accepted:"), reason))

            if accepted_this_iteration:
                stagnation = 0
            else:
                stagnation += 1

            if self._clock() - started >= self._config.max_seconds:
                termination = TerminationReason.TIME_BUDGET
                break
            if evaluations >= self._config.max_evaluations:
                termination = TerminationReason.EVALUATION_BUDGET
                break
            if stagnation >= self._config.stagnation_limit:
                termination = TerminationReason.STAGNATION
                break

        return ImprovementResult(
            baseline_candidate=baseline_candidate,
            baseline=baseline,
            outcomes=tuple(outcomes),
            best_candidate=best_candidate,
            best_evaluation=best_evaluation,
            termination_reason=termination,
            resources=ResourceCounts(
                iterations=iterations,
                proposals=proposals,
                evaluations=evaluations,
                evaluator_failures=failures,
                proposal_failures=proposal_failures,
                peak_parallelism=peak_parallelism,
            ),
        )
