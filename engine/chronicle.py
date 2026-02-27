"""
ZEngine — engine/chronicle.py
Chronicle System: Append-only event journal with epistemic provenance.
======================================================================
Version:     0.1  (Phase 2 — canonical implementation)
Stack:       Python 3.14.3 | stdlib json | bespoke EventBus
Status:      Production-ready for Phase 2. No gameplay logic here.

Architecture notes
------------------
- Chronicle is a PASSIVE wildcard subscriber. It never emits events.
- Append-only JSONL. Inscribed entries are immutable after write.
  Corrections must be new entries referencing the superseded event_id.
- Provenance (witnessed/fabricated) is assigned at inscription time and
  never changed. Player-present encounters → "witnessed". All others →
  "fabricated".
- Significance gate (int 1–5): events below CHRONICLE_SIGNIFICANCE_MIN
  are discarded silently. Default threshold = 2.
- Legibility is "transparent" MVP default. "obscured" is post-MVP.
- citation_count is dormant MVP. Active in post-MVP reconciliation.
- Game time (era/cycle/tick) must be injected via GameClock at
  construction. Chronicle never reads system clock.

Hard Limits Applied Here
------------------------
  #1  No direct inter-layer mutation. Chronicle is read-only (it writes
      JSONL, never components).
  #2  No Chronicle entry modification after inscription. New entry only.
  #7  All design variables documented. No silent defaults.
  #10 Never raw strings for event keys. EVT_* constants only.
  #11 No global EventBus. Bus injected at construction via subscribe().

Significance Scoring Reference (CHRONICLE_SIGNIFICANCE_MIN = 2)
----------------------------------------------------------------
  1 — ambient / noise (EVT_TURN_STARTED, EVT_TURN_ENDED, routine ticks)
  2 — standard combat action (EVT_ACTION_RESOLVED, EVT_ON_DAMAGE)
  3 — notable (EVT_MODIFIER_ADDED, EVT_MODIFIER_EXPIRED, round summary)
  4 — significant (EVT_ON_DEATH, EVT_SOCIAL_STRESS_SPIKE high-magnitude)
  5 — legendary (EVT_SOCIAL_DISPOSITION_SHIFT extreme, Legacy Conversion)

Session Markers
---------------
  "chronicle.session_opened" and "chronicle.session_closed" are inscribed
  unconditionally (no significance gate) via open_session() / close_session().

Design Variables (must not be hardcoded elsewhere)
---------------------------------------------------
  CHRONICLE_SIGNIFICANCE_MIN       2    — minimum significance to inscribe
  CHRONICLE_CONFIDENCE_WITNESSED   0.9  — default confidence when player present
  CHRONICLE_CONFIDENCE_FABRICATED  0.4  — default confidence when player absent
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

from engine.combat import (
    CombatEvent,
    EventBus,
    EVT_TURN_STARTED,
    EVT_ACTION_RESOLVED,
    EVT_TURN_ENDED,
    EVT_ROUND_ENDED,
    EVT_ON_DAMAGE,
    EVT_ON_DEATH,
    EVT_MODIFIER_ADDED,
    EVT_MODIFIER_EXPIRED,
    EVT_SOCIAL_STRESS_SPIKE,
    EVT_SOCIAL_DISPOSITION_SHIFT,
)


# ============================================================
# DESIGN VARIABLE DEFAULTS
# Change here or override via ChronicleConfig. Never hardcode elsewhere.
# ============================================================

CHRONICLE_SIGNIFICANCE_MIN: int = 2
CHRONICLE_CONFIDENCE_WITNESSED: float = 0.9
CHRONICLE_CONFIDENCE_FABRICATED: float = 0.4


# ============================================================
# SIGNIFICANCE SCORING TABLE
# Each EVT_* key maps to a default significance int (1–5).
# Events not listed default to significance 1 (below threshold → discarded).
# Override per-call via score_significance() extensions.
# ============================================================

_SIGNIFICANCE_TABLE: Dict[str, int] = {
    # Combat — routine (significance 1: usually discarded)
    EVT_TURN_STARTED:         1,
    EVT_TURN_ENDED:           1,

    # Combat — standard (significance 2: inscribed by default)
    EVT_ACTION_RESOLVED:      2,
    EVT_ON_DAMAGE:            2,

    # Combat — notable (significance 3: always inscribed)
    EVT_MODIFIER_ADDED:       3,
    EVT_MODIFIER_EXPIRED:     3,
    EVT_ROUND_ENDED:          3,

    # Combat — significant (significance 4: high-priority history)
    EVT_ON_DEATH:             4,

    # Social — magnitude-dependent (base 3; raised to 4 by magnitude check)
    EVT_SOCIAL_STRESS_SPIKE:  3,

    # Social — significant (significance 5: lore-grade)
    EVT_SOCIAL_DISPOSITION_SHIFT: 5,
}


# ============================================================
# GAME CLOCK INTERFACE
# Chronicle never reads wall time. Game time is injected.
# ============================================================

@dataclass
class GameTimestamp:
    """
    Narrative game time. Used in Chronicle entries.

    era:   "Ancient" | "Middle" | "Recent"  (world-age epoch)
    cycle: int  (in-world year or major story arc, 1-indexed)
    tick:  int  (in-world turn number within cycle, 1-indexed)
    """
    era: str = "Recent"
    cycle: int = 1
    tick: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {"era": self.era, "cycle": self.cycle, "tick": self.tick}

    def advance_tick(self) -> "GameTimestamp":
        """Return a new timestamp with tick incremented by 1."""
        return GameTimestamp(era=self.era, cycle=self.cycle, tick=self.tick + 1)


# ============================================================
# CHRONICLE ENTRY  (immutable after construction)
# Schema from SYSTEMS.md § chronicle_inscriber_system
# ============================================================

@dataclass(frozen=True)
class ChronicleEntry:
    """
    Immutable record of a single inscribed event.

    Frozen dataclass enforces immutability in Python.
    Fields match the canonical schema in SYSTEMS.md.

    Hard Limit #2: Once inscribed, entries are never modified.
    Corrections must be new ChronicleEntry objects referencing
    this entry's event_id in their payload.
    """
    event_id: str                       # UUID4 string
    timestamp: Dict[str, Any]           # {era, cycle, tick}
    provenance: str                     # "witnessed" | "fabricated"
    legibility: str                     # "transparent" | "obscured" (MVP: always transparent)
    actor_handle: str                   # abstract actor reference (entity name MVP; Legacy handle post-MVP)
    payload: Dict[str, Any]             # {event_type, verb, object, modifier}
    confidence: float                   # 0.0–1.0
    citation_count: int                 # dormant MVP (always 0 at inscription)
    significance: int                   # 1–5

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict for JSONL write."""
        return {
            "event_id":      self.event_id,
            "timestamp":     self.timestamp,
            "provenance":    self.provenance,
            "legibility":    self.legibility,
            "actor_handle":  self.actor_handle,
            "payload":       self.payload,
            "confidence":    self.confidence,
            "citation_count": self.citation_count,
            "significance":  self.significance,
        }


# ============================================================
# PAYLOAD BUILDER
# Converts a CombatEvent into the Chronicle payload sub-dict:
#   {event_type, verb, object, modifier}
# "modifier" is the event-specific detail field (not a Modifier instance).
# ============================================================

def _build_combat_action_payload(key: str, event: CombatEvent, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if key == EVT_ACTION_RESOLVED:
        return {
            "event_type": key,
            "verb": "attacked",
            "object": event.target or data.get("defender", "unknown"),
            "modifier": {
                "outcome": data.get("outcome"),
                "damage": data.get("damage"),
                "roll_total": data.get("roll", {}).get("total"),
                "dc": data.get("dc"),
                "is_crit": data.get("roll", {}).get("is_crit", False),
                "is_fumble": data.get("roll", {}).get("is_fumble", False),
            },
        }
    if key == EVT_ON_DAMAGE:
        return {
            "event_type": key,
            "verb": "took_damage",
            "object": event.source,
            "modifier": {
                "amount": data.get("amount"),
                "hp_remaining": data.get("hp_remaining"),
            },
        }
    if key == EVT_ON_DEATH:
        return {
            "event_type": key,
            "verb": "died",
            "object": event.source,
            "modifier": {"final_hp": data.get("final_hp")},
        }
    return None

def _build_turn_flow_payload(key: str, event: CombatEvent, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if key == EVT_TURN_STARTED:
        return {
            "event_type": key,
            "verb": "activated",
            "object": event.source,
            "modifier": {"action_energy": data.get("action_energy")},
        }
    if key == EVT_TURN_ENDED:
        return {
            "event_type": key,
            "verb": "ended_turn",
            "object": event.source,
            "modifier": {"ap_spent": data.get("ap_spent", 0)},
        }
    if key == EVT_ROUND_ENDED:
        return {
            "event_type": key,
            "verb": "round_concluded",
            "object": event.source,
            "modifier": {
                "hp": data.get("hp"),
                "modifiers": data.get("modifiers", []),
            },
        }
    return None

def _build_modifier_payload(key: str, event: CombatEvent, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if key == EVT_MODIFIER_ADDED:
        return {
            "event_type": key,
            "verb": "received_effect",
            "object": event.source,
            "modifier": {
                "name": data.get("modifier"),
                "stat": data.get("stat"),
                "value": data.get("value"),
                "expires_on": data.get("expires_on", []),
            },
        }
    if key == EVT_MODIFIER_EXPIRED:
        return {
            "event_type": key,
            "verb": "effect_expired",
            "object": event.source,
            "modifier": {
                "name": data.get("modifier"),
                "stat": data.get("stat"),
            },
        }
    return None

def _build_social_payload(key: str, event: CombatEvent, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if key == EVT_SOCIAL_STRESS_SPIKE:
        return {
            "event_type": key,
            "verb": "stressed",
            "object": event.source,
            "modifier": {
                "cause": data.get("cause"),
                "magnitude": data.get("magnitude"),
                "source_entity": data.get("source_entity"),
            },
        }
    if key == EVT_SOCIAL_DISPOSITION_SHIFT:
        return {
            "event_type": key,
            "verb": "reputation_shifted",
            "object": event.source,
            "modifier": {
                "direction": data.get("direction"),
                "amount": data.get("amount"),
                "reason": data.get("reason"),
                "party_entity": data.get("party_entity"),
            },
        }
    return None

def build_payload(event: CombatEvent) -> Dict[str, Any]:
    """
    Build the Chronicle-normalized payload from a raw CombatEvent.

    The payload schema is:
      event_type: str  — canonical EVT_* value
      verb:       str  — past-tense action description
      object:     str  — target entity, item, or effect
      modifier:   Any  — event-specific supplemental detail (JSON-safe)

    This is intentionally a thin normalization layer. Raw event data
    is preserved under 'modifier' for fidelity. The verb/object pair
    is what downstream grammar tables will consume (post-MVP).
    """
    key = event.event_key
    data = event.data

    payload = _build_combat_action_payload(key, event, data)
    if payload is not None: return payload

    payload = _build_turn_flow_payload(key, event, data)
    if payload is not None: return payload

    payload = _build_modifier_payload(key, event, data)
    if payload is not None: return payload

    payload = _build_social_payload(key, event, data)
    if payload is not None: return payload

    # --- Fallback: unknown / session marker events ---
    return {
        "event_type": key,
        "verb": "occurred",
        "object": event.source,
        "modifier": dict(data),
    }

# ============================================================
# SIGNIFICANCE SCORER
# Computes int 1–5. Includes magnitude-based overrides.
# ============================================================

def score_significance(event: CombatEvent) -> int:
    """
    Return significance score (int 1–5) for an event.

    Uses _SIGNIFICANCE_TABLE as the base. Applies overrides:
      - EVT_SOCIAL_STRESS_SPIKE with magnitude >= 0.5 → raised to 4
      - EVT_ON_DEATH always → 4 regardless of table
    """
    base = _SIGNIFICANCE_TABLE.get(event.event_key, 1)

    # Magnitude override: high-stress spikes are more significant
    if event.event_key == EVT_SOCIAL_STRESS_SPIKE:
        magnitude = event.data.get("magnitude", 0.0)
        if isinstance(magnitude, (int, float)) and magnitude >= 0.5:
            base = max(base, 4)

    return base


# ============================================================
# CHRONICLE INSCRIBER SYSTEM
# Wildcard subscriber. Writes to JSONL. Never emits events.
# ============================================================

class ChronicleInscriber:
    """
    Passive wildcard subscriber that evaluates every CombatEvent and
    inscribes qualifying entries to an append-only JSONL file.

    Usage:
        bus = EventBus()
        clock = GameTimestamp(era="Recent", cycle=1, tick=1)
        inscriber = ChronicleInscriber(
            bus=bus,
            chronicle_path=Path("sessions/chronicle.jsonl"),
            clock=clock,
            player_present=True,
        )
        # ... game loop ...
        inscriber.open_session()
        # run encounter
        inscriber.close_session()

    Hard Limits:
        #2  — entries are frozen (ChronicleEntry is frozen=True dataclass)
        #11 — bus is injected; no global singleton
    """

    def __init__(
        self,
        bus: EventBus,
        chronicle_path: Path,
        clock: GameTimestamp,
        player_present: bool = True,
        significance_min: int = CHRONICLE_SIGNIFICANCE_MIN,
        confidence_witnessed: float = CHRONICLE_CONFIDENCE_WITNESSED,
        confidence_fabricated: float = CHRONICLE_CONFIDENCE_FABRICATED,
    ) -> None:
        self.bus = bus
        self.chronicle_path = chronicle_path
        self.clock = clock
        self.player_present = player_present
        self.significance_min = significance_min
        self.confidence_witnessed = confidence_witnessed
        self.confidence_fabricated = confidence_fabricated

        # Ensure parent directory exists
        self.chronicle_path.parent.mkdir(parents=True, exist_ok=True)

        # Subscribe as wildcard receiver — always last registered
        bus.subscribe("*", self._on_event)

    # ----------------------------------------------------------
    # Public API: session lifecycle
    # ----------------------------------------------------------

    def open_session(self) -> None:
        """
        Inscribe session-open marker unconditionally.
        No significance gate for session markers.
        """
        marker = CombatEvent(
            event_key="chronicle.session_opened",
            source="system",
            data={"clock": self.clock.to_dict(), "player_present": self.player_present},
        )
        self._inscribe(marker, significance=5, bypass_gate=True)

    def close_session(self) -> None:
        """
        Inscribe session-close marker unconditionally.
        No significance gate for session markers.
        """
        marker = CombatEvent(
            event_key="chronicle.session_closed",
            source="system",
            data={"clock": self.clock.to_dict()},
        )
        self._inscribe(marker, significance=5, bypass_gate=True)

    def advance_clock(self, ticks: int = 1) -> None:
        """Advance the injected clock by N ticks in place."""
        for _ in range(ticks):
            self.clock = self.clock.advance_tick()

    def set_player_present(self, present: bool) -> None:
        """
        Update player-present flag. Provenance assignments after this
        call reflect the new state.
        """
        self.player_present = present

    # ----------------------------------------------------------
    # Internal: wildcard subscriber
    # ----------------------------------------------------------

    def _on_event(self, event: CombatEvent) -> None:
        """
        Called for every event emitted on the bus (wildcard subscription).
        Evaluates significance gate, then inscribes.
        """
        significance = score_significance(event)
        if significance < self.significance_min:
            return  # below threshold; discard silently
        self._inscribe(event, significance=significance)

    # ----------------------------------------------------------
    # Internal: inscription
    # ----------------------------------------------------------

    def _inscribe(
        self,
        event: CombatEvent,
        significance: int,
        bypass_gate: bool = False,
    ) -> ChronicleEntry:
        """
        Build a ChronicleEntry and append to JSONL.
        Returns the inscribed entry (for testing / integration).

        bypass_gate is True only for session lifecycle markers.
        """
        provenance = "witnessed" if self.player_present else "fabricated"
        confidence = (
            self.confidence_witnessed
            if provenance == "witnessed"
            else self.confidence_fabricated
        )

        entry = ChronicleEntry(
            event_id=str(uuid.uuid4()),
            timestamp=self.clock.to_dict(),
            provenance=provenance,
            legibility="transparent",      # MVP default; "obscured" is post-MVP
            actor_handle=event.source,     # MVP: entity name; Legacy handle post-MVP
            payload=build_payload(event),
            confidence=confidence,
            citation_count=0,              # dormant MVP
            significance=significance,
        )

        self._append_jsonl(entry)
        return entry

    def _append_jsonl(self, entry: ChronicleEntry) -> None:
        """
        Append a single ChronicleEntry as a JSON line.
        File is opened in append mode; never truncated.
        Hard Limit #2: entries are never modified after write.
        """
        with open(self.chronicle_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")


# ============================================================
# CHRONICLE READER  (query interface — read-only)
# Utility for tests and post-MVP reconciliation.
# ============================================================

class ChronicleReader:
    """
    Read-only query interface for a chronicle.jsonl file.

    Entries are never modified. All queries return lists of dicts.
    The JSONL format is one JSON object per line.
    """

    def __init__(self, chronicle_path: Path) -> None:
        self.chronicle_path = chronicle_path

    def all_entries(self) -> List[Dict[str, Any]]:
        """Return all inscribed entries in insertion order."""
        if not self.chronicle_path.exists():
            return []
        entries = []
        with open(self.chronicle_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def by_event_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Return all entries whose payload.event_type matches."""
        return [
            e for e in self.all_entries()
            if e.get("payload", {}).get("event_type") == event_type
        ]

    def by_actor(self, actor_handle: str) -> List[Dict[str, Any]]:
        """Return all entries for a given actor handle."""
        return [
            e for e in self.all_entries()
            if e.get("actor_handle") == actor_handle
        ]

    def by_significance(self, minimum: int) -> List[Dict[str, Any]]:
        """Return entries at or above a given significance threshold."""
        return [
            e for e in self.all_entries()
            if e.get("significance", 0) >= minimum
        ]

    def deaths(self) -> List[Dict[str, Any]]:
        """Convenience: all death events (significance 4)."""
        return self.by_event_type(EVT_ON_DEATH)

    def session_markers(self) -> List[Dict[str, Any]]:
        """Return all session open/close marker entries."""
        return [
            e for e in self.all_entries()
            if e.get("payload", {}).get("event_type", "").startswith("chronicle.session")
        ]


# ============================================================
# SMOKE TEST
# ============================================================

if __name__ == "__main__":
    import tempfile
    import os
    from engine.combat import (
        Combatant, FoeFactory, CombatEngine,
    )
    from engine.social_state import SocialStateSystem

    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "sessions" / "chronicle.jsonl"

        bus = EventBus()
        clock = GameTimestamp(era="Recent", cycle=1, tick=1)
        inscriber = ChronicleInscriber(
            bus=bus,
            chronicle_path=chronicle_path,
            clock=clock,
            player_present=True,
        )

        social_system = SocialStateSystem(bus)
        engine = CombatEngine(bus)

        hero = Combatant(
            name="Aric", is_player=True, max_hp=30,
            stats={"attack_bonus": 5, "defense_bonus": 3},
            damage_bonus=2, speed=10.0,
        )
        hero.register_with_bus(bus)

        foe = FoeFactory.generate(
            threat_level=2, archetype="Skirmisher",
            name_override="Cave Crawler",
        )
        foe.register_with_bus(bus)

        print("\n--- CHRONICLE SMOKE TEST ---")
        inscriber.open_session()

        round_num = 1
        while not hero.is_dead and not foe.is_dead and round_num <= 10:
            inscriber.clock = inscriber.clock.advance_tick()
            engine.start_turn(hero)
            engine.resolve_attack(hero, foe)
            if foe.is_dead:
                break
            inscriber.clock = inscriber.clock.advance_tick()
            engine.start_turn(foe)
            engine.resolve_attack(foe, hero)
            engine.end_round([hero, foe])
            round_num += 1

        inscriber.close_session()

        # --- Read back and report ---
        reader = ChronicleReader(chronicle_path)
        all_entries = reader.all_entries()
        print(f"\nTotal entries inscribed: {len(all_entries)}")

        deaths = reader.deaths()
        print(f"Death events: {len(deaths)}")
        for d in deaths:
            print(f"  [{d['provenance']}] {d['actor_handle']} died "
                  f"(significance {d['significance']}, confidence {d['confidence']})")

        markers = reader.session_markers()
        print(f"Session markers: {len(markers)}")
        for m in markers:
            print(f"  {m['payload']['event_type']} @ tick {m['timestamp']['tick']}")

        print(f"\nChronicle JSONL path: {chronicle_path}")
        print("\nSignificance distribution:")
        from collections import Counter
        dist = Counter(e["significance"] for e in all_entries)
        for sig in sorted(dist):
            print(f"  [{sig}] {dist[sig]} entries")

        print("\n✅ chronicle.py smoke test passed.")
