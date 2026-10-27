"""Deterministic tests for the standalone bounded optimizer."""

import pytest

from src.optimization import Candidate, Evaluation, optimize


def evaluate(candidate):
    return Evaluation(score=candidate.value)


def increment(best, index):
    return Candidate(best.value + 1)


def test_improves_deterministically_and_tracks_audit():
    kwargs = dict(max_iterations=3, max_evaluations=4)
    first = optimize(Candidate(0), increment, evaluate, **kwargs)
    assert first == optimize(Candidate(0), increment, evaluate, **kwargs)
    assert first.best_candidate == Candidate(3)
    assert (first.baseline_score, first.best_score) == (0, 3)
    assert (first.accepted_count, first.rejected_count) == (3, 0)
    assert (first.iterations, first.evaluations) == (3, 4)
    assert first.stop_reason == "max_iterations"


@pytest.mark.parametrize("evaluation", [
    Evaluation(-1, 5),
    Evaluation(0, 5),
    Evaluation(0.5, 5),
    Evaluation(10, 4),
    Evaluation(10, 5, valid=False),
])
def test_rejects_worse_tied_below_threshold_invalid_or_lower_quality(evaluation):
    result = optimize(
        Candidate(0), increment,
        lambda candidate: Evaluation(0, 5) if candidate.value == 0 else evaluation,
        max_iterations=1, min_improvement=1,
    )
    assert result.best_candidate == Candidate(0)
    assert result.best_score == 0
    assert (result.accepted_count, result.rejected_count) == (0, 1)


def test_threshold_equality_is_accepted_and_quality_cannot_regress_from_best():
    evaluations = [Evaluation(0, 1), Evaluation(1, 2), Evaluation(2, 1)]
    result = optimize(
        Candidate(0), lambda best, index: Candidate(index + 1),
        lambda candidate: evaluations[candidate.value],
        max_iterations=2, min_improvement=1,
    )
    assert result.best_candidate == Candidate(1)
    assert (result.accepted_count, result.rejected_count) == (1, 1)


@pytest.mark.parametrize("budgets, reason, iterations, evaluations", [
    ({"max_iterations": 0}, "max_iterations", 0, 1),
    ({"max_iterations": 2}, "max_iterations", 2, 3),
    ({"max_evaluations": 1}, "max_evaluations", 0, 1),
    ({"max_evaluations": 3}, "max_evaluations", 2, 3),
    ({"stagnation_limit": 2}, "stagnation", 2, 3),
])
def test_stopping_budgets(budgets, reason, iterations, evaluations):
    result = optimize(Candidate(0), increment, lambda _: Evaluation(0), **budgets)
    assert result.stop_reason == reason
    assert (result.iterations, result.evaluations) == (iterations, evaluations)
    assert result.rejected_count == iterations


def test_acceptance_resets_stagnation():
    scores = [0, -1, 1, 0, 0]
    result = optimize(
        Candidate(0), lambda best, index: Candidate(index + 1),
        lambda candidate: Evaluation(scores[candidate.value]),
        stagnation_limit=2,
    )
    assert result.stop_reason == "stagnation"
    assert result.iterations == 4
    assert (result.accepted_count, result.rejected_count) == (1, 3)


@pytest.mark.parametrize("name, value", [
    ("max_iterations", -1), ("max_iterations", 1.5),
    ("max_iterations", True), ("max_evaluations", 0),
    ("max_evaluations", float("inf")), ("stagnation_limit", 0),
    ("stagnation_limit", False), ("min_improvement", -1),
    ("min_improvement", float("nan")), ("min_improvement", float("inf")),
    ("min_improvement", None), ("time_limit_seconds", -1),
    ("time_limit_seconds", float("inf")),
    ("time_limit_seconds", float("nan")), ("time_limit_seconds", True),
    ("fail_fast", "yes"),
])
def test_invalid_config_is_rejected_before_callbacks(name, value):
    def unexpected(*args):
        pytest.fail("invalid configuration must not invoke callbacks")

    with pytest.raises(ValueError, match=name):
        optimize(Candidate(0), unexpected, unexpected, **{name: value})


@pytest.mark.parametrize("field", ["score", "quality"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_proposals_are_rejected(field, value):
    def evaluator(candidate):
        return (Evaluation(0) if candidate.value == 0
                else Evaluation(**{field: value, **({"score": 1}
                                                  if field == "quality"
                                                  else {})}))

    result = optimize(Candidate(0), increment, evaluator, max_iterations=1)
    assert result.best_score == 0
    assert result.rejected_count == 1
    with pytest.raises(ValueError, match="finite"):
        optimize(Candidate(0), increment, evaluator, fail_fast=True)


@pytest.mark.parametrize("failure", ["exception", "non_finite", "invalid"])
def test_failed_baseline_returns_no_verified_scores(failure):
    def evaluator(candidate):
        if failure == "exception":
            raise RuntimeError("evaluation failed")
        if failure == "non_finite":
            return Evaluation(float("nan"))
        return Evaluation(1, valid=False)

    result = optimize(Candidate(0), increment, evaluator)
    assert result.stop_reason == "baseline_failed"
    assert result.baseline_score is result.best_score is None
    assert result.best_candidate == Candidate(0)
    assert (result.iterations, result.evaluations) == (0, 1)
    assert (result.accepted_count, result.rejected_count) == (0, 0)


def test_evaluator_exception_is_rejected_and_run_continues():
    def evaluator(candidate):
        if candidate.value == 1:
            raise RuntimeError("evaluation failed")
        return Evaluation(candidate.value)

    result = optimize(
        Candidate(0), lambda best, index: Candidate(index + 1), evaluator,
        max_iterations=2,
    )
    assert result.best_score == 2
    assert (result.accepted_count, result.rejected_count) == (1, 1)
    assert result.evaluations == 3
    with pytest.raises(RuntimeError, match="evaluation failed"):
        optimize(Candidate(0), increment, evaluator, fail_fast=True)


def test_fail_fast_propagates_baseline_exception():
    def evaluator(candidate):
        raise RuntimeError("baseline failed")

    with pytest.raises(RuntimeError, match="baseline failed"):
        optimize(Candidate(0), increment, evaluator, fail_fast=True)


@pytest.mark.parametrize("ticks, iterations, evaluations", [
    ([0, 0, 1], 0, 1),
    ([0, 0, 0, 1], 1, 1),
    ([0, 0, 0, 0, 1], 1, 2),
])
def test_deadline_checks_between_callbacks(monkeypatch, ticks,
                                          iterations, evaluations):
    clock = iter(ticks)
    monkeypatch.setattr("src.optimization.monotonic", lambda: next(clock))
    result = optimize(
        Candidate(0), increment, evaluate, time_limit_seconds=1,
    )
    assert result.stop_reason == "deadline"
    assert (result.iterations, result.evaluations) == (iterations, evaluations)


def test_zero_time_budget_invokes_no_callbacks():
    def unexpected(*args):
        pytest.fail("expired deadline must not invoke callbacks")

    result = optimize(
        Candidate(0), unexpected, unexpected, time_limit_seconds=0,
    )
    assert result.stop_reason == "deadline"
    assert result.evaluations == 0


def test_no_clock_dependency_without_time_budget(monkeypatch):
    def unexpected():
        pytest.fail("clock should not be used without a time budget")

    monkeypatch.setattr("src.optimization.monotonic", unexpected)
    assert optimize(
        Candidate(0), increment, evaluate, max_iterations=1,
    ).best_score == 1
