import pytest
import tcod.ecs
import tempfile
from pathlib import Path
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, ActiveModifiers, Attributes, CombatStats
from engine.item_factory import create_item
from engine.ecs.systems import get_effective_stats

def test_consumable_attribute_buff():
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
        player.components[Attributes] = Attributes(scores={"might": 10})
        player.components[CombatStats] = CombatStats()
        from engine.ecs.components import ActionEconomy, CombatVitals
        player.components[ActionEconomy] = ActionEconomy(ap_pool=100)
        player.components[CombatVitals] = CombatVitals(hp=10, max_hp=10)
        
        # 1. Check base might mod
        from engine.ecs.systems import get_attr_mod
        assert get_attr_mod(player, "might") == 0 # (10-10)//2
        
        # 2. Use Strength Potion
        potion = create_item(sim.registry, "consumables/strength_potion")
        player.relation_tags_many["IsCarrying"].add(potion)
        
        sim.open_session()
        sim.invoke_ability_ecs(player, "use", potion)
        
        # 3. Verify Buff
        # Might should now be 10 + 5 = 15
        # Mod should be (15-10)//2 = 2
        assert get_attr_mod(player, "might") == 2
        
        # Verify derived damage bonus (Might mod 2 + base 0 = 2)
        eff = get_effective_stats(player)
        assert eff.damage_bonus == 2
        
        # 4. Test Duration Refresh (Option A)
        # Manually set duration low
        player.components[ActiveModifiers].effects[0].duration = 10
        
        # Use another potion
        potion2 = create_item(sim.registry, "consumables/strength_potion")
        player.relation_tags_many["IsCarrying"].add(potion2)
        sim.invoke_ability_ecs(player, "use", potion2)
        
        # Duration should be refreshed to 1000
        assert player.components[ActiveModifiers].effects[0].duration == 1000
        # Still only one effect
        assert len(player.components[ActiveModifiers].effects) == 1
        
        sim.close_session()
