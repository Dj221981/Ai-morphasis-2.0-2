# AI-Morphasis 2.0 Architecture Guide

## Table of Contents
- [1. System Overview](#1-system-overview)
- [2. Component Architecture](#2-component-architecture)
- [3. Deep Thinking Engine Architecture](#3-deep-thinking-engine-architecture)
- [4. Training Pipeline](#4-training-pipeline)
- [5. Deployment Architecture](#5-deployment-architecture)
- [6. Testing Strategy](#6-testing-strategy)
- [7. Development Workflow](#7-development-workflow)
- [8. Dependencies and Tech Stack](#8-dependencies-and-tech-stack)
- [9. Future Extensions](#9-future-extensions)

---

## 1. System Overview

AI-Morphasis 2.0 is a Python-based AI system focused on adaptive agents, reinforcement learning, and structured reasoning. The current implementation combines three major capabilities:

1. **Agent orchestration and behavior management** using a multi-agent framework in `/src/agents/super_agentic_agents.py`.
2. **Neural learning components** (DQN and policy models) in `/src/models/neural_network.py`.
3. **Deep reasoning tools** in `/Deep thinking`, implemented as reusable reasoning modules.

The architecture is intentionally modular so teams can evolve training logic, reasoning behavior, and deployment independently.

### High-level design goals

- Keep agent behavior and model behavior decoupled.
- Provide production-ready model building blocks (TensorFlow/Keras).
- Support reproducible configuration and environment-driven settings.
- Make extension points explicit for additional agent types, model variants, and reasoning modules.

### High-level component map

```text
+--------------------------- AI-Morphasis 2.0 ---------------------------+
|                                                                         |
|   +--------------------+       +---------------------+                  |
|   | Agent System       |<----->| Learning Models     |                  |
|   | src/agents         |       | src/models          |                  |
|   +--------------------+       +---------------------+                  |
|            ^                               ^                            |
|            |                               |                            |
|   +--------------------+       +---------------------+                  |
|   | Deep Thinking      |       | Data Processing     |                  |
|   | Deep thinking      |       | src/data            |                  |
|   +--------------------+       +---------------------+                  |
|            ^                               ^                            |
|            +----------------+--------------+                            |
|                             |                                           |
|                    +---------------------+                              |
|                    | Config Layer        |                              |
|                    | src/config + .env   |                              |
|                    +---------------------+                              |
+-------------------------------------------------------------------------+
```

### Runtime request/training flow

```text
Input/Task
  -> AgentSystem creates/submits Task
  -> OrchestratorAgent assigns to Executor/Analyzer/Learner
  -> Agent interacts with model (action selection / learning)
  -> Experience captured in ExperienceReplay
  -> train_step updates network weights
  -> Metrics/checkpoints/history persisted
  -> Updated model behavior feeds future tasks
```

---

## 2. Component Architecture

### 2.1 Agent system (`/src/agents/`)

**Primary file:** `/src/agents/super_agentic_agents.py`

This module defines the full agent hierarchy and lifecycle control.

#### Core abstractions

- `BaseAgent`: abstract contract for all agent types.
  - Required methods: `think(input_data)` and `act(decision)`.
  - Built-in capabilities:
    - capability registration (`register_capability`)
    - task assignment and execution (`assign_task`, `execute_task`)
    - memory-backed context and metrics.

- `AgentMemory`: memory model with:
  - `episodic_memory` (short-term events)
  - `semantic_memory` (long-term knowledge)
  - `procedural_memory` (callable skills)

- `Task`: task object with priority, assignment, status, dependencies, result, and metadata.

#### Specialized agent pattern

The architecture follows role-specific classes inheriting from `BaseAgent`:

- `OrchestratorAgent` (coordination, routing)
- `ExecutorAgent` (execution-oriented actions)
- `AnalyzerAgent` (analysis and insight generation)
- `LearnerAgent` (pattern learning and adaptation)

System-level management is handled by:

- `AgentSystem`: lifecycle and routing boundary
- `AgentFactory`: standardized creation and team assembly (`create_agent`, `create_team`)

#### Production responsibility split

- `OrchestratorAgent`: load balancing and distribution policy.
- Execution agents: task throughput and operational work.
- Analyzer agents: interpretation and diagnostics.
- Learner agents: adaptation, memory updates, and pattern evolution.

This split enables scaling by role (for example: many executors, fewer orchestrators).

---

### 2.2 Model layer (`/src/models/`)

**Primary file:** `/src/models/neural_network.py`

This layer provides TensorFlow/Keras models and training primitives.

#### Key classes

- `DQNNetwork(tf.keras.Model)`
  - Dense hidden layers with batch normalization and dropout.
  - Q-value output per action.

- `PolicyNetwork(tf.keras.Model)`
  - Shared trunk.
  - Discrete mode: softmax policy head.
  - Continuous mode: mean + log_std output.
  - Value head for actor-critic style usage.

- `AgentLearningModel`
  - Wraps network(s), optimizer, loss, epsilon-greedy policy, and device strategy.
  - Supports DQN path (`network` + `target_network`) and policy path.
  - Core APIs: `select_action`, `train_step`, `update_target_network`, `save_model`, `load_model`.

- `ExperienceReplay`
  - Fixed-size cyclic buffer.
  - Random batch sampling (`sample`) for de-correlated training.

#### Example usage (from current API surface)

```python
from src.models.neural_network import AgentLearningModel, ExperienceReplay

model = AgentLearningModel(state_size=64, action_size=10, model_type="dqn", device="cpu")
replay = ExperienceReplay(max_size=100000)

action = model.select_action(state_vector, training=True)
replay.add(state_vector, action, reward, next_state_vector, done)

if len(replay) >= 32:
    batch = replay.sample(32)
    loss = model.train_step(*batch)
```

#### Production notes

- Device handling is explicit (`cpu`/`gpu`) and resolved to TensorFlow device scope.
- DQN target network update behavior is encapsulated and test-covered.
- Checkpoint compatibility is based on Keras weight serialization (`save_weights` / `load_weights`).

---

### 2.3 Training layer (`/src/training/`)

The test suite references:

- `TrainingEnvironment`
- `AgentTrainer`
- expected import path: `src.training.train`

These interfaces are validated in `/tests/test_models.py` (`TestTrainingEnvironment`, `TestAgentTrainer`) and represent the intended orchestration contract for production training loops:

- experience collection
- batch training
- episode-based metrics
- checkpoint/history persistence.

**Current architecture intent:** training orchestration should remain separate from raw model definitions, with `AgentLearningModel` acting as the model core and trainer/environment classes acting as runtime orchestration.

---

### 2.4 Config layer (`/src/config/` + `.env`)

**Primary files:**

- `/src/config/model_config.py`
- `/.env.example`

`model_config.py` defines registry-based configurations (for example `dqn_config`, `policy_config`, `large_config`) plus lookup helpers:

- `get_config(config_name)`
- `list_configs()`

`.env.example` captures deployment-level runtime values:

- `MODEL_DEVICE`
- `BATCH_SIZE`
- `LEARNING_RATE`
- `LOG_LEVEL`
- `LOG_FILE`

This split supports both:

- **experiment profiles** (Python config registry), and
- **environment-specific runtime overrides** (env vars in container/host runtime).

---

### 2.5 Data layer (`/src/data/` + `/storage/`)

**Primary code file:** `/src/data/preprocessing.py`

Data-processing components include:

- `StateNormalizer` + `NormalizationStats`
- `DataAugmentation`
- `ExperiencePreprocessor`
- `BatchGenerator`
- utility functions: `split_data`, `create_sliding_window`

Persistence patterns currently include:

- JSON serialization for normalization stats (`save`/`load`)
- training history persistence (validated in tests)
- model checkpoint files (`.h5` style naming in tests)
- filesystem-backed `storage/` path for future expansion.

---

## 3. Deep Thinking Engine Architecture

**Primary file:** `/Deep thinking`

The deep thinking engine is built from five explicit reasoning modules:

1. `ReasoningChain`
2. `SocraticDialogue`
3. `HypothesisEngine` (with `Hypothesis`)
4. `MetaCognition`
5. `AnalogicalMapper`

### Module responsibilities

- `ReasoningChain`: captures sequential reasoning steps and a conclusion.
- `SocraticDialogue`: generates structured self-questioning prompts.
- `HypothesisEngine`: tracks competing hypotheses with confidence updates.
- `MetaCognition`: bias/gap audit and confidence calibration checks.
- `AnalogicalMapper`: cross-domain structural mapping for transfer insight.

### Reasoning pipeline pattern

```text
Problem/Topic
  -> ReasoningChain (step decomposition)
  -> SocraticDialogue (assumption pressure-testing)
  -> HypothesisEngine (candidate explanations + confidence)
  -> MetaCognition (bias and quality audit)
  -> AnalogicalMapper (transferable patterns)
  -> Consolidated insight for agent decision path
```

### Integration points with agent system

Recommended integration between `/Deep thinking` and `/src/agents/super_agentic_agents.py`:

- `AnalyzerAgent.think(...)` can invoke `ReasoningChain` + `HypothesisEngine` for structured diagnostic output.
- `LearnerAgent.learn_from_experience(...)` can add `MetaCognition` checks before committing semantic memory.
- `OrchestratorAgent` can request analogical mappings for strategy transfer between task domains.

This preserves a clean boundary: deep reasoning modules remain framework-agnostic while agents decide when and how to consume them.

---

## 4. Training Pipeline

The core training architecture is reinforcement-learning oriented, anchored in `AgentLearningModel` and `ExperienceReplay`.

### 4.1 End-to-end flow

```text
[1] Environment interaction
    state_t -> action_t -> reward_t, state_t+1, done

[2] Experience collection
    ExperienceReplay.add(state, action, reward, next_state, done)

[3] Batch sampling
    states, actions, rewards, next_states, dones = replay.sample(batch_size)

[4] Learning step
    AgentLearningModel.train_step(...)
      - compute current_q
      - compute target_q via target network
      - compute loss (Huber for DQN)
      - apply gradients via Adam

[5] Stabilization
    AgentLearningModel.update_target_network() periodically

[6] Policy control
    AgentLearningModel.decay_epsilon() for exploration scheduling
```

### 4.2 Model persistence and checkpoints

Existing persistence paths in code/tests:

- `AgentLearningModel.save_model(filepath)`
- `AgentLearningModel.load_model(filepath)`
- trainer checkpoint expectations in tests (e.g., `model_episode_0.h5`)
- history serialization pattern (`save_history` tested via JSON)

### 4.3 Metrics and history tracking

Current metric surfaces include:

- per-step/epoch loss (`self.train_loss`)
- trainer-level episode metrics expected by tests:
  - `reward`
  - `steps`
  - `avg_loss`
  - `epsilon`
- evaluation metrics expected by tests:
  - `mean_reward`, `std_reward`, `max_reward`, `min_reward`

For production, these should be emitted to structured logs and optionally external telemetry.

---

## 5. Deployment Architecture

### 5.1 Current deployment model

The present architecture is **single-process Python runtime** with TensorFlow/Keras execution and in-process memory/state.

Key characteristics:

- One runtime process hosts agents, model inference/training, and reasoning modules.
- Model/data persistence is filesystem-backed.
- Logging is Python logging in core model code and `loguru` in project documentation references.
- CI workflows exist in:
  - `/.github/workflows/django.yml`
  - `/workflows/tests.yml`

### 5.2 Device handling (CPU/GPU)

`AgentLearningModel` resolves runtime device using:

- input `device` parameter (`"cpu"` or `"gpu"`)
- TensorFlow GPU availability check
- explicit `tf.device(...)` training scope

Operational guidance:

- default safely to CPU for deterministic local/CI behavior.
- gate GPU activation behind environment config and runtime capability checks.

### 5.3 Scalability considerations

Current single-process design is strong for prototyping and bounded production workloads. For higher scale:

- separate training workers from inference workers.
- externalize replay buffer or event stream (instead of in-memory list only).
- move checkpoints/history to object storage.
- isolate orchestrator from executor pools.

### 5.4 Logging and monitoring integration points

Recommended immediate instrumentation boundaries:

- Agent lifecycle events (`add_agent`, `submit_task`, task completion/failure)
- Training lifecycle events (batch loss, target updates, checkpoint saves)
- Reasoning engine traces (module usage and confidence changes)

Potential sinks:

- structured JSON logs to stdout/file
- log aggregation platform (ELK/OpenSearch/Cloud logging)
- metrics endpoint (Prometheus/OpenTelemetry)

---

## 6. Testing Strategy

**Primary suite:** `/tests/test_models.py`

### 6.1 Unit organization

The test file is organized by behavior-focused classes:

- `TestDQNNetwork`
- `TestPolicyNetwork`
- `TestAgentLearningModel`
- `TestExperienceReplay`
- `TestTrainingEnvironment`
- `TestAgentTrainer`

Coverage validates:

- model initialization and tensor shape correctness
- action-selection bounds and exploration policy
- gradient training path and target-network synchronization
- replay buffer overflow + sampling behavior
- trainer metrics/checkpoint/history expectations

### 6.2 Integration test patterns

Even within a single file, tests apply integration-style checks by combining:

- environment interactions
- replay collection
- model updates
- checkpoint writing/reading

This gives high confidence in end-to-end RL loop behavior.

### 6.3 Performance and benchmark considerations

`/workflows/tests.yml` contains a dedicated `performance` job with benchmark hooks (`pytest-benchmark`) and optional memory profiling. This supports progressive non-functional validation without coupling benchmark tooling to all local developer flows.

### 6.4 Practical CI caveat

Workflow files expect `requirements.txt` and Python test tooling in CI. Keep dependency manifests aligned with test imports to avoid false CI failures unrelated to core architecture.

---

## 7. Development Workflow

This section describes how to extend architecture safely with minimal coupling.

### 7.1 Add a new agent type

1. Create subclass of `BaseAgent` in `/src/agents/super_agentic_agents.py`.
2. Implement `think(...)` and `act(...)`.
3. Register in `AgentFactory._agent_templates`.
4. Validate via agent lifecycle flows (`AgentSystem.add_agent`, task submission).

Example skeleton:

```python
class PlannerAgent(BaseAgent):
    def __init__(self, name: str = "Planner"):
        super().__init__(name, role=AgentRole.SPECIALIZED)

    def think(self, input_data):
        return {"plan": "generated", "input": input_data}

    def act(self, decision):
        return {"status": "planned", "decision": decision}
```

### 7.2 Extend neural networks

1. Add architecture changes in `DQNNetwork` or `PolicyNetwork`.
2. Keep constructor signatures backward-compatible where possible.
3. Update `AgentLearningModel` wiring if new outputs/losses are introduced.
4. Add shape and training-path tests in `/tests/test_models.py`.

### 7.3 Implement a new reasoning module

1. Add class in `/Deep thinking` with clear single responsibility.
2. Keep method surface composable (similar to `display`, fluent methods).
3. Integrate from agent `think(...)` methods as optional reasoning stage.
4. Add deterministic tests once dedicated deep-thinking tests are introduced.

### 7.4 Extend configuration

1. Add new profile in `/src/config/model_config.py` and register in `CONFIG_REGISTRY`.
2. Add corresponding env knobs in `/.env.example` where runtime tuning is required.
3. Use `get_config(...)` to avoid ad hoc config dictionaries across code paths.

---

## 8. Dependencies and Tech Stack

Current architecture and workflows are centered on:

- **Python 3.8+ runtime** (workflow matrices include multiple versions)
- **TensorFlow/Keras** for neural model definition and training
- **NumPy** for tensor/array preprocessing and replay batching
- **Pytest** for unit/integration test execution
- **Loguru** for production logging strategy (documented API layer)
- **GitHub Actions** for CI (tests, quality checks, performance hooks)

### Minimal runtime dependency groups

- **Core ML runtime:** TensorFlow, NumPy
- **Test/runtime validation:** pytest (+ optional benchmark plugins)
- **Quality/security (CI optional):** flake8, mypy, pylint, bandit

---

## 9. Future Extensions

The current architecture is a strong monolithic baseline. The following roadmap evolves it into distributed production systems.

### 9.1 Distributed training architecture

- shard experience collection across worker processes/nodes
- centralize replay buffer with prioritized sampling
- asynchronous gradient aggregation and checkpoint coordination

### 9.2 Multi-agent coordination patterns

- role-based autoscaling (executor pools)
- explicit inter-agent messaging protocol
- failure isolation and retry queues for task execution

### 9.3 Real-time inference serving

- split online inference service from offline training jobs
- package trained models behind API layer (REST/gRPC)
- introduce model registry + canary deployment path

### 9.4 Storage layer expansion

- move from local filesystem to durable object storage for checkpoints
- store task/audit history in relational or document database
- add feature store or vector memory for long-term semantic retrieval

---

## Production Readiness Summary

Today, AI-Morphasis 2.0 already contains production-grade primitives in modeling, agent abstractions, and reasoning modules. The architecture is modular, test-oriented, and extension-friendly. To complete full production hardening, focus next on:

1. formalizing training orchestration module implementation (`src/training` contract),
2. dependency manifest consistency for CI reproducibility,
3. observability and persistence externalization for scale.

With these additions, the system can transition from strong single-process architecture to robust multi-service production deployment while retaining current class-level design investments.
