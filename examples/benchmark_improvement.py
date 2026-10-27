"""Compare linear and set-based membership using the bounded local optimizer."""

from src.agents.improvement import (
    Candidate,
    Evaluation,
    ImprovementConfig,
    ImprovementController,
)


TERMS = tuple(f"indicator-{index}" for index in range(5000))
QUERIES = tuple(
    f"indicator-{index % 6000}" for index in range(4000)
)
EXPECTED = set(TERMS)
EXPECTED_RESULTS = tuple(query in EXPECTED for query in QUERIES)


def evaluate_membership(candidate: Candidate) -> Evaluation:
    strategy = candidate.parameters["strategy"]
    if strategy not in ("linear", "set"):
        raise ValueError("unsupported membership strategy")
    lookup = list(TERMS) if strategy == "linear" else set(TERMS)
    decisions = tuple(query in lookup for query in QUERIES)
    matches = sum(decisions)
    quality = sum(
        actual == reference for actual, reference in zip(decisions, EXPECTED_RESULTS)
    ) / len(EXPECTED_RESULTS)
    correct = decisions == EXPECTED_RESULTS
    return Evaluation(
        quality,
        correct,
        {"matches": matches, "queries": len(QUERIES)},
    )


def propose_indexed_strategy(current: Candidate, iteration: int):
    if current.parameters["strategy"] == "linear":
        yield Candidate("set-membership", {"strategy": "set"})


def main() -> None:
    baseline = Candidate("linear-membership", {"strategy": "linear"})
    result = ImprovementController(
        evaluator=evaluate_membership,
        proposer=propose_indexed_strategy,
        config=ImprovementConfig(
            max_iterations=1,
            max_evaluations=2,
            max_seconds=10,
            quality_floor=1,
            min_speedup=0.01,
        ),
    ).run(baseline)
    print(
        f"baseline: quality={result.baseline.evaluation.quality_score:.3f}, "
        f"correct={result.baseline.evaluation.correct}, "
        f"elapsed={result.baseline.elapsed_seconds:.6f}s"
    )
    for outcome in result.outcomes:
        elapsed = (
            outcome.measured.elapsed_seconds if outcome.measured is not None else "unavailable"
        )
        print(
            f"candidate {outcome.candidate.name}: accepted={outcome.accepted}, "
            f"elapsed={elapsed}, reason={outcome.reason}"
        )
    print(
        f"best proposal: {result.best_candidate.name}; "
        f"termination={result.termination_reason.value}; "
        f"evaluations={result.resources.evaluations}; "
        "proposal_only=True (no live settings were changed)"
    )


if __name__ == "__main__":
    main()
