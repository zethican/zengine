# SYSTEMS.md — ECS System Contracts

**Phase 1 Deliverable: System function signatures, query patterns, and dispatch contracts**
**Status:** ✅ Final
**Last Updated:** 2026-02-27

---

## Overview

This document defines all ECS systems. Each system is a function (or class with a `run()` method) that queries the entity registry for specific component combinations and performs game logic on matching entities.

**Guiding principles:**
- Systems own all behavior. Components are data only.
- Systems communicate exclusively via EventBus. No direct cross-system calls.
- No system holds global state. All dependencies injected at construction.
- Hard limits from CONTEXT.md apply to every system without exception.

---

## System Definition Template

Each system is documented with:

- **System Name** — `snake_case` module or function identifier
- **Location** — file path (planned)
- **Query** — component tuple this system operates on
- **Reads** — components it consumes without writing
- **Writes** — components it mutates
- **Emits** — events it publishes to EventBus
- **Subscribes** — events it listens for
- **Dispatch Point** — when it runs in the game loop
- **Phase Gate** — which phase introduces this system
- **Hard Limits** — applicable constraints

---

## DISPATCH ORDER (Canonical Turn Loop)

This is the authoritative execution sequence for a single game tick. Systems run in this order.

```
TICK START
  1. turn-resolution-system        ← tick action_energy for all actors
  2. action-economy-reset-system   ← reset AP pool for newly eligible actors
  3. [player input / AI decision]  ← external; writes pending-action component
  4. action-validator-system       ← validate pending-action AP affordability
  5. action-resolution-system      ← execute pending-action; emit EVT_ACTION_RESOLVED
       └─ combat-damage-system     ← apply_damage(); emit EVT_ON_DAMAGE, EVT_ON_DEATH
       └─ modifier-lifecycle-sys   ← add modifier; emit EVT_MODIFIER_ADDED
  6. turn-end-system               ← emit EVT_TURN_ENDED; trigger modifier expiry
       └─ modifier-expiry-system   ← check expires_on; emit EVT_MODIFIER_EXPIRED
  7. encounter-state-system        ← check victory/defeat conditions
ROUND END (after all actors act)
  8. round-end-system              ← emit EVT_ROUND_ENDED for all combatants

SESSION BOUNDARY (between sessions)
  9. social-catchup-system         ← advance Social Layer N catch-up ticks
 10. equilibrium-system            ← recompute node vitality; Taper formula

ALWAYS (wildcard subscriber, fires on every event)
  11. chronicle-inscriber-system   ← evaluate significance; inscribe to JSONL
```

**Rule:** Systems 1–8 run per combat tick. Systems 9–10 run once at session open. System 11 is event-driven, not tick-driven.

---

## COMBAT SYSTEMS

### `turn_resolution_system`

**Location:** `engine/combat.py` → `CombatEngine` (Phase 0 stub; full system Phase 2)

**Query:** entities with `[action-economy, movement-stats]`

**Reads:** `movement-stats.speed`, `action-economy.action_energy`

**Writes:** `action-economy.action_energy` (increments by speed each tick)

**Emits:** Nothing directly. Sets up eligibility for EVT_TURN_STARTED.

**Dispatch Point:** First in tick loop. Runs before any action resolution.

**Pseudocode:**
```python
def run(registry, bus):
    for entity in registry.query(ActionEconomy, MovementStats):
        economy = entity.get(ActionEconomy)
        stats = entity.get(MovementStats)
        economy.action_energy += stats.speed
        # Eligibility checked by action-resolution; no event here
```

**Phase Gate:** 1 (design), 2 (implementation)

---

### `action_economy_reset_system`

**Location:** `engine/combat.py` (Phase 2)

**Query:** entities with `[action-economy]` where `action_energy >= ENERGY_THRESHOLD`

**Reads:** `action-economy.action_energy`

**Writes:** `action-economy.ap_pool` → reset to `AP_POOL_SIZE`; `action-economy.ap_spent_this_turn` → reset to 0

**Emits:** `EVT_TURN_STARTED`

**Dispatch Point:** Immediately after `turn_resolution_system`. One call per newly eligible actor.

**Design Variable References:** `ENERGY_THRESHOLD = 100.0`, `AP_POOL_SIZE = 100`

**Phase Gate:** 1 (design), 2 (implementation)

---

### `action_validator_system`

**Location:** `engine/ecs/systems.py` (Phase 2)

**Query:** entities with `[pending-action, action-economy, available-abilities]`

**Reads:** `pending-action.action_type`, `pending-action.action_payload`, `action-economy.ap_pool`, `available-abilities.ability_ids`

**Writes:** Nothing. Rejects or passes pending-action to resolution.

**Emits:** Nothing. Raises validation error if AP insufficient or ability unknown.

**Logic:**
```python
def validate(pending, economy, abilities):
    if pending.action_type == "ability":
        ability_id = pending.action_payload["ability_id"]
        assert ability_id in abilities.ability_ids
        ap_cost = load_toml_ability(ability_id).ap_cost
        assert economy.ap_pool >= ap_cost
    elif pending.action_type == "move":
        ap_cost = entity.get(MovementStats).movement_ap_cost
        assert economy.ap_pool >= ap_cost
```

**Hard Limit:** All ability costs come from TOML. Never hardcode AP costs (#4).

**Phase Gate:** 2

---

### `action_resolution_system`

**Location:** `engine/combat.py` → `CombatEngine.resolve_attack()` (Phase 0 stub; generalized Phase 2)

**Query:** entities with `[pending-action, combat-stats, action-economy]`

**Reads:** `pending-action.*`, `combat-stats.*`, `active-modifiers.*`

**Writes:** `action-economy.ap_pool` (deduct AP cost); clears `pending-action`

**Emits:** `EVT_ACTION_RESOLVED` (always); may trigger `combat_damage_system`

**Dispatch Point:** After validation. One resolution per eligible actor per tick.

**Delegates to:**
- `combat_damage_system` — if action deals damage
- `modifier_lifecycle_system` — if action applies buff/debuff

**Hard Limit:** Never call social systems directly. Damage-triggered stress flows through EVT_ON_DAMAGE → social subscriber (#1).

**Phase Gate:** 1 (design), 2 (implementation)

---

### `combat_damage_system`

**Location:** `engine/combat.py` → `Combatant.apply_damage()` (Phase 0 stub; canonical)

**Query:** Not a query system — invoked directly by `action_resolution_system` with target entity.

**Reads:** `combat-vitals.hp`, damage amount from action payload

**Writes:** `combat-vitals.hp` (via `apply_damage()` only — hard limit #9)

**Emits:** `EVT_ON_DAMAGE` (always); `EVT_ON_DEATH` (if fatal); `EVT_SOCIAL_STRESS_SPIKE` (stub, on death)

**Hard Limit:** `hp` mutated only through `Combatant.apply_damage()`. Never directly (#9).

**Phase Gate:** 0 (already implemented in combat.py)

---

### `modifier_lifecycle_system`

**Location:** `engine/combat.py` → `Combatant.add_modifier()` / `Combatant._handle_event()` (Phase 0 stub)

**Reads:** `active-modifiers.modifiers`, incoming event_key for expiry checks

**Writes:** `active-modifiers.modifiers` (append on add, remove on expiry)

**Emits:** `EVT_MODIFIER_ADDED` (on add); `EVT_MODIFIER_EXPIRED` (on expiry)

**Subscribes:** `"*"` (wildcard) — checks every event against modifier `expires_on` lists

**Timing:** Expiry checks are synchronous during EVT_TURN_ENDED processing. No events fire mid-check.

**Hard Limit:** Engine never manages modifier duration. Modifiers are self-expiring via event subscription (#4 implied).

**Phase Gate:** 0 (already implemented in combat.py)

---

### `turn_end_system`

**Location:** `engine/combat.py` → `CombatEngine.resolve_attack()` (implicit emit, Phase 0)

**Query:** active actor entity

**Reads:** `action-economy.ap_spent_this_turn`

**Writes:** `action-economy.action_energy` (deduct ENERGY_THRESHOLD; residual carries forward)

**Emits:** `EVT_TURN_ENDED` — triggers modifier expiry checks and all turn-end subscribers

**Dispatch Point:** After `action_resolution_system` completes. Always fires, even if actor took no action.

**Phase Gate:** 0 (already implemented)

---

### `encounter_state_system`

**Location:** `engine/combat.py` (Phase 2)

**Query:** all entities with `[combat-vitals]`

**Reads:** `combat-vitals.is_dead` for all combatants

**Writes:** Nothing to components. Sets encounter state flag (local variable in combat loop).

**Emits:** `EVT_VICTORY_CONDITION_MET` or `EVT_DEFEAT_CONDITION_MET` (Phase 2+)

**Subscribes:** `EVT_ON_DEATH` — re-checks conditions on each death

**Dispatch Point:** After EVT_ON_DEATH or end of every actor's turn.

**Phase Gate:** 2

---

### `round_end_system`

**Location:** `engine/combat.py` → `CombatEngine.end_round()` (Phase 0 stub)

**Query:** all combatants list (passed directly, not ECS query)

**Reads:** `combat-vitals.hp`, `active-modifiers.modifier_ids`

**Writes:** Nothing

**Emits:** `EVT_ROUND_ENDED` for each combatant

**Dispatch Point:** After all actors complete their turns in a round.

**Phase Gate:** 0 (already implemented)

---

## SOCIAL SYSTEMS

All Social Layer mutations must emit Chronicle events before taking effect (hard limit #1). Systems 9–10 run at session boundary.

### `social_state_system`

**Location:** `engine/social_state.py` (Phase 2)

**Query:** entities with `[disposition, stress, entity-identity]`

**Reads:** Subscribes to `EVT_ON_DAMAGE`, `EVT_ON_DEATH`, `EVT_ACTION_RESOLVED`

**Writes:** `stress.stress_level` (via event); `disposition.reputation` (via event)

**Emits:** `EVT_SOCIAL_STRESS_SPIKE` → listened to by conduction and stress writer; `EVT_SOCIAL_DISPOSITION_SHIFT` → listened to by disposition writer

**Contract (from manifest §2 Contract 2):**
```
SocialState fields:
  reputation:    float -1.0 to 1.0   (default 0.0)
  moral_weight:  float 0.0 to 1.0    (default 0.5)
  stress:        float 0.0 to 1.0    (default 0.0)
  resilience:    float 0.0 to 1.0    (default 1.0)
  consequence_log: List[event_id]
```

**Field distinctions (critical — never conflate):**
- `reputation` — written by social interaction systems; drives behavioral consequences and Apathy Exodus
- `moral_weight` — written by Chronicle reconciliation ONLY; governs lore description register
- `stress` — written by Chronicle events tagged `stress_delta`; third independent field
- `resilience` — absorbs stress deltas (DOS2 binary armor adapted for stress); depletes under pressure, recovers at rest in high-vitality nodes

**Dispatch Point:** Subscribes to EventBus; fires reactively on relevant combat events.

**Hard Limit:** No direct state mutation from Dungeon Layer. All changes via Chronicle event first (#1).

**Phase Gate:** 2

---

### `social_catchup_system`

**Location:** `engine/social_state.py` (Phase 2)

**Query:** all entities with `[disposition, stress]`

**Triggered:** Once at session open (session boundary tick)

**Reads:** `SOCIAL_CATCHUP_TICKS`, `CATCHUP_TRANSITION_CAP`, current state of all NPC social components

**Writes:** Advances Social Layer state by N ticks; applies at most `CATCHUP_TRANSITION_CAP` state transitions per node

**Emits:** `EVT_SOCIAL_STRESS_SPIKE` and/or `EVT_SOCIAL_DISPOSITION_SHIFT` for each simulated tick (Chronicle-inscribed)

**Design Variable References:** `SOCIAL_CATCHUP_TICKS = 5`, `CATCHUP_TRANSITION_CAP = 1`

**Rationale:** Simulates narrative passage of time. Single-transition cap ensures player returns to a changed but recognizable world. Prevents state explosion on long absence.

**Phase Gate:** 2

---

### `conduction_system`

**Location:** `engine/equilibrium.py` (Phase 2)

**Query:** entities with `[position, stress, disposition]` (spatially adjacent entities)

**Subscribes:** `EVT_SOCIAL_STRESS_SPIKE` — propagates spike to nearby entities

**Reads:** `position` (to calculate distance), `stress.stress_level`, `CONDUCTION_COEFFICIENT`, `CONDUCTION_ATTENUATION`

**Writes:** Emits secondary `EVT_SOCIAL_STRESS_SPIKE` for each adjacent entity (attenuated by distance)

**Formula (from manifest §2 Contract 3):**
```python
# Conduction coefficient = 0.3 (configurable; 0.0 disables)
# Attenuation = 0.6 per distance unit (range 0.1–0.9)
propagated_magnitude = original_magnitude * CONDUCTION_COEFFICIENT * (CONDUCTION_ATTENUATION ** distance)
```

**Emits:** `EVT_SOCIAL_STRESS_SPIKE` with `cause = "conduction_from_{source_entity}"`

**Hard Limit:** No cross-faction conduction during MVP (post-MVP; see FUTURE.md).

**Design Variable References:** `CONDUCTION_COEFFICIENT = 0.3`, `CONDUCTION_ATTENUATION = 0.6`

**Phase Gate:** 2

---

### `exodus_checker_system`

**Location:** `engine/social_state.py` (Phase 3)

**Query:** entities with `[stress, entity-identity]` where `entity-identity.is_player == False`

**Subscribes:** `EVT_SOCIAL_STRESS_SPIKE`

**Reads:** `stress.stress_level`, `STRESS_EXODUS_THRESHOLD`

**Writes:** Sets internal flag on entity; does not mutate stress component

**Emits:** Nothing directly. Triggers NPC-leaves-party narrative event (Phase 3 AI system).

**Design Variable Reference:** `STRESS_EXODUS_THRESHOLD = 0.7`

**Phase Gate:** 3

---

## CHRONICLE SYSTEM

### `chronicle_inscriber_system`

**Location:** `engine/chronicle.py` (Phase 2)

**Subscribes:** `"*"` (wildcard — receives every event in emission order)

**Query:** No ECS query. Event-driven only.

**Reads:** Every `CombatEvent` payload; `CHRONICLE_SIGNIFICANCE_MIN`, `CHRONICLE_CONFIDENCE_WITNESSED`, `CHRONICLE_CONFIDENCE_FABRICATED`

**Writes:** Appends to `sessions/chronicle.jsonl` (append-only, write-on-dispatch)

**Chronicle Entry Schema (from manifest §2 Contract 1):**
```
ChronicleEntry:
  event_id:        UUID
  timestamp:       {era: Ancient|Middle|Recent, cycle: int, tick: int}
  provenance:      witnessed | fabricated
  legibility:      transparent | obscured
  actor_handle:    abstract reference (living | Legacy | faction | place)
  payload:         {event_type, verb, object, modifier}
  confidence:      float 0.0–1.0  (default: 0.9 witnessed, 0.4 fabricated)
  citation_count:  int  (dormant MVP; active post-MVP reconciliation)
  significance:    int 1–5  (minimum inscription threshold: 2, configurable)
```

**Epistemic layering:**
- `witnessed + transparent` = unambiguous record
- `witnessed + obscured` = real history rendered fragmentary
- `fabricated + transparent` = acknowledged myth
- `fabricated + obscured` = default state of procedural prehistory

**Inscription logic:**
```python
def on_event(event: CombatEvent):
    significance = score_significance(event)          # evaluate int 1–5
    if significance < CHRONICLE_SIGNIFICANCE_MIN:
        return                                         # below threshold; discard
    provenance = "witnessed" if player_present else "fabricated"
    confidence = CHRONICLE_CONFIDENCE_WITNESSED if provenance == "witnessed" \
                 else CHRONICLE_CONFIDENCE_FABRICATED
    entry = ChronicleEntry(
        event_id=uuid4(),
        timestamp=current_game_time(),
        provenance=provenance,
        legibility="transparent",                      # default; obscured post-MVP
        actor_handle=resolve_handle(event.source),
        payload=build_payload(event),
        confidence=confidence,
        citation_count=0,
        significance=significance,
    )
    append_jsonl(entry)
```

**Prime directives (from manifest):**
- Append-only. Corrections are new entries referencing the superseded event.
- All inter-layer communication passes through the Chronicle.
- Provenance is assigned at inscription and never changed.
- Write-on-dispatch. Session markers: `session.opened` and `session.closed`.

**Hard Limits:** No entry modification after inscription (#2). No direct inter-layer mutation (#1).

**Design Variable References:** `CHRONICLE_SIGNIFICANCE_MIN = 2`, `CHRONICLE_CONFIDENCE_WITNESSED = 0.9`, `CHRONICLE_CONFIDENCE_FABRICATED = 0.4`

**Phase Gate:** 2

---

## EQUILIBRIUM SYSTEM

### `equilibrium_system`

**Location:** `engine/equilibrium.py` (Phase 2)

**Triggered:** Session boundary (once per session open), and on-demand for node state display

**Query:** All Point of Light nodes (not ECS entities — node graph data structure)

**Reads:** `living_count` per node, `vitality_score` per node, `EQUILIBRIUM_BASE_RESISTANCE`

**Writes:** Node vitality score (node graph — not entity component)

**Emits:** Migration events, Legacy conversion events (Phase 2+)

**Vitality Ranges (from manifest §2 Contract 3):**
```
0.6 – 1.0  (flourishing)  Migration inflows. Rich population. Dense living NPCs, sparse lore.
0.2 – 0.6  (stable)       Equilibrium. Moderate migration. Nominal Chronicle rate.
−0.2 – 0.2 (declining)    Apathy Exodus active. Accelerated Legacy conversion.
−1.0 – −0.2 (collapsing)  Rapid Legacy conversion. Outflows only. Collapse events inscribed.
Collapse threshold         Ruin state. No living NPCs. Maximum lore density. Permanent in session.
```

**Equilibrium Taper formula (from manifest):**
```python
BASE_RESISTANCE = 40  # configurable; EQUILIBRIUM_BASE_RESISTANCE
taper_threshold = BASE_RESISTANCE + (living_count * vitality_score)
migration_occurs = random(1, 100) > taper_threshold
```

**Hard Limit:** Vitality is computed on demand — never cached during MVP (#3).

**Design Variable References:** `EQUILIBRIUM_BASE_RESISTANCE = 40`, `CONDUCTION_COEFFICIENT = 0.3`, `CONDUCTION_ATTENUATION = 0.6`

**Phase Gate:** 2

---

### `legacy_conversion_system`

**Location:** `engine/social_state.py` (Phase 2)

**Triggered:** When NPC reaches retirement condition (death, Apathy Exodus, collapse event)

**Retirement 5-step sequence (from manifest §2 Contract 2):**
```
1. Retirement Chronicle event inscribed (carries final reputation, moral weight, cause)
2. Legacy Actor handle created; LegacySocialState populated with bidirectional link
3. Living actor flagged retired; removed from all active simulation pools
4. Legacy Actor enters archaeological record; begins accreting citation counts
5. Adjacent actors may receive Social State modifications per relationship tags
```

**Reads:** `entity-identity`, `disposition.reputation`, `stress.stress_level` of retiring NPC

**Writes:** New `LegacySocialState` entry (Chronicle-adjacent data store); flags `entity-identity` as retired

**Emits:** Retirement Chronicle event (high significance, `provenance = "witnessed"` or `"fabricated"`)

**Prime directives (from manifest):**
- Reputation and moral weight have distinct producers. Never conflate.
- No system may act on the retirement flag without querying the retirement Chronicle event for cause context.
- Legacy Actor records are immutable after creation.

**Hard Limit:** Legacy Actor handles are immutable after creation (#2 implied). Corrections are new entries.

**Phase Gate:** 2

---

## SPATIAL SYSTEMS (Phase 2+)

### `movement_system`

**Location:** `engine/ecs/systems.py` (Phase 2)

**Query:** entities with `[position, movement-stats, pending-action]` where `pending-action.action_type == "move"`

**Reads:** `pending-action.action_payload` (target tile), `movement-stats.movement_ap_cost`, `movement-stats.can_occupy_terrain`

**Writes:** `position.x`, `position.y`; deducts AP from `action-economy.ap_pool`

**Emits:** `EVT_ENTITY_MOVED` (Phase 2+)

**Hard Limit:** No NumPy in movement system. NumPy scoped to spatial math and lighting only (#5).

**Phase Gate:** 2

---

### `visibility_system`

**Location:** `engine/ecs/systems.py` (Phase 2)

**Query:** entities with `[position]`; runs FOV from player position

**Reads:** `position` of all entities; world tile map

**Writes:** `visible-position.visible_to_player`; `visible-position.last_seen_at` (on exit from FOV)

**Emits:** `EVT_VISIBILITY_CHANGED` (Phase 2+)

**Note:** Uses tcod FOV algorithm. NumPy permitted here (spatial math — hard limit #5 exception).

**Phase Gate:** 2

---

## ENCOUNTER DENSITY SYSTEM (Phase 2+)

### `encounter_spawn_system`

**Location:** `world/wilderness.py` (Phase 3)

**Triggered:** On player entering new territory node

**Reads:** Node `vitality_score`, `living_count`, Legacy Actor density from Chronicle

**Logic:** Encounter density driven by Legacy Actor density in territory — not spawn tables (CONTEXT.md Contract 4).

**Emits:** `EVT_ENCOUNTER_SPAWNED` (Phase 2+)

**Phase Gate:** 3

---

## UI / RENDER SYSTEMS (Phase 2+)

### `render_system`

**Location:** `ui/renderer.py` (Phase 2)

**Query:** entities with `[position, entity-identity, visible-position]`

**Reads:** `position`, `entity-identity.name`, `combat-vitals.hp`, `stress.stress_level`, `disposition.baseline_mood`

**Writes:** Nothing. Renders to tcod terminal.

**Subscribes:** Nothing. Reads component state each frame.

**Note:** NumPy permitted for alpha gradient lighting calculation (hard limit #5 exception).

**Phase Gate:** 2

---

## System Interaction Matrix

| System | Reads Components | Writes Components | Emits Events | Subscribes |
| --- | --- | --- | --- | --- |
| turn_resolution | action-economy, movement-stats | action-economy | — | — |
| action_economy_reset | action-economy | action-economy | EVT_TURN_STARTED | — |
| action_validator | pending-action, action-economy, available-abilities | — | — | — |
| action_resolution | pending-action, combat-stats | action-economy, pending-action | EVT_ACTION_RESOLVED | — |
| combat_damage | combat-vitals | combat-vitals | EVT_ON_DAMAGE, EVT_ON_DEATH, EVT_SOCIAL_STRESS_SPIKE | — |
| modifier_lifecycle | active-modifiers | active-modifiers | EVT_MODIFIER_ADDED, EVT_MODIFIER_EXPIRED | * (wildcard) |
| turn_end | action-economy | action-economy | EVT_TURN_ENDED | — |
| encounter_state | combat-vitals | — | EVT_VICTORY/DEFEAT | EVT_ON_DEATH |
| round_end | combat-vitals, active-modifiers | — | EVT_ROUND_ENDED | — |
| social_state | disposition, stress | disposition, stress (via event) | EVT_SOCIAL_STRESS_SPIKE, EVT_SOCIAL_DISPOSITION_SHIFT | EVT_ON_DAMAGE, EVT_ON_DEATH |
| social_catchup | disposition, stress | disposition, stress (via event) | EVT_SOCIAL_STRESS_SPIKE, EVT_SOCIAL_DISPOSITION_SHIFT | — |
| conduction | position, stress | — (emits only) | EVT_SOCIAL_STRESS_SPIKE | EVT_SOCIAL_STRESS_SPIKE |
| exodus_checker | stress | — | — (flags internally) | EVT_SOCIAL_STRESS_SPIKE |
| chronicle_inscriber | (event payloads) | chronicle.jsonl | — | * (wildcard) |
| equilibrium | node graph | node graph | migration events | — |
| legacy_conversion | entity-identity, disposition | LegacySocialState | retirement Chronicle event | — |
| movement | position, movement-stats | position | EVT_ENTITY_MOVED | — |
| visibility | position | visible-position | EVT_VISIBILITY_CHANGED | — |
| render | position, entity-identity, combat-vitals | — (terminal output) | — | — |

---

## Hard Limits Applied to All Systems

1. **No direct inter-layer mutation** — Dungeon→Social always via Chronicle event (#1)
2. **No Chronicle entry modification** — corrections are new entries (#2)
3. **No vitality caching** — equilibrium_system computes on demand (#3)
4. **No hardcoded ability behavior** — all costs and effects from TOML (#4)
5. **No NumPy outside spatial/lighting** — movement_system uses pure int math; only visibility/render use NumPy (#5)
6. **Grammar tables read-only** — no system generates grammar (#6)
7. **All design variables documented** — no silent defaults (#7)
8. **Post-MVP deferred** — no system architects toward FUTURE.md items (#8)
9. **HP via apply_damage() only** — combat_damage_system is the sole writer (#9)
10. **EVT_* constants only** — no raw strings in any system (#10)
11. **No global EventBus** — bus injected at construction into every system (#11)

---

## Post-Phase-1 Discoveries

(Log here as implementation reveals dispatch order constraints or system interaction issues)

- *(none yet)*
