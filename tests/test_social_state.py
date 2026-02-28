import pytest
import tcod.ecs
from engine.social_state import SocialStateSystem
from engine.combat import EventBus, CombatEvent, EVT_ON_DAMAGE, EVT_ON_DEATH
from engine.ecs.components import EntityIdentity, Disposition, Stress

def test_social_components_initialization():
    registry = tcod.ecs.Registry()
    ent = registry.new_entity()
    ent.components[Disposition] = Disposition()
    ent.components[Stress] = Stress()
    
    assert ent.components[Disposition].reputation == 0.0
    assert ent.components[Disposition].moral_weight == 0.5
    assert ent.components[Stress].stress_level == 0.0
    assert ent.components[Disposition].resilience == 1.0

def test_stress_spike_on_damage():
    bus = EventBus()
    registry = tcod.ecs.Registry()
    social = SocialStateSystem(bus, registry)
    
    npc = registry.new_entity()
    npc.components[EntityIdentity] = EntityIdentity(entity_id=1, name="NPC", archetype="NPC")
    
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
    registry = tcod.ecs.Registry()
    social = SocialStateSystem(bus, registry)
    
    npc = registry.new_entity()
    npc.components[EntityIdentity] = EntityIdentity(entity_id=1, name="NPC", archetype="NPC")
    
    bus.emit(CombatEvent(
        event_key=EVT_ON_DAMAGE,
        source="Hero",
        target="NPC",
        data={"amount": 200}
    ))
    
    assert social.get_stress("NPC") == 1.0

def test_stress_spike_on_death():
    bus = EventBus()
    registry = tcod.ecs.Registry()
    social = SocialStateSystem(bus, registry)
    
    npc = registry.new_entity()
    npc.components[EntityIdentity] = EntityIdentity(entity_id=1, name="NPC", archetype="NPC")
    
    bus.emit(CombatEvent(
        event_key=EVT_ON_DEATH,
        source="NPC",
        data={"final_hp": -5}
    ))
    
    # Death should trigger a significant stress spike (e.g., 0.5)
    assert social.get_stress("NPC") == 0.5
