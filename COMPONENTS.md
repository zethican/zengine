# COMPONENTS.md — ECS Component Contracts

**Phase 1 Deliverable: Component taxonomy and data contracts**
**Status:** ✅ Final
**Last Updated:** 2026-02-27

---

## Overview

This document defines all ECS component types for the python-tcod-ecs entity system. Each component is a data container; systems query for entities with specific component combinations and operate on them.

**Guiding principle:** Components are data only. No logic lives in components. All behavior is in systems.

---

## Component Definition Template

Each component is documented with:

- **Component Name** — kebab-case identifier (e.g., `combat-vitals`)
- **Data Fields** — typed attributes with defaults/constraints
- **Lifecycle** — creation, modification, destruction rules
- **Read By** — systems that query this component
- **Written By** — systems that mutate this component
- **Immutability** — fields that lock after creation (if any)
- **Phase Gate** — which phase introduces this component

---

## METADATA LAYER

Components that define entity identity, type, and history references.

### `entity-identity`

**Fields:**
```
entity_id: int                          # Unique entity ID (assigned at creation)
name: str                               # Display name (mutable; may change in social events)
archetype: str                          # immutable; "Brute" | "Standard" | "Skirmisher" | "NPC" | "Legacy"
is_player: bool                         # immutable; true for PC, false for NPC/foe
legacy_actor_id: Optional[int]          # Reference to Chronicle legacy actor if this is a named NPC
template_origin: Optional[str]          # TOML template used to generate this entity (e.g., "templates/tier2_skirmisher")
```

**Lifecycle:** Created at entity spawn; `archetype` and `is_player` never change. `name` can shift via social events (ritual renaming, shame mechanics—post-MVP).

**Read By:** Renderer (display), encounter logging, Chronicle inscriber

**Written By:** Entity factory, Chronicle epistemology system (post-MVP renaming)

**Phase:** 1

---

### `chronicle-reference`

**Fields:**
```
inscribed_events: List[int]             # IDs of Chronicle events mentioning this entity
significance_score: float               # Cumulative significance; range 0.0–1.0
last_inscribed_at: Optional[float]      # Timestamp of most recent Chronicle mention
```

**Lifecycle:** Created empty when entity spawns. Updated by Chronicle system when events are inscribed. Never manually mutated.

**Read By:** Chronicle system (query for "who is this entity?"), UI (display reputation/renown)

**Written By:** Chronicle inscriber system (when EVT_* events fire)

**Immutability:** `inscribed_events` is append-only

**Phase:** 2 (Chronicle implementation)

---

## SPATIAL LAYER

Components for position, movement, and spatial constraints.

### `position`

**Fields:**
```
x: int                                  # Current x coordinate
y: int                                  # Current y coordinate
terrain_type: str                       # "floor" | "wall" | "water" | "rubble" (terrain class at this position)
```

**Lifecycle:** Created at entity spawn. `x`, `y` mutated by movement system. `terrain_type` read from world chunk; only changes if entity moves to different chunk.

**Read By:** Renderer, collision system, encounter spawn logic, visibility/FOV

**Written By:** Movement system (resolve_movement action)

**Phase:** 2

---

### `movement-stats`

**Fields:**
```
speed: float                            # Base speed attribute; affects action energy gain rate
movement_ap_cost: int                   # Calculated AP cost per tile; ceil(100 / speed)
can_occupy_terrain: List[str]           # List of terrain types this entity can walk on (e.g., ["floor", "water"])
```

**Lifecycle:** Created at entity spawn. Immutable during MVP (speed defines archetype; derived `movement_ap_cost` computed once).

**Read By:** Turn resolution (action energy tick), movement validator, UI (tooltip "cost: X AP/tile")

**Written By:** Entity factory only (during construction)

**Immutability:** All fields immutable after creation

**Phase:** 1

---

### `visible-position` (runtime cache)

**Fields:**
```
visible_to_player: bool                 # Whether player's FOV includes this entity
last_seen_at: Optional[Tuple[int, int]] # Last known position if entity left FOV
```

**Lifecycle:** Updated every frame during visibility calculation. Reset when entity moves out of FOV.

**Read By:** Renderer (draw only visible entities), player input validation

**Written By:** Visibility system (FOV calculation)

**Note:** This is a cached component; not persisted to save files.

**Phase:** 2

---

## COMBAT LAYER

Components for turn resolution, action economy, and encounter state.

### `combat-vitals`

**Fields:**
```
hp: int                                 # Current hit points
max_hp: int                             # immutable; maximum HP
is_dead: bool                           # Cached flag; true if hp <= 0
```

**Lifecycle:** Created with max_hp set at entity spawn. `hp` mutated only via `Combatant.apply_damage()` method (hard limit #9). `is_dead` updated when EVT_ON_DEATH fires.

**Read By:** Combat engine (damage calculation), renderer (health bar), turn eligibility checks

**Written By:** Combatant.apply_damage() only (via combat.py); triggered by EVT_ON_DAMAGE emission

**Immutability:** `max_hp` immutable; `hp` mutable only through apply_damage(); `is_dead` is derived (updated on death event)

**Hard Limit:** Never write `hp` directly. Always use `Combatant.apply_damage()` to enforce event emission.

**Phase:** 1

---

### `action-economy`

**Fields:**
```
action_energy: float                    # Accumulates from speed; checked against ENERGY_THRESHOLD
ap_pool: int                            # Action Points for this turn; resets to AP_POOL_SIZE each turn
ap_spent_this_turn: int                 # Tracking for display and undo (post-MVP)
turn_number: int                        # Which turn this entity last acted on
```

**Lifecycle:** Created at spawn. `action_energy` ticked upward by turn resolution system. `ap_pool` reset to AP_POOL_SIZE at start of entity's turn; `ap_spent_this_turn` reset simultaneously.

**Read By:** Turn eligibility check, action validator (can afford this ability?), UI (AP bar)

**Written By:** Turn resolution system, action resolution system

**Design Variable References:** `ENERGY_THRESHOLD` (100.0), `AP_POOL_SIZE` (100)

**Phase:** 1

---

### `combat-stats`

**Fields:**
```
attack_bonus: int                       # Adds to attack roll (2d8 + this)
defense_bonus: int                      # Adds to defense class (BASE_HIT_DC + this)
damage_bonus: int                       # Adds to raw damage dealt
armor_class: int                        # Alternative to defense_bonus; may be unused in MVP
resistances: Dict[str, int]             # Resist types → reduction (e.g., {"fire": 5}); post-MVP
```

**Lifecycle:** Created at spawn from archetype template. Modified by modifier system (temporary buffs/debuffs via Modifier.add_modifier()). Base stats immutable; modifiers overlay them.

**Read By:** Combat engine (attack/defense roll calculation), UI (stat display)

**Written By:** Modifier system (Combatant.add_modifier() adds, modifier expiry removes)

**Immutability:** Base stats immutable; modifiers are separate component

**Phase:** 1

---

### `active-modifiers`

**Fields:**
```
modifiers: List[Modifier]               # List of active Modifier instances
modifier_ids: List[str]                 # Named references (e.g., ["Blessing of Swiftness", "Curse of Weakness"])
```

**Lifecycle:** Created empty at spawn. Modifiers added via `add_modifier()` and removed when they expire (self-expiring via event subscription). See `combat.py::Modifier` for expiry mechanics.

**Read By:** Combat stats resolver (overlay modifiers on base stats), renderer (display active buffs), modifier ticker

**Written By:** Modifier lifecycle system (add on ability cast, remove on expiry event)

**Hard Limit:** Modifiers are self-expiring event-driven; they declare `expires_on: List[str]` events and remove themselves when triggered. Engine never manages modifier duration.

**Phase:** 1

---

## SOCIAL LAYER

Components for disposition, stress, faction standing, and NPC relationships. **All mutations must emit Chronicle events** (hard limit #1).

### `social-identity`

**Fields:**
```
npc_faction: str                        # "Seekers" | "Beholders" | "Lost" | ... (faction allegiance)
caste: str                              # "high" | "low" | "none"; archaic caste system from lore; post-MVP customization
pronouns: str                           # Display pronouns; "they/them" default; post-MVP expansion to third gender
```

**Lifecycle:** Set at NPC creation from lore templates. Immutable during MVP (caste/pronouns are narrative anchors).

**Read By:** Chronicle scribe (lore generation), NPC AI (faction-aware behavior—Phase 3+), renderer (display name with faction tag)

**Written By:** Entity factory only (during NPC generation from template)

**Immutability:** All fields immutable during MVP

**Phase:** 2

---

### `disposition`

**Fields:**
```
reputation: float                       # Range -1.0 to +1.0; party standing with this NPC
moral_weight: float                     # Range 0.0 to 1.0 (default 0.5); governs lore description register
baseline_mood: str                      # "cheerful" | "neutral" | "grim" | "hostile"; read from Chronicle lore fragments
mood_modifiers: Dict[str, float]        # Temporary mood shifts (e.g., {"grief": -0.2, "inspired": +0.1})
resilience: float                       # Range 0.0 to 1.0 (default 1.0); absorbs stress deltas before stress accumulates
```

**Field Distinctions (critical — never conflate; from manifest §2 Contract 2):**
- `reputation` — written by social interaction systems; drives behavioral consequences and Apathy Exodus
- `moral_weight` — written by Chronicle reconciliation ONLY; governs lore description register; never written by combat or social systems
- `resilience` — absorbs stress deltas (DOS2 binary armor model adapted for stress); depletes under pressure, recovers at rest in high-vitality nodes
- `baseline_mood` — read from Chronicle lore fragments; not a live computed value

**Lifecycle:** Created from lore template with `moral_weight = 0.5`, `resilience = 1.0`. `reputation` mutated by disposition system. `mood_modifiers` updated by conduction system. `moral_weight` updated by Chronicle reconciliation only (Phase 2+). `resilience` depletes when stress deltas land; recovers at session boundary in high-vitality nodes.

**Read By:** NPC AI (behavior selection), encounter spawner (ally vs. enemy), Combat engine (disposition-based ability costs—post-MVP), renderer (NPC color tint by mood), lore generator (moral_weight governs register)

**Written By:**
- `reputation` → social state system (on significant events)
- `moral_weight` → Chronicle reconciliation system ONLY
- `mood_modifiers` → conduction system (mood propagation)
- `resilience` → stress absorption system (Phase 2)

**Event Requirement:** All `reputation` mutations emit `EVT_SOCIAL_DISPOSITION_SHIFT` (hard limit #1). `moral_weight` mutations never emit combat events — Chronicle reconciliation only.

**Thresholds (from DESIGN_VARIABLES.md):**
- Ostracization: reputation < -0.3 → NPC refuses interaction
- Cooperation: reputation > 0.4 → mutual aid behaviors

**Phase:** 2

**Note (Phase 1 discovery):** `moral_weight` and `resilience` surfaced from manifest §2 Contract 2 during SYSTEMS.md drafting. Added here to keep COMPONENTS.md as ground truth. Confirm field behavior with `engine/social_state.py` implementation in Phase 2.

---

### `stress`

**Fields:**
```
stress_level: float                     # Range 0.0 (calm) to 1.0 (breaking point)
stress_sources: Dict[str, float]        # Tracking where stress came from (e.g., {"combat": 0.3, "loss": 0.4})
passive_decay_enabled: bool             # If true, stress decays passively (post-MVP); MVP always false
exodus_risk: float                      # Calculated likelihood of leaving party (if stress > STRESS_EXODUS_THRESHOLD)
```

**Lifecycle:** Created at 0.0 for all entities. Incremented by combat events, deaths, social failures. MVP: no passive decay (stress sticks). Post-MVP: decay configurable via STRESS_PASSIVE_DECAY_RATE.

**Read By:** Party cohesion tracker, encounter spawner (stressed NPCs behave differently), renderer (stress meter), AI decision tree (exodus checks—Phase 3+)

**Written By:** Combat system (EVT_ON_DAMAGE → stress spike), social system (disposition failure → stress), conduction system (peer stress propagation)

**Event Requirement:** All mutations emit `EVT_SOCIAL_STRESS_SPIKE` (hard limit #1)

**Thresholds (from DESIGN_VARIABLES.md):**
- Exodus: stress > 0.7 → NPC considers leaving party

**Design Variable:** `STRESS_PASSIVE_DECAY_RATE = 0.0` (no decay in MVP)

**Phase:** 2

---

### `faction-standing`

**Fields:**
```
faction: str                            # Current primary faction (immutable; NPC's home faction from social-identity)
standing: Dict[str, float]              # Per-faction standing; range -1.0 to +1.0 (e.g., {"Seekers": 0.6, "Beholders": -0.2})
```

**Lifecycle:** Created at spawn with home faction at 0.0; other factions also 0.0. Updated by social conduction and lore hooks (faction hooking—Phase 3+).

**Read By:** Encounter spawner (faction alignment affects party assembly), NPC AI (faction goals—Phase 3+), Chronicle epistemology (plot alignment—Phase 4+)

**Written By:** Social conduction system, lore object reader (Phase 3+)

**Event Requirement:** Mutations emit Chronicle events for tracking

**Phase:** 3 (deferred for MVP)

---

## ABILITY & ACTION LAYER

Components for ability selection, action queuing, and TOML-driven mechanics.

### `available-abilities`

**Fields:**
```
ability_ids: List[str]                  # Names of abilities entity can cast (e.g., ["basic-attack", "backstab", "blessing"])
ability_toml_sources: Dict[str, str]    # Maps ability_id → TOML file path (e.g., {"backstab": "data/abilities/rogue/backstab.toml"})
learned_at: Dict[str, int]              # Ability → turn number learned (for post-MVP progression)
```

**Lifecycle:** Created at spawn from archetype template. Abilities are immutable for MVP (no learning mid-session). Post-MVP: abilities gain/lost via story events.

**Read By:** Action validator (can this entity cast X?), UI ability list, TOML loader (fetch ability definition)

**Written By:** Entity factory only (MVP); future story systems (post-MVP progression)

**Hard Limit:** No hardcoded ability behavior. All mechanics defined in TOML (hard limit #4).

**Phase:** 1 (abilities registered), Phase 4+ (ability TOML content)

---

### `pending-action`

**Fields:**
```
action_type: str                        # "attack" | "ability" | "move" | "item" | "defend"
action_target: Optional[str]            # Target entity name (null for self-targeted or movement)
action_payload: Dict[str, Any]          # Ability-specific data (e.g., {"ability_id": "backstab", "with_advantage": false})
queued_at: float                        # Timestamp when queued (for undo windows—post-MVP)
```

**Lifecycle:** Created when player/AI selects action. Consumed by action resolution system. Removed after resolution event fires.

**Read By:** Action validator, action resolution engine, undo system (post-MVP)

**Written By:** Player input system / AI decision system; cleared by action resolution system

**Phase:** 2

---

## INVENTORY LAYER

Components for carrying items and equipment. **Deferred for MVP** but contract defined.

### `inventory` (Phase 3+)

**Fields:**
```
items: List[ItemInstance]               # Items carried; ItemInstance defined in TOML / item system
carrying_capacity: int                  # Max weight/count
equipment_slots: Dict[str, Optional[ItemInstance]]  # Active gear (e.g., {"mainhand": ItemInstance, "armor": ItemInstance})
```

**Lifecycle:** Created empty at spawn. Items added/removed by pickup/drop actions. Equipment changed by equip actions.

**Read By:** Renderer (equipment display), combat stats resolver (equipment modifiers), weight checker (can carry more?)

**Written By:** Pickup/drop/equip systems

**Phase:** 3+ (deferred)

---

## AI & BEHAVIOR LAYER

Components for NPC decision-making, goal stack, and tactic state. **Deferred for MVP**.

### `ai-state` (Phase 3+)

**Fields:**
```
goal_stack: List[str]                   # Current goals in priority order (e.g., ["protect_ally", "defeat_enemy", "explore"])
current_tactic: str                     # Active behavior (e.g., "aggressive", "defensive", "flee")
awareness_level: str                    # "unaware" | "alert" | "engaged"
```

**Lifecycle:** Created at spawn with default goals from NPC template. Modified by perception system and goal planner (Phase 3+).

**Read By:** Decision system (what should I do?), renderer (AI state for debug display)

**Written By:** Goal planner, perception system

**Phase:** 3+ (deferred)

---

## VITALITY CACHE LAYER (MVP STUB)

### `vitality-cache` (NOT IMPLEMENTED)

**Fields:**
```
cached_vitality: Dict[str, float]       # DO NOT USE
```

**Status:** Stub field only. Do NOT read or write this component during MVP (hard limit #3). Placeholder for Phase 2+ cross-session persistence optimization.

**Phase:** 2+ (deferred)

---

## Component Query Patterns (for Systems to Know)

| Query | Result | Systems Using |
| --- | --- | --- |
| `entity_identity + position` | Spatial entity (PC/NPC/foe) | Renderer, collision |
| `combat-vitals + combat-stats + active-modifiers` | Combat-ready entity | Combat engine |
| `entity-identity + disposition + stress` | Social entity (NPC/PC) | Social system, conduction |
| `position + movement-stats + action-economy` | Mobile entity | Movement system, turn resolution |
| `available-abilities + action-economy` | Action-capable entity | Action validator, ability resolver |

---

## Implementation Notes for Phase 1

- Each component is a Pydantic model or dataclass
- Use python-tcod-ecs sparse-set registry to store component instances
- Query syntax: `registry.query(ComponentA, ComponentB)` returns entities with both
- No component has methods except `__init__` and validators
- All behavior lives in systems that consume components

---

## Deferred to Phase 2+

- `faction-standing` (Phase 3, depends on conduction system)
- `inventory` (Phase 3, depends on item system)
- `ai-state` (Phase 3, depends on goal planner)
- `chronicle-reference` (Phase 2, depends on Chronicle system)
- `visible-position` (Phase 2, depends on FOV system)

---

## Post-Phase-1 Discoveries

- **`moral_weight` and `resilience`** (2026-02-27): Both are canonical SocialState fields from manifest §2 Contract 2 that surfaced during SYSTEMS.md drafting. Added to `disposition` component. `moral_weight` written by Chronicle reconciliation ONLY — never by combat or social systems directly. `resilience` is a stress-absorption buffer (DOS2 binary armor model). Confirm against `engine/social_state.py` in Phase 2.
