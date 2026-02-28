# FUTURE.md — Post-MVP Deferred Systems

**DO NOT ARCHITECT TOWARD THESE DURING MVP PHASES.**

Phase 2+ features, nice-to-haves, and speculative systems are queued below. If you encounter a requirement that appears here, implement the simpler MVP version and note the full vision in this file.

---

## Active Roadmap (Phases 19-25)

### Faction Territories & Shifts (Meaningful Emergence)
- **Vision:** Dynamic regional control using **A Priori Topological Graphing**. Instead of stochastic physical partitioning, we define the "Theory of the Place" (faction nodes, supply paths, contested locks/keys) as a conceptual graph *before* geometry is generated.
- **Status:** **UP NEXT** (Phase 20).
- **Complexity:** High; requires a graph-solving pass before `world/generator.py` materializes tiles.

### JIT Materialization (Lazy Instantiation)
- **Vision:** Transition from chunk-buffered generation to true JIT instantiation. Entities and tiles only materialize in the ECS registry at the "moment of observation" (within FOV). Outside the player's bubble, entities exist only as `Chronicle` records or world-seed rules.
- **Status:** Queued for Phase 21.
- **Complexity:** High; requires decoupling the `SimulationLoop` from active spatial chunks.

### Party Management System
- **Vision:** Recruiting NPCs into a persistent party; tactical control of multiple units; party-shared inventory and collective stress.
- **Status:** Queued for Phase 22.
- **Complexity:** High; requires UI overhaul and AI sub-agent logic.

### Exploration Memory (Fog of War)
- **Vision:** Persistent "fog" or memory of explored chunks; map UI for visited areas.
- **Status:** Queued for Phase 23.
- **Complexity:** Moderate; requires bitmask persistence per world chunk.

### Narrative Expression (Chronicle UI)
- **Vision:** In-game "History" or "Legacy" screen that interprets the JSONL log into readable prose for the player.
- **Status:** Queued for Phase 24.
- **Complexity:** Moderate; requires significance-based filtering.

---

## Core Systems (Completed or Hardened)

### Cross-Session World Persistence
- **Status:** ✅ COMPLETED (v0.22)
- **Detail:** Entities, stats, recursive inventory, and faction standings now persist via spatial snapshots. Deterministic world seed handles chunk recovery.

### Reactive Modifier System
- **Status:** ✅ COMPLETED (v0.31)
- **Detail:** Entities support multiple buffs/debuffs; reactive on-hit triggers; consumable self-application.

### Procedural Affix System
- **Status:** ✅ COMPLETED (v0.34)
- **Detail:** Diablo-style tiered rarity (Common, Magic, Rare) with prefixes and suffixes.

---

## Deferred Advanced Systems (Post-Phase 25)

### AP Economy & Reaction System
- **Vision:** AP carry-over across turns; reaction pool for interrupt mechanics.
- **Why deferred:** Adds complexity to economy; ARPG kinetic feel mandate is better served by clean AP reset.

### Real-time Social Layer Daemon
- **Vision:** Background NPC simulation runs continuously during dungeon exploration.
- **Why deferred:** Post-MVP complexity; current approach preserves player agency to react to major events.

### Tag-Based Casting (Wildermyth Model)
- **Vision:** Abilities selected via tag subscriptions instead of hardcoded behavior.
- **Complexity:** High; affects entire ability resolution architecture.

### Third Gender / Custom Caste System
- **Vision:** Character generation system allowing non-binary and caste-based identity.
- **Status:** Deferred for a focused cultural representation pass.

---

## Known Speculations (Exploratory)

- **Procedural Legend Generation:** character backstories generated from encounter history.
- **NPC Apprenticeship:** recruiting former enemies as specialized allies.
- **World Eras:** world state shifts drastically after major narrative milestones (Cycle completion).
- **Item Corruption:** cursed gear acting as narrative and mechanical hooks.

---

## How to Use This File

1. **If you discover a "nice to have"** → Add it here with Vision, Status, Complexity.
2. **If you implement a deferred system** → Move it to "Active Roadmap" or "Completed".
3. **Agent closing ritual** → Check this file; confirm no new post-MVP items were sneaked into MVP scope.
