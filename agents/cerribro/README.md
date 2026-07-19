# Cerribro — Specialist Agentic AI (v2.0)

Cerribro is a specialist agent built on top of the Ai-morphasis 2.0 agent framework.  
It is designed to be a reliable, grounded co-pilot for developers who need help with:

- **Application building** — scaffold, architect, and iterate on full-stack or standalone apps.
- **Game development** — engine-agnostic design, game-loop guidance, and mechanic implementation.
- **Coding assistance** — debug, refactor, write tests, and document code.

All responses are grounded in verifiable knowledge. Cerribro will never fabricate API names,
library versions, or citations. See [`grounding_policy.md`](grounding_policy.md) for full details.

**v2.0 adds three deep upgrade layers** — Deep Intelligence, Deep Research, and a
DeepMind-style execution loop — that can be toggled independently without changing the
base grounding behaviour. See [Deep Upgrade Layers](#deep-upgrade-layers) below.


---

## Quick Start

```python
from src.agents.super_agentic_agents import CerribroAgent, AgentFactory

# Option 1 — direct instantiation (standard mode)
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

print(result["status"])           # "completed"
print(result["confidence"])       # e.g. 0.87
print(result["confidence_band"])  # "High" / "Medium" / "Low" / "Uncertain"
print(result["output"])           # structured execution summary
print(result["facts"])            # verified claims
print(result["assumptions"])      # unconfirmed premises
print(result["proposals"])        # recommendations requiring a decision
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

## Grounding Guarantees

Cerribro enforces a strict evidence-first policy on every response:

| Flag                          | Default | Meaning                                       |
|-------------------------------|---------|-----------------------------------------------|
| `retrieval_first`             | `true`  | Prefer retrieved/verified facts over inference |
| `fabrication_allowed`         | `false` | Never invent API names, library versions, etc. |
| `confidence_signalling`       | `true`  | Every response includes a `confidence` score   |
| `source_attribution`          | `true`  | Cite sources where applicable                  |
| `clarification_on_ambiguity`  | `true`  | Ask before guessing on under-specified requests |
| `unsafe_request_rejection`    | `true`  | Reject malicious or harmful requests with a safe alternative |
| `minimal_viable_change`       | `true`  | Default to the smallest safe change            |
| `test_alongside`              | `true`  | Recommend or generate tests with code changes  |

These flags are also present in [`agent_config.json`](agent_config.json) for programmatic access.

---

## Deep Upgrade Layers

Three optional deep layers add rigour, traceability, and evidence to Cerribro's responses.
Each layer is **disabled by default** and can be toggled independently.

### A — Deep Intelligence (`strict_planning`)

Adds structured reasoning before every response:
- Problem decomposition into subproblems with explicit deliverables.
- Assumptions log with confidence levels and verification status.
- Decision log — why approach A was chosen over B.
- Branching strategy with fallback plans.
- Aggregate confidence scoring; pauses if below threshold.

**Enable in code:**
```python
cerribro.enable_deep_mode("strict_planning")
# or at init:
cerribro = CerribroAgent(deep_mode_config={"strict_planning": {"enabled": True}})
```

**Enable in config** (`agent_config.json`):
```json
"deep_modes": { "strict_planning": { "enabled": true } }
```

**Output adds:**
```python
result["deep_intelligence"]  # subproblems, assumptions, decisions, branches
```

See [`intelligence_framework.md`](intelligence_framework.md) for the full specification.

---

### B — Deep Research (`deep_research`)

Adds an evidence-gathering pipeline before any factual claim enters a response:
- Research question formulation from the user request.
- Multi-source evidence gathering with quality tier ranking.
- Contradiction detection and resolution across sources.
- Freshness warnings for time-sensitive claims.
- Minimum evidence thresholds by task complexity.
- Anti-hallucination constraints: no unsupported factual claims.

**Enable:**
```python
cerribro.enable_deep_mode("deep_research")
```

**Output adds:**
```python
result["evidence_bundle"]  # research_questions, evidence_records, contradictions,
                           # evidence_map, synthesis_confidence
```

See [`deep_research.md`](deep_research.md) and [`evidence_schema.json`](evidence_schema.json).

---

### C — DeepMind Loop (`deepmind_loop`)

Adds an iterative hypothesis/experiment/evaluation cycle:
1. Define hypothesis + success criteria (falsifiable).
2. Design minimal experiment.
3. Execute or simulate; record results.
4. Evaluate against metrics.
5. Record learnings.
6. Iterate or finalise.

Per-mode metrics, stop conditions, and escalation criteria are documented in
[`deepmind_loop.md`](deepmind_loop.md).

**Enable:**
```python
cerribro.enable_deep_mode("deepmind_loop")
```

**Output adds:**
```python
result["deepmind_loop"]  # rounds, final_verdict, final_confidence, escalated
```

---

### Enabling All Three at Once

```python
cerribro = CerribroAgent(
    name="Cerribro-Deep",
    mode="coding_assistant",
    deep_mode_config={
        "strict_planning": {"enabled": True},
        "deep_research":   {"enabled": True},
        "deepmind_loop":   {"enabled": True},
    },
)
```

---

## Output Format (with deep layers)

```json
{
  "status": "completed",
  "mode": "coding_assistant",
  "confidence": 0.91,
  "confidence_band": "High",
  "output": { "workflow": "...", "steps_planned": [...], "steps_completed": [...] },
  "facts":       ["[FACT] Python dict.get() returns None for missing keys (EV-01)."],
  "assumptions": ["[ASSUMPTION] Tests use pytest (A-01, unverified)."],
  "proposals":   ["[PROPOSAL] Use .get('name', 'User') to handle missing key (DEC-01)."],
  "speculative": [],
  "deep_intelligence": { "subproblems": [], "assumptions": [], "decisions": [] },
  "evidence_bundle":   { "evidence_records": [], "synthesis_confidence": null },
  "deepmind_loop":     { "rounds": [], "final_verdict": null }
}
```

When confidence is below `0.55`, a `unknowns_and_next_steps` field is added.

---

## Workflow Templates

Each workflow now includes the five deep-upgrade stages:
**Intelligence Plan → Research Plan → Experimentation Loop → Validation Gate → Grounded Output.**

- [`workflows/app_builder.md`](workflows/app_builder.md)
- [`workflows/game_builder.md`](workflows/game_builder.md)
- [`workflows/coding_assistant.md`](workflows/coding_assistant.md)
- [`workflows/autonomous.md`](workflows/autonomous.md)
- [`workflows/software_maker.md`](workflows/software_maker.md)

---

## Configuration

[`agent_config.json`](agent_config.json) contains all tunable parameters:

```jsonc
{
  "grounding":  { ... },    // evidence and safety flags
  "capabilities": { ... },  // confidence thresholds per capability
  "deep_modes": {           // deep upgrade layer toggles
    "strict_planning": { "enabled": false, ... },
    "deep_research":   { "enabled": false, ... },
    "deepmind_loop":   { "enabled": false, ... },
    "governance":      { ... }
  }
}
```

---

## System Prompt

The full identity and instruction set for Cerribro is in [`system_prompt.md`](system_prompt.md).
When integrating Cerribro with an LLM backend, pass that file's content as the system message.
The system prompt now includes instructions for all three deep modes and governance tags.

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

## Governance and Safety

Every Cerribro response in deep mode separates content into labelled categories:

| Tag           | Meaning                                         |
|---------------|-------------------------------------------------|
| `[FACT]`      | Verified, evidence-backed statement             |
| `[ASSUMPTION]`| Unconfirmed premise                             |
| `[PROPOSAL]`  | Recommendation requiring a decision             |
| `[SPECULATIVE]`| Extrapolated or uncertain; user should verify  |

Unsafe requests are rejected with a `safe_alternative` suggestion. Code changes require
test evidence. Low-confidence responses include an **Unknowns and Next Steps** section.

See [`grounding_policy.md`](grounding_policy.md) for the full governance rules.

---

## See Also

- [`intelligence_framework.md`](intelligence_framework.md) — Deep Intelligence Layer
- [`deep_research.md`](deep_research.md) — Deep Research Layer
- [`evidence_schema.json`](evidence_schema.json) — Evidence bundle JSON schema
- [`deepmind_loop.md`](deepmind_loop.md) — DeepMind-style execution loop
- [`grounding_policy.md`](grounding_policy.md) — detailed grounding and governance rules
- [`system_prompt.md`](system_prompt.md) — LLM system prompt
- [`agent_config.json`](agent_config.json) — full config reference
- [`docs/API.md`](../../docs/API.md) — framework API reference

