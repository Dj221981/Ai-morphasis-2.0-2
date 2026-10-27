import math
import threading
import time

import pytest

from src.agents.improvement import (
    Candidate,
    Evaluation,
    ImprovementConfig,
    ImprovementController,
    TerminationReason,
)


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


def test_accepts_faster_candidate_with_same_quality_and_keeps_proposal_only():
    clock = FakeClock()
    baseline = Candidate("linear", {"mode": "linear"})
    improved = Candidate("indexed", {"mode": "indexed"})

    def evaluate(candidate):
        clock.value += 10.0 if candidate == baseline else 8.0
        return Evaluation(1.0, True, {"correct_cases": 3})

    controller = ImprovementController(
        evaluate,
        lambda current, iteration: [improved],
        ImprovementConfig(max_iterations=2, max_evaluations=3, min_speedup=0.1),
        clock,
    )
    result = controller.run(baseline)

    assert result.best_candidate == improved
    assert result.baseline.elapsed_seconds == 10.0
    assert result.best_evaluation.elapsed_seconds == 8.0
    assert result.outcomes[0].accepted
    assert result.proposal_only and result.approval_required
    assert result.termination_reason is TerminationReason.EVALUATION_BUDGET
    assert result.resources.evaluations == 3


def test_rejects_quality_regression_even_when_candidate_is_faster():
    clock = FakeClock()
    baseline = Candidate("baseline")
    candidate = Candidate("fast-but-worse")

    def evaluate(item):
        clock.value += 10 if item == baseline else 1
        return Evaluation(1.0 if item == baseline else 0.8, True)

    result = ImprovementController(
        evaluate,
        lambda current, iteration: [candidate],
        ImprovementConfig(
            max_iterations=3,
            max_evaluations=5,
            stagnation_limit=1,
            quality_floor=0.5,
        ),
        clock,
    ).run(baseline)

    assert result.best_candidate == baseline
    assert result.outcomes[0].reason == "candidate regresses quality"
    assert result.termination_reason is TerminationReason.STAGNATION


def test_stops_at_evaluation_budget_including_baseline():
    clock = FakeClock()
    baseline = Candidate("baseline")
    candidate = Candidate("candidate")

    def evaluate(item):
        clock.value += 1
        return Evaluation(1.0, True)

    result = ImprovementController(
        evaluate,
        lambda current, iteration: [candidate],
        ImprovementConfig(max_iterations=10, max_evaluations=2, min_speedup=0),
        clock,
    ).run(baseline)

    assert result.resources.evaluations == 2
    assert result.termination_reason is TerminationReason.EVALUATION_BUDGET


def test_stops_after_configured_stagnation():
    clock = FakeClock()
    baseline = Candidate("baseline")
    candidate = Candidate("tie")

    def evaluate(item):
        clock.value += 1
        return Evaluation(1.0, True)

    result = ImprovementController(
        evaluate,
        lambda current, iteration: [candidate],
        ImprovementConfig(
            max_iterations=10,
            max_evaluations=10,
            stagnation_limit=2,
            min_speedup=0,
        ),
        clock,
    ).run(baseline)

    assert result.resources.iterations == 2
    assert all(not outcome.accepted for outcome in result.outcomes)
    assert result.termination_reason is TerminationReason.STAGNATION


def test_stops_at_iteration_budget():
    clock = FakeClock()
    baseline = Candidate("baseline")
    candidate = Candidate("same-speed")

    def evaluate(item):
        clock.value += 1
        return Evaluation(1.0, True)

    result = ImprovementController(
        evaluate,
        lambda current, iteration: [candidate],
        ImprovementConfig(
            max_iterations=1,
            max_evaluations=5,
            stagnation_limit=3,
            min_speedup=0,
        ),
        clock,
    ).run(baseline)

    assert result.resources.iterations == 1
    assert result.termination_reason is TerminationReason.ITERATION_BUDGET


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_iterations": -1},
        {"max_evaluations": 0},
        {"stagnation_limit": 0},
        {"max_workers": 0},
        {"max_seconds": math.inf},
        {"quality_floor": math.nan},
        {"min_speedup": 1.0},
        {"max_workers": True},
    ],
)
def test_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        ImprovementConfig(**kwargs)


@pytest.mark.parametrize("score", [math.nan, math.inf, -math.inf, -0.1, 1.1, True])
def test_rejects_invalid_quality_scores(score):
    with pytest.raises(ValueError, match="quality_score"):
        Evaluation(score, True)


def test_rejects_non_boolean_correctness_and_mutable_candidate_parameters():
    with pytest.raises(ValueError, match="correct"):
        Evaluation(1.0, 1)

    parameters = {"strategy": "linear"}
    candidate = Candidate("candidate", parameters)
    parameters["strategy"] = "changed"
    assert candidate.parameters["strategy"] == "linear"
    with pytest.raises(TypeError):
        candidate.parameters["strategy"] = "changed"


def test_records_malformed_evaluation_as_rejection():
    baseline = Candidate("baseline")
    candidate = Candidate("malformed")
    clock = FakeClock()

    def evaluate(item):
        clock.value += 1
        return Evaluation(1.0, True) if item == baseline else object()

    result = ImprovementController(
        evaluate,
        lambda current, iteration: [candidate],
        ImprovementConfig(max_iterations=1, max_evaluations=2),
        clock,
    ).run(baseline)

    assert result.outcomes[0].measured is None
    assert "must return an Evaluation" in result.outcomes[0].reason
    assert result.resources.evaluator_failures == 1


def test_records_evaluator_exception_without_discarding_the_result():
    baseline = Candidate("baseline")
    candidate = Candidate("raises")
    clock = FakeClock()

    def evaluate(item):
        clock.value += 1
        if item == candidate:
            raise RuntimeError("evaluation unavailable")
        return Evaluation(1.0, True)

    result = ImprovementController(
        evaluate,
        lambda current, iteration: [candidate],
        ImprovementConfig(max_iterations=1, max_evaluations=2),
        clock,
    ).run(baseline)

    assert result.outcomes[0].measured is None
    assert "evaluation unavailable" in result.outcomes[0].reason
    assert result.resources.evaluator_failures == 1


def test_enforces_bounded_parallel_evaluation():
    baseline = Candidate("baseline")
    candidates = [Candidate("first"), Candidate("second")]
    active = 0
    peak = 0
    lock = threading.Lock()

    def evaluate(candidate):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            time.sleep(0.03 if candidate == baseline else 0.005)
            return Evaluation(1.0, True)
        finally:
            with lock:
                active -= 1

    result = ImprovementController(
        evaluate,
        lambda current, iteration: candidates,
        ImprovementConfig(
            max_iterations=1,
            max_evaluations=3,
            max_workers=2,
            min_speedup=0,
        ),
    ).run(baseline)

    assert peak == 2
    assert result.resources.peak_parallelism == 2
    assert result.resources.evaluations == 3


def test_stops_at_cooperative_time_budget():
    clock = FakeClock()
    baseline = Candidate("baseline")
    candidate = Candidate("candidate")

    def evaluate(item):
        clock.value += 1
        return Evaluation(1.0, True)

    result = ImprovementController(
        evaluate,
        lambda current, iteration: [candidate],
        ImprovementConfig(max_seconds=1, max_iterations=4, max_evaluations=5),
        clock,
    ).run(baseline)

    assert result.resources.evaluations == 1
    assert result.termination_reason is TerminationReason.TIME_BUDGET


def test_baseline_must_meet_correctness_and_quality_floor():
    with pytest.raises(ValueError, match="baseline"):
        ImprovementController(
            lambda candidate: Evaluation(0.5, True),
            lambda current, iteration: [],
            ImprovementConfig(quality_floor=0.8),
        ).run(Candidate("baseline"))
