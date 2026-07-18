# Cerribro Deep Intelligence Framework

This document specifies the **Deep Intelligence Layer** — a reusable reasoning and
planning framework that Cerribro applies when `strict_planning_mode` is enabled (see
[`agent_config.json`](agent_config.json)).

---

## Overview

Standard mode: Cerribro produces a plan and executes it in a single pass.

**Deep Intelligence mode** inserts a structured pre-execution loop that:
1. Decomposes the problem into bounded subproblems.
2. Surfaces and tracks explicit assumptions.
3. Records decision rationale (why approach A was chosen over B).
4. Defines a branching strategy with fallback plans.
5. Scores confidence per major conclusion before proceeding.

This overhead is worth it for complex, multi-step, or high-stakes tasks. For quick
fixes and simple lookups, standard mode is sufficient.

---

## 1 — Problem Decomposition

### Goal
Break a complex request into independently solvable subproblems so that each piece
can be reasoned about, estimated, and validated on its own.

### Template

```
PROBLEM: <one-sentence statement of the overall goal>

SUBPROBLEMS:
  SP-1: <name>
        - Scope:    <what this subproblem covers>
        - Input:    <what it needs from upstream>
        - Output:   <what it produces>
        - Deps:     <list of other SP IDs this depends on>
        - Estimate: <complexity — Simple / Medium / Complex>

  SP-2: ...
```

### Rules
- Each subproblem must have a concrete deliverable (a file, a function, a decision).
- Circular dependencies between subproblems are not allowed.
- A subproblem marked **Complex** must itself be recursively decomposed one level down
  before work begins.

---

## 2 — Assumptions Tracking

### Goal
Prevent hidden assumptions from silently invalidating conclusions later in the workflow.

### Template

```
ASSUMPTIONS LOG
===============
ID   | Assumption                                        | Confidence | Owner  | Verified?
-----|---------------------------------------------------|------------|--------|----------
A-01 | Python ≥ 3.10 is available on the target system   | High       | Cerribro | [ ]
A-02 | The existing tests use pytest                     | Medium     | User     | [ ]
A-03 | Network access is available at runtime            | Low        | System   | [ ]
```

### Rules
- Every assumption must be assigned a confidence level: **High / Medium / Low**.
- Low-confidence assumptions require explicit user confirmation before work proceeds.
- Assumptions must be referenced inline whenever they are used (e.g., "per A-01,
  using `match` statement syntax").
- The assumptions log is included in every Deep Intelligence output bundle.

---

## 3 — Decision Log

### Goal
Record the reasoning behind every significant architectural or implementation choice
so decisions can be revisited, audited, and explained.

### Template

```
DECISION LOG
============
DEC-01: <Short title>
  Context:    <What was the situation that forced a choice?>
  Options:    A) <Option A>  B) <Option B>  [C) ...]
  Chosen:     A
  Rationale:  <Why A over B; trade-offs explicitly stated>
  Reversible: Yes / No
  Date:       <ISO date>
```

### Rules
- Log every decision that has non-trivial impact on correctness, performance,
  or maintainability.
- When a chosen option is later invalidated, the entry is updated with
  `Status: SUPERSEDED → DEC-NN` rather than deleted.
- Decision logs are stored in the session history alongside the output.

---

## 4 — Branching Strategy and Fallback Plans

### Goal
Define an explicit path tree so that Cerribro (and the user) know what to do if
the primary approach fails.

### Template

```
EXECUTION BRANCHES
==================
PRIMARY PATH (P0):
  Steps:    [SP-1 → SP-2 → SP-3]
  Preconditions: [A-01 verified, A-02 verified]
  Stop condition: All steps complete with confidence ≥ 0.75

FALLBACK-1 (F1): Triggered if SP-2 fails
  Steps:    [SP-2-alt → SP-3]
  Changes:  Use alternative library X instead of Y
  Escalate: If F1 also fails → ESCALATE_TO_USER

FALLBACK-2 (F2): Triggered if confidence < 0.5 at SP-3
  Action:   Pause, emit partial output, request user guidance
  Output:   Partial plan + explicit unknowns list
```

### Rules
- Every primary path must have at least one fallback.
- Fallbacks are lighter-weight by design — they solve a smaller scope rather
  than attempting the same approach again.
- Escalation to the user is always the final fallback.

---

## 5 — Confidence Scoring

### Goal
Give every major conclusion a numeric confidence score so stakeholders can
calibrate trust appropriately.

### Scoring Rubric

| Band  | Score Range | Meaning                                                              |
|-------|-------------|----------------------------------------------------------------------|
| High  | 0.80 – 1.00 | Well-established fact, verified against training data / docs         |
| Medium| 0.55 – 0.79 | Likely correct; may be version-sensitive or recently changed         |
| Low   | 0.30 – 0.54 | Extrapolated or uncertain; user verification strongly recommended    |
| Uncertain | 0.00 – 0.29 | Insufficient evidence — do not act without user confirmation     |

### Scoring Factors

Each conclusion's score is adjusted by the following factors:

| Factor                          | Adjustment       |
|---------------------------------|------------------|
| Task description ≥ 50 words     | +0.05            |
| All assumptions verified        | +0.10            |
| Contradictory evidence found    | −0.15            |
| Capability confidence_score < 0.8 | −0.05          |
| Low-confidence assumption used  | −0.10 per usage  |
| Freshness flag triggered        | −0.05            |

### Rules
- A score below **0.55** must not result in an auto-proceed; the plan pauses
  and Cerribro reports the insufficiency to the user.
- Scores are displayed both as floats (e.g., `0.72`) and as band labels
  (e.g., `Medium`) in outputs.
- The aggregate confidence for a multi-step plan is the minimum across all
  sub-conclusion scores.

---

## 6 — Intelligence Plan Output Format

When strict planning mode is active, Cerribro's `think()` output includes a
`deep_intelligence` key with the following structure:

```json
{
  "deep_intelligence": {
    "subproblems": [
      {
        "id": "SP-1",
        "name": "...",
        "scope": "...",
        "input": "...",
        "output": "...",
        "dependencies": [],
        "complexity": "Medium"
      }
    ],
    "assumptions": [
      {
        "id": "A-01",
        "text": "...",
        "confidence": "High",
        "verified": false
      }
    ],
    "decisions": [
      {
        "id": "DEC-01",
        "title": "...",
        "chosen": "A",
        "rationale": "...",
        "reversible": true
      }
    ],
    "branches": {
      "primary": ["SP-1", "SP-2", "SP-3"],
      "fallbacks": [
        { "trigger": "SP-2 fails", "steps": ["SP-2-alt", "SP-3"] }
      ]
    },
    "confidence_score": 0.82,
    "confidence_band": "High"
  }
}
```

---

## 7 — Enabling / Disabling Strict Planning Mode

See [`agent_config.json`](agent_config.json) for the `deep_modes.strict_planning`
toggle and all related thresholds. The config section is:

```json
"deep_modes": {
  "strict_planning": {
    "enabled": false,
    "confidence_threshold_auto_proceed": 0.75,
    "require_assumption_verification": true,
    "log_decisions": true,
    "max_subproblem_depth": 2
  }
}
```

Set `enabled` to `true` to activate the full Deep Intelligence layer for all requests.

---

## 8 — Pre-Response Checklist (Deep Intelligence Mode)

Before emitting any response in strict planning mode, Cerribro verifies:

- [ ] Problem decomposed into ≤ 10 subproblems, each with a clear deliverable
- [ ] All assumptions listed and confidence levels assigned
- [ ] At least one decision log entry for every non-trivial architectural choice
- [ ] Primary path and at least one fallback defined
- [ ] Aggregate confidence score calculated and ≥ threshold for auto-proceed
- [ ] No circular subproblem dependencies
- [ ] Low-confidence assumptions flagged to user if `require_assumption_verification` is true

---

## See Also

- [`deep_research.md`](deep_research.md) — evidence gathering layer
- [`deepmind_loop.md`](deepmind_loop.md) — hypothesis/experiment/evaluation loop
- [`grounding_policy.md`](grounding_policy.md) — base grounding rules
- [`agent_config.json`](agent_config.json) — config reference
