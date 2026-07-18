# Workflow: `game_builder`

Use this workflow when Cerribro is in `game_builder` mode. It covers game concept
development through to a playable, tested first build.

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

## Planning Steps

1. **Concept clarification**
   - Confirm the core game loop (what does the player do repeatedly?).
   - Identify the unique selling point / fun factor.
   - Surface missing information by asking the user.

2. **Engine / framework selection** (if not specified)
   - Recommend an engine grounded in the stated platform and genre.
   - List alternatives with trade-offs (e.g., Godot vs Unity for 2D).
   - Confirm with the user before proceeding.

3. **High-level design**
   - Define scenes/levels/screens.
   - Map out the core game-state machine (menu → play → pause → game-over).
   - Identify reusable systems (physics, input, audio, UI).

4. **Asset plan**
   - List required asset categories (sprites, tilemaps, sounds, fonts).
   - Identify placeholder vs final assets for the first build.

---

## Implementation Steps

5. **Project setup**
   - Create the engine project or repository scaffold.
   - Set up folder conventions (assets, scenes, scripts, tests).
   - Configure source control to exclude engine-generated binaries.

6. **Core game loop**
   - Implement the minimal playable loop (player input → game state update → render).
   - Keep it thin; add polish after correctness is confirmed.

7. **Mechanics implementation** (one mechanic at a time)
   - Implement, test, and confirm each mechanic before adding the next.
   - Use feature flags or stub implementations for unstarted mechanics.

8. **UI and HUD**
   - Add start/pause/game-over screens.
   - Implement score, health, or other HUD elements.

9. **Audio**
   - Add placeholder or final sound effects and music.
   - Ensure audio can be muted/controlled by the player.

10. **Polish and optimisation**
    - Profile for frame-rate issues; optimise draw calls and physics.
    - Tune game-feel (input responsiveness, animation timing, juice).

---

## Validation / Testing Steps

11. **Playtest** — run through the core loop manually; confirm it is fun and bug-free.
12. **Edge case tests** — boundary inputs (max score, instant death, empty level, etc.).
13. **Performance test** — confirm target frame rate on the minimum spec device/platform.
14. **Accessibility check** — colour-blind modes, scalable text, keyboard/gamepad support.

---

## Output Format

```json
{
  "status": "completed",
  "mode": "game_builder",
  "confidence": 0.88,
  "output": {
    "workflow": "game_builder",
    "steps_planned": ["clarify_game_concept", "select_engine_or_framework", "..."],
    "steps_completed": ["clarify_game_concept"],
    "notes": "Engine selected: Godot 4. Proceeding to core game-loop implementation."
  }
}
```

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
