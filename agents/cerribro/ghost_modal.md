# Ghost Modal: Adaptive AI + Cybersecurity Toolbox

## Purpose
The **Ghost Modal** is a mode controller that lets AI agents operate with two toolboxes:

1. **AI Toolbox (Normal Mode)** for routine operations.
2. **Cybersecurity Toolbox (Security Mode)** for defensive actions when threat signals are detected.

It is designed to be reused by both `cerribro` and `cerribrobaddan`.

## Key Behavior
- Computes a threat score from input text + optional context.
- Switches to `security` mode when score >= threshold.
- Keeps an audit trail of mode evaluations and escalations.
- Routes tool execution based on active mode.

## Included Tools

### Normal mode (default)
- `summarize`
- `plan`
- `refactor_hint`

### Security mode (on threat)
- `threat_scan`
- `ioc_extract`
- `incident_note`

## Integrating with Agents

### 1) Create one modal per agent

```python
from agents.cerribro.ghost_modal import GhostModal

ghost = GhostModal(agent_name="cerribro")
```

### 2) Evaluate incoming requests

```python
state = ghost.evaluate(
    text=user_prompt,
    context={"source": "chat", "stage": "first_pass"},
)
```

### 3) Execute tools through the modal

```python
result = ghost.execute("summarize", user_prompt)
```

If threat conditions are met, the same call will be restricted to security-allowed tools.

### 4) Optional shared use across both agents

- `cerribro`: first-pass orchestration with threat-aware routing
- `cerribrobaddan`: second-pass defense review using the same security mode

## Threat Rules (default)
Threat points are assigned for risky indicators in text:
- malware, exploit, zero-day, ransomware
- credential, token, secret, api key
- exfiltration, privilege escalation, backdoor
- sql injection, xss, command injection

Score behavior:
- **< threshold:** `normal`
- **>= threshold:** `security`

Defaults can be tuned in `agents/cerribro/agent_config.json` under `ghost_modal`.
