# CONTEXT.md — ZEngine Handoff

**Packaged:** February 27, 2026 | **Phase:** 7 (complete) | **Next:** Phase 8 (TBD)

---

## Project / Session Identity

- **Project:** ZEngine — social ecology simulator / party-based roguelike
- **Author:** Zachery (solo indie)
- **Stack:** Python 3.14.3 | python-tcod-ecs | tcod renderer | Pydantic v2 | TOML | JSONL Chronicle
- **Active environment:** Agentic CLI, local filesystem
- **Design status:** v0.17 (Inventory/Items complete)
- **Canonical design reference:** `ZEngine_Manifest_v0_2.pdf` (§1–§7)

---

## Canonical State

### Files that exist

| File                       | Status                                                      |
| -------------------------- | ----------------------------------------------------------- |
| `engine/combat.py`         | Canonical constants and event definitions — Phase 7 updated |
| `engine/loop.py`           | Main Simulation Loop — Phase 7 updated                      |
| `engine/data_loader.py`    | JIT TOML Loaders — Phase 7 updated (ItemDef)                |
| `engine/item_factory.py`   | ECS Item Entity Factory — Phase 7 NEW                       |
| `engine/ecs/components.py` | ECS Component Definitions — Phase 7 updated                 |
| `engine/ecs/systems.py`    | ECS Systems — Phase 7 updated (Inventory systems)           |
| `CONTEXT.md`               | Single source of truth — Phase 7 updated                    |
| `STATE_OF_THE_PROJECT.md`  | Project status and activity log — Phase 7 updated           |
| `DESIGN_VARIABLES.md`      | All confirmed design variables — Phase 7 updated            |
| `FUTURE.md`                | Post-MVP deferred systems — populated                       |
| `DO_NOT_TOUCH.md`          | Phase-locking mechanism — Phase 1 locks applied             |

---

## Decisions & Rationale (Phase 7 Inventory)

### Pure ECS Items
- **Decision:** Items are full ECS entities linked to actors via `IsCarrying` and `IsEquipped` relations.
- **Rationale:** Supports complex inheritance (Lineage), modular anatomy, and high performance via python-tcod-ecs sparse sets.
- **Transaction Pattern:** Pickup/Drop/Equip are atomic systems that verify spatial/anatomical constraints before mutating relations.

### Built-in vs Data-Driven Actions
- **Decision:** `pickup`, `drop`, and `equip` are handled as built-in action types in `action_resolution_system` with hardcoded AP costs (synced with `DESIGN_VARIABLES.md`).
- **Rationale:** Simplifies common interaction logic while maintaining the ability to define specific item-use behaviors in TOML later.

---

## DESIGN_VARIABLES.md — Confirmed Values

```
ENERGY_THRESHOLD            100.0       # turn eligibility; float
AP_POOL_SIZE                100         # resets each turn; matches ENERGY_THRESHOLD scale
AP_COST_PICKUP              10          # inventory action
AP_COST_DROP                10          # inventory action
AP_COST_EQUIP               20          # inventory action
MOVEMENT_ALLOCATION         ceil(100/speed)  # AP per tile; ceiling rounding; speed-derived
SOCIAL_CATCHUP_TICKS        5           # narrative gap; session boundary Social Layer advance
CATCHUP_TRANSITION_CAP      1           # max node state transitions per session boundary
COMBAT_ROLL_DISPLAY         "category"  # "category" | "raw" (configurable flag)
CRIT_THRESHOLD              20          # d20 natural roll
FUMBLE_THRESHOLD            1           # d20 natural roll
BASE_HIT_DC                 10          # default defense class when no stat provided
REPUTATION_OSTRACIZATION   -0.3        # threshold
REPUTATION_COOPERATION      0.4         # threshold
STRESS_EXODUS_THRESHOLD     0.7         # float 0.0–1.0
STRESS_PASSIVE_DECAY_RATE   0.0         # 0.0 = no passive decay
EQUILIBRIUM_BASE_RESISTANCE 40          # range 20–80
CONDUCTION_COEFFICIENT      0.3         # 0.0 disables conduction
CONDUCTION_ATTENUATION      0.6         # per distance unit; range 0.1–0.9
CHRONICLE_SIGNIFICANCE_MIN  2           # minimum inscription threshold; range 1–5
VITALITY_CACHE              NOT_IMPLEMENTED  # stub field; do not read or write MVP
```

---

## Agent Hard Limits (memorize)

1. No direct inter-layer state mutation — all Dungeon→Social changes via Chronicle events
2. No Chronicle entry modification after inscription — corrections are new entries
3. No vitality caching during MVP — stub field present, must not be read or written
4. No hardcoded ability or event behavior — TOML data and tag subscriptions only
5. No NumPy outside spatial layer and lighting
6. Grammar tables are never agent-generated — read only
7. Undocumented design variables go in `DESIGN_VARIABLES.md` — never silent defaults
8. Post-MVP systems: note in `FUTURE.md`, implement simpler MVP version
9. Never mutate `Combatant.hp` directly — always `Combatant.apply_damage()`
10. Never use raw strings as event keys — use `EVT_*` constants from `engine/combat.py`
11. Never instantiate a global `EventBus` — pass the instance at construction
