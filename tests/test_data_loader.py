import pytest
from engine.data_loader import get_ability_def, get_entity_def, get_starting_rumors

def test_load_basic_attack():
    ability = get_ability_def("basic_attack")
    assert ability.id == "basic_attack"
    assert ability.damage_die == 6
    assert ability.ap_cost == 50

def test_load_entity_hero():
    hero = get_entity_def("hero_standard")
    assert hero.id == "hero_standard"
    assert hero.hp == 30
    assert "basic_attack" in hero.abilities

def test_load_entity_foe():
    foe = get_entity_def("foe_skirmisher")
    assert foe.id == "foe_skirmisher"
    assert foe.archetype == "Skirmisher"

def test_load_rumors():
    rumors = get_starting_rumors()
    assert len(rumors) >= 2
    assert rumors[0].pol_type == "dungeon"

def test_load_item_def():
    from engine.data_loader import get_item_def
    item = get_item_def("weapons/iron_sword")
    assert item.name == "Iron Sword"
    assert item.equippable["slot"] == "hand"
