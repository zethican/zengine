# DO_NOT_TOUCH.md — Phase-Locked Files

**Check this file before editing ANY file.** Files listed here are locked for the current phase and must not be modified without explicit user consent in chat.

---

## Phase 1 (Complete — Locked)

**Status:** Phase 1 contracts are final. All three documents are peer-reviewed and approved. No further modifications permitted without user sign-off and a logged rationale.

| File | Reason | Unlocked in |
| ---- | ------ | ----------- |
| `COMPONENTS.md` | Phase 1 contract — ECS component taxonomy finalized | Phase 3 (new component layers only) |
| `EVENTS.md` | Phase 1 contract — Event catalog and typed payloads finalized | Phase 2 (Post-Phase-1 Discoveries section only) |
| `SYSTEMS.md` | Phase 1 contract — System dispatch contracts finalized | Phase 3 (new system layers only) |
| `engine/combat.py` | Canonical Phase 0 stub — only extend; never restructure | Phase 2 (additive only; no signature changes) |

**Allowed writes to locked files:**
- `EVENTS.md` → append to `## Post-Phase-1 Discoveries` section only
- `SYSTEMS.md` → append to `## Post-Phase-1 Discoveries` section only
- `COMPONENTS.md` → append to `## Post-Phase-1 Discoveries` section only
- `engine/combat.py` → additive imports and extensions; no changes to existing signatures or EVT_* constants

**Prohibited:**
- Changing field names, types, or cardinality in any component definition
- Adding or removing EVT_* constants from combat.py
- Reordering the canonical dispatch sequence in SYSTEMS.md
- Modifying the turn resolution sequence in EVENTS.md

---

## Phase 2 (Active)

**Status:** Implementation underway. Files below are in active development and must not be pre-created or stubbed ahead of their designated system.

| File | Reason | Locked Until |
| ---- | ------ | ------------ |
| `world/generator.py` | Phase 3 — do not create | Phase 3 start |
| `world/wilderness.py` | Phase 3 — do not create | Phase 3 start |
| `data/abilities/` | Phase 4+ — TOML ability tables | Phase 4 start |
| `data/grammar/` | Phase 4+ — grammar tag tables | Phase 4 start |
| `data/templates/` | Phase 4+ — entity templates | Phase 4 start |
| `data/chronicle_significance.toml` | Phase 4+ — Chronicle significance config | Phase 4 start |
| `sessions/chronicle.jsonl` | Runtime artifact — created at game start | Runtime |
| `sessions/spatial_snapshot.toml` | Runtime artifact — created at game start | Runtime |

---

## Phase 2 Target Files (Create in Phase 2 Only)

These files do not exist yet. They are the Phase 2 deliverables. Do not create them ahead of the corresponding implementation task.

| File | System |
| ---- | ------ |
| `engine/chronicle.py` | Chronicle write/query interface (append-only JSONL) |
| `engine/social_state.py` | Social State schema and transition logic |
| `engine/equilibrium.py` | Vitality, Taper formula, conduction |
| `engine/ecs/` | ECS component and system definitions |
| `ui/renderer.py` | tcod terminal renderer |

---

## How This Works

1. **Before every session:** Read this file. Respect all locks.
2. **If you need to modify a locked file:** Stop. Ask in chat. Do not proceed without explicit user consent.
3. **If you need to modify a locked file AND user consents:** Log the change in the locked file's `## Post-Phase-N Discoveries` section.
4. **At Phase N → Phase N+1 transition:** Old production locks expire; new pre-creation locks applied.
5. **If a lock seems wrong:** Flag it; do not silently violate it.

---

## Current Phase Status

- **Active Phase:** 2 (implementation)
- **Previous Phase:** 1 (contracts — complete and locked)
- **Phase 2 Deliverables:** engine/chronicle.py, engine/social_state.py, engine/equilibrium.py, engine/ecs/, ui/renderer.py
- **Phase 2 Exit Gate:** All five implementation targets functional; smoke tests pass; no hard limit violations
