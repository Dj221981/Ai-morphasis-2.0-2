# Ai-morphasis Defensive Agentic Armies

This repository now includes two defensive-only multi-agent cybersecurity swarms:

- `agents/cerribro/army/`
- `agents/cerribrobadden/army/`

Both are designed for:

- Threat detection
- Incident triage
- Forensics support
- Defensive remediation recommendations
- Human-in-the-loop approvals for high-impact actions

> Safety boundary: This configuration is strictly defensive. It does not support offensive intrusion, exploit development, malware generation, persistence, or unauthorized access.

---

## Directory Overview

- `manifest.yaml`  
  Agent inventory, squads, allowed/disallowed capabilities.

- `orchestrator.yaml`  
  Event routing and human approval gates.

- `safety_policy.yaml`  
  Hard policy constraints and response style.

- `playbooks/`  
  Response playbooks (phishing, ransomware).

- `metrics/kpi.yaml`  
  Operational targets (MTTD/MTTR/coverage/etc.).

---

## Quick Start (Runtime-Agnostic)

1. **Review policies first**
   - `agents/cerribro/army/safety_policy.yaml`
   - `agents/cerribrobadden/army/safety_policy.yaml`

2. **Copy environment template**
   - Duplicate `config.env.example` to your runtime secret store or `.env` equivalent.

3. **Wire integrations**
   - Connect SIEM/EDR/Identity/Cloud sources to your ingestion pipeline.
   - Route normalized events into the orchestrator event stream.

4. **Enable approval workflow**
   - Ensure actions like host isolation/account disable require human approval.

5. **Run playbook simulation in non-production**
   - Validate phishing and ransomware playbook logic against test telemetry.

6. **Monitor KPIs**
   - Track MTTD/MTTR/false positives and tune detection/triage squads.

---

## Suggested Operating Model

- Start in **observe-only mode** for 7–14 days.
- Tune alert thresholds and deduplication before enabling containment recommendations.
- Require analyst sign-off for all production-impacting actions.
- Review ATT&CK coverage monthly and close control gaps.

---

## Minimal Event Contract (Example)

Your runtime/orchestrator should normalize incoming events into a common schema, e.g.:

```json
{
  "event_id": "evt-123",
  "timestamp": "2026-07-27T00:00:00Z",
  "source": "siem",
  "severity": 8,
  "ioc_match": true,
  "incident_confirmed": false,
  "asset": "host-22",
  "user": "user@example.com"
}
```

---

## Human-in-the-Loop Controls

High-impact actions should always require explicit approval:

- Host isolation
- Account disable
- Firewall global block
- Any production configuration change

---

## Next Steps

- Add additional playbooks (credential stuffing, insider risk, cloud misconfiguration).
- Add ATT&CK technique mapping matrix per squad.
- Add CI policy checks to fail PRs that introduce disallowed capabilities.

---

## Disclaimer

This project scaffold is for authorized, defensive cybersecurity operations only. Always follow legal, organizational, and regulatory requirements for monitoring and response.
