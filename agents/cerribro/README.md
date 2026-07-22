# cerribro Agent Kit

This directory contains collaboration and quality-defense artifacts for `cerribro` and `cerribrobaddan`.

## Files

- `cerribrobaddan.md`
  - Identity and mission profile for `cerribrobaddan`.
  - Defines role as second-line quality control, mistake correction, and security backstop.

- `coordination-protocol.md`
  - Defines handoff flow between `cerribro` (first pass) and `cerribrobaddan` (second pass).
  - Includes severity rules, conflict resolution, and auto-block defense triggers.

- `qc-cybersecurity-checklist.md`
  - Practical pre-release checklist for quality, bad code cleanup, defensive review, and cybersecurity checks.

- `auto-review-rubric.md`
  - Scoring rubric (0–5 across 6 categories) for structured review decisions: APPROVE / REVISE / BLOCK.

## Recommended Usage Flow

1. `cerribro` drafts output/code.
2. `cerribrobaddan` reviews with `qc-cybersecurity-checklist.md`.
3. `cerribrobaddan` scores with `auto-review-rubric.md`.
4. Apply `coordination-protocol.md` decision rules.
5. Release only after passing quality and safety gates.

## Design Intent

- Improve output correctness and code quality.
- Catch mistakes missed in first pass.
- Reduce security risk through consistent hardening checks.
- Keep decisions explicit, auditable, and repeatable.
