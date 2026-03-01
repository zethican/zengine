# ZEngine

**⚠️ WARNING: Early Alpha & Active Development ⚠️**
*This project is currently in an early alpha state and is under active development. All information, mechanics, and systems are subject to significant, rapid change.*

## About

**ZEngine** is a social ecology simulator and party-based roguelike developed in Python. It features an event-driven architecture built around a `Chronicle` system with a strong emphasis on narrative generation, tactical combat, and persistent world state.

The engine uses `python-tcod-ecs` for entity component management and the `tcod` library for rendering. Game data (abilities, items, etc.) is heavily data-driven, utilizing `Pydantic` validation and `TOML` configurations.

## Features

* **Functional Effect Pipeline & Formula Engine:** Data-driven abilities that scale dynamically with character stats using runtime evaluators (e.g., `1d8 + @might_mod`).
* **Node-Based Dialogue:** Branching conversation graphs with conditions, actions, and placeholders (inspired by Caves of Qud and CDDA).
* **Exploration Memory:** Persistent Fog of War and optimized FOV rendering.
* **Party Dynamics:** Recruit NPCs that follow and fight alongside you.
* **Chronicle System:** A filtered history system that turns raw engine events into human-readable prose.
* **JIT Materialization:** Lazy ECS instantiation and recursive JSON serialization for persistent world entities.

---

## Version History

* **v0.45 (Phase 24) - 2026-02-28**
  * **Narrative UI Complete:** Implemented Node-Based Dialogue graphs (conditions, actions, placeholders).
  * **Chronicle UI:** Added a human-readable history screen that translates raw event streams into meaningful prose via `NarrativeGenerator`.

* **v0.42 (Phase 23)**
  * **Exploration Memory:** Added `ExplorationManager` for persistent Fog of War.
  * Optimized FOV rendering with a restrictive algorithm centered on the player.

* **v0.40 (Phase 22)**
  * **Party & Companions:** Introduced `PartyMember` component and follower AI logic (`recruit_npc_system`).

* **v0.38 (Phase 21)**
  * **JIT Materialization:** Implemented `manage_entity_lifecycle` for lazy ECS instantiation and recursive JSON-based serialization for persistent entities.

* **v0.36 (Phase 20)**
  * **Territory & Factions:** `TerritoryManager` a priori topological graphing. `FactionSystem` and relationship matrices.

* **v0.35 (Phase 19) - 2026-02-27**
  * **Tag-Based Functional Overhaul Complete:** Abilities migrated to collections of atomic `Effect` objects instead of hardcoded branches.
  * **Formula Engine:** Added runtime evaluator for magnitude strings.
  * **Functional Targeting:** Reusable targeting logic (self, primary, adjacent_all) decoupled from effect execution.

---

## Roadmap

* **Phase 25: Game-Over Flow** — Terminal states and player death recovery.
* **Phase 26: Pathfinding** — `tcod.path.AStar` integration in AI system.
* **Phase 27: Player Progression** — XP, levels, and attribute growth.
