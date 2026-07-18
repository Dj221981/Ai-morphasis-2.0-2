# Cerribro — Software Maker / OT Builder Workflow

`software_maker` mode guides Cerribro through the **full lifecycle of building a
software product**, with first-class support for Operational Technology (OT) /
industrial deployments alongside traditional cloud and on-premises targets.

---

## When to use

Use `software_maker` mode when you need to:

- Build a production software product from scratch or a detailed specification.
- Target OT / industrial environments (PLCs, SCADA, edge devices, IEC 62443 zones).
- Integrate software with hardware interfaces, field buses, or industrial protocols
  (Modbus, OPC-UA, MQTT, etc.).
- Ensure domain-specific compliance (IEC 62443, ISA-95, FDA 21 CFR Part 11, etc.).

---

## Activation

```python
cerribro = CerribroAgent(name="Cerribro", mode="software_maker")
# or switch at runtime:
cerribro.set_mode("software_maker")
```

---

## Execution pipeline

| Step | Name | Description |
|------|------|-------------|
| 1 | `elicit_and_refine_requirements` | Gather functional, non-functional, and regulatory requirements. Clarify ambiguities before proceeding. |
| 2 | `define_system_architecture` | Propose a layered architecture appropriate for the deployment target (cloud / on-prem / OT / edge). |
| 3 | `identify_ot_or_domain_constraints` | Surface OT-specific concerns: real-time requirements, safety integrity levels, protocol support, network segmentation. |
| 4 | `scaffold_project_and_toolchain` | Create the project skeleton, CI/CD pipeline, and OT-compatible toolchain. |
| 5 | `implement_core_modules` | Build the primary functional modules with unit tests alongside each component. |
| 6 | `integrate_ot_interfaces_or_apis` | Wire up OT protocols, hardware drivers, or third-party APIs. Validate integration with stubs/simulators first. |
| 7 | `write_and_run_tests` | Execute the full test suite: unit, integration, hardware-in-the-loop (HIL) where applicable. |
| 8 | `validate_against_requirements` | Cross-check every requirement against the delivered implementation. Document any gaps. |
| 9 | `package_and_document_release` | Build release artefacts, write operator manuals, and produce a compliance evidence pack if required. |

---

## OT builder specifics

### Supported deployment targets

| Target | Notes |
|--------|-------|
| `cloud` | Standard web/cloud deployment (AWS, Azure, GCP). |
| `on-prem` | Traditional server/VM deployment inside a corporate network. |
| `ot` | Operational Technology environment — PLCs, DCS, SCADA, HMI systems. |
| `edge` | Resource-constrained edge devices, IoT gateways. |

### OT compliance check

When `ot_compliance_check` is `true` (default), Cerribro will:

1. Flag any component that introduces unnecessary attack surface in the OT network.
2. Recommend network segmentation (ISA/IEC 62443 zones and conduits).
3. Warn if communications traverse an unencrypted channel in a production OT zone.
4. Suggest appropriate safety-integrity-level (SIL) controls where applicable.

### Common OT protocols

Cerribro can scaffold integration stubs for:
- **Modbus TCP/RTU** — industrial register read/write.
- **OPC-UA** — information modelling and secure pub/sub.
- **MQTT** — lightweight edge messaging.
- **DNP3** — SCADA / utility automation.
- **Profinet / EtherNet/IP** — PLC field buses (specialist knowledge; verify against vendor docs).

---

## Configuration knobs (`agent_config.json → software_maker`)

| Key | Default | Meaning |
|-----|---------|---------|
| `supported_deployment_targets` | `["cloud","on-prem","ot","edge"]` | Targets Cerribro will reason about. |
| `ot_compliance_check` | `true` | Enable OT security and compliance analysis. |
| `default_toolchain` | `"auto"` | Let Cerribro choose the best toolchain, or specify (e.g. `"python"`, `"rust"`, `"c++"`). |

---

## Example

```python
task_params = {
    "description": "Build an OPC-UA data collector that reads sensor values from "
                   "three PLCs every 500 ms and stores them in InfluxDB.",
    "context": "Python 3.11, Raspberry Pi 4, plant network isolated from corporate LAN",
    "deployment_target": "ot",
    "compliance": ["IEC 62443-3-3"],
}
cerribro.set_mode("software_maker")
reasoning = cerribro.think(task_params)
result    = cerribro.act(reasoning)
print(result["status"])   # "completed"
print(result["output"])   # structured build plan
```

---

## Grounding in software_maker mode

All standard grounding guarantees apply:

- No invented library names or OT protocol capabilities.
- OT compliance recommendations cite the relevant standard clause.
- Confidence signalled at each architectural decision.
- Ambiguous requirements trigger clarification before architecture is committed.
