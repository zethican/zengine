# STATE_OF_THE_PROJECT.md

**Last Updated:** 2026-02-28 (Manual Checkpoint v0.45 - Exploration & Narrative Complete)

---

## Quick Status Snapshot

| Aspect                  | Status                  | Details                                                      |
| ----------------------- | ----------------------- | ------------------------------------------------------------ |
| **Current Phase**       | 24 (Narrative UI)       | ✅ Node-Based Dialogue & Chronicle UI implemented (v0.45)    |
| **Phase 24 Status**     | ✅ COMPLETE              | Branching dialogue graphs; human-readable history screen     |
| **Next Immediate Task** | Phase 25: Ability Effect Resolver | Fix silent no-op for triggered ability effects   |
| **Active Agent**        | Ready                   | All tests passing                                            |

---

## Holistic Roadmap (Active Horizon - Gap Analysis Priorities)

### Phase 25: Ability Effect Resolver (Blocking: Core Combat)
- **Goal:** Wire `action_resolution_system` to actually apply `effects[]` from ability TOMLs.
- **Key System:** `systems.py` (`evaluate_formula`, `resolve_effect_targets`, `apply_modifier_blueprint`).

### Phase 26: Game-Over / Restart Flow (Blocking: Playtestability)
- **Goal:** Implement terminal game states so player death is recoverable rather than a hard halt.
- **Key System:** `GameState` enum transitions (`GameOverState`) and `EVT_ON_DEATH` event bus handlers.

### Phase 27: AI Multi-Tile Pathfinding (Blocking: Navigation)
- **Goal:** Replace 1-tile greedy lookahead with AStar path caching so NPCs can navigate around obstacles.
- **Key System:** `tcod.path.AStar` integration in `ai_system.py`.

### Phase 28: Player Progression (Blocking: Core RPG Arc)
- **Goal:** Implement XP, levels, and attribute growth.
- **Key System:** `XPComponent`, `LevelComponent`, and a `LevelingSystem` tied to Chronicle kill events.

### Phase 29: Status Effect HUD (Blocking: Gameplay Feel)
- **Goal:** Visually surface active modifiers and survival conditions to the player.
- **Key System:** A new HUD widget in `ui/renderer.py` and `ConditionComponent`.

### Phase 30: Quest / Objective System (Blocking: RPG Layer)
- **Goal:** Ensure exploration and dialogue have persistent mechanical consequences.
- **Key System:** An ECS singleton `QuestRegistry` hooked to Chronicle `bus.emit()` events.

### Phase 31: Content Volume (Ongoing)
- **Goal:** Continuous expansion of `data/` TOML files (enemies, recipes, abilities, loot).
- **Key System:** `data_loader.py` and TOML data authoring.

### Phase 32: Character Creation Screen (Blocking: Player Agency)
- **Goal:** Allow player agency before world generation (archetype selection, stat allocation).
- **Key System:** Requires Progression System. New `CharacterCreationState`.

### Phase 33: Dialogue World-State Flags (Blocking: Immersive Sim Layer)
- **Goal:** Persistently alter the world via conversation in ways other systems observe.
- **Key System:** Requires Quest System. Add a `WorldState` flag store.

### Phase 34: NPC Off-Screen Simulation
- **Goal:** Run factions and NPCs outside of the player's immediate engagement range.
- **Key System:** Requires World-State flags. Off-screen tick on session load/save.

### Phase 35: Crafting Depth & Economy
- **Goal:** Supply/demand driven item pricing and equipment durability loops.
- **Key System:** Requires Content Volume. `DurabilityComponent` and dynamic item value mapping.

### Phase 36: Wilderness / Biome Depth
- **Goal:** Per-biome spawn tables, noise-blended biome seams, and dynamic weather hazards.
- **Key System:** Cosmetic until late stage. `WeatherSystem` with per-tile movement modifiers.

### Phase 37: Destructible / Dynamic Terrain
- **Goal:** Tile state mutations (barricades, destruction) that rebuild pathfinding cost maps.
- **Key System:** `TileStateMutator` that invalidates the chunk's cached arrays. Highest architectural cost.

### Phase 38: Tooltips / UX Polish
- **Goal:** Minimap, hover tooltips for item descriptions, and raw dice roll surfacing.
- **Key System:** Tooltip render pass in `ui/renderer.py`.

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
