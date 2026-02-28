import pytest
import tcod.ecs
import tempfile
from pathlib import Path
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Attributes, CombatStats, Position, CombatVitals, ActionEconomy, ActiveModifiers

def test_complex_ability_functional_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        
        # 1. Setup Attacker
        attacker = sim.registry.new_entity()
        attacker.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Hero", archetype="Standard", is_player=True)
        attacker.components[Attributes] = Attributes(scores={"might": 14, "resolve": 14}) # Mod +2
        attacker.components[CombatStats] = CombatStats(attack_bonus=100) # Guaranteed hit
        attacker.components[ActionEconomy] = ActionEconomy(ap_pool=100)
        attacker.components[CombatVitals] = CombatVitals(hp=5, max_hp=20) # Wounded
        attacker.components[Position] = Position(x=5, y=5)
        
        # 2. Setup Target
        target = sim.registry.new_entity()
        target.components[EntityIdentity] = EntityIdentity(entity_id=2, name="Foe", archetype="Skirmisher")
        target.components[CombatVitals] = CombatVitals(hp=20, max_hp=20)
        target.components[CombatStats] = CombatStats(defense_bonus=0)
        target.components[Position] = Position(x=6, y=5)
        
        sim.open_session()
        
        # 3. Create a Custom Ability with multiple effects:
        # Effect A: Damage to target (magnitude 10)
        # Effect B: Heal self (magnitude 5)
        from engine.data_loader import AbilityDef, EffectDef
        custom_ability = AbilityDef(
            id="vampiric_strike",
            name="Vampiric Strike",
            ap_cost=10,
            target_type="single",
            effects=[
                EffectDef(effect_type="damage", target_pattern="primary_target", magnitude="10"),
                EffectDef(effect_type="heal", target_pattern="self", magnitude="5")
            ]
        )
        
        # Mock get_ability_def to return our custom ability
        from unittest.mock import patch
        with patch('engine.data_loader.get_ability_def', return_value=custom_ability):
            
            # Also mock resolve_roll to avoid fumbles
            with patch('engine.loop.resolve_roll', return_value={"total": 100, "is_crit": False, "is_fumble": False, "rolls": [10, 10]}):
                sim.invoke_ability_ecs(attacker, "vampiric_strike", target)
            
        # 4. Verify Results
        # Target should be damaged: 20 - (10 + attacker.dmg_bonus)
        # attacker.dmg_bonus comes from might mod (+2)
        assert target.components[CombatVitals].hp <= 8
        
        # Attacker should be healed: 5 + 5 = 10
        assert attacker.components[CombatVitals].hp == 10
        
        sim.close_session()

def test_tag_loading_integrity():
    from engine.data_loader import get_ability_def
    ability = get_ability_def("heavy_blow")
    
    assert "melee" in ability.tags
    assert len(ability.effects) == 2
    assert ability.effects[0].effect_type == "damage"
    assert "crushing" in ability.effects[0].tags
    assert ability.effects[1].effect_type == "apply_modifier"
    assert ability.effects[1].modifier_id == "sunder"
