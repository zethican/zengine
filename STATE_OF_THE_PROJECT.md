# STATE_OF_THE_PROJECT.md

**Last Updated:** 2026-02-28 (Manual Checkpoint v0.45 - Exploration & Narrative Complete)

---

## Quick Status Snapshot

| Aspect                  | Status                  | Details                                                      |
| ----------------------- | ----------------------- | ------------------------------------------------------------ |
| **Current Phase**       | 25 (Game-Over Flow)     | ✅ Terminal states and player death recovery (v0.50)        |
| **Phase 25 Status**     | ✅ COMPLETE              | State-machine transitions on death; permadeath enforced     |
| **Next Immediate Task** | Phase 26: AI Pathfinding| AStar navigation and obstacle avoidance                     |
| **Active Agent**        | Ready                   | All 97 project tests passing                                 |

---

## Holistic Roadmap (Active Horizon - Gap Analysis Priorities)

### Phase 25: Game-Over / Restart Flow
- **Goal:** Implement terminal game states so player death is recoverable rather than a hard halt.
- **Key System:** `GameState` transitions and `EVT_ON_DEATH` handlers.

### Phase 26: AI Multi-Tile Pathfinding
- **Goal:** Replace 1-tile greedy lookahead with AStar path caching so NPCs can navigate around obstacles.
- **Key System:** `tcod.path.AStar` integration in `ai_system.py`.

### Phase 27: Player Progression
- **Goal:** Implement XP, levels, and attribute growth.
- **Key System:** `XPComponent` and `LevelingSystem` tied to Chronicle events.

---

## What Exists Right Now

### Phase 24 Implementation (Narrative UI)
- ✅ engine/narrative.py — `NarrativeGenerator` prose translation (v0.45).
- ✅ ui/screens.py — `ChronicleUIState` for significance-filtered history (v0.45).
- ✅ ui/screens.py — Refactored **Node-Based Dialogue System** (CoQ/CDDA inspired) (v0.45).

### Phase 23 Implementation (Exploration Memory)
- ✅ world/exploration.py — `ExplorationManager` for persistent Fog of War (v0.42).
- ✅ ui/screens.py — Optimized FOV rendering with restrictive algorithm (v0.42).

### Phase 22 Implementation (Party & Companions)
- ✅ engine/ecs/components.py — `PartyMember` component (v0.40).
- ✅ engine/ecs/systems.py — `recruit_npc_system` and following AI logic (v0.40).

### Phase 21 Implementation (JIT Materialization)
- ✅ engine/loop.py — `manage_entity_lifecycle` for lazy ECS instantiation (v0.38).
- ✅ engine/loop.py — Recursive JSON-based serialization for persistent entities (v0.38).

---

## Recent Activity

### Session: 2026-02-28 (Phases 23-25: Narrative, Exploration, Game-Over)

**Completed:**
- Implemented **Game-Over Flow**: Terminal `GameOverState` with permadeath (session deletion) and restart capability (v0.50).
- Implemented **Fog of War**: Persistent exploration memory and optimized FOV rendering (v0.42).
- Implemented **Node-Based Dialogue**: Branching conversation graphs with conditions, actions, and placeholders (v0.45).
- Implemented **Chronicle UI**: A human-readable history screen translating event streams to prose (v0.45).
- Stabilized test suite: All 97 project tests passing.

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
