# Bounded iterative improvement

`src.agents.improvement.ImprovementController` provides a bounded, proposal-only
loop for comparing application strategy configurations. It runs the baseline
and proposals through the same caller-supplied evaluator, records quality,
correctness, and controller-measured elapsed time separately, and retains the
best valid candidate without changing live configuration.

The controller is an optimizer, not a candidate generator or self-training
model. Callers provide a proposal function; this repository does not connect
that function to an LLM, rewrite source code, or change model weights. A
deterministic local example is available at
`examples/benchmark_improvement.py`, runnable from the repository root with:

```bash
python -m examples.benchmark_improvement
```

The existing `AgentTrainer.evaluate` measures RL episode rewards, not generic
application-strategy correctness and latency, so this controller does not
replace or modify that trainer.

The example compares list-based and set-based membership on the same fixed
workload, reports measured timings, and only describes a faster result if the
run actually accepts it. Timings are machine- and workload-dependent; this is
not a general speedup claim.

## API and defaults

Construct immutable `Candidate` values for an application strategy and an
`Evaluation` from a fixed evaluator. The evaluator's `quality_score` is a
finite value in `[0, 1]`; `correct` is an independent boolean correctness
check. The controller measures evaluator elapsed time itself. The baseline
must be correct and meet `quality_floor`.

`ImprovementConfig` bounds a run to 5 iterations, 20 total evaluations
(including baseline), 30 seconds, 2 consecutive stagnant iterations, and 1
worker by default. Candidates are accepted only when correct, at or above the
quality floor, no worse in quality than the incumbent, and faster by at least
`min_speedup` (default 1%). Equal timings retain the incumbent, so ties are
stable. Stop reasons and resource counts are returned with the baseline,
candidate measurements, and each acceptance/rejection reason.

Independent evaluations can use `max_workers` to set a bounded thread pool;
at most that many candidates are evaluated concurrently. The time budget is
checked between proposals and evaluation batches. Python cannot forcibly stop
arbitrary proposal or evaluator callbacks, so a blocking callback can overrun
the deadline; callbacks must cooperate with their own I/O and work limits.
Evaluation timings are never memoized.

## Safety and limitations

Results are always proposals (`proposal_only=True`, `approval_required=True`).
Applying a candidate requires a separate integration and explicit human
approval. The controller does not execute generated code, write production
settings, deploy, edit policies, or alter permissions. It optimizes only
application-level candidate parameters against the evaluator and workload
provided by the caller. It does not improve model weights or provide
autonomous recursive intelligence.

For a meaningful comparison, keep the evaluator and workload fixed, include
setup costs that differ between strategies, run baseline and candidate under
the same conditions, and repeat measurements on representative workloads.
Quality/correctness are evaluated independently from speed; a timing win alone
cannot override a quality regression or failed correctness check.
