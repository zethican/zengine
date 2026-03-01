"""
ZEngine — engine/combat.py
Combat System: Turn resolution, action economy, event bus, modifier lifecycle.
==============================================================================
Version:     0.2  (canonical stub — Phase 0)
Stack:       Python 3.14.3 | Pydantic v2 | bespoke pub-sub
Status:      Handoff-ready stub. No gameplay loop code belongs here yet.

Architecture notes
------------------
- EventBus is Pydantic v2–typed. All events are BaseModel subclasses.
- No module may mutate another module's state without emitting an event.
- Combatant.hp is NEVER mutated directly. Use Combatant.apply_damage().
- Chronicle receives every event via wildcard subscription ("*").
- Social State hooks are no-op stubs here; wired in engine/social_state.py.
- 2d8 resolution is the canonical mechanic (CONTEXT.md v0.20).
  A bell-curve model provides more stable median results for social ecology.

Event emission sequence per round
----------------------------------
  1. combat.turn_started       — actor activation
  2. combat.action_resolved    — per action (attack, ability, item, etc.)
  3. combat.turn_ended         — end of actor's turn; modifier ticks
  4. combat.round_ended        — after all actors in round; both combatants

Modifier timing (Option C — event-driven expiry)
-------------------------------------------------
  Modifiers declare expires_on: list[str] event keys.
  They self-expire when their trigger fires. The engine loop never
  manages modifier duration. max_triggers controls multi-hit modifiers.

Design Variables (all values configurable — do not hardcode)
-------------------------------------------------------------
  AP_POOL_SIZE            100          — resets each turn; see DESIGN_VARIABLES.md
  MOVEMENT_ALLOCATION     ceil(100/speed) — AP per tile; ceiling rounding; speed-derived
  ENERGY_THRESHOLD        100.0        — turn eligibility
  COMBAT_ROLL_DISPLAY     "category"   — "category" | "raw" (configurable flag)
  STRESS_DELTA_COMBAT     per event    — configured in TOML ability/grammar tables

Open Questions (Phase 1 resolved — Phase 2 blockers remain)
-------------------------------------------------------------
  [x] AP pool size: AP_POOL_SIZE = 100 (DESIGN_VARIABLES.md)
  [x] Movement allocation: ceil(100/speed) (DESIGN_VARIABLES.md)
  [x] Social Layer catch-up ticks: SOCIAL_CATCHUP_TICKS = 5 (DESIGN_VARIABLES.md)
  [ ] EventPayload.data: typed dicts per event — Phase 1 hardening task; deferred to Phase 2
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any, Type, TypeVar

from pydantic import BaseModel

# ============================================================
# DESIGN VARIABLE DEFAULTS
# Change here or override at runtime. Never hardcode elsewhere.
# ============================================================

ENERGY_THRESHOLD: float = 100.0
CRIT_THRESHOLD: int = 16          # 2d8 natural roll (max)
FUMBLE_THRESHOLD: int = 2         # 2d8 natural roll (min)
BASE_HIT_DC: int = 10             # default defense class when no stat provided
COMBAT_ROLL_DISPLAY: str = "category"   # "category" | "raw"

# AP and Movement — resolved Phase 1; registered in DESIGN_VARIABLES.md
AP_POOL_SIZE: int = 100                     # Resets each turn; matches ENERGY_THRESHOLD scale
AP_COST_PICKUP: int = 10                    # AP cost to pick up an item
AP_COST_DROP: int = 10                      # AP cost to drop an item
AP_COST_EQUIP: int = 20                     # AP cost to equip an item
AP_COST_CRAFT: int = 30                     # AP cost to combine two items
AP_COST_USE: int = 20                       # AP cost to use a consumable item
MOVEMENT_ALLOCATION: str = "ceil(100/speed)" # Formula; computed per entity at spawn


# ============================================================
# CANONICAL EVENT KEYS
# Never use raw strings. Add new keys here only.
# ============================================================

EVT_TURN_STARTED          = "combat.turn_started"
EVT_ACTION_RESOLVED       = "combat.action_resolved"
EVT_TURN_ENDED            = "combat.turn_ended"
EVT_ROUND_ENDED           = "combat.round_ended"
EVT_ON_DAMAGE             = "combat.on_damage"
EVT_ON_DEATH              = "combat.on_death"
EVT_MODIFIER_ADDED        = "combat.modifier_added"
EVT_MODIFIER_EXPIRED      = "combat.modifier_expired"

# Social State hook stubs (wired in social_state.py — no-op here)
EVT_SOCIAL_STRESS_SPIKE: str = "social.stress_spike"
EVT_SOCIAL_DISPOSITION_SHIFT: str = "social.disposition_shift"
EVT_SOCIAL_RUMOR_SHARED: str = "social.rumor_shared"



# ============================================================
# EVENT MODELS  (Pydantic v2)
# All events are typed. data dict must remain flat + JSON-serializable.
# Typed-per-event hardening is a Phase 1 task.
# ============================================================

class CombatEvent(BaseModel):
    """Base envelope. Chronicle receives these directly."""
    event_key: str
    source: str
    target: Optional[str] = None
    data: Dict[str, Any] = {}


# ============================================================
# EVENT BUS  (canonical Pydantic v2 stub — CONTEXT.md § Tech Stack)
# ============================================================

E = TypeVar("E", bound=BaseModel)
HandlerFn = Callable[[CombatEvent], None]


class EventBus:
    """
    Bespoke pub-sub. Pass instance at construction — no global singleton.

    Wildcard key "*" receives every emitted event (used by Chronicle).
    Per-handler errors are swallowed and logged to stderr so emission
    always continues (daemon protection principle).
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[HandlerFn]] = {}

    def subscribe(self, event_key: str, handler: HandlerFn) -> None:
        self._subscribers.setdefault(event_key, []).append(handler)

    def unsubscribe(self, event_key: str, handler: HandlerFn) -> None:
        if event_key in self._subscribers:
            self._subscribers[event_key] = [
                h for h in self._subscribers[event_key] if h is not handler
            ]

    def emit(self, event: CombatEvent) -> None:
        targets = (
            self._subscribers.get(event.event_key, [])
            + self._subscribers.get("*", [])
        )
        for handler in targets:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[EventBus] Handler error on '{event.event_key}': {exc}",
                    file=sys.stderr,
                )


# ============================================================
# MODIFIER  (event-driven, self-expiring)
# ============================================================

@dataclass
class Modifier:
    """
    Stat modifier that expires when its trigger events fire.

    expires_on    — event keys that trigger expiry check.
                    Empty list = permanent (never self-expires).
    max_triggers  — how many trigger firings before expiry.
                    Default 1 (expires on first matching event).
                    Use >1 for absorb-N-hits shield effects etc.
    """
    name: str
    stat_target: str
    value: int
    expires_on: List[str] = field(default_factory=list)
    max_triggers: int = 1

    _trigger_count: int = field(default=0, init=False, repr=False)
    _expired: bool = field(default=False, init=False, repr=False)

    @property
    def is_expired(self) -> bool:
        return self._expired

    def on_event(self, event_key: str) -> bool:
        """
        Call when an event fires against this modifier's owner.
        Returns True if the modifier just expired this call.
        """
        if self._expired or event_key not in self.expires_on:
            return False
        self._trigger_count += 1
        if self._trigger_count >= self.max_triggers:
            self._expired = True
            return True
        return False


# ============================================================
# DICE ENGINE
# ============================================================

def roll_2d8() -> int:
    return random.randint(1, 8) + random.randint(1, 8)


def resolve_roll(modifier: int = 0, advantage: bool = False,
                 disadvantage: bool = False) -> Dict[str, Any]:
    """
    Roll 2d8 + modifier vs target DC.
    advantage/disadvantage: roll twice, keep high/low respectively.
    Returns a Chronicle-ready payload dict.
    """
    rolls = [roll_2d8(), roll_2d8()]
    if advantage:
        natural = max(rolls)
    elif disadvantage:
        natural = min(rolls)
    else:
        natural = rolls[0]

    total = natural + modifier
    is_crit   = natural >= CRIT_THRESHOLD
    is_fumble = natural <= FUMBLE_THRESHOLD

    return {
        "rolls":      rolls,
        "natural":    natural,
        "modifier":   modifier,
        "total":      total,
        "is_crit":    is_crit,
        "is_fumble":  is_fumble,
        "advantage":  advantage,
        "disadvantage": disadvantage,
    }


def roll_outcome_category(total: int, dc: int,
                           is_crit: bool, is_fumble: bool) -> str:
    """
    Maps roll result to outcome category per COMBAT_ROLL_DISPLAY default.
    Graze: missed DC by 1–4.
    """
    if is_fumble:
        return "fumble"
    if is_crit:
        return "critical"
    if total >= dc:
        return "hit"
    if total >= dc - 4:
        return "graze"
    return "miss"


# ============================================================
# COMBATANT
# ============================================================

class Combatant:
    """
    Represents any actor in a combat encounter (PC or NPC).

    action_energy accumulates per tick at rate = speed attribute.
    At ENERGY_THRESHOLD, actor is eligible to act (Contract 4).
    AP pool governs significant actions; TBD Phase 1.
    """

    def __init__(self, name: str, is_player: bool, max_hp: int,
                 stats: Dict[str, int], damage_bonus: int = 0,
                 speed: float = 10.0):
        self.name = name
        self.is_player = is_player
        self.max_hp = max_hp
        self.hp = max_hp
        self._base_stats = stats
        self.damage_bonus = damage_bonus
        self.speed = speed
        self.action_energy: float = 0.0
        self.modifiers: List[Modifier] = []
        self._bus: Optional[EventBus] = None

    # ----------------------------------------------------------
    # Bus wiring
    # ----------------------------------------------------------

    def register_with_bus(self, bus: EventBus) -> None:
        """Wire this combatant into the event bus for modifier dispatch."""
        self._bus = bus
        bus.subscribe("*", self._handle_event)

    def _handle_event(self, event: CombatEvent) -> None:
        if event.source != self.name and event.target != self.name:
            return
        expired = [m for m in self.modifiers if m.on_event(event.event_key)]
        for mod in expired:
            self.modifiers.remove(mod)
            if self._bus:
                self._bus.emit(CombatEvent(
                    event_key=EVT_MODIFIER_EXPIRED,
                    source=self.name,
                    data={"modifier": mod.name, "stat": mod.stat_target},
                ))

    # ----------------------------------------------------------
    # Stats and modifiers
    # ----------------------------------------------------------

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    @property
    def is_turn_eligible(self) -> bool:
        return self.action_energy >= ENERGY_THRESHOLD

    def get_stat(self, stat_name: str) -> int:
        base = self._base_stats.get(stat_name, 0)
        return base + sum(
            m.value for m in self.modifiers
            if m.stat_target == stat_name and not m.is_expired
        )

    def add_modifier(self, mod: Modifier) -> None:
        self.modifiers.append(mod)
        if self._bus:
            self._bus.emit(CombatEvent(
                event_key=EVT_MODIFIER_ADDED,
                source=self.name,
                data={"modifier": mod.name,
                      "stat": mod.stat_target,
                      "value": mod.value,
                      "expires_on": mod.expires_on},
            ))

    def tick_energy(self) -> None:
        """Advance action energy by speed value."""
        self.action_energy += self.speed

    def consume_turn_energy(self) -> None:
        """Deduct threshold on acting. Residual carries forward."""
        self.action_energy = max(0.0, self.action_energy - ENERGY_THRESHOLD)

    # ----------------------------------------------------------
    # Damage (only legal mutation path for hp)
    # ----------------------------------------------------------

    def apply_damage(self, amount: int, bus: Optional[EventBus] = None) -> None:
        """
        Apply damage and emit EVT_ON_DAMAGE.
        NEVER mutate self.hp directly anywhere else.
        """
        amount = max(0, amount)
        self.hp -= amount
        b = bus or self._bus
        if b:
            b.emit(CombatEvent(
                event_key=EVT_ON_DAMAGE,
                source=self.name,
                target=self.name,
                data={"amount": amount, "hp_remaining": self.hp},
            ))
            if self.is_dead:
                b.emit(CombatEvent(
                    event_key=EVT_ON_DEATH,
                    source=self.name,
                    data={"final_hp": self.hp},
                ))
                # Death triggers a major stress spike (processed by SocialStateSystem)
                b.emit(CombatEvent(
                    event_key=EVT_SOCIAL_STRESS_SPIKE,
                    source=self.name,
                    data={"cause": "combat_death", "magnitude": 0.5},
                ))


# ============================================================
# FOE FACTORY
# ============================================================

class FoeFactory:
    """
    Procedural combatant generator.
    Threat level scales attack/defense bonuses within 2d8 range.
    Encounter density is driven by Legacy Actor density in territory
    (CONTEXT.md Contract 4) — not spawn tables.
    """

    ARCHETYPES: Dict[str, Dict[str, Any]] = {
        "Brute":      {"hp_mult": 1.5, "atk_bonus": 0,  "def_bonus": -2, "dmg_bonus": 2,  "speed": 8.0},
        "Skirmisher": {"hp_mult": 0.8, "atk_bonus": -1, "def_bonus": 2,  "dmg_bonus": 0,  "speed": 12.0},
        "Elite":      {"hp_mult": 1.2, "atk_bonus": 2,  "def_bonus": 1,  "dmg_bonus": 1,  "speed": 10.0},
    }
    BASE_BONUS: int = 3  # Baseline attack/defense bonus at threat 0

    @classmethod
    def generate(cls, threat_level: int, archetype: str,
                 name_override: str = "") -> Combatant:
        threat_level = max(0, threat_level)
        tmpl = cls.ARCHETYPES.get(archetype, cls.ARCHETYPES["Brute"])
        base = cls.BASE_BONUS + threat_level

        stats = {
            "attack_bonus":  max(0, min(10, base + tmpl["atk_bonus"])),
            "defense_bonus": max(0, min(10, base + tmpl["def_bonus"])),
        }
        hp = max(1, int((10 + threat_level * 5) * tmpl["hp_mult"]))
        name = name_override or f"Tier-{threat_level} {archetype}"

        return Combatant(
            name=name, is_player=False, max_hp=hp,
            stats=stats, damage_bonus=tmpl["dmg_bonus"],
            speed=tmpl["speed"],
        )


# ============================================================
# COMBAT ENGINE
# ============================================================

class CombatEngine:
    """
    Thin wrapper: resolves action exchanges, emits Chronicle events.

    Three dispatch points per actor activation (Contract 4):
      EVT_TURN_STARTED → EVT_ACTION_RESOLVED → EVT_TURN_ENDED
    EVT_ROUND_ENDED fires after all actors complete their turns.

    Damage formula: 2d8 + attacker.attack_bonus vs BASE_HIT_DC + defender.defense_bonus.
    Outcome categories: fumble / miss / graze / hit / critical.
    Raw damage: d6 + damage_bonus (weapon die TBD Phase 2 per ability TOML).
    """

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    # ----------------------------------------------------------
    # Resolution primitives
    # ----------------------------------------------------------

    def resolve_attack(
        self,
        attacker: Combatant,
        defender: Combatant,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> Dict[str, Any]:
        """
        Single attack action. Emits EVT_ACTION_RESOLVED.
        Returns a Chronicle-ready result dict.
        """
        atk_mod  = attacker.get_stat("attack_bonus")
        def_mod  = defender.get_stat("defense_bonus")
        dc       = BASE_HIT_DC + def_mod

        roll_data = resolve_roll(modifier=atk_mod,
                                 advantage=advantage,
                                 disadvantage=disadvantage)
        outcome = roll_outcome_category(
            roll_data["total"], dc,
            roll_data["is_crit"], roll_data["is_fumble"],
        )

        damage = 0
        if outcome in ("hit", "critical", "graze"):
            raw = random.randint(1, 6) + attacker.damage_bonus
            if outcome == "critical":
                raw = 6 + attacker.damage_bonus   # max damage on crit
            if outcome == "graze":
                raw = max(1, raw // 2)             # half damage on graze
            damage = max(0, raw)
            defender.apply_damage(damage, self.bus)

        result = {
            "attacker":        attacker.name,
            "defender":        defender.name,
            "roll":            roll_data,
            "dc":              dc,
            "outcome":         outcome,
            "damage":          damage,
            "defender_hp":     defender.hp,
            "display_mode":    COMBAT_ROLL_DISPLAY,
        }

        self.bus.emit(CombatEvent(
            event_key=EVT_ACTION_RESOLVED,
            source=attacker.name,
            target=defender.name,
            data=result,
        ))

        # Trigger modifier expiry for attacker post-action
        self.bus.emit(CombatEvent(
            event_key=EVT_TURN_ENDED,
            source=attacker.name,
            data={},
        ))

        return result

    def start_turn(self, actor: Combatant) -> None:
        self.bus.emit(CombatEvent(
            event_key=EVT_TURN_STARTED,
            source=actor.name,
            data={"action_energy": actor.action_energy},
        ))

    def end_round(self, combatants: List[Combatant]) -> None:
        for c in combatants:
            self.bus.emit(CombatEvent(
                event_key=EVT_ROUND_ENDED,
                source=c.name,
                data={"hp": c.hp, "modifiers": [m.name for m in c.modifiers]},
            ))


# ============================================================
# SOCIAL STATE HOOKS
# These hooks link the combat layer to the social layer.
# In Phase 2, these are wired into SocialStateSystem via bus subscriptions.
# ============================================================

def wire_social_state_system(bus: EventBus, social_system: Any) -> None:
    """
    SocialStateSystem self-subscribes at initialization.
    This helper is kept for explicit dependency injection if needed.
    """
    pass # SocialStateSystem handles its own subscriptions in __init__


# ============================================================
# SMOKE TEST
# ============================================================

if __name__ == "__main__":
    from engine.social_state import SocialStateSystem
    bus = EventBus()

    # Chronicle stub — prints every event in emission order
    def chronicle_log(event: CombatEvent) -> None:
        print(f"[CHRONICLE] {event.event_key:35s} | "
              f"src={event.source:<15s} tgt={event.target or '—':<15s} | "
              f"{event.data}")

    bus.subscribe("*", chronicle_log)
    social = SocialStateSystem(bus)

    engine = CombatEngine(bus)

    # --- Build combatants ---
    hero = Combatant(
        name="Aric", is_player=True, max_hp=30,
        stats={"attack_bonus": 5, "defense_bonus": 3},
        damage_bonus=2, speed=10.0,
    )
    hero.register_with_bus(bus)

    # Blessing expires after hero's own attack
    hero.add_modifier(Modifier(
        name="Blessing of Swiftness",
        stat_target="defense_bonus",
        value=2,
        expires_on=[EVT_TURN_ENDED],
        max_triggers=1,
    ))

    foe = FoeFactory.generate(
        threat_level=2, archetype="Skirmisher",
        name_override="Cave Crawler",
    )
    foe.register_with_bus(bus)

    print(f"\n--- COMBAT START: {hero.name} vs {foe.name} ---")
    print(f"{foe.name} | HP:{foe.hp} "
          f"Atk:+{foe.get_stat('attack_bonus')} "
          f"Def:+{foe.get_stat('defense_bonus')}\n")

    round_num = 1
    while not hero.is_dead and not foe.is_dead:
        print(f"\n=== Round {round_num} ===")

        # Hero attacks
        engine.start_turn(hero)
        log = engine.resolve_attack(hero, foe)
        print(f"  {hero.name} → {foe.name}: "
              f"{log['outcome'].upper()} "
              f"[roll {log['roll']['total']} vs DC {log['dc']}] "
              f"dmg={log['damage']} | {foe.name} HP={log['defender_hp']}")

        if foe.is_dead:
            print(f"\n*** {foe.name} defeated! ***")
            break

        # Foe attacks
        engine.start_turn(foe)
        log = engine.resolve_attack(foe, hero)
        print(f"  {foe.name} → {hero.name}: "
              f"{log['outcome'].upper()} "
              f"[roll {log['roll']['total']} vs DC {log['dc']}] "
              f"dmg={log['damage']} | {hero.name} HP={log['defender_hp']}")

        print(f"  (SOCIAL) {foe.name} Stress: {social.get_stress(foe.name):.2f} | {hero.name} Stress: {social.get_stress(hero.name):.2f}")

        engine.end_round([hero, foe])
        round_num += 1

    if hero.is_dead:
        print(f"\n*** {hero.name} has perished. ***")
