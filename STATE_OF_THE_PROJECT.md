# STATE_OF_THE_PROJECT.md

**Last Updated:** 2026-02-28 (Manual Checkpoint v0.45 - Exploration & Narrative Complete)

---

## Quick Status Snapshot

| Aspect                  | Status                  | Details                                                      |
| ----------------------- | ----------------------- | ------------------------------------------------------------ |
| **Current Phase**       | 24 (Narrative UI)       | ✅ Node-Based Dialogue & Chronicle UI implemented (v0.45)    |
| **Phase 24 Status**     | ✅ COMPLETE              | Branching dialogue graphs; human-readable history screen     |
| **Next Immediate Task** | Phase 25: Game-Over Flow| Terminal states and player death recovery                    |
| **Active Agent**        | Ready                   | All 95 project tests passing                                 |

---

## Holistic Roadmap (Active Horizon - Gap Analysis Priorities)

### Phase 25: Game-Over / Restart Flow (Blocking: Playtestability)
- **Goal:** Implement terminal game states so player death is recoverable rather than a hard halt.
- **Key System:** `GameState` enum transitions (`GameOverState`) and `EVT_ON_DEATH` event bus handlers.

### Phase 26: AI Multi-Tile Pathfinding (Blocking: Navigation)
- **Goal:** Replace 1-tile greedy lookahead with AStar path caching so NPCs can navigate around obstacles.
- **Key System:** `tcod.path.AStar` integration in `ai_system.py`.

### Phase 27: Player Progression (Blocking: Core RPG Arc)
- **Goal:** Implement XP, levels, and attribute growth.
- **Key System:** `XPComponent`, `LevelComponent`, and a `LevelingSystem` tied to Chronicle kill events.

### Phase 28: Status Effect HUD (Blocking: Gameplay Feel)
- **Goal:** Visually surface active modifiers and survival conditions to the player.
- **Key System:** A new HUD widget in `ui/renderer.py`.

### Phase 29: Quest / Objective System (Blocking: RPG Layer)
- **Goal:** Ensure exploration and dialogue have persistent mechanical consequences.
- **Key System:** An ECS singleton `QuestRegistry` hooked to Chronicle `bus.emit()` events.

### Phase 30: Character Creation Screen
- **Goal:** Allow player agency before world generation (archetype selection, stat allocation).
- **Key System:** Requires Progression System. New `CharacterCreationState`.

### Phase 31: Dialogue World-State Flags
- **Goal:** Persistently alter the world via conversation in ways other systems observe.
- **Key System:** Requires Quest System. Add a `WorldState` flag store.

---

## What Exists Right Now

### Phase 24 Implementation (Narrative UI)
- ✅ `engine/narrative.py` — `NarrativeGenerator` prose translation (v0.45).
- ✅ `ui/screens.py` — `ChronicleUIState` for significance-filtered history (v0.45).
- ✅ `ui/screens.py` — Refactored **Node-Based Dialogue System** (CoQ/CDDA inspired) (v0.45).

### Phase 23 Implementation (Exploration Memory)
- ✅ `world/exploration.py` — `ExplorationManager` for persistent Fog of War (v0.42).
- ✅ `ui/screens.py` — Optimized FOV rendering with restrictive algorithm (v0.42).

### Phase 22 Implementation (Party & Companions)
- ✅ `engine/ecs/components.py` — `PartyMember` component (v0.40).
- ✅ `engine/ecs/systems.py` — `recruit_npc_system` and following AI logic (v0.40).

### Phase 21 Implementation (JIT Materialization)
- ✅ `engine/loop.py` — `manage_entity_lifecycle` for lazy ECS instantiation (v0.38).
- ✅ `engine/loop.py` — Recursive JSON-based serialization for persistent entities (v0.38).

### Phase 20 Implementation (Territory & Factions)
- ✅ `world/territory.py` — `TerritoryManager` a priori topological graphing (v0.36).
- ✅ `world/factions.py` — `FactionSystem` and relationship matrices.

---

## Recent Activity

### Session: 2026-02-28 (Phases 23-24: Narrative & Exploration)

**Completed:**
- Implemented **Fog of War**: Persistent exploration memory and optimized FOV rendering (centered on player).
- Implemented **Node-Based Dialogue**: Branching conversation graphs with conditions, actions, and placeholders.
- Implemented **Chronicle UI**: A human-readable history screen that filters the low-level event stream into meaningful prose.
- Stabilized test suite: All 95 project tests passing.

---

## Hard Limits (Must Never Violate)

1. No direct inter-layer state mutation — all Dungeon→Social via Chronicle events
2. No Chronicle entry modification after inscription
3. No vitality caching during MVP
4. No hardcoded ability behavior — TOML data only
5. No NumPy outside spatial layer, lighting, and AI Influence Maps
6. HP mutation only via `apply_damage()`
7. Event keys only via `EVT_*` constants
8. Pass `EventBus` at construction (no global singletons)
