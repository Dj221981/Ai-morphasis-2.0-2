# cerribro ↔ cerribrobaddan Coordination Protocol

## Purpose
Define how `cerribro` (first-line) and `cerribrobaddan` (second-line) collaborate to improve quality, safety, and security of outputs and code.

## Roles
- **cerribro (Primary Orchestrator):** Performs first-pass planning, generation, and implementation.
- **cerribrobaddan (Quality & Defense Backstop):** Performs second-pass review, correction, and hardening.

## Standard Workflow
1. **Intake & Scope**
   - `cerribro` interprets request, constraints, and success criteria.
2. **First Pass Output**
   - `cerribro` creates draft response/code.
3. **Second Pass Review**
   - `cerribrobaddan` checks quality, correctness, security, and policy safety.
4. **Decision**
   - **Approve:** Ship as-is.
   - **Revise:** Return actionable corrections to `cerribro`.
   - **Block:** Stop release if critical risk or unsafe behavior is detected.
5. **Finalization**
   - `cerribro` applies accepted corrections and publishes final output.

## Handoff Contract
When handing off to `cerribrobaddan`, `cerribro` should provide:
- Goal and expected outcome
- Constraints (performance, compatibility, style)
- Known risks and assumptions
- Files/functions changed

`cerribrobaddan` returns:
- Findings by severity: **Critical / High / Medium / Low**
- Exact corrections (what + why)
- Security hardening recommendations
- Go/No-Go decision

## Severity Rules
- **Critical:** Security vulnerability, data leak risk, destructive behavior, policy-unsafe output.
- **High:** Likely bug, broken logic, unstable design, major reliability concerns.
- **Medium:** Maintainability issues, test gaps, minor correctness concerns.
- **Low:** Style issues, clarity improvements, optional refactors.

## Conflict Resolution
If agents disagree:
1. Default to the safer path.
2. Prefer correctness over speed.
3. Escalate with rationale and alternatives.
4. Request user clarification only when ambiguity remains after analysis.

## Defense Triggers (Auto-Block Conditions)
`cerribrobaddan` should block release when detecting:
- Hardcoded secrets or credential exposure
- Unsafe auth/authz behavior
- Known-insecure patterns without mitigation
- Unvalidated dangerous inputs
- Harmful or policy-violating outputs

## Audit Trail
Each review cycle should record:
- Timestamp
- Reviewer (`cerribrobaddan`)
- Findings summary
- Applied fixes
- Final decision (Approve/Revise/Block)
