# Threat Modeling Playbook

Use this playbook when designing new systems or assessing existing architecture.

## Objectives

- Identify realistic abuse scenarios early.
- Prioritize controls by risk reduction impact.
- Create a living model that evolves with architecture.

## Step 1 — Scope Definition

- Define system boundary and assumptions.
- List critical assets:
  - Sensitive data
  - Privileged operations
  - Identity and secrets
- Identify trust boundaries and third-party dependencies.

## Step 2 — Architecture Mapping

- Document components, data flows, and entry points.
- Mark authentication, authorization, and encryption points.
- Highlight internet-exposed and high-privilege paths.

## Step 3 — Threat Enumeration

Apply STRIDE (optional but recommended):

- Spoofing
- Tampering
- Repudiation
- Information Disclosure
- Denial of Service
- Elevation of Privilege

For each threat, capture:
- Attack preconditions
- Potential impact
- Existing controls
- Detection gaps

## Step 4 — Risk Prioritization

Rate each scenario by:
- Likelihood
- Impact
- Exploitability
- Detection difficulty

Prioritize into:
- Immediate remediation
- Planned remediation
- Accepted risk (with rationale)

## Step 5 — Control Plan

Recommend layered controls:
- Preventive (hardening, least privilege, segmentation)
- Detective (logging, alerts, anomaly detection)
- Corrective (rollback, isolation, key rotation)

## Step 6 — Validation

- Define tests for critical assumptions.
- Add abuse-case tests into CI/CD where possible.
- Track residual risks and review periodically.

## Threat Model Output Template

- Scope and Assumptions
- Asset Inventory
- Trust Boundaries
- Top Threat Scenarios
- Risk Ratings
- Mitigation Roadmap
- Residual Risks
- Validation Plan
