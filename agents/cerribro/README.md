# Cerribro — Specialist Agentic AI

Cerribro is a specialist agent built on top of the Ai-morphasis 2.0 agent framework.  
It is designed to be a reliable, grounded co-pilot for developers who need help with:

- **Application building** — scaffold, architect, and iterate on full-stack or standalone apps.
- **Game development** — engine-agnostic design, game-loop guidance, and mechanic implementation.
- **Coding assistance** — debug, refactor, write tests, and document code.

All responses are grounded in verifiable knowledge. Cerribro will never fabricate API names,
library versions, or citations. See [`grounding_policy.md`](grounding_policy.md) for full details.

---

## Quick Start

```python
from src.agents.super_agentic_agents import CerribroAgent, AgentFactory

# Option 1 — direct instantiation
cerribro = CerribroAgent(name="Cerribro", mode="coding_assistant")

# Option 2 — via AgentFactory
cerribro = AgentFactory.create_agent("cerribro", "Cerribro")

# Submit a task
task_params = {
    "description": "Refactor the authentication module to use dependency injection",
    "language": "python",
    "context": "Django REST Framework project",
}
reasoning = cerribro.think(task_params)
result    = cerribro.act(reasoning)

print(result["status"])     # "completed"
print(result["confidence"]) # e.g. 0.87
print(result["output"])     # structured execution summary
```

---

## Operating Modes

| Mode               | Purpose                                          |
|--------------------|--------------------------------------------------|
| `coding_assistant` | Debug, refactor, test, and document code (default) |
| `app_builder`      | Scaffold and architect full applications          |
| `game_builder`     | Engine-agnostic game development guidance         |
| `autonomous`       | Goal-driven autonomous execution with iterative planning and replanning |
| `software_maker`   | End-to-end software product development with OT/industrial builder support |

Switch modes at runtime:

```python
cerribro.set_mode("app_builder")
```

---

## Coding tools integration

Cerribro uses a dedicated coding-tools policy for concrete code work:

- [`coding_tools.md`](coding_tools.md)

### Auto-activation behavior

- `coding_assistant`: coding tools are always active.
- `app_builder` / `game_builder`: coding tools activate only when concrete code changes are requested.
- Conceptual-only requests avoid unnecessary tool execution, but can still include tool-backed validation on request.

### Verification expectations

Cerribro should provide evidence for coding claims with available checks (lint, type checks, tests, or execution logs), and clearly mark assumptions as unverified when execution is not possible.

### Production readiness expectations

- Include a release-readiness checklist in coding task summaries.
- Run dependency vulnerability checks before introducing new dependencies.
- Run secret scanning before commit.
- Treat green CI as a release gate.

---

## Grounding Guarantees

Cerribro enforces a strict evidence-first policy on every response:

| Flag                          | Default | Meaning                                       |
|-------------------------------|---------|-----------------------------------------------|
| `retrieval_first`             | `true`  | Prefer retrieved/verified facts over inference |
| `fabrication_allowed`         | `false` | Never invent API names, library versions, etc. |
| `confidence_signalling`       | `true`  | Every response includes a `confidence` score   |
| `source_attribution`          | `true`  | Cite sources where applicable                  |
| `clarification_on_ambiguity`  | `true`  | Ask before guessing on under-specified requests |
| `unsafe_request_rejection`    | `true`  | Reject malicious or harmful requests           |
| `minimal_viable_change`       | `true`  | Default to the smallest safe change            |
| `test_alongside`              | `true`  | Recommend or generate tests with code changes  |

These flags are also present in [`agent_config.json`](agent_config.json) for programmatic access.

---

## Workflow Templates

- [`workflows/app_builder.md`](workflows/app_builder.md)
- [`workflows/game_builder.md`](workflows/game_builder.md)
- [`workflows/coding_assistant.md`](workflows/coding_assistant.md)
- [`workflows/autonomous.md`](workflows/autonomous.md)
- [`workflows/software_maker.md`](workflows/software_maker.md)

---

## Configuration

[`agent_config.json`](agent_config.json) contains all tunable parameters. The most important
sections are:

```jsonc
{
  "grounding": { ... },   // evidence and safety flags
  "capabilities": { ... }, // confidence thresholds per capability
  "coding_tools": { ... } // coding tools activation and workflow policy
}
```

---

## System Prompt

The full identity and instruction set for Cerribro is in [`system_prompt.md`](system_prompt.md).
When integrating Cerribro with an LLM backend, pass that file's content as the system message.

---

## Integration into Agent System

```python
from src.agents.super_agentic_agents import AgentSystem, CerribroAgent

system   = AgentSystem("MyTeam")
cerribro = CerribroAgent("Cerribro-1", mode="app_builder")
system.add_agent(cerribro)

task = system.create_task(
    description="Scaffold a REST API with authentication",
    parameters={"stack": "FastAPI + PostgreSQL", "auth": "JWT"},
)
system.submit_task(task, cerribro.id)
system.execute_task(task.id, cerribro.id)
```

---

## Extending Cerribro

Register additional capabilities at runtime:

```python
from src.agents.super_agentic_agents import AgentCapability

cerribro.register_capability(AgentCapability(
    name="database_design",
    description="Design relational and document database schemas.",
    confidence_score=0.89,
))
```

---

## See Also

- [`grounding_policy.md`](grounding_policy.md) — detailed grounding rules
- [`system_prompt.md`](system_prompt.md) — LLM system prompt
- [`agent_config.json`](agent_config.json) — full config reference
- [`docs/API.md`](../../docs/API.md) — framework API reference
