# Cerribro — Autonomous Mode Workflow

Autonomous mode lets Cerribro pursue a **high-level objective** end-to-end with
minimal step-by-step human guidance. It cycles through planning, execution, and
replanning until the acceptance criteria are met or a human checkpoint is reached.

---

## When to use

Use `autonomous` mode when you want Cerribro to:

- Complete a multi-step development goal (e.g., "add authentication to this API")
  without hand-holding each individual step.
- Run iterative improvement loops (refactor → test → review → refactor …).
- Orchestrate a sequence of subtasks that depend on each other's outputs.

---

## Activation

```python
cerribro = CerribroAgent(name="Cerribro", mode="autonomous")
# or switch at runtime:
cerribro.set_mode("autonomous")
```

---

## Execution pipeline

| Step | Name | Description |
|------|------|-------------|
| 1 | `parse_high_level_objective` | Extract the goal, constraints, and acceptance criteria from the request. |
| 2 | `decompose_into_sub_goals` | Break the objective into an ordered list of independently verifiable sub-goals. |
| 3 | `select_tools_and_resources` | Identify which capabilities, APIs, or external tools are required. |
| 4 | `execute_sub_goals_iteratively` | Execute each sub-goal in sequence, storing intermediate results. |
| 5 | `evaluate_intermediate_results` | Check each result against the sub-goal's acceptance criteria. |
| 6 | `replan_if_deviation_detected` | If a sub-goal fails or drifts, regenerate a revised plan and continue. |
| 7 | `verify_acceptance_criteria` | Run a final check that all top-level acceptance criteria are satisfied. |
| 8 | `produce_final_report` | Emit a structured report: steps taken, decisions made, outcomes, and any open items. |

---

## Human checkpoints

By default Cerribro pauses for human review every **5 autonomous iterations**
(`human_checkpoint_interval` in `agent_config.json`). You can override this:

```python
# Pause every 3 iterations instead of 5
cerribro.grounding_flags["human_checkpoint_interval"] = 3
```

If `abort_on_unsafe_action` is `true` (default), the agent stops immediately
and requests confirmation before taking any action flagged as potentially
destructive or irreversible.

---

## Configuration knobs (`agent_config.json → autonomous_mode`)

| Key | Default | Meaning |
|-----|---------|---------|
| `max_autonomous_iterations` | 20 | Hard cap on planning-execution cycles. |
| `replan_on_deviation` | `true` | Trigger replanning when an intermediate result deviates from expectations. |
| `human_checkpoint_interval` | 5 | Request human confirmation every N iterations. |
| `abort_on_unsafe_action` | `true` | Halt before any potentially destructive action. |
| `confidence_threshold_to_proceed` | 0.70 | Minimum confidence required to proceed without prompting. |

---

## Example

```python
task_params = {
    "description": "Add JWT authentication to the existing FastAPI project, "
                   "write tests, and update the README.",
    "context": "FastAPI project in /src, tests in /tests, Python 3.11",
    "acceptance_criteria": [
        "All existing tests still pass",
        "New auth endpoints have >90% test coverage",
        "README documents the new /auth/* routes",
    ],
}
cerribro.set_mode("autonomous")
reasoning = cerribro.think(task_params)
result    = cerribro.act(reasoning)
print(result["status"])   # "completed"
print(result["output"])   # structured report
```

---

## Grounding in autonomous mode

All grounding guarantees remain active in autonomous mode:

- No fabricated APIs or library names.
- Confidence signalled at each decision point.
- Unsafe actions rejected automatically.
- Ambiguous sub-goals trigger clarification rather than guessing.
