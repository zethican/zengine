import pytest
import tcod.ecs
from engine.ecs.components import EntityIdentity, CombatStats, ActiveModifiers, Modifier, ItemStats
from engine.ecs.systems import get_effective_stats, modifier_tick_system

def test_effective_stats_with_modifiers():
    registry = tcod.ecs.Registry()
    ent = registry.new_entity()
    ent.components[CombatStats] = CombatStats(attack_bonus=10)
    
    # Add a +5 attack modifier
    ent.components[ActiveModifiers] = ActiveModifiers(effects=[
        Modifier(id="blessing", name="Blessing", stat_field="attack_bonus", magnitude=5, duration=10)
    ])
    
    eff = get_effective_stats(ent)
    # 10 (base) + 5 (mod) = 15
    # (Note: Attributes might add more if we had them, but here we don't)
    assert eff.attack_bonus == 15

def test_modifier_lifecycle_decay():
    registry = tcod.ecs.Registry()
    ent = registry.new_entity()
    ent.components[ActiveModifiers] = ActiveModifiers(effects=[
        Modifier(id="temp", name="Temp", stat_field="speed", magnitude=2, duration=2)
    ])
    
    # Tick 1
    modifier_tick_system(registry)
    assert len(ent.components[ActiveModifiers].effects) == 1
    assert ent.components[ActiveModifiers].effects[0].duration == 1
    
    # Tick 2
    modifier_tick_system(registry)
    assert len(ent.components[ActiveModifiers].effects) == 0

def test_on_hit_modifier_application():
    from engine.loop import SimulationLoop
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        
        attacker = sim.registry.new_entity()
        attacker.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Attacker", archetype="Standard")
        attacker.components[CombatStats] = CombatStats(attack_bonus=100) # Guaranteed hit
        from engine.ecs.components import ActionEconomy
        attacker.components[ActionEconomy] = ActionEconomy(ap_pool=100)
        
        # Give attacker a "Sunder Sword"
        weapon = sim.registry.new_entity()
        weapon.components[ItemStats] = ItemStats(modifiers=[
            {"id": "sunder", "stat_field": "protection", "magnitude": -5, "duration": 3}
        ])
        attacker.relation_tags_many["IsEquipped"].add(weapon)
        
        target = sim.registry.new_entity()
        target.components[EntityIdentity] = EntityIdentity(entity_id=2, name="Target", archetype="NPC")
        target.components[CombatStats] = CombatStats(defense_bonus=0)
        from engine.ecs.components import CombatVitals
        target.components[CombatVitals] = CombatVitals(hp=100, max_hp=100)
        
        sim.open_session()
        
        # Mock ability for attack
        from engine.data_loader import AbilityDef, EffectDef
        mock_ability = AbilityDef(
            id="basic_attack",
            name="Strike",
            ap_cost=10,
            target_type="single",
            effects=[
                EffectDef(effect_type="damage", target_pattern="primary_target", magnitude="1")
            ]
        )

        from unittest.mock import patch
        with patch('engine.data_loader.get_ability_def', return_value=mock_ability):
            # Mock resolve_roll to always return a 'hit'
            with patch('engine.loop.resolve_roll', return_value={
                "total": 100, "is_crit": False, "is_fumble": False, "rolls": [10, 10]
            }):
                sim.invoke_ability_ecs(attacker, "basic_attack", target)
        # Verify target has the modifier
        assert ActiveModifiers in target.components
        effects = target.components[ActiveModifiers].effects
        assert len(effects) == 1
        assert effects[0].id == "sunder"
        assert effects[0].magnitude == -5
        
        sim.close_session()
