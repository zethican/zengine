import pytest
import tcod.ecs
import tempfile
from pathlib import Path
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, ItemIdentity, Disposition, Faction
from engine.spawner import spawn_npc
from engine.ecs.systems import get_adjusted_value

def test_trade_item_valuation_math():
    registry = tcod.ecs.Registry()
    item = registry.new_entity()
    item.components[ItemIdentity] = ItemIdentity(entity_id="potion", name="Potion", description="Heals", value=100)
    
    # Neutral (1.0x)
    assert get_adjusted_value(item, 0.0, is_npc_item=True) == 100
    
    # Hostile (NPC items 2.0x, Player items 0.5x)
    assert get_adjusted_value(item, -0.5, is_npc_item=True) == 200
    assert get_adjusted_value(item, -0.5, is_npc_item=False) == 50
    
    # Friendly (NPC items 0.8x, Player items 1.2x)
    assert get_adjusted_value(item, 0.6, is_npc_item=True) == 80
    assert get_adjusted_value(item, 0.6, is_npc_item=False) == 120

def test_trade_execution_and_generosity():
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
        
        npc = spawn_npc(sim.registry, "hero_standard", 5, 5)
        npc.components[EntityIdentity].name = "Merchant"
        npc.components[Faction] = Faction(faction_id="merchants")
        
        # Give player an item
        p_item = sim.registry.new_entity()
        p_item.components[ItemIdentity] = ItemIdentity(entity_id="gold", name="Gold", description="Shiny", value=100)
        player.relation_tags_many["IsCarrying"].add(p_item)
        
        # Give NPC an item
        n_item = sim.registry.new_entity()
        n_item.components[ItemIdentity] = ItemIdentity(entity_id="bread", name="Bread", description="Tasty", value=20)
        npc.relation_tags_many["IsCarrying"].add(n_item)
        
        sim.open_session()
        
        # 1. Execute Generous Trade (100 value for 20 value)
        sim.execute_trade(player, npc, [p_item], [n_item], is_generous=True)
        
        # Verify swap
        assert p_item in npc.relation_tags_many["IsCarrying"]
        assert n_item in player.relation_tags_many["IsCarrying"]
        
        # Verify reputation (Base 0.05 + Generosity 0.10 = 0.15)
        # SocialStateSystem.get_reputation returns individual rep if it exists
        assert sim.social_system.get_reputation("Merchant") == 0.15
        
        # Faction standing should be 0.075 (0.15 * 0.5 conduction)
        assert sim.faction_standing["merchants"] == 0.075
        
        # 2. Test Cooldown (Immediate second gift should only give base 0.05)
        p_item2 = sim.registry.new_entity()
        p_item2.components[ItemIdentity] = ItemIdentity(entity_id="gold2", name="Gold2", description="Shiny", value=100)
        player.relation_tags_many["IsCarrying"].add(p_item2)
        
        sim.execute_trade(player, npc, [p_item2], [], is_generous=True)
        
        # Reputation should increase by only 0.05 (individual)
        # Total: 0.15 + 0.05 = 0.20
        assert sim.social_system.get_reputation("Merchant") == pytest.approx(0.20)
        
        sim.close_session()
