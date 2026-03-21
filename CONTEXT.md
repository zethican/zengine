# CONTEXT.md — ZEngine Handoff

**Packaged:** February 28, 2026 | **Phase:** 24 (complete) | **Next:** Phase 25 (Game-Over Flow)

---

## Project / Session Identity

- **Project:** ZEngine — social ecology simulator / party-based roguelike
- **Author:** Zachery (solo indie)
- **Stack:** Python 3.14.3 | python-tcod-ecs | tcod renderer | Pydantic v2 | TOML | JSONL Chronicle
- **Active environment:** Agentic CLI, local filesystem
- **Design status:** v0.45 (Narrative UI & Exploration complete)
- **Canonical design reference:** `ZEngine_Manifest_v0_2.pdf` (§1–§24)

---

## Canonical State

### Files that exist

| File                       | Status                                                      |
| -------------------------- | ----------------------------------------------------------- |
| `engine/narrative.py`      | Chronicle UI & Narrative Generator — Phase 24 updated       |
| `ui/screens.py`            | Node-Based Dialogue & Chronicle UI — Phase 24 updated       |
| `world/exploration.py`     | Fog of War & Persistent Memory — Phase 23 updated           |
| `engine/loop.py`           | JIT Materialization — Phase 21 updated                      |
| `world/territory.py`       | A Priori Topological Graphing — Phase 20 updated            |
| `world/factions.py`        | Faction System & Relationships — Phase 20 updated           |
| `engine/ecs/systems.py`    | Formula engine & Target resolution — Phase 19 updated       |
| `engine/data_loader.py`    | EffectDef & AbilityDef functional schemas — Phase 19 updated|
| `data/abilities/`          | Migrated functional ability definitions — Phase 19 updated  |
| `engine/item_factory.py`   | Rarity rolls & Affix composition — Phase 18 updated         |
| `CONTEXT.md`               | Single source of truth — Phase 24 updated                   |
| `STATE_OF_THE_PROJECT.md`  | Project status and activity log — Phase 24 updated          |

---

## Decisions & Rationale (Phases 19-24)

### Node-Based Dialogue (Phase 24)
- **Decision:** Conversation graphs with conditions, actions, and placeholders using `NarrativeGenerator`.
- **Rationale:** Moves dialogue complexity from Python logic into configuration, preparing for broader content authoring.

### Exploration Memory & Fog of War (Phase 23)
- **Decision:** Added `ExplorationManager` and optimized FOV rendering centered on the player.
- **Rationale:** Ensures world state persists across sessions and chunks, enhancing tactical depth.

### JIT Materialization (Phase 21)
- **Decision:** Entities exist as Chronicle records outside FOV and are only instantiated in ECS upon observation.
- **Rationale:** Enables an infinite world by aggressively culling the active ECS registry size and dynamically deserializing entities.

### Functional Effect Pipeline (Phase 19)
- **Decision:** Abilities are now collections of atomic `Effect` objects rather than hardcoded `if/else` branches.
- **Rationale:** Hardens the foundation for complex interactions (AOE, multi-phase spells, life-steal) and ensures that future content expansion requires zero new Python code.

### Formula Engine
- **Decision:** Implemented a runtime evaluator for magnitude strings (e.g., `1d8 + @might_mod`).
- **Rationale:** Allows data-driven abilities to scale dynamically with character stats while maintaining the tactical uncertainty of dice rolls.

### Functional Targeting
- **Decision:** Targeting logic (self, primary, adjacent_all) is functionalized and reusable across all effects.
- **Rationale:** Decouples "what an ability does" from "who it affects," allowing for unique targeting patterns like "Chain Lightning" or "Cleave."

---

## DESIGN_VARIABLES.md — Confirmed Values

```
ENERGY_THRESHOLD            100.0       # turn eligibility; float
AP_POOL_SIZE                100         # resets each turn
CRIT_THRESHOLD              16          # 2d8 natural roll (max)
FUMBLE_THRESHOLD            2           # 2d8 natural roll (min)
REPUTATION_OSTRACIZATION   -0.3        # threat threshold
REPUTATION_COOPERATION      0.4         # affinity threshold
FACTION_CONDUCTION_FACTOR   0.5         # reputation propagation strength
SOCIAL_AUTOPOP_COOLDOWN     2000        # ticks between NPC-initiated talks
RARITY_MAGIC_CHANCE         0.25        # 25% chance for 1 affix
RARITY_RARE_CHANCE          0.05        # 5% chance for 2 affixes
```

---

## Agent Hard Limits (memorize)

1. No direct inter-layer state mutation — all Dungeon→Social changes via Chronicle events
2. No Chronicle entry modification after inscription
3. No vitality caching during MVP
4. No hardcoded ability behavior — TOML data only
5. No NumPy outside spatial layer, lighting, and AI Influence Maps
6. Undocumented design variables go in `DESIGN_VARIABLES.md` — never silent defaults
7. Post-MVP systems: note in `FUTURE.md`, implement simpler MVP version
8. Never mutate `Combatant.hp` directly — always `Combatant.apply_damage()`
9. Never use raw strings as event keys — use `EVT_*` constants from `engine/combat.py`
10. Never instantiate a global `EventBus` — pass the instance at construction
