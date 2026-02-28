# DO_NOT_TOUCH.md — Phase-Locked Files

**Check this file before editing ANY file.** Files listed here are locked for the current phase and must not be modified without explicit user consent in chat.

---

## Phase 1–6 (Complete — Locked)

**Status:** Phase 1–6 contracts and implementations are final. No further modifications permitted without user sign-off.

| File | Reason | Unlocked in |
| ---- | ------ | ----------- |
| `COMPONENTS.md` | Phase 1 contract — ECS component taxonomy finalized | Phase 3 (new component layers only) |
| `EVENTS.md` | Phase 1 contract — Event catalog and typed payloads finalized | Phase 2 (Post-Phase-1 Discoveries section only) |
| `SYSTEMS.md` | Phase 1 contract — System dispatch contracts finalized | Phase 3 (new system layers only) |
| `engine/combat.py` | Canonical Phase 0 constants — Phase 7 additive only | Phase 8+ (additive only) |
| `engine/chronicle.py` | Phase 2 implementation — Chronicle write/query | Locked |
| `engine/social_state.py` | Phase 2 implementation — Social State logic | Locked |
| `engine/equilibrium.py` | Phase 2 implementation — Equilibrium math | Locked |
| `world/generator.py` | Phase 3 implementation — BSP World Gen | Locked |
| `ui/renderer.py` | Phase 6 implementation — TCOD Renderer | Locked |

---

## Phase 7 (Complete — Locked)

**Status:** Phase 7 Inventory/Items system is complete and verified. 

| File | Reason | Locked Until |
| ---- | ------ | ------------ |
| `engine/item_factory.py` | Phase 7 implementation — Item Factory | Phase 8+ |
| `engine/ecs/systems.py` | Phase 7 updated — Inventory Systems | Phase 8+ |
| `engine/data_loader.py` | Phase 7 updated — ItemDef schema | Phase 8+ |

---

## Phase 8 (TBD)

**Status:** Awaiting start. 

---

## How This Works

1. **Before every session:** Read this file. Respect all locks.
2. **If you need to modify a locked file:** Stop. Ask in chat. Do not proceed without explicit user consent.
3. **At Phase N → Phase N+1 transition:** Old production locks expire; new pre-creation locks applied.
