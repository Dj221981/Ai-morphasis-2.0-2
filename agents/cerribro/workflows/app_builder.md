# Workflow: `app_builder`

Use this workflow when Cerribro is in `app_builder` mode. It covers the full lifecycle from
requirements gathering through to a production-ready first increment.

Each workflow now incorporates the five deep-upgrade stages:
**Intelligence Plan → Research Plan → Experimentation Loop → Validation Gate → Grounded Output.**

Enable each stage individually in [`agent_config.json`](../agent_config.json) under `deep_modes`.

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

## Stage 1 — Intelligence Plan

*(Active when `deep_modes.strict_planning.enabled: true`)*

1. **Decompose** the app into subproblems (auth, data layer, API, frontend, infra …).
   Each subproblem gets a scope, input/output, and complexity estimate.
2. **Log assumptions** — record every assumption made before requirements are
   confirmed (e.g., "Python ≥ 3.11 available", "PostgreSQL is acceptable").
3. **Decide and document** the architectural style; log DEC-01 with options
   considered and rationale.
4. **Define branches** — primary path (happy path) and at least one fallback
   (e.g., if chosen framework has a known CVE, fallback to alternative).
5. **Score confidence** — calculate aggregate confidence; pause if below 0.75.

*Output:* `deep_intelligence` block attached to the plan. See
[`intelligence_framework.md`](../intelligence_framework.md).

---

## Stage 2 — Research Plan

*(Active when `deep_modes.deep_research.enabled: true`)*

1. **Identify claims** in the architecture plan that require verified evidence
   (e.g., library support matrix, OWASP compliance patterns, performance benchmarks).
2. **Formulate research questions** (e.g., RQ-01: "Does FastAPI support async
   background tasks natively?").
3. **Gather evidence** — minimum 2 records for medium-complexity claims,
   3 for complex claims.
4. **Rank and synthesise** — discard Tier 3+ sources; resolve contradictions.
5. **Attach Evidence Bundle** — include before proceeding to implementation.
6. **Gate**: if `synthesis_confidence < 0.55`, emit Insufficient Evidence response.

*Output:* `evidence_bundle` block. See [`deep_research.md`](../deep_research.md)
and [`evidence_schema.json`](../evidence_schema.json).

---

## Stage 3 — Experimentation Loop (Planning Phase)

*(Active when `deep_modes.deepmind_loop.enabled: true`)*

Apply the DeepMind loop to the architecture/stack decisions:

| Round | Hypothesis                                                | Metrics                          | Stop condition                       |
|-------|-----------------------------------------------------------|----------------------------------|--------------------------------------|
| R1    | Proposed stack covers all stated requirements             | Requirements coverage %          | 100 % or user-accepted trade-off     |
| R2    | Architecture has no circular dependencies                 | Dependency graph is a DAG        | Graph validated                      |
| R3    | Security baseline is in place                            | OWASP checks pass                | All critical checks pass             |

**Escalation criteria** (stop and ask user):
- Conflicting requirements cannot be reconciled after 2 rounds.
- Tech stack choice has two near-equal options and user preference is unknown.
- A required dependency has a published security advisory.

*Output:* `deepmind_loop` block. See [`deepmind_loop.md`](../deepmind_loop.md).

---

## Stage 4 — Validation and Verification Gate

Before proceeding to final output, all of the following must pass:

- [ ] All subproblems from Stage 1 have planned implementations
- [ ] All high-confidence assumptions verified (or flagged to user)
- [ ] Evidence Bundle attached (if deep_research enabled)
- [ ] Architecture validated (no circular deps, security baseline)
- [ ] Aggregate confidence ≥ 0.75 (or user explicitly accepts lower confidence)
- [ ] Unit and integration test coverage planned for all non-trivial logic
- [ ] Security review checklist completed (injection, CSRF, CVE scan intent noted)

---

## Stage 5 — Final Grounded Output Format

```json
{
  "status": "completed",
  "mode": "app_builder",
  "confidence": 0.91,
  "confidence_band": "High",
  "output": {
    "workflow": "app_builder",
    "steps_planned": ["clarify_requirements", "choose_architecture", "..."],
    "steps_completed": ["clarify_requirements"],
    "notes": "Architecture proposed; awaiting user confirmation before scaffolding."
  },
  "facts": ["FastAPI supports async background tasks natively (EV-01)."],
  "assumptions": ["Python ≥ 3.11 available on target system (A-01, unverified)."],
  "proposals": ["Use JWT for auth via python-jose library (DEC-01)."],
  "speculative": [],
  "unknowns_and_next_steps": [],
  "deep_intelligence": { "..." : "..." },
  "evidence_bundle": { "..." : "..." },
  "deepmind_loop": { "..." : "..." }
}
```

**Governance tags in every response:**
- `facts` — verified, evidence-backed statements.
- `assumptions` — stated premises that have not been externally confirmed.
- `proposals` — recommendations that require a decision.
- `speculative` — marked with `[SPECULATIVE]`; user should verify.
- `unknowns_and_next_steps` — populated when confidence < 0.55.

---

## Legacy Planning Steps (Standard Mode)

When `strict_planning` is disabled, the original planning steps apply:

1. **Requirements clarification** — confirm functional and non-functional requirements.
2. **Architecture decision** — choose style, justify, identify components.
3. **Tech-stack selection** — propose grounded stack; confirm with user.
4. **Project structure design** — directory layout and naming conventions.
5. **Scaffold the project** — folder structure, dependency management, `.gitignore`.
6. **Implement core features** — smallest slice per feature.
7. **Wire up config and environment** — externalise secrets.
8. **Add auth/authorisation** (if required) — use proven library, follow OWASP.
9. **Unit tests** — cover all non-trivial business logic.
10. **Integration tests** — verify component interactions.
11. **Smoke test** — health-check endpoint.
12. **Security review** — injection, CSRF, open redirects, dependency CVEs.

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

