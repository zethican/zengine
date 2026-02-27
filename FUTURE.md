# FUTURE.md — Post-MVP Deferred Systems

**DO NOT ARCHITECT TOWARD THESE DURING MVP PHASES.**

Phase 2+ features, nice-to-haves, and speculative systems are queued below. If you encounter a requirement that appears here, implement the simpler MVP version and note the full vision in this file.

---

## Core Systems (Phase 2+)

### AP Economy & Reaction System
- **Vision:** AP carry-over across turns; reaction pool for interrupt mechanics
- **MVP:** AP resets to full each turn; no reactions
- **Why deferred:** Adds complexity to economy; ARPG kinetic feel mandate is better served by clean reset

### Real-time Social Layer Daemon
- **Vision:** Background NPC simulation runs continuously during dungeon exploration
- **MVP:** Social Layer catch-up tick fires only at session boundary
- **Why deferred:** Post-MVP complexity; MVP approach preserves player agency to react to major events

### Vitality Caching System
- **Vision:** Cached vital stats (HP, stress) to enable fast quests / parallelism
- **MVP:** Stub field present; never read or written
- **Why deferred:** Not required for single-session MVP; revisit for cross-session persistence

### Chronicle Active Epistemology
- **Vision:** Reconciliation daemon; confidence weight adjustment as events are witnessed/disproven
- **MVP:** Write-once Chronicle; confidence static per event
- **Why deferred:** Post-MVP refinement; simple epistemology sufficient for MVP narrative feel

### EventPayload.data Typed Dicts
- **Vision:** Per-event-type TypedDict for `data` field (compile-time type safety)
- **MVP:** `data: Dict[str, Any]` flat dict per `CombatEvent`
- **Phase:** Phase 1 hardening task (possible parallel work)
- **Why deferred:** Not blocking MVP; can be bolted on once event taxonomy stabilizes

---

## Advanced Systems (Phase 3+)

### Faction Hooking
- **Vision:** Reading lore objects in-dungeon automatically updates party faction standing
- **Status:** Queued; requires Phase 3+ world persistence layer
- **Complexity:** Moderate; depends on Chronicle cross-reference system

### Tag-Based Casting (Wildermyth Model)
- **Vision:** Abilities selected via tag subscriptions instead of hardcoded behavior
- **Status:** Long-term goal; MVP uses ability TOML with simpler branching
- **Complexity:** High; affects entire ability resolution architecture

### Ancestor Worship / Healing Legacy
- **Vision:** Deceased party members grant passive bonuses; persistent story beat
- **Status:** Post-MVP narrative layer
- **Complexity:** Medium; requires Chronicle persistence + NPC state recovery

### Gift Economy
- **Vision:** NPC-to-NPC / party-to-NPC gift mechanics driving reputation & faction
- **Status:** Queued for Phase 3+
- **Complexity:** High; requires disposition system overhaul

### Third Gender / Custom Caste System
- **Vision:** Character generation system allowing non-binary and caste-based identity
- **Status:** Deferred for cultural representation pass
- **Complexity:** Medium-high; affects lore generation and NPC relation constraints

### Blue Prince Mode
- **Vision:** Permadeath + ironman mechanics; single-save run
- **Status:** Post-MVP mode; requires robust save/load infrastructure
- **Complexity:** Low-moderate; orthogonal to core systems

---

## World & Procedural Generation (Phase 3+)

### Cross-Session World Persistence
- **Vision:** Dungeon state, NPC locations, faction stands persist across save/load
- **Status:** Requires Chronicle JSONL persistence + spatial snapshot recovery
- **Complexity:** High; depends on Phase 2 Chronicle completion

### Ruin Recovery
- **Vision:** Collapsed locations become reclamable dungeons with loot scaling
- **Status:** Post-MVP world evolution mechanic
- **Complexity:** Moderate; requires encounter density + procedural scaling

### Cross-Faction Social Conduction
- **Vision:** Rival faction stress cascades propagate between groups
- **Status:** Advanced feature; requires faction graph + conduction routing
- **Complexity:** High; architectural refactor to conduction system

### NPC AI Goal-and-Tactic Planning
- **Vision:** NPCs pursue multi-turn objectives; dynamic alliance breaking
- **Status:** Post-MVP behavioral layer
- **Complexity:** Very high; full planning system required

---

## UI & UX (Phase 6+)

### Combat Roll Display Toggle
- **Vision:** Player-selectable "raw" (rolls) vs. "category" (outcome) display
- **Default:** "category" (established in Phase 0)
- **Status:** Phase 6 UI pass; low priority for MVP
- **Complexity:** Minimal; already architected in `combat.py`

### Real-time Mood Visualization
- **Vision:** NPC disposition auras; stress levels visible in dungeon
- **Status:** Post-MVP polish
- **Complexity:** Moderate; tcod rendering + stat tracking

---

## Data & Content (Phase 4+)

### Grammar Table Generation
- **Vision:** AI-generated grammar tables for story beats
- **Status:** READ-ONLY tables only during MVP; agent never generates
- **Why restricted:** Ensures narrative control; human-authored content only

### Ability TOML Authoring
- **Vision:** Comprehensive ability library; stress deltas, animation cues, tag subscriptions
- **Status:** Phase 4 content pass
- **Complexity:** High volume; low-per-item complexity

### Chronicle Significance TOML
- **Vision:** Per-event-type significance and confidence defaults
- **Status:** Phase 4 content pass
- **Depends on:** Chronicle system stabilization

---

## Known Speculations (Exploratory)

- Procedural legend generation (character backstories from encounters)
- Permadeath + mourning mechanics (party grieves fallen members)
- NPC apprenticeship (recruit enemies as allies)
- Cross-party alignment (faction reputation affects party starting standing)
- Item corruption (cursed gear as narrative hooks)
- Ancestor visions (deceased party members appear as guides)

---

## How to Use This File

1. **If you discover a "nice to have"** → Add it here with Vision, Status, Complexity
2. **If you're asked to implement a deferred system** → Note it here, implement simpler MVP version
3. **Before Phase 2 starts** → Revisit, prioritize, and move top items to CONTEXT.md decisions
4. **Agent closing ritual** → Check this file; confirm no new post-MVP items were sneaked into MVP scope
