# FUTURE.md — Post-MVP Deferred Systems & Active Roadmap

This document serves as the strategic roadmap for ZEngine. It has been reorganized to incorporate the comprehensive Gap Analysis between ZEngine and genre touchstones (Caves of Qud / Project Zomboid).

---

## Active Roadmap: Gap Analysis Implementation Sequence

The following priorities must be addressed in sequence to unblock architectural dependencies and bridge the core feature gaps.

### Phase 25: Game-Over / Restart Flow (ACTIVE)
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

### Phase 30: Character Creation Screen
- **Gap:** Player has no authoring agency at game start.
- **Implementation:** Requires Progression System. New `CharacterCreationState`.

### Phase 31: Dialogue World-State Flags
- **Gap:** Dialogue choices can't affect the world in ways other systems observe.
- **Implementation:** Requires Quest System. Add a `WorldState` flag store.

---

## Deferred Advanced Systems (High Architectural Cost)

These systems are recognized gaps but must not interrupt the execution of the Active Roadmap.

### NPC Off-Screen Simulation
- **Vision:** Run factions and NPCs outside of the player's immediate engagement range.
- **Status:** Deferred until World-State flags are hardened.

### Crafting Depth & Economy
- **Vision:** Supply/demand driven item pricing and equipment durability loops.
- **Status:** Deferred until Content Volume supports a robust economy.

### Destructible / Dynamic Terrain
- **Vision:** Tile state mutations (barricades, destruction) that rebuild pathfinding cost maps.
- **Status:** Deferred (Highest architectural cost).

### Tooltips / UX Polish
- **Vision:** Minimap, hover tooltips for item descriptions, and raw dice roll surfacing.
- **Status:** Deferred (Low priority polish).

---

## Core Systems (Recently Completed)

- **Ability Effect Resolver:** (Phase 19) Abilities fire complex, data-driven functional pipelines.
- **Territory & Factions:** (Phase 20) Topological graphing and faction relationship matrices.
- **JIT Materialization:** (Phase 21) Lazy instantiation and dematerialization of chunks.
- **Party Management:** (Phase 22) `PartyMember` and `InPartyWith` systems for recruitment.
- **Exploration Memory / Fog of War:** (Phase 23) Masking and discovery persistence.
- **Narrative UI / Node-Based Dialogue:** (Phase 24) Chronicle UI and branching conversation graphs.