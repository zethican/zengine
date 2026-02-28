# STATE_OF_THE_PROJECT.md

**Last Updated:** 2026-02-27 21:00 (final Phase 2 core checkpoint)

---

## Quick Status Snapshot

| Aspect                  | Status                  | Details                                                      |
| ----------------------- | ----------------------- | ------------------------------------------------------------ |
| **Current Phase**       | 7 (Inventory/Items)     | Phase 6 Interactive UI complete and verified                 |
| **Phase 6 Status**      | ✅ IMPLEMENTED           | TCOD state machine wired to core ECS; standalone .exe built  |
| **Next Immediate Task** | Review Next Phase       | Awaiting user direction on Phase 7 (likely Inventory)        |
| **Active Agent**        | Ready                   | Phase 6 complete                                             |

---

## What Exists Right Now

### Documentation (complete)

- ✅ CONTEXT.md — Single source of truth (updated to Phase 2)
- ✅ AGENT_ONBOARDING.md — Agent ritual templates and hard limits
- ✅ DESIGN_VARIABLES.md — All 20 parameters with confirmed values
- ✅ FUTURE.md — 20+ post-MVP deferred items
- ✅ DO_NOT_TOUCH.md — Phase 1 locks applied; Phase 2 targets listed

### Phase 2 Implementation (Core Feature Complete)

- ✅ engine/chronicle.py — Chronicle write/query interface (append-only JSONL)
- ✅ engine/social_state.py — Social State schema and stress reaction logic
- ✅ engine/equilibrium.py — Vitality, Taper formula, and conduction math
- ✅ engine/ecs/components.py — Core ECS components (Vitals, Economy, Position)
- ✅ engine/ecs/systems.py — ECS systems for turn resolution and actions
- ✅ world/generator.py — Chunk-based world generator with rumor resolution
- ✅ data/ — Minimal Viable Encounter dataset (Abilities, Entities, World Rumors)
- ✅ ui/renderer.py — tcod terminal renderer stub
- ✅ 24/24 Unit Tests passing — verified core system logic and data loading

### Archive (not in tree)

- 📦 user_scratch/ — Raw content dump (ZEngine_Manifest_v0_2.pdf, MCP_GUIDE.md, etc.)

---

## Phase Gates & Blockers

### Phase 2 Implementation Gate

**Status:** ✅ COMPLETE — moving to Phase 7 Inventory/Items

**Completed in Phase 6 Interactive UI:**
- Implemented `tcod` event loop.
- Architected Screen State Machine (`MainMenuState`, `ExplorationState`, `InventoryState`).
- Wired input bindings (Escape to Menu, 'i' to Inventory).
- Shipped `build_exe.py` PyInstaller configuration wrapper.

**Next Steps (Phase 7+):**
- Awaiting next target directive from user (likely bridging Inventory ECS Components).

---

## Hard Limits (Must Never Violate)

1. No direct inter-layer state mutation — all Dungeon→Social via Chronicle events
2. No Chronicle entry modification after inscription — corrections are new entries
3. No vitality caching during MVP — stub field exists but unused
4. No hardcoded ability behavior — TOML data + tag subscriptions only
5. No NumPy outside spatial layer and lighting
6. Grammar tables read-only — never agent-generated
7. All undocumented parameters → DESIGN_VARIABLES.md (never silent defaults)
8. Post-MVP systems → note in FUTURE.md, implement simpler MVP version
9. Never mutate `Combatant.hp` directly — only via `apply_damage()`
10. Never use raw strings as event keys — use `EVT_*` constants
11. Never global `EventBus` — pass instances at construction

---

## Design Variables (Confirmed)

| Variable                        | Value           | Notes                                               |
| ------------------------------- | --------------- | --------------------------------------------------- |
| ENERGY_THRESHOLD                | 100.0           | Turn eligibility threshold                          |
| AP_POOL_SIZE                    | 100             | Resets each turn; matches ENERGY_THRESHOLD scale    |
| MOVEMENT_ALLOCATION             | ceil(100/speed) | AP per tile; ceiling rounding; speed-derived        |
| SOCIAL_CATCHUP_TICKS            | 5               | Session boundary advance                            |
| CATCHUP_TRANSITION_CAP          | 1               | Max state transitions per node per session boundary |
| CRIT_THRESHOLD                  | 20              | d20 natural roll                                    |
| FUMBLE_THRESHOLD                | 1               | d20 natural roll                                    |
| BASE_HIT_DC                     | 10              | Default defense class when no stat provided         |
| COMBAT_ROLL_DISPLAY             | "category"      | fumble/miss/graze/hit/crit                          |
| REPUTATION_OSTRACIZATION        | -0.3            | Threshold; configurable                             |
| REPUTATION_COOPERATION          | 0.4             | Threshold; configurable                             |
| STRESS_EXODUS_THRESHOLD         | 0.7             | float 0.0–1.0                                       |
| STRESS_PASSIVE_DECAY_RATE       | 0.0             | 0.0 = no passive decay                              |
| EQUILIBRIUM_BASE_RESISTANCE     | 40              | Range 20–80                                         |
| CONDUCTION_COEFFICIENT          | 0.3             | 0.0 disables conduction                             |
| CONDUCTION_ATTENUATION          | 0.6             | Per distance unit; range 0.1–0.9                    |
| CHRONICLE_SIGNIFICANCE_MIN      | 2               | Minimum inscription threshold; range 1–5            |
| CHRONICLE_CONFIDENCE_WITNESSED  | 0.9             |                                                     |
| CHRONICLE_CONFIDENCE_FABRICATED | 0.4             |                                                     |
| VITALITY_CACHE                  | NOT_IMPLEMENTED | Stub field; do not read or write MVP                |

---

## Recent Activity

### Session: 2026-02-27 (Phase 1 Contracts + Close-out)

**Completed:**

- Drafted COMPONENTS.md — 8-layer ECS component taxonomy with full field types, lifecycle, read/write isolation
- Drafted EVENTS.md — 10 EVT_* constants, TypedDict payloads, canonical turn resolution sequence
- Drafted SYSTEMS.md — 16 systems, dispatch ordering, Chronicle entry schema, Equilibrium Taper formula, Legacy Conversion sequence
- Pre-flight audit: closed 4 issues (combat.py docstring, CONTEXT.md stale state, moral_weight/resilience gap in disposition, DO_NOT_TOUCH.md phase update)
- All Phase 1 contracts locked in DO_NOT_TOUCH.md
- Established hourly STATE_OF_THE_PROJECT.md checkpoint (scheduled task: zengine-project-checkpoint)

**Next:** Phase 2 implementation — move logic to ECS systems

### Session: 2026-02-27 (ECS Systems Migration + Core Logic)

**Completed:**

- Implemented `SocialStateSystem` in `engine/social_state.py` with reactive stress tracking and event emission.
- Implemented `Equilibrium` math in `engine/equilibrium.py` including Taper formula and conduction.
- Defined core ECS components in `engine/ecs/components.py` (Vitals, Economy, Position, Stats).
- Migrated turn resolution and action economy logic to `engine/ecs/systems.py`.
- Implemented `action_resolution_system` for attack handling in ECS.
- Created `ui/renderer.py` stub for TCOD console management.
- Verified all core systems with 18/18 passing unit tests.
- Integrated Social Layer into combat smoke test; verified real-time stress accumulation.

**Next:** Phase 2 world generation — implement chunked generator in `world/generator.py`

### Session: 2026-02-27 (Project Scaffolding)

**Completed:**

- Read all user_scratch files (CONTEXT, AUTHORITATIVE_GROUND_TRUTH, combat.py, MCP_GUIDE, AGENT_ONBOARDING)
- Created root documentation structure (CONTEXT.md, AGENT_ONBOARDING.md, DESIGN_VARIABLES.md, FUTURE.md, DO_NOT_TOUCH.md)
- Copied canonical combat.py stub to engine/combat.py
- Created Phase 1 contract placeholders (COMPONENTS.md, SYSTEMS.md, EVENTS.md)

---

## Upcoming Milestones

### Phase 2 (Completed)

- [x] engine/chronicle.py — Chronicle write/query interface (append-only JSONL) ✅
- [x] engine/social_state.py — Social State schema and transition logic ✅
- [x] engine/equilibrium.py — Vitality, Taper formula, conduction ✅
- [x] engine/ecs/ — ECS component and system definitions ✅
- [x] ui/renderer.py — tcod terminal renderer ✅
- [x] Wire combat system into full encounter loop ✅
- [x] Smoke tests pass for all Phase 2 systems ✅

### Phase 3 (Completed)

- [x] world/generator.py — procedural dungeon/wilderness generation (BSP) ✅
- [x] Encounter density driver (legacy actor spawning) ✅

### Phase 6+ (Completed)

- [x] UI System State Machine (MainMenu, Exploration, Inventory) ✅
- [x] Native Python interactive play session ✅
- [x] Portable Standalone Executable Pipeline (`build_exe.py`) ✅

---

## Known Post-MVP Deferrals

See `FUTURE.md` for full list. Key items:

- AP carry-over / reaction economy
- Real-time Social Layer daemon (replace session-boundary tick)
- Vitality caching system
- Chronicle active epistemology (confidence weight reconciliation)
- EventPayload.data typed dicts per event type
- Tag-based casting (Wildermyth model)
- Faction hooking, gift economy, ancestor worship
- Cover / line-of-sight bonus mechanics
- Cross-session Chronicle persistence

---

## How to Use This File

- **Opening new session:** Read this first for 30-second status
- **Mid-session:** Skim to verify phase assumptions
- **Closing session:** Note any progress; file updates automatically every hour

---

## Automated Update Log

| Timestamp                   | Change                                                                                                                                                                   | Trigger                   |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------- |
| 2026-02-27 16:00            | Initial scaffold                                                                                                                                                         | Project setup complete    |
| 2026-02-27 (Phase 1 end)    | Phase 1 close-out — contracts final, locks applied, Phase 2 open                                                                                                         | Pre-flight audit complete |
| 2026-02-27 (Phase 2 start)  | engine/chronicle.py implemented — ChronicleInscriber, ChronicleEntry, ChronicleReader, GameTimestamp; smoke test: 38 entries, death events, session markers all verified | Phase 2 session           |
| 2026-02-27 (Phase 2 end)    | Phase 2 Integration complete. Full simulation loop written in `engine/loop.py`. Automated end-to-end smoke test passes. `BSPDungeonGenerator` stub added. Now Phase 3.    | Phase 2 Integration close-out |
| 2026-02-27 (Phase 3 end)    | Phase 3 World Gen complete. BSP algorithm and dynamic density wilderness encounters via `ChronicleReader` implemented and tested. Proceeding to Phase 4.                 | Phase 3 close-out |
| 2026-02-27 (Phase 4 end)    | Phase 4 complete. Data loaders wired with Pydantic for JIT caching of TOML seed data, combined with Session Management context collapsing.                             | Phase 4 close-out |
| 2026-02-27 (Phase 5 end)    | Phase 5 complete. Expanded data/abilities schema to handle AoE, Healing, and single-target rules. Rewrote action_resolution_system to dynamically route TOML AP costs. | Phase 5 close-out |
| 2026-02-27 (Phase 6 end)    | Phase 6 complete. Rendered the backend engine into visual tcod screen states. Added PyInstaller wrapper script.                                                        | Phase 6 close-out |

(Auto-updated by scheduled task every hour; user can also request manual refresh)