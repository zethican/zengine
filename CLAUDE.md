# CLAUDE.md — ZEngine (ZRogue Engine)

This file is the canonical onboarding document for **Claude Code** working on ZEngine. Read this file at the start of every session before taking any action.

---

## Project Overview

**ZEngine** is a social ecology simulator and party-based roguelike written in Python. The design philosophy is "Mechanics as Narrative" — all gameplay events feed into a persistent, append-only history that drives NPC behavior and world state.

| Aspect | Detail |
|--------|--------|
| **Genre** | Social ecology simulator / party-based roguelike |
| **Stack** | Python 3.11+ · python-tcod-ecs · tcod · Pydantic v2 · TOML · JSONL Chronicle |
| **Current Phase** | 24 (Narrative UI) — ✅ COMPLETE (v0.45) |
| **Next Phase** | 25: Game-Over / Restart Flow |
| **Test Status** | 148 tests passing — `pytest tests/` |
| **Entry Point** | `run.py` |

---

## Repository Layout

```
zengine/
├── engine/               # Core game logic
│   ├── combat.py         # EventBus, EVT_* constants, CombatEngine (Phase 0 canonical — LOCKED)
│   ├── loop.py           # SimulationLoop: wires ECS, EventBus, Chronicle, JIT materialization
│   ├── chronicle.py      # ChronicleInscriber: append-only JSONL journal (LOCKED)
│   ├── social_state.py   # SocialStateSystem: disposition, stress, Apathy Exodus (LOCKED)
│   ├── equilibrium.py    # Equilibrium/conduction math (LOCKED)
│   ├── ai_system.py      # NPC AI decision-making
│   ├── narrative.py      # NarrativeGenerator: prose from events
│   ├── data_loader.py    # Pydantic schemas for TOML loading (AbilityDef, ItemDef, etc.)
│   ├── item_factory.py   # Item instantiation, rarity rolls, affix composition (LOCKED)
│   ├── spawner.py        # Entity spawning from TOML templates
│   └── ecs/
│       ├── components.py # ECS component dataclasses (pure data, no logic)
│       └── systems.py    # Pure system functions (LOCKED)
├── ui/
│   ├── renderer.py       # tcod terminal window setup (LOCKED)
│   ├── screens.py        # UI states: Chronicle, Dialogue, Trade, Inventory
│   └── states.py         # Engine state machine and event loop
├── world/
│   ├── generator.py      # ChunkManager, BSP procedural dungeon gen (LOCKED)
│   ├── territory.py      # TerritoryManager: macro-scale world nodes
│   ├── exploration.py    # ExplorationManager: Fog of War persistence
│   ├── wilderness.py     # Encounter spawn logic
│   └── factions.py       # Faction definitions and relationships
├── data/
│   ├── abilities/        # TOML ability definitions
│   ├── entities/         # TOML entity templates
│   ├── items/            # TOML item/affix/consumable definitions
│   ├── world/            # TOML world chunk and module definitions
│   └── recipes/          # TOML crafting recipes
├── tests/                # 34 pytest test files (95 tests total)
├── sessions/
│   └── chronicle.jsonl   # Append-only event journal (source of truth)
├── run.py                # Game entry point
│
│   # Design documents (read before any session):
├── STATE_OF_THE_PROJECT.md   # Current phase, milestones, recent activity
├── CONTEXT.md                # Canonical design decisions and rationale
├── DESIGN_VARIABLES.md       # All configurable parameters
├── DO_NOT_TOUCH.md           # Phase-locked files — check before editing ANYTHING
├── COMPONENTS.md             # ECS component contracts (Phase 1, LOCKED)
├── EVENTS.md                 # Event taxonomy and payloads (Phase 1, LOCKED)
├── SYSTEMS.md                # System dispatch contracts (Phase 1, LOCKED)
├── FUTURE.md                 # Post-MVP deferred systems
└── AGENT_ONBOARDING.md       # Supplemental agent rituals
```

---

## Session Opening Ritual

Before writing any code, read these files **in order**:

1. `STATE_OF_THE_PROJECT.md` — current phase, what's done, what's next
2. `CONTEXT.md` — all design decisions and rationale
3. `DESIGN_VARIABLES.md` — all configurable parameters
4. `DO_NOT_TOUCH.md` — phase-locked files you must not edit

Then confirm:
- **Current phase** and completion status
- **Which files are locked** for this phase
- **One hard limit** you will enforce this session (rotate through the list below)

Do not write any code until you have confirmed the above.

---

## Development Workflows

### Running the Game
```bash
python run.py
```

### Running Tests
```bash
pytest tests/
```
All 95 tests must pass before committing. Never leave failing tests.

### Smoke Tests (individual modules)
```bash
python engine/combat.py
python engine/chronicle.py
```

### Building a Windows Executable (PyInstaller)
```bash
pyinstaller ZEngine.spec
```
Output lands in `build/ZEngine/`.

---

## Architecture Overview

ZEngine uses a strict **four-layer** architecture. Layers communicate only through the Chronicle and EventBus — never by direct mutation.

```
┌─────────────────────────────────────────────────────┐
│  Dungeon Layer  — combat, exploration, items         │
│  (CombatEngine, SimulationLoop, world/generator.py)  │
├─────────────────────────────────────────────────────┤
│  Chronicle Bridge — append-only JSONL event journal  │
│  (engine/chronicle.py → sessions/chronicle.jsonl)    │
├─────────────────────────────────────────────────────┤
│  Social Layer  — relationships, stress, reputation   │
│  (engine/social_state.py, engine/equilibrium.py)     │
├─────────────────────────────────────────────────────┤
│  Spatial Layer — world map, FOV, lighting            │
│  (world/territory.py, world/exploration.py)          │
│  NumPy is ONLY permitted here.                       │
└─────────────────────────────────────────────────────┘
```

### ECS Pattern
- **Components** (`engine/ecs/components.py`): pure data containers — zero logic
- **Systems** (`engine/ecs/systems.py`): functions that query components and act
- **Cross-system communication**: exclusively via `EventBus` — no direct system-to-system calls

### EventBus
Defined in `engine/combat.py`. Synchronous pub-sub.
```python
bus.subscribe("EVT_ON_DAMAGE", handler)   # or wildcard "*"
bus.emit(event)
```
Always pass `bus` at construction — never instantiate globally.

### Combat Tick Dispatch Order (canonical)
1. **Turn Resolution** — increment `action_energy`
2. **AP Reset** — reset AP pool for eligible actors
3. **Input / AI** — populate `pending-action`
4. **Validation** — check AP affordability
5. **Resolution** — execute action, apply damage/modifiers, emit events
6. **Turn End** — deduct energy, trigger modifier expiry
7. **Encounter State** — check victory/defeat
8. **Chronicle Inscriber** — inscribe all significant events to JSONL

---

## Code Conventions

| Aspect | Convention | Example |
|--------|-----------|---------|
| ECS component tags | kebab-case strings | `"combat-vitals"`, `"entity-identity"` |
| System functions | snake_case | `turn_resolution_system()` |
| Event constants | `EVT_` prefix, UPPER_SNAKE | `EVT_ON_DAMAGE`, `EVT_TURN_ENDED` |
| Classes | PascalCase | `CombatEngine`, `ChronicleInscriber` |
| Data files | TOML (never hardcode) | `data/abilities/basic_attack.toml` |
| Type hints | Strict everywhere | `from __future__ import annotations` |

---

## Hard Limits

Memorize these. Violating any of them breaks architectural integrity.

1. **No direct inter-layer mutation** — all Dungeon→Social changes must go through Chronicle events
2. **Chronicle is immutable** — never modify an entry after inscription; corrections are new entries
3. **No vitality caching** — `VITALITY_CACHE` stub exists; do NOT read or write it during MVP
4. **No hardcoded ability behavior** — TOML data and tag subscriptions only; no `if ability == "fireball"` in Python
5. **NumPy restricted** — only in the Spatial Layer (world gen, lighting, AI Influence Maps)
6. **No silent defaults** — every configurable parameter must be in `DESIGN_VARIABLES.md`
7. **Post-MVP systems** — note in `FUTURE.md`; implement the simpler MVP version only
8. **HP via `apply_damage()` only** — never mutate `Combatant.hp` directly
9. **Event keys via `EVT_*` only** — never use raw strings as event keys
10. **EventBus injected, never global** — always pass the instance at construction time

---

## Phase-Locked Files

**Check `DO_NOT_TOUCH.md` before editing any file.** Modifying locked files without explicit user consent in chat is a critical error.

| Files | Lock Reason |
|-------|-------------|
| `COMPONENTS.md`, `EVENTS.md`, `SYSTEMS.md` | Phase 1 contracts — final |
| `engine/combat.py` | Phase 0 canonical constants — additive only in Phase 8+ |
| `engine/chronicle.py` | Phase 2 implementation — permanently locked |
| `engine/social_state.py` | Phase 2 implementation — permanently locked |
| `engine/equilibrium.py` | Phase 2 implementation — permanently locked |
| `world/generator.py` | Phase 3 implementation — permanently locked |
| `ui/renderer.py` | Phase 6 implementation — permanently locked |
| `engine/item_factory.py` | Phase 7 implementation — locked until Phase 8+ |
| `engine/ecs/systems.py` | Phase 7 update — locked until Phase 8+ |
| `engine/data_loader.py` | Phase 7 update — locked until Phase 8+ |

---

## Data File Conventions

All game content is data-driven via TOML. **Never hardcode ability costs, effects, or entity stats in Python.**

| Directory | Contents |
|-----------|----------|
| `data/abilities/` | Ability definitions (costs, effects, targeting) |
| `data/entities/` | Entity templates (stats, equipment, AI profile) |
| `data/items/` | Weapons, armor, consumables; `affixes/` subdir for prefix/suffix |
| `data/world/` | World chunks, modules, encounter tables |
| `data/recipes/` | Crafting recipes |

**Chronicle:** `sessions/chronicle.jsonl` — append-only. Each line is one JSON event. Never rewrite or truncate.

---

## Design Variables Reference

Key constants from `DESIGN_VARIABLES.md`:

| Variable | Value | Notes |
|----------|-------|-------|
| `ENERGY_THRESHOLD` | 100.0 | Turn eligibility; speed accumulates to this |
| `AP_POOL_SIZE` | 100 | Resets each turn |
| `CRIT_THRESHOLD` | 16 | Natural 2d8 max roll |
| `FUMBLE_THRESHOLD` | 2 | Natural 2d8 min roll |
| `BASE_HIT_DC` | 10 | Default defense class |
| `REPUTATION_OSTRACIZATION` | -0.3 | Below this → NPC refuses interaction |
| `REPUTATION_COOPERATION` | 0.4 | Above this → mutual aid behaviors |
| `STRESS_EXODUS_THRESHOLD` | 0.7 | Party stress ratio that triggers NPC departure |
| `CHRONICLE_SIGNIFICANCE_MIN` | 2 | Min score (1–5) to be inscribed |
| `RARITY_MAGIC_CHANCE` | 0.25 | 25% chance for 1 affix (Magic tier) |
| `RARITY_RARE_CHANCE` | 0.05 | 5% chance for 2 affixes (Rare tier) |

Always check `DESIGN_VARIABLES.md` for the full list before introducing any numeric constant.

---

## Roadmap

| Phase | Status | Goal |
|-------|--------|------|
| 24: Narrative UI | ✅ COMPLETE | Node-based dialogue, Chronicle UI, Fog of War |
| 25: Game-Over Flow| **NEXT** | Terminal game states for player death |
| 26: Pathfinding   | Queued | `tcod.path.AStar` integration in `ai_system.py` |
| Post-25 deferred  | `FUTURE.md` | Quest System, Content Volume, Character Creation |

---

## Session Closing Ritual

Before ending any session:

1. Log any new design variables encountered in `DESIGN_VARIABLES.md`
2. Log any post-MVP considerations discovered in `FUTURE.md`
3. Confirm phase gate status hasn't changed, or update `STATE_OF_THE_PROJECT.md` if it has
4. Update `CONTEXT.md` if any architectural decisions were made or closed-door rationale added

---

## Key Design Decisions (Phase 19 Foundation)

- **Functional Effect Pipeline:** Abilities are collections of atomic `Effect` objects; no `if/else` branches in Python for ability behavior. Future content = new TOML files, zero new Python.
- **Formula Engine:** Magnitude strings like `1d8 + @might_mod` are evaluated at runtime against character stats.
- **Functional Targeting:** `self`, `primary`, `adjacent_all` etc. are reusable functions decoupled from ability logic.
- **JIT Materialization (Phase 21):** Entities exist as Chronicle records outside FOV; only instantiated in ECS on observation.
- **Node-Based Dialogue (Phase 24):** Conversation graphs with conditions, actions, and placeholders — no hardcoded dialogue trees in Python.
