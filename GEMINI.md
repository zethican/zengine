# GEMINI.md — ZEngine (ZRogue Engine) Context

This document serves as the foundational instructional context for the **ZRogue Engine (ZEngine)** project. It is intended to guide Gemini and other AI agents in maintaining architectural integrity and adhering to established design contracts.

---

## Project Overview

**ZEngine** is a social ecology simulator and party-based roguelike. It focuses on procedural generation, narrative persistence, and a reactive social layer. The project is currently in **Phase 2 (Implementation)**, following a completed and locked **Phase 1 (Design Contracts)**.

- **Stack:** Python 3.14.3
- **ECS:** `python-tcod-ecs` (sparse-set ECS with strong type-hinting)
- **Renderer:** `tcod` (terminal-based UI)
- **Data & Events:** Pydantic v2 (for typed models and event bus)
- **Persistence:** JSONL-based "Chronicle" (append-only narrative journal)
- **Design Philosophy:** "Mechanics as Narrative" — all gameplay events feed into a persistent history.

---

## Architecture & Layers

1. **Dungeon Layer:** Traditional roguelike combat and exploration. Managed by `CombatEngine`.
2. **Social Layer:** Reactive ecology where entity relationships and reputations shift. Managed by `social_state_system`.
3. **Chronicle:** The bridge between layers. Every significant event is inscribed as an immutable record. Append-only JSONL.
4. **Spatial Layer:** World map and territory management. NumPy permitted here for spatial math and lighting.

---

## ECS Architecture (python-tcod-ecs)

ZEngine follows a strict ECS pattern:

- **Components:** Pure data containers (defined in `COMPONENTS.md`). No logic.
- **Systems:** Functions or classes that query components and perform logic (defined in `SYSTEMS.md`).
- **Communication:** Systems communicate exclusively via the **EventBus**. No direct cross-system calls.

### Canonical Dispatch Order (Combat Tick)

1. **Turn Resolution:** Increment `action_energy`.
2. **AP Reset:** Reset AP pool for eligible actors.
3. **Input/AI:** Populate `pending-action`.
4. **Validation:** Check AP affordability.
5. **Resolution:** Execute action, apply damage/modifiers, emit events.
6. **Turn End:** Deduct energy, trigger modifier expiry.
7. **Encounter State:** Check victory/defeat.
8. **Chronicle Inscriber:** (Reactive) Inscribe all significant events.

---

## Building and Running

### Prerequisites

- **Python 3.14.3** is the mandatory runtime version.
- **Dependencies:** `pydantic`, `tcod`, `python-tcod-ecs`, `numpy` (limited use).

### Key Commands

- **Run Smoke Tests:** Execute engine files directly to trigger built-in smoke tests.
  
  ```bash
  py engine/combat.py
  py engine/chronicle.py
  ```
- **Linting & Type Checking:** (TODO: Add project-specific commands). Ensure strict type-hinting is maintained.

---

## Development Conventions & Hard Limits

### Core Mandates (from AGENT_ONBOARDING.md)

1. **No Direct Inter-Layer Mutation:** All Dungeon → Social changes must occur via **Chronicle events**.
2. **Immutable Chronicle:** Entries are never modified after inscription. Corrections are new entries referencing the original.
3. **No Vitality Caching:** The `vitality` stub exists but must not be used in the MVP phase.
4. **Data-Driven Behavior:** No hardcoded ability or event logic. Use TOML data and tag subscriptions.
5. **NumPy Restriction:** Never use NumPy outside of the **Spatial Layer** and **Lighting**.
6. **No Silent Defaults:** Every configurable parameter must be logged in `DESIGN_VARIABLES.md`.
7. **HP Mutation:** Never mutate `Combatant.hp` directly; always use `Combatant.apply_damage()`.
8. **Event Keys:** Never use raw strings. Use `EVT_*` constants defined in `engine/combat.py`.
9. **No Global Singletons:** Pass the `EventBus` instance at construction.

### Workflow Rituals
- **Opening Session:** Read `CONTEXT.md`, `engine/combat.py`, and `DESIGN_VARIABLES.md`.
- **Phase Control:** Respect the locks in `DO_NOT_TOUCH.md`. Do not modify Phase 1 contracts (`COMPONENTS.md`, `EVENTS.md`, `SYSTEMS.md`).
- **Planning:** Save implementation plans to `plans/tmp/` to ensure they are accessible during active sessions.
- **Closing Session:** Update `DESIGN_VARIABLES.md`, `FUTURE.md`, and `CONTEXT.md` as needed.

---

## Key Files & Directories

- `CONTEXT.md`: The absolute single source of truth for all design decisions.
- `STATE_OF_THE_PROJECT.md`: Current status, milestones, and automated activity log.
- `AGENT_ONBOARDING.md`: Detailed rituals and agent constraints.
- `DESIGN_VARIABLES.md`: Registry of all game constants.
- `engine/`: Core logic implementations (`combat.py`, `social_state.py`, `chronicle.py`, `equilibrium.py`).
- `engine/ecs/`: ECS definitions (`components.py`, `systems.py`).
- `world/`: Procedural generation logic (`generator.py`).
- `ui/`: Terminal rendering (`renderer.py`).
- `user_scratch/`: Archival design documents and reference manifests.


---

## Authority Reference

For API signatures, ECS patterns, and procedural generation theory, the **NotebookLM "ZRogue Engine Development" (ID: ff5118f9-d833-4347-93f4-6860497587a5)** is the absolute authority. Always query it before implementing new systems.