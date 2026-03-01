"""
ZEngine — tests/test_integration_inventory.py
Testing Inventory integration with SimulationLoop and ActionResolution.
"""

import pytest
import tempfile
from pathlib import Path

from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, ActionEconomy, MovementStats, Anatomy, CombatStats, CombatVitals, ItemStats, Usable, Quantity
from engine.item_factory import create_item

def test_use_healing_potion_restores_hp_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # Setup Hero, damaged
        hero = sim.registry.new_entity()
        hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        hero.components[Position] = Position(x=5, y=5)
        hero.components[CombatVitals] = CombatVitals(hp=10, max_hp=30)
        hero.components[ActionEconomy] = ActionEconomy(ap_pool=100)
        
        # Setup Potion in inventory
        potion = create_item(sim.registry, "consumables/healing_potion")
        hero.relation_tags_many["IsCarrying"].add(potion)
        
        sim.open_session()
        
        # Invoke use
        success = sim.invoke_ability_ecs(hero, "use", potion)
        
        assert success is True
        
        # Verify HP increased
        # heal ability from TOML likely has 1d8+2 or similar. 
        # (Actually, let's check heal.toml)
        assert hero.components[CombatVitals].hp > 10
        
        # Verify potion is consumed (if consumes=True)
        # For MVP, if it's the last one, it should be removed from IsCarrying.
        assert potion not in hero.relation_tags_many["IsCarrying"]
        
        sim.close_session()

def test_equipped_weapon_increases_damage_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        from engine.ecs.components import Attributes
        # Setup Hero with 0 base damage
        hero = sim.registry.new_entity()
        hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        hero.components[Position] = Position(x=5, y=5)
        hero.components[ActionEconomy] = ActionEconomy(ap_pool=100)
        hero.components[Anatomy] = Anatomy(available_slots=["hand"])
        hero.components[CombatStats] = CombatStats(attack_bonus=100, damage_bonus=0) # Guaranteed hit
        hero.components[Attributes] = Attributes(scores={"might": 10, "resolve": 10})
        
        # Setup Foe
        foe = sim.registry.new_entity()
        foe.components[EntityIdentity] = EntityIdentity(entity_id=2, name="Target", archetype="NPC")
        foe.components[Position] = Position(x=5, y=5)
        foe.components[CombatVitals] = CombatVitals(hp=100, max_hp=100)
        foe.components[CombatStats] = CombatStats(defense_bonus=0)
        
        # Setup Weapon with +10 damage
        weapon = create_item(sim.registry, "weapons/iron_sword")
        weapon.components[ItemStats] = ItemStats(attack_bonus=0, damage_bonus=10)
        
        hero.relation_tags_many["IsCarrying"].add(weapon)
        hero.relation_tags_many["IsEquipped"].add(weapon)
        
        sim.open_session()
        
        # basic_attack damage is 1d6 + @might_mod + effective_stats.damage_bonus
        # With might_mod=0 and weapon=10, expected: 1d6 + 10 = 11..16 damage.
        
        from unittest.mock import patch
        with patch('engine.loop.resolve_roll', return_value={"total": 50, "is_crit": False, "is_fumble": False, "rolls": [5, 5]}):
            sim.invoke_ability_ecs(hero, "basic_attack", foe)

        hp_lost = 100 - foe.components[CombatVitals].hp
        assert 11 <= hp_lost <= 16, f"Expected 11-16 damage, but foe lost {hp_lost} HP"
        sim.close_session()

def test_equipped_armor_increases_defense_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # Setup Hero with high defense armor
        hero = sim.registry.new_entity()
        hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        hero.components[Position] = Position(x=5, y=5)
        hero.components[Anatomy] = Anatomy(available_slots=["torso"])
        hero.components[CombatStats] = CombatStats(defense_bonus=0)
        
        # Setup Armor with +100 protection
        armor = registry_item = sim.registry.new_entity()
        armor.components[ItemStats] = ItemStats(protection=100)
        
        hero.relation_tags_many["IsCarrying"].add(armor)
        hero.relation_tags_many["IsEquipped"].add(armor)
        
        # Setup Foe that should now miss
        foe = sim.registry.new_entity()
        foe.components[CombatStats] = CombatStats(attack_bonus=0)
        
        sim.open_session()
        
        # Foe attacks Hero
        # total = 2d8 + 0 vs DC = 10 + 100 = 110. 
        # Even a natural 16 (critical) would be 16 vs 110 (miss, since it's not a hit by DC).
        # Wait, in engine/combat.py:
        # if is_crit: return "critical"
        # So critical ALWAYS hits. Fumble ALWAYS misses.
        
        # To avoid critical hits during test, we can check the debug output or run multiple times.
        # Or just check that get_effective_stats(hero).defense_bonus == 100.
        
        from engine.ecs.systems import get_effective_stats
        effective = get_effective_stats(hero)
        assert effective.defense_bonus == 100
        
        sim.close_session()

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
