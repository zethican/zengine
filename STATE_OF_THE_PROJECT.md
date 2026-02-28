# STATE_OF_THE_PROJECT.md

**Last Updated:** 2026-02-27 (Manual Checkpoint v0.35 - Tag-Based Functional Overhaul Complete)

---

## Quick Status Snapshot

| Aspect                  | Status                  | Details                                                      |
| ----------------------- | ----------------------- | ------------------------------------------------------------ |
| **Current Phase**       | 19 (Foundation Refactor)| ✅ Tag-Based Functional Ability Pipeline implemented (v0.35) |
| **Phase 19 Status**     | ✅ COMPLETE              | Abilities are now collections of tagged effects; TOML data-driven |
| **Next Immediate Task** | Phase 20: Macro Ecology | Regional Faction Shifts and Territory Control                |
| **Active Agent**        | Ready                   | Action resolution is now generic and extensible              |

---

## Holistic Roadmap (Active Horizon)

### Phase 20: Macro Ecology (Regional Shifts)
- **Goal:** Dynamic regional control using **A Priori Topological Graphing**.
- **Key System:** `TerritoryManager` for graph-based faction control and supply routes.

### Phase 21: Party & Companions (Group Systems)
- **Goal:** Recruiting NPCs into a persistent, controllable party.
- **Key System:** `PartyController` for tactical multi-unit command and collective stress.

### Phase 22: Exploration Memory (Fog of War)
- **Goal:** Persistent memory of explored chunks and discovered POIs.
- **Key System:** `WorldMapState` and chunk bitmask persistence.

---

## What Exists Right Now

### Phase 19 Implementation (Functional Overhaul)

- ✅ engine/loop.py — `apply_effect` and generic functional pipeline (v0.35).
- ✅ engine/ecs/systems.py — `evaluate_formula` supports dice and `@stat_mod` (v0.35).
- ✅ engine/ecs/systems.py — `resolve_effect_targets` for functional targeting patterns (v0.35).
- ✅ engine/data_loader.py — New `EffectDef` and updated `AbilityDef` schemas (v0.35).
- ✅ data/abilities — Migrated all core abilities to the new functional format.

### Phase 18 Implementation (Procedural Affixes)

- ✅ engine/item_factory.py — `create_item` now rolls rarity and applies procedural prefixes/suffixes.
- ✅ engine/data_loader.py — Added `AffixDef` schema and `get_affixes()` loader.

### Phase 17 Implementation (Environmental Modifiers)

- ✅ engine/ecs/systems.py — `environmental_modifier_system` for location-based effects.

---

## Recent Activity

### Session: 2026-02-27 (Phase 19: Foundation Refactor)

**Completed:**

- Implemented **Tag-Based Functional Overhaul (v0.35)**: Abilities are no longer hardcoded branches but collections of atomic, tagged effects.
- Developed **Formula Engine**: magnitudes can now be dynamic strings like `1d8 + @might_mod`, evaluated at runtime.
- Functionalized **Targeting**: patterns like `self`, `primary_target`, and `adjacent_all` are now reusable targeting logic.
- Migrated **Basic Attack, Cleave, and Heal** to the new functional pipeline.
- All 82 project tests passing.

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
