# Workflow: `coding_assistant`

Use this workflow when Cerribro is in `coding_assistant` mode (the default). It covers
understanding a problem through to a tested, documented solution.

Each workflow now incorporates the five deep-upgrade stages:
**Intelligence Plan → Research Plan → Experimentation Loop → Validation Gate → Grounded Output.**

Enable each stage individually in [`agent_config.json`](../agent_config.json) under `deep_modes`.

---

## Inputs Expected

| Input field         | Required | Description                                              |
|---------------------|----------|----------------------------------------------------------|
| `description`       | Yes      | Clear description of the problem or task                 |
| `code`              | No       | The code snippet, file content, or diff to work on       |
| `language`          | No       | Programming language (Python, TypeScript, Go, etc.)      |
| `framework`         | No       | Framework in use (Django, React, FastAPI, etc.)          |
| `error_message`     | No       | Error or traceback if debugging                          |
| `expected_behavior` | No       | What the code should do (for bug reports)                |
| `actual_behavior`   | No       | What it currently does (for bug reports)                 |
| `test_framework`    | No       | Testing framework to use (pytest, Jest, etc.)            |
| `context`           | No       | Additional project context                               |

**Minimum viable input:** `description` (ideally with `code` for non-trivial requests).

---

## Stage 1 — Intelligence Plan

*(Active when `deep_modes.strict_planning.enabled: true`)*

1. **Decompose** into subproblems: root-cause isolation, fix scope, regression risk,
   documentation update, test additions.
2. **Log assumptions** — e.g., "Tests use pytest", "Python ≥ 3.10", "no public API change".
3. **Decision log** — if multiple fix approaches exist, document options and chosen rationale.
4. **Branches** — primary fix and fallback if root cause assessment is wrong.
5. **Confidence score** — pause if below 0.75; ask user for more context.

*Output:* `deep_intelligence` block. See [`intelligence_framework.md`](../intelligence_framework.md).

---

## Stage 2 — Research Plan

*(Active when `deep_modes.deep_research.enabled: true`)*

1. **Identify claims** requiring evidence: API behaviour, language semantics,
   library version compatibility, OWASP patterns for security fixes.
2. **Formulate research questions** (e.g., RQ-01: "Does Python's `dict.get()` return
   `None` by default for missing keys?").
3. **Gather evidence** — minimum 1 record for simple claims, 2 for medium.
4. **Synthesise** and attach Evidence Bundle; note any freshness warnings.
5. **Gate**: if `synthesis_confidence < 0.55`, emit Insufficient Evidence response and
   list what needs to be looked up externally.

*Output:* `evidence_bundle` block. See [`deep_research.md`](../deep_research.md).

---

## Stage 3 — Experimentation Loop (Fix Validation)

*(Active when `deep_modes.deepmind_loop.enabled: true`)*

| Round | Hypothesis                                              | Metrics                            | Stop condition                |
|-------|---------------------------------------------------------|------------------------------------|-------------------------------|
| R1    | Proposed change fixes the reported bug                 | Failing test written; fix applied  | Test passes                   |
| R2    | No pre-existing tests are broken by the change         | Full test suite passes             | Zero new failures             |
| R3    | Code quality is maintained (linter, type checker)      | No new linter / type errors        | Clean run                     |

**Escalation criteria** (stop and ask user):
- Root cause cannot be isolated after 3 rounds of narrowing.
- Fix requires a breaking API change affecting callers outside scope.
- Two valid approaches have different correctness/performance trade-offs
  requiring a business decision.

*Output:* `deepmind_loop` block. See [`deepmind_loop.md`](../deepmind_loop.md).

---

## Stage 4 — Validation and Verification Gate

Before proceeding to final output, all of the following must pass:

- [ ] Root cause identified and documented
- [ ] Failing test written (for bug fixes) or test coverage plan stated
- [ ] Proposed change is the minimal viable fix
- [ ] All pre-existing tests pass (or test run is explicitly deferred with reason)
- [ ] No new linter or type-checker warnings introduced
- [ ] Evidence Bundle attached (if deep_research enabled)
- [ ] Speculative content explicitly marked `[SPECULATIVE]`
- [ ] Documentation updated where changed behaviour is referenced

---

## Stage 5 — Final Grounded Output Format

```json
{
  "status": "completed",
  "mode": "coding_assistant",
  "confidence": 0.95,
  "confidence_band": "High",
  "output": {
    "workflow": "coding_assistant",
    "steps_planned": ["understand_context", "identify_problem", "..."],
    "steps_completed": [],
    "notes": "Plan produced. Steps are ready for iterative execution."
  },
  "facts": ["Python dict.get() returns None for missing keys by default (EV-01)."],
  "assumptions": ["Tests are using pytest (A-01, unverified)."],
  "proposals": ["Add .get('name', 'User') to safely handle missing key (DEC-01)."],
  "speculative": [],
  "unknowns_and_next_steps": [],
  "deep_intelligence": { "..." : "..." },
  "evidence_bundle": { "..." : "..." },
  "deepmind_loop": { "..." : "..." }
}
```

---

## Legacy Planning Steps (Standard Mode)

When `strict_planning` is disabled, the original planning steps apply:

1. **Understand context** — read code, error, and description; ask if unclear.
2. **Identify the problem** — root cause vs symptom; related issues.
3. **Propose a minimal fix** — one sentence before writing code; confirm if non-trivial.
4. **Apply the change** — smallest correct change; preserve style.
5. **Check for side effects** — review callers; confirm backward compatibility.
6. **Update documentation** — docstrings, README, API docs where needed.
7. **Run existing tests** — confirm no regressions.
8. **Write new tests** — cover the specific fix or feature.
9. **Edge cases** — boundary values, empty inputs, error paths.
10. **Linting / type-checking** — run the project's linter and type checker.

---

## Example Invocations

### Debugging

```python
cerribro = CerribroAgent(mode="coding_assistant")

params = {
    "description": "Function raises KeyError when the input dict is missing the 'name' key",
    "code": "def greet(user): return f\"Hello, {user['name']}\"",
    "language": "python",
    "error_message": "KeyError: 'name'",
    "expected_behavior": "Return a friendly fallback when 'name' is absent",
}

reasoning = cerribro.think(params)
result    = cerribro.act(reasoning)
print(result)
```

### Refactoring

```python
params = {
    "description": "Refactor the authentication module to use dependency injection",
    "language": "python",
    "framework": "Django REST Framework",
    "context": "Current implementation uses module-level globals for the JWT secret",
}

reasoning = cerribro.think(params)
result    = cerribro.act(reasoning)
print(result)
```

### Test generation

```python
params = {
    "description": "Generate pytest tests for the calculate_discount function",
    "code": (
        "def calculate_discount(price: float, pct: float) -> float:\n"
        "    if not 0 <= pct <= 100:\n"
        "        raise ValueError('pct must be 0–100')\n"
        "    return round(price * (1 - pct / 100), 2)\n"
    ),
    "language": "python",
    "test_framework": "pytest",
}

reasoning = cerribro.think(params)
result    = cerribro.act(reasoning)
print(result)
```

