# Cerribro DeepMind-Style Execution Loop

This document specifies the **DeepMind-style Execution Loop** — a rigorous,
iterative experimentation framework that Cerribro applies when
`deep_modes.deepmind_loop.enabled` is `true` (see [`agent_config.json`](agent_config.json)).

It is inspired by the iterative research-engineering cycle: hypothesise → design
minimal experiment → execute → evaluate → learn → iterate or finalise.

---

## Overview

Standard engineering often skips the "why does this approach work?" question.
The DeepMind loop makes that reasoning **explicit and auditable**:

```
┌──────────────────────────────────────────────────────────┐
│                   DeepMind Execution Loop                │
│                                                          │
│  1. DEFINE hypothesis + success criteria                 │
│         ↓                                                │
│  2. DESIGN minimal experiment                            │
│         ↓                                                │
│  3. EXECUTE (or simulate if no runtime)                  │
│         ↓                                                │
│  4. EVALUATE against metrics                             │
│         ↓                                                │
│  5. RECORD learnings                                     │
│         ↓                                                │
│  6. ITERATE ──→ back to step 1  (if not done)            │
│     or FINALISE ──→ emit grounded output                 │
└──────────────────────────────────────────────────────────┘
```

Each iteration is a **round**. The loop terminates when a stop condition is met
(see per-mode stop conditions in Sections 4–6).

---

## 1 — Define: Hypothesis and Success Criteria

### Template

```
ROUND N — DEFINE
================
Hypothesis:
  H-N: <A falsifiable statement about what a change will achieve.>
  Example: "Replacing the O(n²) sort with heapsort will reduce latency below 50 ms
            for inputs of 10,000 items."

Success criteria (all must be true for the hypothesis to be confirmed):
  SC-N-1: <measurable criterion>
  SC-N-2: <measurable criterion>
  ...

Failure criteria (any one being true falsifies the hypothesis):
  FC-N-1: <measurable criterion>
```

### Rules
- Hypotheses must be **falsifiable** — if the criterion cannot be measured or
  observed, it is not a valid success criterion.
- Each round introduces at most one new hypothesis.
- Hypotheses are refined (not replaced) across rounds; prior rounds' results
  must be respected.

---

## 2 — Design: Minimal Experiment

### Goal
Design the **smallest possible experiment** that can confirm or falsify the
current hypothesis — no more, no less.

### Template

```
ROUND N — DESIGN
================
Experiment:
  EXP-N: <Description of the experiment>

Scope:
  - Files/modules touched: [list]
  - Test cases added/modified: [list]
  - External dependencies required: [list or "none"]

Controlled variables:
  - <What is held constant so the experiment is fair>

Measured variables:
  - <What is observed / recorded>

Instrumentation:
  - <How the measurement is taken: profiler, test assertion, log line, etc.>
```

### Rules
- Touch the minimum number of files/functions necessary.
- Do not include exploratory refactors in the experiment scope.
- If no runtime is available, design a **simulated experiment**: a static
  analysis, unit test, or thought experiment with explicit assumptions.

---

## 3 — Execute (or Simulate)

### Execution Path
If a runtime is available:
1. Apply the change from the experiment design.
2. Run the instrumented tests / profiler / checker.
3. Collect raw output (pass/fail, timing, coverage, etc.).

### Simulation Path
If no runtime is available (e.g., documentation task, architecture review):
1. Reason through the expected outcome step-by-step.
2. State explicit assumptions the simulation depends on.
3. Tag the result as `SIMULATED` in the output.
4. Flag that a live run is recommended before finalising.

### Execution Record

```
ROUND N — EXECUTE
=================
Method: [Runtime | Simulated]
Command / trigger:  <command run or simulation description>
Raw output summary: <key observations from output>
Assumptions (simulated only): [list]
Status: [Pass | Fail | Inconclusive]
```

---

## 4 — Evaluate Against Metrics

### Evaluation Record

```
ROUND N — EVALUATE
==================
Hypothesis H-N: <restated>

Success criteria assessment:
  SC-N-1: [Met | Not met | Partial] — <evidence>
  SC-N-2: [Met | Not met | Partial] — <evidence>

Failure criteria assessment:
  FC-N-1: [Triggered | Not triggered] — <evidence>

Hypothesis verdict:   [CONFIRMED | FALSIFIED | INCONCLUSIVE]
Confidence delta:     [+/- value]
Notes:                <any unexpected observations>
```

### Confidence Adjustment Rules
- `CONFIRMED` → +0.10 to the aggregate confidence score for this approach.
- `FALSIFIED` → −0.15 and trigger fallback plan.
- `INCONCLUSIVE` → −0.05; redesign experiment before next round.

---

## 5 — Record Learnings

### Learning Record

```
ROUND N — LEARNINGS
===================
What worked:    <observation>
What did not:   <observation>
Surprises:      <anything unexpected>
Updated assumptions:
  A-NN: [CONFIRMED | INVALIDATED | UPDATED] — <new text if updated>
Carry-forward to round N+1:
  - <specific change to hypothesis or experiment design>
```

Learning records are stored in the session history and available to inform
subsequent rounds and future sessions.

---

## 6 — Iterate or Finalise

### Iteration Decision Tree

```
Evaluate verdict
    │
    ├─ CONFIRMED and all SCs met ──→ FINALISE
    │
    ├─ CONFIRMED but SCs partially met ──→ ITERATE (refine hypothesis, tighten scope)
    │
    ├─ FALSIFIED ──→ Activate fallback plan
    │                   │
    │                   ├─ Fallback succeeds ──→ ITERATE with fallback approach
    │                   └─ Fallback fails    ──→ ESCALATE TO USER
    │
    └─ INCONCLUSIVE ──→ ITERATE (redesign experiment, gather more evidence)
```

### Finalise Checklist

Before emitting the final grounded output:

- [ ] All success criteria confirmed in at least one round
- [ ] No unresolved failure criteria
- [ ] Evidence Bundle attached (if deep_research enabled)
- [ ] Intelligence Plan attached (if strict_planning enabled)
- [ ] Learning records saved to session history
- [ ] Output tagged with final confidence score and band
- [ ] All simulated results flagged as `SIMULATED`

---

## Mode-Specific Metrics and Stop Conditions

### `app_builder` Mode

| Evaluation metric              | Measurement                                     |
|--------------------------------|-------------------------------------------------|
| Requirements coverage          | % of stated requirements addressed in scaffold  |
| Architecture validity          | No circular dependencies, no undefined services |
| Security baseline              | Auth layer present if `auth_required` is true   |
| Test coverage intent           | At least one test file per module planned        |
| Build signal                   | Project structure parsable / importable          |

**Stop condition:** All requirements covered, architecture validated, and confidence ≥ 0.75.

**Escalation criteria:** Stop and ask user if:
- Conflicting requirements cannot be reconciled after 2 rounds.
- Tech stack choice has two options with near-equal trade-offs and user preference unknown.
- A required dependency has a known security advisory.

---

### `game_builder` Mode

| Evaluation metric              | Measurement                                     |
|--------------------------------|-------------------------------------------------|
| Game loop completeness         | Core loop (update/draw/input) fully specified   |
| Mechanic coherence             | No contradictory game rules in design doc       |
| Engine fit                     | Chosen engine supports all required features    |
| Performance feasibility        | Target frame rate achievable given scope        |
| Playability signal             | At least one playable path from start to win    |

**Stop condition:** Core loop specified, mechanics coherent, engine fit confirmed,
and confidence ≥ 0.70.

**Escalation criteria:** Stop and ask user if:
- Two proposed mechanics directly conflict and user priority is unclear.
- Chosen engine cannot support a core feature after 2 redesign rounds.
- Performance target is infeasible given platform constraints.

---

### `coding_assistant` Mode

| Evaluation metric              | Measurement                                     |
|--------------------------------|-------------------------------------------------|
| Bug reproduction               | Failing test case written that captures the bug |
| Fix correctness                | All pre-existing tests pass after change        |
| Regression safety              | No new test failures introduced                 |
| Code quality                   | Linter passes, no new warnings                  |
| Documentation accuracy         | Docstrings / comments updated where changed     |

**Stop condition:** Bug fixed, all tests pass, linter clean, and confidence ≥ 0.80.

**Escalation criteria:** Stop and ask user if:
- Root cause cannot be isolated after 3 rounds of narrowing.
- Fix requires a breaking API change that affects callers outside scope.
- Two valid approaches have different correctness/performance trade-offs that
  require a business decision.

---

## 7 — Loop Output Format

The DeepMind loop produces a `deepmind_loop` key in the response payload:

```json
{
  "deepmind_loop": {
    "mode": "coding_assistant",
    "total_rounds": 2,
    "rounds": [
      {
        "round": 1,
        "hypothesis": "H-1: ...",
        "success_criteria": ["SC-1-1: ...", "SC-1-2: ..."],
        "experiment": "EXP-1: ...",
        "execution_method": "Runtime",
        "status": "CONFIRMED",
        "confidence_delta": 0.10,
        "learnings": "..."
      }
    ],
    "final_verdict": "CONFIRMED",
    "final_confidence": 0.87,
    "final_confidence_band": "High",
    "escalated": false,
    "escalation_reason": null
  }
}
```

---

## 8 — Enabling / Disabling the DeepMind Loop

See [`agent_config.json`](agent_config.json):

```json
"deep_modes": {
  "deepmind_loop": {
    "enabled": false,
    "max_rounds": 5,
    "min_confidence_to_finalise": 0.75,
    "confirmed_delta": 0.10,
    "falsified_delta": -0.15,
    "inconclusive_delta": -0.05
  }
}
```

---

## See Also

- [`intelligence_framework.md`](intelligence_framework.md) — problem decomposition and planning
- [`deep_research.md`](deep_research.md) — evidence gathering pipeline
- [`grounding_policy.md`](grounding_policy.md) — base grounding rules
- [`agent_config.json`](agent_config.json) — config reference
- Workflow files in [`workflows/`](workflows/) — per-mode integration
