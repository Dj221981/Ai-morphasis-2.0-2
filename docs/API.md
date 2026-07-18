# API Reference

## Core Modules

### `ai.agents.BaseAgent`

Base class for all adaptive agents in the system.

#### Methods

**`__init__(name: str, agent_type: str = "base")`**
- Initialize a new agent
- Parameters:
  - `name`: Unique identifier for the agent
  - `agent_type`: Type of agent (default: "base")

**`execute_action(action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`**
- Execute an action in the environment
- Parameters:
  - `action`: Name of the action to execute
  - `params`: Optional parameters for the action
- Returns: Dictionary with action result

**`learn(experience: Dict[str, Any]) -> None`**
- Process experience and update knowledge
- Parameters:
  - `experience`: Dictionary containing experience data

**`get_state() -> Dict[str, Any]`**
- Get current agent state
- Returns: State dictionary

**`reset() -> None`**
- Reset agent to initial state

#### Properties

- `name`: Get agent name
- `agent_id`: Get unique agent ID

#### Example

```python
from ai.agents import BaseAgent

# Create an agent
agent = BaseAgent(name="MyAgent")

# Execute an action
result = agent.execute_action("move", {"direction": "north", "distance": 10})

# Learn from experience
agent.learn({"observation": "wall_detected", "reward": -1})

# Get current state
state = agent.get_state()

# Reset agent
agent.reset()
```

## Configuration

### `config.Settings`

Application-wide settings using Pydantic.

#### Configuration Options

```python
# App Info
app_name: str = "Ai-morphasis"
version: str = "2.0.2"
debug: bool = False

# Agent Configuration
max_agents: int = 100
agent_memory_size: int = 10000

# Game Configuration
game_width: int = 1280
game_height: int = 720
target_fps: int = 60

# Model Configuration
model_device: str = "cpu"  # cpu or cuda
batch_size: int = 32
learning_rate: float = 0.001

# Logging
log_level: str = "INFO"
log_file: Optional[str] = "logs/ai_morphasis.log"
```

#### Usage

```python
from config import Settings

config = Settings()
print(f"Running {config.app_name} v{config.version}")
print(f"Using device: {config.model_device}")
```

### `src.agents.CerribroAgent`

Specialist agentic AI for application building, game development, and coding assistance.
Extends `BaseAgent` with mode-based workflows and an enforced grounding policy.

#### Constructor

**`__init__(name: str = "Cerribro", mode: str = "coding_assistant")`**
- `name` — display name for this agent instance.
- `mode` — one of `"coding_assistant"` (default), `"app_builder"`, or `"game_builder"`.
- Raises `ValueError` if `mode` is not one of the valid options.

#### Key Methods

**`think(input_data: Any) -> Dict[str, Any]`**
- Reason about the request and produce a structured plan.
- Applies safety gate (rejects unsafe requests), ambiguity gate (requests clarification),
  and confidence assessment before building a mode-specific plan.
- Returns a dict with `decision`, `workflow`, `steps`, `confidence`, `grounding_flags`, `mode`.

**`act(decision: Dict[str, Any]) -> Any`**
- Execute or relay the plan produced by `think()`.
- Returns a result dict with `status`, `mode`, `confidence`, and `output`.

**`set_mode(mode: str) -> None`**
- Switch the operating mode at runtime. Raises `ValueError` for invalid modes.

#### Grounding Flags

Available via `cerribro.grounding_flags`:

| Flag                         | Default | Meaning                                        |
|------------------------------|---------|------------------------------------------------|
| `retrieval_first`            | `True`  | Prefer verified facts over inference           |
| `fabrication_allowed`        | `False` | Never invent APIs, versions, or citations      |
| `confidence_signalling`      | `True`  | Every response includes a confidence score     |
| `source_attribution`         | `True`  | Cite sources where applicable                  |
| `clarification_on_ambiguity` | `True`  | Ask before guessing on under-specified inputs  |
| `unsafe_request_rejection`   | `True`  | Reject malicious or harmful requests           |
| `minimal_viable_change`      | `True`  | Default to the smallest safe change            |
| `test_alongside`             | `True`  | Recommend or generate tests with code changes  |

#### Example

```python
from src.agents.super_agentic_agents import CerribroAgent, AgentFactory

# Direct instantiation
cerribro = CerribroAgent(name="Cerribro", mode="coding_assistant")

# Via factory
cerribro = AgentFactory.create_agent("cerribro", "Cerribro")

# Submit a coding task
params = {
    "description": "Refactor the authentication module to use dependency injection",
    "language": "python",
    "framework": "Django REST Framework",
}
reasoning = cerribro.think(params)
result    = cerribro.act(reasoning)
print(result["status"])     # "completed"
print(result["confidence"]) # float in [0, 1]

# Switch mode
cerribro.set_mode("app_builder")
```

For full documentation see [`agents/cerribro/README.md`](../agents/cerribro/README.md).

---

## Testing

### Fixtures

All pytest fixtures are defined in `tests/conftest.py`:

- `sample_agent`: Pre-configured test agent
- `test_config`: Test configuration

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_base_agent.py -v

# Run specific test
pytest tests/test_base_agent.py::TestBaseAgentInitialization::test_agent_creation -v

# Run with markers
pytest tests/ -m "unit"
```

## Logging

The application uses `loguru` for logging:

```python
from loguru import logger

logger.info("Information message")
logger.debug("Debug message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
```

Logs are written to:
- Console (stdout)
- File: `logs/ai_morphasis.log` (with rotation)

---

**For more information, see:**
- [Architecture Guide](ARCHITECTURE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [README](README.md)
