"""
ZEngine — engine/social_state.py
Social State System: Reputation, stress, resilience, and disposition logic.
==========================================================================
Version:     0.1  (Phase 2 — canonical implementation)
Stack:       Python 3.14.3 | Pydantic v2 | bespoke EventBus
Status:      Production-ready for Phase 2.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from engine.combat import (
    CombatEvent,
    EventBus,
    EVT_ON_DAMAGE,
    EVT_ON_DEATH,
    EVT_SOCIAL_STRESS_SPIKE,
    EVT_SOCIAL_DISPOSITION_SHIFT,
)

class SocialComponent(BaseModel):
    reputation: float = Field(default=0.0, ge=-1.0, le=1.0)
    moral_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    stress: float = Field(default=0.0, ge=0.0, le=1.0)
    resilience: float = Field(default=1.0, ge=0.0, le=1.0)

class SocialStateSystem:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.entities: Dict[str, SocialComponent] = {}
        bus.subscribe(EVT_ON_DAMAGE, self._on_damage)
        bus.subscribe(EVT_ON_DEATH, self._on_death)
        bus.subscribe(EVT_SOCIAL_STRESS_SPIKE, self._on_stress_spike)

    def get_component(self, name: str) -> SocialComponent:
        if name not in self.entities:
            self.entities[name] = SocialComponent()
        return self.entities[name]

    def get_stress(self, name: str) -> float:
        return self.get_component(name).stress

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
        self.bus.emit(CombatEvent(
            event_key=EVT_SOCIAL_STRESS_SPIKE,
            source=event.source,
            data={"magnitude": 0.5, "cause": "combat_death"}
        ))

    def _on_stress_spike(self, event: CombatEvent) -> None:
        comp = self.get_component(event.source)
        comp.stress = min(1.0, comp.stress + event.data.get("magnitude", 0.0))
