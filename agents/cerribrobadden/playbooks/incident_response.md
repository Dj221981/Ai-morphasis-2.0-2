# Incident Response Playbook

Use this playbook for suspected or confirmed security incidents.

## Goals

1. Contain damage quickly.
2. Preserve evidence quality.
3. Restore operations safely.
4. Prevent recurrence.

## Phase 1 — Triage

- Confirm incident signal source(s): alert, user report, log anomaly.
- Determine scope-initial:
  - Affected hosts/accounts/services
  - Earliest known timestamp
  - Current attacker access likelihood
- Assign severity (Critical / High / Medium / Low).
- Start an incident timeline immediately.

## Phase 2 — Containment

- Isolate affected endpoints/systems where feasible.
- Revoke/rotate potentially compromised credentials.
- Block known malicious indicators (domains/IPs/hashes) through approved controls.
- Disable risky integrations or exposed tokens.
- Record every containment action with timestamp and owner.

## Phase 3 — Investigation

- Collect and preserve evidence:
  - Auth logs
  - Endpoint telemetry
  - Network flows
  - Cloud audit trails
  - Relevant application logs
- Reconstruct sequence of events.
- Identify root cause and persistence mechanisms.
- Validate whether data access/exfiltration occurred.

## Phase 4 — Eradication & Recovery

- Remove persistence artifacts.
- Patch exploited vulnerabilities/misconfigurations.
- Rebuild from known-good images where appropriate.
- Restore services in controlled stages.
- Increase monitoring sensitivity during recovery window.

## Phase 5 — Post-Incident Review

- Summarize:
  - What happened
  - Why defenses failed
  - What worked well
  - What to improve
- Define corrective actions with owners and due dates.
- Update playbooks, detections, and training.

## Minimum Output Template

- Incident Summary
- Impact Assessment
- Scope and Affected Assets
- Timeline of Key Events
- Immediate Actions Taken
- Remaining Risks
- Next 24h / 7d Actions
- Communication Notes (internal/external)
