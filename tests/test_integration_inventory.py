"""
ZEngine — tests/test_integration_inventory.py
Testing Inventory integration with SimulationLoop and ActionResolution.
"""

import pytest
import tempfile
from pathlib import Path

from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, ActionEconomy, MovementStats, Anatomy
from engine.item_factory import create_item

def test_action_resolution_pickup_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # Setup Hero
        hero = sim.registry.new_entity()
        hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        hero.components[Position] = Position(x=5, y=5)
        hero.components[ActionEconomy] = ActionEconomy(ap_pool=100)
        hero.components[MovementStats] = MovementStats(speed=10.0)
        
        # Setup Item on floor at same pos
        item = create_item(sim.registry, "weapons/iron_sword")
        item.components[Position] = Position(x=5, y=5)
        
        sim.open_session()
        
        # Invoke pickup via SimulationLoop (which calls action_resolution_system)
        # Note: action_resolution_system currently only handles abilities. 
        # I need to update it to handle 'pickup', 'drop', 'equip'.
        
        success = sim.invoke_ability_ecs(hero, "pickup", item)
        
        assert success is True
        assert Position not in item.components
        assert item in hero.relation_tags_many["IsCarrying"]
        
        sim.close_session()

def test_action_resolution_equip_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # Setup Hero
        hero = sim.registry.new_entity()
        hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        hero.components[Position] = Position(x=5, y=5)
        hero.components[ActionEconomy] = ActionEconomy(ap_pool=100)
        hero.components[Anatomy] = Anatomy(available_slots=["hand"])
        
        # Setup Item in inventory
        item = create_item(sim.registry, "weapons/iron_sword")
        hero.relation_tags_many["IsCarrying"].add(item)
        
        sim.open_session()
        
        # Invoke equip
        success = sim.invoke_ability_ecs(hero, "equip", item)
        
        assert success is True
        assert item in hero.relation_tags_many["IsEquipped"]
        
        sim.close_session()
