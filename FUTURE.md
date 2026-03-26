# FUTURE.md — Post-MVP Deferred Systems & Active Roadmap

This document serves as the strategic roadmap for ZEngine. It has been reorganized to incorporate the comprehensive Gap Analysis between ZEngine and genre touchstones (Caves of Qud / Project Zomboid).

---

## Deferred Advanced Systems (High Architectural Cost)

These systems are recognized gaps but must not interrupt the execution of the Active Roadmap.

### NPC Off-Screen Simulation
- **Vision:** Run factions and NPCs outside of the player's immediate engagement range.
- **Status:** Deferred until World-State flags are hardened.

### Crafting Depth & Economy
- **Vision:** Supply/demand driven item pricing and equipment durability loops.
- **Status:** Deferred until Content Volume supports a robust economy.

### Wilderness / Biome Depth
- **Vision:** Per-biome spawn tables, noise-blended biome seams, and dynamic weather hazards.
- **Status:** Deferred (Cosmetic until late stage).

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