import pytest
import tcod.ecs
from engine.ecs.components import Attributes, CombatStats
from engine.ecs.systems import get_effective_stats, get_attr_mod

def test_get_attr_mod():
    registry = tcod.ecs.Registry()
    ent = registry.new_entity()
    ent.components[Attributes] = Attributes(scores={"might": 14, "finesse": 8})
    
    # (14 - 10) // 2 = 2
    assert get_attr_mod(ent, "might") == 2
    # (8 - 10) // 2 = -1
    assert get_attr_mod(ent, "finesse") == -1
    # Missing attribute defaults to 10 -> (10 - 10) // 2 = 0
    assert get_attr_mod(ent, "resolve") == 0

def test_get_effective_stats_includes_attributes():
    registry = tcod.ecs.Registry()
    ent = registry.new_entity()
    ent.components[Attributes] = Attributes(scores={"might": 14, "finesse": 12})
    ent.components[CombatStats] = CombatStats(attack_bonus=1, damage_bonus=5)
    
    # Base: Atk=1, Dmg=5
    # Mods: Might 14 -> +2 Dmg, Finesse 12 -> +1 Atk, +1 Dfn
    # Total: Atk=2, Dmg=7, Dfn=1
    
    eff = get_effective_stats(ent)
    assert eff.attack_bonus == 2
    assert eff.damage_bonus == 7
    assert eff.defense_bonus == 1
