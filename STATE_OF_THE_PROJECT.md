# STATE_OF_THE_PROJECT.md

**Last Updated:** 2026-02-28 (Manual Checkpoint v0.45 - Exploration & Narrative Complete)

---

## Quick Status Snapshot

| Aspect                  | Status                  | Details                                                      |
| ----------------------- | ----------------------- | ------------------------------------------------------------ |
| **Current Phase**       | 24 (Narrative UI)       | ✅ Node-Based Dialogue & Chronicle UI implemented (v0.45)    |
| **Phase 24 Status**     | ✅ COMPLETE              | Branching dialogue graphs; human-readable history screen     |
| **Next Immediate Task** | Phase 25: Game-Over Flow| Terminal states and player death recovery                    |
| **Active Agent**        | Ready                   | All 148 project tests passing                                |

---

## Holistic Roadmap (Active Horizon - Gap Analysis Priorities)

### Phase 25: Game-Over / Restart Flow (Blocking: Playtestability)
- **Gap:** Player death (`vitals.is_dead = True`) halts gameplay with no recovery.
- **Implementation:** Add terminal `GameState` enum values (`GameOverState`). Wire death check into a state-machine transition via `EventBus` subscriber (`EVT_ON_DEATH`).

### Phase 26: AI Multi-Tile Pathfinding (Blocking: Navigation)
- **Gap:** AI relies on 1-tile greedy lookahead of influence maps and gets stuck on obstacles.
- **Implementation:** Implement `AStar` path caching using `tcod.path`. Compute 8-15 tile paths on target acquisition and pop waypoints for movement.

### Phase 27: Player Progression (Blocking: Core RPG Arc)
- **Gap:** No XP, levels, or skill growth. Attributes are static after template load.
- **Implementation:** Add `XPComponent`, `LevelComponent`, and a `LevelingSystem` hooked to Chronicle kill events.

### Phase 28: Status Effect HUD (Blocking: Gameplay Feel)
- **Gap:** Modifiers fire invisibly; no persistent survival conditions.
- **Implementation:** Add `ConditionComponent` (list of named conditions with tick durations) and a HUD widget in `ui/renderer.py`.

### Phase 29: Quest / Objective System (Blocking: RPG Layer)
- **Gap:** Exploration and dialogue have no mechanical consequence.
- **Implementation:** An ECS singleton `QuestRegistry` hooked to Chronicle `bus.emit()` events.

### Ongoing: Content Volume
- **Gap:** Most data tables (enemies, recipes, abilities, loot) are stubs.
- **Implementation:** Continuous expansion of `data/` TOML files (loot tables, more recipes, unique NPCs).

### Phase 30: Character Creation Screen
- **Gap:** Player has no authoring agency at game start.
- **Implementation:** Requires Progression System. New `CharacterCreationState`.

### Phase 31: Dialogue World-State Flags
- **Gap:** Dialogue choices can't affect the world in ways other systems observe.
- **Implementation:** Requires Quest System. Add a `WorldState` flag store.

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
- Stabilized test suite: All 148 project tests passing.

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
