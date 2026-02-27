import pytest
from engine.social_state import SocialStateSystem, SocialComponent
from engine.combat import EventBus, CombatEvent, EVT_ON_DAMAGE, EVT_ON_DEATH

def test_social_component_initialization():
    comp = SocialComponent()
    assert comp.reputation == 0.0
    assert comp.moral_weight == 0.5
    assert comp.stress == 0.0
    assert comp.resilience == 1.0

def test_stress_spike_on_damage():
    bus = EventBus()
    social = SocialStateSystem(bus)
    
    # Target starts with 0 stress
    bus.emit(CombatEvent(
        event_key=EVT_ON_DAMAGE,
        source="Hero",
        target="NPC",
        data={"amount": 10}
    ))
    
    # 10 damage / 100 = 0.1 stress
    assert social.get_stress("NPC") == 0.1

def test_stress_max_cap():
    bus = EventBus()
    social = SocialStateSystem(bus)
    
    bus.emit(CombatEvent(
        event_key=EVT_ON_DAMAGE,
        source="Hero",
        target="NPC",
        data={"amount": 200}
    ))
    
    assert social.get_stress("NPC") == 1.0

def test_stress_spike_on_death():
    bus = EventBus()
    social = SocialStateSystem(bus)
    
    bus.emit(CombatEvent(
        event_key=EVT_ON_DEATH,
        source="NPC",
        data={"final_hp": -5}
    ))
    
    # Death should trigger a significant stress spike (e.g., 0.5)
    assert social.get_stress("NPC") == 0.5
