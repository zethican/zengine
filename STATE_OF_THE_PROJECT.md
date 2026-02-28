# STATE_OF_THE_PROJECT.md

**Last Updated:** 2026-02-27 (Manual Checkpoint v0.17 - Phase 7 Complete)

---

## Quick Status Snapshot

| Aspect                  | Status                  | Details                                                      |
| ----------------------- | ----------------------- | ------------------------------------------------------------ |
| **Current Phase**       | 8 (Crafting)           | ✅ IMPLEMENTED and verified via integration tests             |
| **Phase 8 Status**      | ✅ COMPLETE              | Crafting with lineage merging, AP cost, and inventory cleanup |
| **Next Immediate Task** | Phase 9 (TBD)           | Equipment effects or Item usage                              |
| **Active Agent**        | Ready                   | Phase 8 complete                                             |

---

## What Exists Right Now

### Phase 8 Implementation (Crafting)

- ✅ engine/item_factory.py — `merge_items` with lineage and stat inheritance.
- ✅ engine/ecs/systems.py — `action_resolution_system` handles "craft" action.
- ✅ engine/loop.py — `invoke_ability_ecs` supports flexible payloads for crafting.
- ✅ tests/test_integration_crafting.py — Verified full crafting loop.

### Phase 7 Implementation (Inventory/Items)

- ✅ engine/item_factory.py — ECS Entity Factory for items from TOML blueprints.
- ✅ engine/data_loader.py — Added `ItemDef` schema and JIT loader.
- ✅ engine/ecs/components.py — Added ItemIdentity, Quantity, Equippable, ItemStats, Anatomy, Lineage.
- ✅ engine/ecs/systems.py — Implemented `pickup_item_system`, `drop_item_system`, `equip_item_system`.
- ✅ engine/loop.py — Integrated inventory actions into `invoke_ability_ecs`.
- ✅ tests/test_inventory.py — Unit tests for factory and item systems.
- ✅ tests/test_integration_inventory.py — Integration tests for full inventory transaction loop.

### Phase 6 Implementation (Interactive UI)

- ✅ ui/renderer.py — TCOD terminal renderer.
- ✅ ui/screens.py — Screen State Machine (MainMenu, Exploration, Inventory).
- ✅ native .exe build pipeline via `build_exe.py`.

---

## Recent Activity

### Session: 2026-02-27 (Phase 7: Inventory/Items)

**Completed:**

- Defined Item ECS components (Identity, Stats, Equippable, Anatomy, etc.).
- Implemented TOML-based Item Loader in `data_loader.py`.
- Created `ItemFactory` for entity instantiation.
- Wrote atomic state transition systems (Pickup, Drop, Equip).
- Wired inventory actions into `SimulationLoop` and `ActionResolutionSystem`.
- Verified with 6/6 new tests (unit + integration).
- All 41/41 project tests passing.

---

## Upcoming Milestones

### Phase 8 (TBD)

- [ ] Equipment effect application (stats modification on equip)
- [ ] Item usage (consumables, tools)
- [ ] Crafting / Lineage merging

---

## Hard Limits (Must Never Violate)

1. No direct inter-layer state mutation — all Dungeon→Social via Chronicle events
2. No Chronicle entry modification after inscription
3. No vitality caching during MVP
4. No hardcoded ability behavior — TOML data only
5. No NumPy outside spatial layer and lighting
6. HP mutation only via `apply_damage()`
7. Event keys only via `EVT_*` constants
8. Pass `EventBus` at construction (no global singletons)
