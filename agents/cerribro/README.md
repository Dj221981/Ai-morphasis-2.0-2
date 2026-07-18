# Cerribro Agent Profile

Cerribro is configured with a base profile plus optional deep-upgrade layers and a coding-tools workflow.

## Deep upgrade layers

- `strict_planning`
- `deep_research`
- `deepmind_loop`

These remain optional and can be toggled in `agents/cerribro/agent_config.json`.

## Coding tools integration

When Cerribro receives concrete code tasks, it follows the coding-tools profile in:

- `agents/cerribro/coding_tools.md`

### Auto-activation behavior

- `coding_assistant`: coding tools are always active.
- `app_builder` / `game_builder`: coding tools activate only when concrete code changes are requested.
- Conceptual-only requests avoid unnecessary tool execution, but can still include tool-backed validation on request.

### Verification expectations

Cerribro should provide evidence for coding claims with available checks (lint, type checks, tests, or execution logs), and clearly mark assumptions as unverified when execution is not possible.

## Customization

Update `agents/cerribro/agent_config.json` to customize:

- activation rules
- tool category expectations
- pipeline and required artifacts
- guardrails and output contract

## Examples

- **Debugging:** inspect failing path, apply minimal fix, run targeted tests, report evidence.
- **Feature build:** inspect existing module boundaries, add focused changes, run quality gates, summarize risk.
- **Refactor:** allow only scoped refactors unless explicitly requested for larger structural changes.
