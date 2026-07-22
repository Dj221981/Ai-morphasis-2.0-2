# QC + Cybersecurity Checklist (cerribrobaddan)

Use this checklist during second-pass review before final release.

## A) Quality Control
- [ ] Requirements are fully addressed.
- [ ] Output/code is internally consistent.
- [ ] Logic is correct and edge cases are considered.
- [ ] No contradictory statements or duplicated intent.
- [ ] Naming and structure are clear and maintainable.
- [ ] Error handling is present and meaningful.
- [ ] Tests or validation steps are defined (when applicable).

## B) Bad Code Detection & Cleanup
- [ ] Remove dead code / unreachable branches.
- [ ] Remove obvious anti-patterns and brittle hacks.
- [ ] Replace duplicated logic with reusable components.
- [ ] Eliminate magic values where constants/config are better.
- [ ] Improve readability (small functions, clear naming, comments where needed).
- [ ] Verify refactors do not change expected behavior.

## C) Security Checks
- [ ] No secrets/tokens/keys in code or logs.
- [ ] Input validation exists for external/user input.
- [ ] Authentication and authorization checks are enforced.
- [ ] Output encoding/sanitization considered where relevant.
- [ ] Dependencies are reasonable and not obviously risky/outdated.
- [ ] Secure defaults used (least privilege, safe fallbacks).
- [ ] Sensitive data handling minimizes exposure.

## D) Defensive Review
- [ ] No harmful/policy-unsafe behavior in responses.
- [ ] High-risk actions require explicit confirmation/guardrails.
- [ ] Ambiguous risky instructions are clarified or refused safely.

## E) Release Decision
- [ ] **APPROVE**: No Critical/High issues remain.
- [ ] **REVISE**: Medium/Low fixes required before release.
- [ ] **BLOCK**: Any Critical issue present.

## Findings Template
- **Severity:** Critical | High | Medium | Low
- **Location:** file/function/section
- **Issue:** what is wrong
- **Risk:** why it matters
- **Fix:** exact recommended correction
