# Auto-Review Rubric (Bad Code Detection & Cleanup)

Score each category from **0 to 5**. Target overall score: **≥ 22/30** with no category below **3**.

## 1) Correctness (0–5)
- **5:** Behavior is correct across normal and edge cases.
- **3:** Mostly correct, minor edge-case concerns.
- **1:** Frequent logic errors or unhandled cases.
- **0:** Fundamentally broken.

## 2) Reliability & Error Handling (0–5)
- **5:** Robust failures, clear errors, safe recovery paths.
- **3:** Basic handling present but incomplete.
- **1:** Fragile behavior under failure.
- **0:** No meaningful handling.

## 3) Maintainability & Clarity (0–5)
- **5:** Clear structure, readable naming, low complexity.
- **3:** Understandable with moderate complexity/debt.
- **1:** Hard to follow; high coupling/duplication.
- **0:** Unmaintainable.

## 4) Security Posture (0–5)
- **5:** Strong controls, validated input, safe defaults, no secret exposure.
- **3:** Acceptable baseline with minor hardening needed.
- **1:** Multiple risky patterns.
- **0:** Critical vulnerabilities likely.

## 5) Code Hygiene (0–5)
- **5:** No dead code, minimal duplication, no obvious anti-patterns.
- **3:** Some cleanup needed.
- **1:** Significant bloat or poor practices.
- **0:** Very poor hygiene.

## 6) Standards & Policy Safety (0–5)
- **5:** Fully aligned with project conventions and safety expectations.
- **3:** Mostly aligned; small deviations.
- **1:** Frequent non-compliance.
- **0:** Unsafe or non-compliant.

---

## Decision Rules
- **APPROVE** if:
  - Total score ≥ 22, and
  - No category below 3, and
  - No Critical findings.

- **REVISE** if:
  - Total score 16–21, or
  - Any category is 2, and
  - No Critical findings.

- **BLOCK** if:
  - Total score ≤ 15, or
  - Any category is 0–1, or
  - Any Critical finding exists.

## Required Output Format for Reviews
1. Category scores (1–6)
2. Total score
3. Severity-ranked findings
4. Exact remediation steps
5. Final decision: APPROVE / REVISE / BLOCK
