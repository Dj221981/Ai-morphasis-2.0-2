# Workflow: `app_builder`

Use this workflow when Cerribro is in `app_builder` mode. It covers the full lifecycle from
requirements gathering through to a production-ready first increment.

---

## Inputs Expected

| Input field         | Required | Description                                              |
|---------------------|----------|----------------------------------------------------------|
| `description`       | Yes      | One-paragraph summary of what the app should do          |
| `platform`          | Yes      | Target platform(s): web, mobile, desktop, CLI, API       |
| `stack`             | No       | Preferred language, framework, or tech stack             |
| `auth_required`     | No       | Whether authentication/authorisation is needed           |
| `data_storage`      | No       | Database preference (SQL, NoSQL, file-based, none)       |
| `existing_code`     | No       | Snippet or repo URL of any existing code to build on     |
| `constraints`       | No       | Performance, licensing, accessibility, or other limits   |

**Minimum viable input:** `description` + `platform`.

---

## Planning Steps

1. **Requirements clarification**
   - Confirm functional requirements (what the app must do).
   - Identify non-functional requirements (performance, security, accessibility).
   - Surface any missing inputs by asking the user.

2. **Architecture decision**
   - Choose an architectural style (monolith, microservices, serverless, etc.).
   - Justify the choice against the stated requirements.
   - Identify major components (API layer, frontend, database, auth, background jobs).

3. **Tech-stack selection** (if not specified)
   - Propose a stack grounded in stable, well-supported technologies.
   - List alternatives with trade-offs.
   - Confirm with the user before proceeding.

4. **Project structure design**
   - Produce a directory/module layout.
   - Define naming conventions and module boundaries.

---

## Implementation Steps

5. **Scaffold the project**
   - Generate the folder structure and boilerplate files.
   - Set up dependency management (e.g., `pyproject.toml`, `package.json`).
   - Add a `.gitignore` appropriate to the stack.

6. **Implement core features** (one at a time)
   - Build the smallest slice of each feature end-to-end.
   - Use feature flags or stubs for work not yet started.

7. **Wire up configuration and environment**
   - Externalise secrets and config (environment variables, config files).
   - Document all required environment variables in a `.env.example`.

8. **Add authentication / authorisation** (if required)
   - Use a proven library; do not roll custom auth.
   - Follow OWASP secure coding guidelines.

---

## Validation / Testing Steps

9. **Unit tests** — cover all non-trivial business logic.
10. **Integration tests** — verify component interactions (API ↔ database, etc.).
11. **Smoke test** — confirm the app starts and serves a health-check endpoint.
12. **Security review** — check for injection, CSRF, open redirects, dependency CVEs.

---

## Output Format

```json
{
  "status": "completed",
  "mode": "app_builder",
  "confidence": 0.91,
  "output": {
    "workflow": "app_builder",
    "steps_planned": ["clarify_requirements", "choose_architecture", "..."],
    "steps_completed": ["clarify_requirements"],
    "notes": "Architecture proposed; awaiting user confirmation before scaffolding."
  }
}
```

---

## Example Invocation

```python
cerribro = CerribroAgent(mode="app_builder")

params = {
    "description": "A task-management REST API with user accounts and JWT auth",
    "platform": "API",
    "stack": "FastAPI + PostgreSQL",
    "auth_required": True,
    "data_storage": "PostgreSQL",
}

reasoning = cerribro.think(params)
result    = cerribro.act(reasoning)
print(result)
```
