# Workflow: `game_builder`

Use this workflow when Cerribro is in `game_builder` mode. It covers game concept
development through to a playable, tested first build.

Each workflow now incorporates the five deep-upgrade stages:
**Intelligence Plan → Research Plan → Experimentation Loop → Validation Gate → Grounded Output.**

Enable each stage individually in [`agent_config.json`](../agent_config.json) under `deep_modes`.

---

## Inputs Expected

| Input field         | Required | Description                                              |
|---------------------|----------|----------------------------------------------------------|
| `description`       | Yes      | One-paragraph summary of the game concept                |
| `platform`          | Yes      | Target platform(s): PC, mobile, browser, console         |
| `genre`             | No       | Genre (platformer, RPG, puzzle, shooter, simulation, etc.) |
| `engine`            | No       | Preferred engine or framework (Unity, Godot, Pygame, etc.) |
| `player_count`      | No       | Single-player, local co-op, online multiplayer           |
| `art_style`         | No       | 2D pixel art, 3D low-poly, vector, photorealistic, etc.  |
| `existing_code`     | No       | Snippet or repo URL of any existing game code            |
| `constraints`       | No       | Performance, asset budget, accessibility, or other limits |

**Minimum viable input:** `description` + `platform`.

---

## Stage 1 — Intelligence Plan

*(Active when `deep_modes.strict_planning.enabled: true`)*

1. **Decompose** the game into subproblems: core loop, mechanics, assets, UI, audio, engine setup.
2. **Log assumptions** — e.g., "Godot 4 supports GDScript and C#", "target device is mid-range PC".
3. **Document engine/framework decision** (DEC-01) with alternatives and trade-offs.
4. **Define branches** — primary approach and fallback if engine feature is missing.
5. **Score confidence** — pause if aggregate confidence < 0.75.

*Output:* `deep_intelligence` block. See [`intelligence_framework.md`](../intelligence_framework.md).

---

## Stage 2 — Research Plan

*(Active when `deep_modes.deep_research.enabled: true`)*

1. **Identify claims** requiring evidence: engine capabilities, platform constraints,
   asset format support, physics engine defaults.
2. **Formulate research questions** (e.g., RQ-01: "Does Godot 4 support 2D procedural
   generation natively?").
3. **Gather evidence** — minimum 2 records for medium-complexity claims.
4. **Synthesise** and attach Evidence Bundle; resolve any contradictions.
5. **Gate**: if `synthesis_confidence < 0.55`, emit Insufficient Evidence response.

*Output:* `evidence_bundle` block. See [`deep_research.md`](../deep_research.md).

---

## Stage 3 — Experimentation Loop (Design Phase)

*(Active when `deep_modes.deepmind_loop.enabled: true`)*

| Round | Hypothesis                                                | Metrics                          | Stop condition                        |
|-------|-----------------------------------------------------------|----------------------------------|---------------------------------------|
| R1    | Core game loop is fully specified and coherent            | Loop completeness checklist      | All loop phases defined               |
| R2    | All mechanics are compatible (no rule conflicts)          | Contradiction scan on design doc | Zero conflicts                        |
| R3    | Performance target is feasible on stated platform         | Estimated draw calls vs budget   | Within 20 % of target frame budget    |

**Escalation criteria** (stop and ask user):
- Two proposed mechanics directly conflict and user priority is unclear.
- Chosen engine cannot support a core feature after 2 redesign rounds.
- Performance target is infeasible given platform constraints.

*Output:* `deepmind_loop` block. See [`deepmind_loop.md`](../deepmind_loop.md).

---

## Stage 4 — Validation and Verification Gate

Before proceeding to final output, all of the following must pass:

- [ ] Core game loop fully specified (update / draw / input phases defined)
- [ ] All mechanics coherent (no rule conflicts in design)
- [ ] Engine fit confirmed (all required features supported)
- [ ] Performance feasibility validated
- [ ] At least one playable path from start to a win/end state defined
- [ ] Evidence Bundle attached (if deep_research enabled)
- [ ] Aggregate confidence ≥ 0.70 (or user accepts lower)

---

## Stage 5 — Final Grounded Output Format

```json
{
  "status": "completed",
  "mode": "game_builder",
  "confidence": 0.88,
  "confidence_band": "High",
  "output": {
    "workflow": "game_builder",
    "steps_planned": ["clarify_game_concept", "select_engine_or_framework", "..."],
    "steps_completed": ["clarify_game_concept"],
    "notes": "Engine selected: Godot 4. Proceeding to core game-loop implementation."
  },
  "facts": ["Godot 4 supports 2D physics and GDScript natively (EV-01)."],
  "assumptions": ["Target device is a mid-range PC with discrete GPU (A-01, unverified)."],
  "proposals": ["Use TileMap node for procedural level generation (DEC-01)."],
  "speculative": [],
  "unknowns_and_next_steps": [],
  "deep_intelligence": { "..." : "..." },
  "evidence_bundle": { "..." : "..." },
  "deepmind_loop": { "..." : "..." }
}
```

---

## Legacy Planning Steps (Standard Mode)

When `strict_planning` is disabled, the original planning steps apply:

1. **Concept clarification** — core game loop, unique selling point.
2. **Engine / framework selection** — recommend grounded choice; confirm with user.
3. **High-level design** — scenes, state machine, reusable systems.
4. **Asset plan** — list required asset categories; placeholders vs final.
5. **Project setup** — create engine project, folder conventions, source control.
6. **Core game loop** — minimal playable loop.
7. **Mechanics implementation** — one at a time, with testing after each.
8. **UI and HUD** — start/pause/game-over screens.
9. **Audio** — placeholder or final SFX and music.
10. **Polish and optimisation** — profile, tune game-feel.
11. **Playtest** — core loop manually; confirm fun and bug-free.
12. **Edge case tests** — boundary inputs.
13. **Performance test** — target frame rate on minimum spec.
14. **Accessibility check** — colour-blind, scalable text, gamepad support.

---

## Example Invocation

```python
cerribro = CerribroAgent(mode="game_builder")

params = {
    "description": "A 2D side-scrolling platformer with procedurally generated levels",
    "platform": "PC",
    "genre": "platformer",
    "engine": "Godot",
    "player_count": "single-player",
    "art_style": "2D pixel art",
}

reasoning = cerribro.think(params)
result    = cerribro.act(reasoning)
print(result)
```

