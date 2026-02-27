# EVENTS.md — Event Contract & Taxonomy

**Phase 1 Deliverable: Event catalog, typed payloads, and dispatch timing**
**Status:** ✅ Final
**Last Updated:** 2026-02-27

---

## Overview

This document defines all events flowing through the EventBus. Events are the primary inter-layer communication mechanism (Combat ↔ Social ↔ Chronicle). Each event is a typed Pydantic model with required/optional fields; systems subscribe and react.

**Guiding principle:** Events are the ONLY way to mutate state across layers. No direct state mutation. No hidden side effects.

---

## Event Envelope Contract

```python
class CombatEvent(BaseModel):
    event_key: str                          # Canonical EVT_* constant (never raw strings)
    source: str                             # Entity name that emitted event
    target: Optional[str] = None            # Target entity (null for broadcast events)
    data: Dict[str, Any] = {}               # Event-specific payload (flat, JSON-serializable)
```

**Rules:**
- Always use EVT_* constants from `engine/combat.py` (hard limit #10)
- `data` dict is flat (no nested objects); all values JSON-serializable
- `source` and `target` are entity names (match `entity-identity.name`)
- Chronicle receives ALL events via wildcard ("*") subscription

---

## Turn Resolution Sequence & Timing

**This is the canonical event order per round.** Systems must respect this ordering.

```
Per Actor Activation (eligible when action_energy >= ENERGY_THRESHOLD):
  1. EVT_TURN_STARTED          ← Turn eligibility confirmed, actor begins turn
  2. EVT_ACTION_RESOLVED       ← Action (attack/ability/move) executes
     └─ May trigger EVT_ON_DAMAGE (if damage dealt)
     └─ May trigger EVT_ON_DEATH (if HP ≤ 0)
     └─ May trigger EVT_MODIFIER_ADDED (if ability adds buff)
  3. EVT_TURN_ENDED            ← Modifier expiry checks; modifier.on_event() called
     └─ May trigger EVT_MODIFIER_EXPIRED (for each expired modifier)

After All Actors Complete Turns:
  4. EVT_ROUND_ENDED           ← Summary; both combatants emit this
```

**Critical constraint:** Modifier expiry is synchronous within EVT_TURN_ENDED. No events emit DURING modifier checks; checks complete first, then expiry events emit.

---

## COMBAT EVENTS

Events emitted by CombatEngine and Combatant class.

### `EVT_TURN_STARTED` = `"combat.turn_started"`

**Fired by:** `CombatEngine.start_turn(actor)`

**Payload (TypedDict):**
```python
{
    "action_energy": float,              # Actor's current action_energy value
}
```

**Semantics:** Actor has met ENERGY_THRESHOLD; is now eligible to act. Systems can subscribe to finalize turn setup (e.g., apply passive effects, recalculate stat overlays).

**Subscribers (Phase 2+):**
- Turn resolution system (logs turn start)
- UI system (highlight active actor)
- Passive effect applier (pre-turn buffs—post-MVP)

---

### `EVT_ACTION_RESOLVED` = `"combat.action_resolved"`

**Fired by:** `CombatEngine.resolve_attack(attacker, defender)`

**Payload (TypedDict):**
```python
{
    "attacker": str,                    # Attacker entity name
    "defender": str,                    # Defender entity name
    "roll": {
        "rolls": List[int],             # [roll1, roll2] or just [roll1] if no advantage/disadvantage
        "natural": int,                 # Final natural roll (1–20, after advantage/disadvantage resolution)
        "modifier": int,                # Attack bonus applied
        "total": int,                   # natural + modifier
        "is_crit": bool,                # natural >= CRIT_THRESHOLD (20)
        "is_fumble": bool,              # natural <= FUMBLE_THRESHOLD (1)
        "advantage": bool,              # True if rolled with advantage
        "disadvantage": bool,           # True if rolled with disadvantage
    },
    "dc": int,                          # Defense class (BASE_HIT_DC + defender defense_bonus)
    "outcome": str,                     # "fumble" | "miss" | "graze" | "hit" | "critical"
    "damage": int,                      # Damage dealt (0 if miss/fumble/graze-reduced)
    "defender_hp": int,                 # Defender's HP after damage applied
    "display_mode": str,                # "category" | "raw" (for UI rendering)
}
```

**Semantics:** Single attack action completed. Damage already applied to defender via `apply_damage()`. This event logs the outcome.

**Ordering:** Fires AFTER all damage processing, BEFORE EVT_TURN_ENDED.

**Subscribers:**
- Chronicle inscriber (record attack for history)
- UI system (display roll and outcome)
- Social stress system (stress spike on damage—Phase 2)
- Statistics tracker (win rate, damage dealt—post-MVP)

---

### `EVT_TURN_ENDED` = `"combat.turn_ended"`

**Fired by:** `CombatEngine.resolve_attack()` after action completes (implicit); also called explicitly by turn resolution loop.

**Payload (TypedDict):**
```python
{
    "ap_spent": int,                    # AP consumed this action (optional; defaults to 0)
}
```

**Semantics:** Actor's turn concludes. Modifier expiry checks fire synchronously. Systems that depend on "end of turn" (reset cooldowns, apply passive decay—post-MVP) subscribe here.

**Timing:** This is the critical checkpoint for modifier.on_event(event_key="combat.turn_ended"). Modifiers with `expires_on=["combat.turn_ended"]` self-expire.

**Subscribers:**
- Modifier system (check expiry conditions)
- Passive decay system (post-MVP: reduce temporary buffs)
- UI system (clear turn highlight)

---

### `EVT_ROUND_ENDED` = `"combat.round_ended"`

**Fired by:** `CombatEngine.end_round(combatants)` after all actors complete their turns.

**Payload (TypedDict):**
```python
{
    "hp": int,                          # Actor's current HP
    "modifiers": List[str],             # Active modifier names on this actor
}
```

**Semantics:** Full round is complete. Both combatants emit this. Systems that track round-level summaries (round count, round-end triggers) subscribe here.

**Subscribers:**
- Round counter (increment round_number)
- Chronicle scribe (round summary inscription—Phase 4)
- Encounter tracker (check victory/defeat conditions)

---

### `EVT_ON_DAMAGE` = `"combat.on_damage"`

**Fired by:** `Combatant.apply_damage(amount, bus)`

**Payload (TypedDict):**
```python
{
    "amount": int,                      # Damage taken (>= 0)
    "hp_remaining": int,                # Defender's HP after damage
}
```

**Semantics:** Damage applied to entity. Fires synchronously before any death check.

**Ordering:** Fires BEFORE EVT_ON_DEATH (if fatal) and BEFORE EVT_ACTION_RESOLVED.

**Subscribers:**
- Social stress system (stress spike on damage)
- UI system (damage flash, HP bar update)
- Sound system (pain sound—post-MVP)
- Damage tracker (statistics)

**Hard Limit:** HP mutation ONLY via `apply_damage()` method (hard limit #9). Never write `hp` directly.

---

### `EVT_ON_DEATH` = `"combat.on_death"`

**Fired by:** `Combatant.apply_damage()` when `hp <= 0` after damage applied.

**Also fires:** `EVT_SOCIAL_STRESS_SPIKE` (see Social Events below).

**Payload (TypedDict):**
```python
{
    "final_hp": int,                    # HP at death (always <= 0)
}
```

**Semantics:** Entity is dead. Fires after damage taken; combat engine should check `is_dead` and halt combat if both combatants dead or one victorious.

**Ordering:** Fires immediately after EVT_ON_DAMAGE if fatal. BEFORE EVT_ACTION_RESOLVED.

**Subscribers:**
- Combat engine (victory/defeat check)
- Chronicle scribe (death inscription—high significance)
- Social system (party morale hit; stress spike on allies)
- UI system (death animation, defeat screen)

---

### `EVT_MODIFIER_ADDED` = `"combat.modifier_added"`

**Fired by:** `Combatant.add_modifier(mod)`

**Payload (TypedDict):**
```python
{
    "modifier": str,                    # Modifier name (e.g., "Blessing of Swiftness")
    "stat": str,                        # Stat affected (e.g., "defense_bonus")
    "value": int,                       # Modification amount (positive or negative)
    "expires_on": List[str],            # Event keys that trigger expiry (e.g., ["combat.turn_ended"])
}
```

**Semantics:** Buff/debuff applied to entity. Adds to `active-modifiers` component.

**Subscribers:**
- UI system (display new buff icon)
- Combat stats resolver (recalculate stat overlay)
- Chronicle scribe (log applied effect)

---

### `EVT_MODIFIER_EXPIRED` = `"combat.modifier_expired"`

**Fired by:** `Combatant._handle_event()` when `modifier.on_event(event_key)` returns True.

**Payload (TypedDict):**
```python
{
    "modifier": str,                    # Modifier name that expired
    "stat": str,                        # Stat that was affected
}
```

**Semantics:** Temporary effect ended. Modifier removed from `active-modifiers` list.

**Ordering:** Fires during EVT_TURN_ENDED processing (synchronous modifier checks).

**Subscribers:**
- UI system (remove buff icon)
- Combat stats resolver (recalculate stat overlay)
- Chronicle scribe (log effect expiry)

---

## SOCIAL EVENTS

Events emitted by Social State system (Phase 2+). All social mutations trigger these events (hard limit #1).

### `EVT_SOCIAL_STRESS_SPIKE` = `"social.stress_spike"`

**Fired by:**
- `Combatant.apply_damage()` → combat stress system (Phase 2)
- Explicitly by social state system on significant events

**Payload (TypedDict):**
```python
{
    "cause": str,                       # "combat_damage" | "ally_death" | "failed_action" | "conduction_from_{entity}" | ...
    "magnitude": float,                 # Stress increase (0.0–1.0 range; fraction to add to stress_level)
    "source_entity": Optional[str],     # Entity causing stress (e.g., attacker name for combat_damage)
}
```

**Semantics:** NPC stress increases. Affected entity is the `source` of this event (the entity whose stress rose).

**Subscribers:**
- Social state system (increment stress_level)
- Conduction system (propagate stress to nearby NPCs—Phase 2)
- Chronicle scribe (log stress event—moderate significance)
- Exodus checker (if stress > STRESS_EXODUS_THRESHOLD, flag for leaving—Phase 3)

**Design Variable Reference:** `STRESS_EXODUS_THRESHOLD = 0.7`

---

### `EVT_SOCIAL_DISPOSITION_SHIFT` = `"social.disposition_shift"`

**Fired by:** Social state system (Phase 2) when disposition changes.

**Payload (TypedDict):**
```python
{
    "direction": str,                   # "positive" | "negative"
    "amount": float,                    # Magnitude of shift (0.0–1.0)
    "reason": str,                      # "shared_victory" | "betrayal" | "conversation" | ...
    "party_entity": Optional[str],      # Party member causing shift (if applicable)
}
```

**Semantics:** NPC reputation with party changes. Affected entity is the `source` (the NPC whose disposition shifted).

**Subscribers:**
- Social state system (update reputation field)
- Conduction system (affect nearby NPCs' mood—Phase 2)
- Encounter spawner (recalculate ally/enemy status—Phase 2)
- Chronicle scribe (high significance)

**Thresholds (from DESIGN_VARIABLES.md):**
- Ostracization: reputation < -0.3 → NPC refuses interaction
- Cooperation: reputation > 0.4 → mutual aid behaviors

---

## CHRONICLE EVENTS

Events emitted by Chronicle system (Phase 2+). Chronicle receives ALL events via "*" wildcard.

### No direct event emission

Chronicle is a **passive wildcard subscriber**. It doesn't emit events; it **receives and inscribes** all events from combat and social systems. See Phase 2 `engine/chronicle.py` for subscription and inscription logic.

**Chronicle constraints (hard limits #1–3):**
- No direct inter-layer mutation → all changes via events
- No entry modification after inscription → corrections are new entries
- Chronicle is append-only (JSONL)

---

## PLACEHOLDER EVENTS (Phase 2+)

Reserved event keys for future implementation. Do NOT use until system is ready.

### Movement/Spatial Events (Phase 2+)

```python
EVT_ENTITY_MOVED           = "entity.moved"              # Position changed
EVT_ENTITY_COLLIDED        = "entity.collided"           # Collision detected
EVT_VISIBILITY_CHANGED     = "entity.visibility_changed" # FOV state changed
```

### Inventory Events (Phase 3+)

```python
EVT_ITEM_PICKED_UP         = "item.picked_up"
EVT_ITEM_DROPPED           = "item.dropped"
EVT_ITEM_EQUIPPED          = "item.equipped"
```

### Encounter Events (Phase 2+)

```python
EVT_ENCOUNTER_SPAWNED      = "encounter.spawned"
EVT_ENCOUNTER_CLEARED      = "encounter.cleared"
EVT_VICTORY_CONDITION_MET  = "encounter.victory"
EVT_DEFEAT_CONDITION_MET   = "encounter.defeat"
```

### UI Events (Phase 2+)

```python
EVT_PLAYER_ACTION_INPUT    = "player.action_input"       # Player selected action
EVT_DISPLAY_STATE_CHANGED  = "ui.display_state_changed"
```

---

## Event Payload Design Rules (Phase 1)

1. **Flat structure only** — No nested objects in `data` dict
2. **JSON-serializable** — All values must serialize to JSON (for Chronicle JSONL)
3. **Required vs. optional** — Use TypedDict with explicit Optional[] for optional fields
4. **Timestamps optional** — Include if event timing matters; omit if not
5. **Entity references** — Use entity names (strings); use null for "broadcast" events

---

## Phase 1 Hardening Task

**Task:** Convert all `data: Dict[str, Any]` payloads to per-event TypedDict definitions.

**Benefit:** Compile-time type safety; mypy can validate event payloads.

**Can be done in parallel** with Phase 1 contract review; deferred until Phase 2 implementation if not critical.

---

## Integration with engine/combat.py

All event keys in this document must be defined as EVT_* constants in `engine/combat.py`. Example:

```python
# engine/combat.py
EVT_TURN_STARTED          = "combat.turn_started"
EVT_ACTION_RESOLVED       = "combat.action_resolved"
EVT_TURN_ENDED            = "combat.turn_ended"
EVT_ROUND_ENDED           = "combat.round_ended"
EVT_ON_DAMAGE             = "combat.on_damage"
EVT_ON_DEATH              = "combat.on_death"
EVT_MODIFIER_ADDED        = "combat.modifier_added"
EVT_MODIFIER_EXPIRED      = "combat.modifier_expired"
EVT_SOCIAL_STRESS_SPIKE        = "social.stress_spike"
EVT_SOCIAL_DISPOSITION_SHIFT   = "social.disposition_shift"
```

---

## Post-Phase-1 Discoveries

(Log here as implementation reveals event ordering or payload issues)

- *(none yet)*
