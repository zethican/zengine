"""
ZEngine — tests/test_integration_crafting.py
Testing Crafting integration with SimulationLoop and ActionResolution.
"""

import pytest
import tempfile
from pathlib import Path

from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, ActionEconomy, MovementStats, ItemIdentity
from engine.item_factory import create_item

def test_action_resolution_craft_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # Setup Hero
        hero = sim.registry.new_entity()
        hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        hero.components[Position] = Position(x=5, y=5)
        hero.components[ActionEconomy] = ActionEconomy(ap_pool=100)
        hero.components[MovementStats] = MovementStats(speed=10.0)
        
        # Setup Parts in inventory
        # We need entities with tags matching a recipe. 
        # data/recipes/basic_sword.toml: part_a_tag = "is_blade", part_b_tag = "is_hilt"
        
        part_a = create_item(sim.registry, "parts/iron_blade")
        part_b = create_item(sim.registry, "parts/wooden_hilt")
        
        hero.relation_tags_many["IsCarrying"].add(part_a)
        hero.relation_tags_many["IsCarrying"].add(part_b)
        
        sim.open_session()
        
        # Invoke craft
        success = sim.invoke_ability_ecs(hero, "craft", part_a=part_a, part_b=part_b)
        
        assert success is True
        
        # Verify result
        # The result should be 'weapons/iron_sword' (from basic_sword.toml)
        # It should be in the hero's inventory.
        
        carried_items = list(hero.relation_tags_many["IsCarrying"])
        assert len(carried_items) == 1
        
        result_item = carried_items[0]
        assert ItemIdentity in result_item.components
        assert result_item.components[ItemIdentity].entity_id == "iron_sword"
        
        # Verify parents are cleared
        assert part_a not in hero.relation_tags_many["IsCarrying"]
        assert part_b not in hero.relation_tags_many["IsCarrying"]
        
        sim.close_session()
