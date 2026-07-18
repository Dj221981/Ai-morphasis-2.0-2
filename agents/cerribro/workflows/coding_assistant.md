# Workflow: `coding_assistant`

Use this workflow when Cerribro is in `coding_assistant` mode (the default). It covers
understanding a problem through to a tested, documented solution.

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

## Planning Steps

1. **Understand context**
   - Read the provided code, error, and description carefully.
   - Identify the language, framework, and relevant patterns in use.
   - Ask for clarification if the problem statement is unclear.

2. **Identify the problem**
   - Pinpoint the root cause (logic error, off-by-one, missing null-check, etc.).
   - Distinguish between symptoms and root causes.
   - Check for related issues that should be addressed at the same time.

3. **Propose a minimal fix**
   - Describe the change in one sentence before writing code.
   - Confirm the approach with the user if the fix is non-trivial.

---

## Implementation Steps

4. **Apply the change**
   - Make the smallest correct change.
   - Add or update comments where the logic is non-obvious.
   - Preserve existing code style and conventions.

5. **Check for side effects**
   - Review callers of any modified function or module.
   - Confirm that interfaces remain backward-compatible unless a break is intentional.

6. **Update documentation** (if needed)
   - Update docstrings, README sections, or API docs that reference changed behaviour.

---

## Validation / Testing Steps

7. **Run existing tests** — confirm no regressions.
8. **Write new tests** — cover the specific bug fixed or feature added.
9. **Edge cases** — test boundary values, empty inputs, and error paths.
10. **Linting / type-checking** — run the project's linter and type checker.

---

## Output Format

```json
{
  "status": "completed",
  "mode": "coding_assistant",
  "confidence": 0.95,
  "output": {
    "workflow": "coding_assistant",
    "steps_planned": ["understand_context", "identify_problem", "..."],
    "steps_completed": [],
    "notes": "Plan produced. Steps are ready for iterative execution."
  }
}
```

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
