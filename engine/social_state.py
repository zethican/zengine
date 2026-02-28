"""
ZEngine — engine/social_state.py
Social State System: Reputation, stress, resilience, and disposition logic.
==========================================================================
Version:     0.3  (Phase 14 Step 2 — Faction Conduction)
Stack:       Python 3.14.3 | bespoke EventBus | python-tcod-ecs
Status:      Production-ready.
"""

from __future__ import annotations
from typing import Dict, Any, Optional

import tcod.ecs
from engine.combat import (
    CombatEvent,
    EventBus,
    EVT_ON_DAMAGE,
    EVT_ON_DEATH,
    EVT_SOCIAL_STRESS_SPIKE,
    EVT_SOCIAL_DISPOSITION_SHIFT,
)
from engine.ecs.components import EntityIdentity, Disposition, Stress, Faction

class SocialStateSystem:
    def __init__(self, bus: EventBus, registry: tcod.ecs.Registry, faction_standing: Optional[Dict[str, float]] = None):
        self.bus = bus
        self.registry = registry
        # Reference to the loop's faction dictionary for atomic updates
        self.faction_standing = faction_standing if faction_standing is not None else {}
        
        bus.subscribe(EVT_ON_DAMAGE, self._on_damage)
        bus.subscribe(EVT_ON_DEATH, self._on_death)
        bus.subscribe(EVT_SOCIAL_STRESS_SPIKE, self._on_stress_spike)
        bus.subscribe(EVT_SOCIAL_DISPOSITION_SHIFT, self._on_disposition_shift)

    def _get_entity_by_name(self, name: str) -> Optional[tcod.ecs.Entity]:
        """Finds an entity by its display name in EntityIdentity."""
        for entity in self.registry.Q.all_of(components=[EntityIdentity]):
            if entity.components[EntityIdentity].name == name:
                return entity
        return None

    def get_stress(self, name: str) -> float:
        """Helper to get stress level by entity name."""
        entity = self._get_entity_by_name(name)
        if entity:
            if Stress not in entity.components:
                entity.components[Stress] = Stress()
            return entity.components[Stress].stress_level
        return 0.0

    def get_reputation(self, name: str) -> float:
        """Helper to get reputation by entity name."""
        entity = self._get_entity_by_name(name)
        if entity:
            if Disposition in entity.components:
                return entity.components[Disposition].reputation
            
            # Check Faction Standing fallback
            if Faction in entity.components:
                fid = entity.components[Faction].faction_id
                return self.faction_standing.get(fid, 0.0)
                
        return 0.0

    def _on_damage(self, event: CombatEvent) -> None:
        target = event.target
        if not target: return
        amount = event.data.get("amount", 0)
        self.bus.emit(CombatEvent(
            event_key=EVT_SOCIAL_STRESS_SPIKE,
            source=target,
            data={"magnitude": amount / 100.0, "cause": "combat_damage"}
        ))

    def _on_death(self, event: CombatEvent) -> None:
        # source is the one who died
        self.bus.emit(CombatEvent(
            event_key=EVT_SOCIAL_STRESS_SPIKE,
            source=event.source,
            data={"magnitude": 0.5, "cause": "combat_death"}
        ))
        
        # Reputation loss for killing someone
        # (Assuming player is the cause for now in MVP)
        self.bus.emit(CombatEvent(
            event_key=EVT_SOCIAL_DISPOSITION_SHIFT,
            source=event.source,
            data={"delta": -0.2, "cause": "killing"}
        ))

    def _on_stress_spike(self, event: CombatEvent) -> None:
        entity = self._get_entity_by_name(event.source)
        if entity:
            if Stress not in entity.components:
                entity.components[Stress] = Stress()
            comp = entity.components[Stress]
            comp.stress_level = min(1.0, comp.stress_level + event.data.get("magnitude", 0.0))

    def _on_disposition_shift(self, event: CombatEvent) -> None:
        """Handles reputation shifts and faction conduction."""
        entity = self._get_entity_by_name(event.source)
        if not entity: return
        
        delta = event.data.get("delta", 0.0)
        
        # 1. Update Individual Disposition
        if Disposition not in entity.components:
            entity.components[Disposition] = Disposition()
        disp = entity.components[Disposition]
        disp.reputation = max(-1.0, min(1.0, disp.reputation + delta))
        
        # 2. Conduction: Update Faction Standing
        if Faction in entity.components:
            fid = entity.components[Faction].faction_id
            conduction_factor = 0.5 # 50% of delta propagates to faction
            current = self.faction_standing.get(fid, 0.0)
            self.faction_standing[fid] = max(-1.0, min(1.0, current + (delta * conduction_factor)))
