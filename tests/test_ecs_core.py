import tcod.ecs
import pytest
from engine.ecs.components import CombatVitals, Position, ActionEconomy

def test_ecs_registry_and_components():
    registry = tcod.ecs.Registry()
    
    # Create entity with core components (fix deprecation warning by using explicit keys if needed, 
    # but new_entity with list should work if components are unique types)
    hero = registry.new_entity()
    hero.components[CombatVitals] = CombatVitals(hp=30, max_hp=30)
    hero.components[Position] = Position(x=10, y=10)
    hero.components[ActionEconomy] = ActionEconomy(action_energy=0.0, ap_pool=100)
    
    # Query registry using registry.Q
    entities = list(registry.Q.all_of(components=[CombatVitals, Position]))
    assert len(entities) == 1
    assert entities[0] == hero
    
    # Check component values
    vitals = hero.components[CombatVitals]
    assert vitals.hp == 30
    assert vitals.max_hp == 30

def test_component_mutation():
    registry = tcod.ecs.Registry()
    npc = registry.new_entity()
    npc.components[CombatVitals] = CombatVitals(hp=10, max_hp=10)
    
    # Mutate through reference
    npc.components[CombatVitals].hp -= 5
    assert npc.components[CombatVitals].hp == 5

def test_query_filter():
    registry = tcod.ecs.Registry()
    
    e1 = registry.new_entity()
    e1.components[Position] = Position(x=1, y=1)
    
    e2 = registry.new_entity()
    e2.components[Position] = Position(x=2, y=2)
    e2.components[CombatVitals] = CombatVitals(hp=5, max_hp=5)
    
    # Entities with Position only
    all_pos = list(registry.Q.all_of(components=[Position]))
    assert len(all_pos) == 2
    
    # Entities with both Position and CombatVitals
    combatants = list(registry.Q.all_of(components=[Position, CombatVitals]))
    assert len(combatants) == 1
    assert combatants[0] == e2
