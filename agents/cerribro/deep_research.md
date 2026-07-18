# Cerribro Deep Research Layer

This document specifies the **Deep Research Layer** — a structured research pipeline
that Cerribro activates when `deep_modes.deep_research.enabled` is `true` (see
[`agent_config.json`](agent_config.json)).

---

## Overview

Cerribro's standard mode answers questions from its training knowledge.

**Deep Research mode** adds a full evidence-gathering workflow before any factual
claim enters a response:

1. **Query formulation** — translate the user's request into targeted research questions.
2. **Multi-source evidence gathering** — identify and assess available sources.
3. **Source quality ranking** — score each source against the quality rubric.
4. **Contradiction detection** — flag conflicting claims across sources.
5. **Synthesis** — build a traceable evidence map and draw grounded conclusions.
6. **Freshness check** — flag time-sensitive topics and recency gaps.

Anti-hallucination constraints apply at every stage. See [Section 7](#7--anti-hallucination-constraints).

---

## 1 — Query Formulation Strategy

### Goal
Translate a loosely stated user request into precise, answerable research questions
before retrieving any evidence.

### Steps

1. **Restate the core claim or question** in neutral, unbiased language.
2. **Identify implicit sub-questions** — list every fact that must be true for the
   main claim to hold.
3. **Tag question type** for each sub-question:
   - `FACTUAL` — has a single verifiable answer (e.g., "What is the default timeout?")
   - `COMPARATIVE` — requires weighing two or more options
   - `PROCEDURAL` — asks how to do something step-by-step
   - `EVALUATIVE` — asks whether something is good/correct/safe
4. **Mark time-sensitivity** — flag questions where the answer may have changed since
   the knowledge cutoff.

### Template

```
RESEARCH QUERIES
================
Main question: <restated goal>

Sub-questions:
  RQ-01 [FACTUAL, time-sensitive]:   <question text>
  RQ-02 [PROCEDURAL]:                <question text>
  RQ-03 [COMPARATIVE]:               <question text>
```

---

## 2 — Multi-Source Evidence Gathering

### Source Categories

| Category          | Examples                                               | Default Trust |
|-------------------|--------------------------------------------------------|---------------|
| Primary official  | Official docs, RFCs, language specs, package changelogs | High          |
| Peer-reviewed     | Academic papers, formal benchmarks                     | High          |
| Community         | Stack Overflow (accepted answers), GitHub issues       | Medium        |
| Blog / Tutorial   | Dev.to, personal blogs, YouTube walkthroughs           | Low–Medium    |
| Training knowledge| Cerribro's internalized training data                  | Medium        |

### Evidence Record

For every piece of evidence gathered, create an **Evidence Record**:

```
EV-01
  Source:     <title / URL / package>
  Category:   Primary official
  Claim:      <exact claim extracted from the source>
  Relevance:  <why this answers RQ-01>
  Confidence: High
  Last-seen:  <date if known, else "unknown">
  Citation:   <formatted citation — see evidence_schema.json>
```

### Minimum Evidence Threshold

| Task complexity | Minimum evidence records |
|-----------------|--------------------------|
| Simple          | 1                        |
| Medium          | 2                        |
| Complex         | 3                        |

If the threshold is not met, Cerribro must emit an **Insufficient Evidence** response
(see [Section 7](#7--anti-hallucination-constraints)).

---

## 3 — Source Quality Ranking Rubric

Rate each source on a 5-point scale across four dimensions:

| Dimension     | Score 1 (poor)                  | Score 5 (excellent)                  |
|---------------|---------------------------------|--------------------------------------|
| **Authority** | Anonymous, unknown author       | Official maintainer / standards body |
| **Recency**   | > 3 years old, no update noted  | Published / updated within 6 months  |
| **Specificity**| Generic overview               | Directly addresses the research query|
| **Verifiability**| No way to cross-check        | Cross-confirmed by ≥ 2 independent sources |

**Composite score** = average of four dimensions.

| Composite score | Quality band | Action                         |
|-----------------|--------------|--------------------------------|
| 4.0 – 5.0       | Tier 1       | Use directly                   |
| 3.0 – 3.9       | Tier 2       | Use with Medium confidence tag |
| 2.0 – 2.9       | Tier 3       | Use only if no Tier 1/2 exists; Low confidence |
| < 2.0           | Tier 4       | Discard                        |

Only Tier 1 and Tier 2 sources may be cited in a final grounded response.

---

## 4 — Contradiction Detection

### Goal
Prevent conflicting claims from silently coexisting in a synthesised answer.

### Algorithm

1. After gathering evidence records, group by research question (RQ).
2. For each group, compare all `Claim` fields.
3. Flag a **Contradiction** if two claims assert mutually exclusive facts
   (e.g., "library X supports feature Y" vs "library X does not support feature Y").
4. For each contradiction:
   - Record both sides in the `contradictions` array of the Evidence Bundle.
   - Assign a resolution strategy:
     - `RECENCY_WINS` — use the more recently dated source.
     - `AUTHORITY_WINS` — use the higher-authority source.
     - `UNRESOLVED` — report both sides to the user and do not assert either.

### Contradiction Record

```
CONTRADICTION: EV-02 vs EV-05
  Claim A (EV-02): "Django 4.2 requires Python ≥ 3.8"
  Claim B (EV-05): "Django 4.2 requires Python ≥ 3.10"
  Resolution:      RECENCY_WINS → EV-05 (2024 official changelog)
  Final claim:     "Django 4.2 requires Python ≥ 3.10"
  Confidence delta: −0.05 (contradiction detected)
```

---

## 5 — Synthesis Protocol

### Goal
Produce a traceable, evidence-backed conclusion from the gathered evidence records.

### Steps

1. **Group evidence** by research question.
2. **Resolve contradictions** per Section 4.
3. **Build evidence map** — a graph linking each conclusion to its supporting evidence:
   ```
   Conclusion C1  ←  EV-01 (Tier 1, High), EV-03 (Tier 2, Medium)
   Conclusion C2  ←  EV-02 (Tier 2, Medium) [contradiction resolved]
   ```
4. **Assign synthesis confidence** per conclusion:
   - All supporting evidence Tier 1 → start at 0.90
   - Mix of Tier 1 + Tier 2 → start at 0.75
   - Only Tier 2 → start at 0.60
   - Apply adjustments from [Intelligence Framework § 5](intelligence_framework.md#5--confidence-scoring)
5. **Draft grounded answer** — every factual sentence in the answer must reference
   at least one Evidence Record ID (e.g., "per EV-01, …").
6. **Attach evidence bundle** — the full set of Evidence Records and the evidence map
   must be included in the output payload.

---

## 6 — Freshness and Recency Checks

For any research question tagged `time-sensitive`:

1. Check whether any evidence source has a known `last-seen` date.
2. If the most recent evidence is > 12 months old, add a **Freshness Warning**:
   ```
   ⚠ FRESHNESS WARNING: The most recent evidence for this claim is from [date].
   The information may be outdated. Verify at [official source URL].
   ```
3. Apply a `−0.05` confidence adjustment for each affected conclusion.
4. If no evidence has a known date, the claim must be tagged as `UNVERIFIED_RECENCY`.

---

## 7 — Anti-Hallucination Constraints

The following constraints are **non-negotiable** in Deep Research mode:

### 7.1 — No Unsupported Factual Claims

> A factual claim is any assertion that can be true or false independently of opinion.

Every factual claim **must** be backed by at least one Evidence Record.  
Claims with no supporting evidence are **prohibited**. Violating this rule causes the
response to be suppressed and replaced with an Insufficient Evidence response.

### 7.2 — Insufficient Evidence Response Behaviour

When the minimum evidence threshold (Section 2) is not met, Cerribro **must** return:

```
INSUFFICIENT EVIDENCE

I do not have enough verified evidence to answer this question confidently.

What I know:
  - <any partial evidence gathered>

What I could not verify:
  - <list of unverified claims>

Recommended next steps:
  - Check [official source 1]
  - Check [official source 2]
  - Consider running [command or test] to verify locally
```

### 7.3 — Citation Placeholders and Conventions

All citations in responses follow this convention:

```
[EV-NN] <Title or description of source> — <URL or "no URL available">
```

If a URL is not available (e.g., internal docs, training knowledge), the citation must
explicitly say `no URL available` and describe the source type.

**Placeholder for unknown URLs:**  
`[EV-NN] <Source title> — URL: verify at <recommended lookup path>`

### 7.4 — Prohibited Phrases

The following patterns must never appear in a Deep Research response without evidence:

- "According to the documentation, …" — unless EV record cites that exact doc
- "This is a well-known fact that …" — confidence signalling must be explicit
- "As of the latest version, …" — requires a freshness check and citation
- Version numbers in code examples — must be backed by an EV record

---

## 8 — Evidence Bundle Output Format

The Deep Research layer produces an **Evidence Bundle** attached to every response:

```json
{
  "evidence_bundle": {
    "research_questions": [
      { "id": "RQ-01", "text": "...", "type": "FACTUAL", "time_sensitive": true }
    ],
    "evidence_records": [
      {
        "id": "EV-01",
        "source_title": "...",
        "source_url": "...",
        "category": "Primary official",
        "tier": 1,
        "claim": "...",
        "relevance_to": "RQ-01",
        "confidence": "High",
        "last_seen": "2024-03-15",
        "citation": "[EV-01] ... — https://..."
      }
    ],
    "contradictions": [],
    "evidence_map": {
      "C1": ["EV-01", "EV-03"],
      "C2": ["EV-02"]
    },
    "freshness_warnings": [],
    "synthesis_confidence": 0.85
  }
}
```

For the full JSON schema, see [`evidence_schema.json`](evidence_schema.json).

---

## 9 — Enabling / Disabling Deep Research Mode

See [`agent_config.json`](agent_config.json):

```json
"deep_modes": {
  "deep_research": {
    "enabled": false,
    "min_evidence_records": {
      "simple": 1,
      "medium": 2,
      "complex": 3
    },
    "max_source_age_months": 12,
    "require_tier1_for_high_confidence": true,
    "freshness_penalty": -0.05,
    "contradiction_penalty": -0.05
  }
}
```

---

## 10 — Workflow Integration Points

Each Cerribro workflow (`app_builder`, `game_builder`, `coding_assistant`) must include
a **Research Plan** step (see updated workflow files) that:

1. Identifies which claims in the plan require evidence.
2. Runs the query formulation → evidence gathering → synthesis pipeline.
3. Attaches the resulting Evidence Bundle to the workflow output.
4. Gates the **Implementation** step on a minimum synthesis confidence of `0.55`.

---

## See Also

- [`evidence_schema.json`](evidence_schema.json) — formal JSON schema for evidence bundles
- [`intelligence_framework.md`](intelligence_framework.md) — reasoning and planning layer
- [`deepmind_loop.md`](deepmind_loop.md) — hypothesis/experiment/evaluation loop
- [`grounding_policy.md`](grounding_policy.md) — base grounding rules
- [`agent_config.json`](agent_config.json) — config reference
