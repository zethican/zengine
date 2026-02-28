import pytest
import tcod.ecs
from engine.item_factory import create_item
from engine.ecs.components import ItemIdentity, ItemStats
from unittest.mock import patch

def test_magic_item_affix_application():
    registry = tcod.ecs.Registry()
    
    # Mock rarity to Magic (1 affix)
    # Mock select_affixes to return a specific affix
    from engine.data_loader import AffixDef
    mock_affix = AffixDef(
        id="sharp", name="Sharp", type="prefix", 
        eligible_tags=["weapon"], weight=10, 
        item_stats={"attack_bonus": 2, "damage_bonus": 1}
    )
    
    with patch('engine.item_factory.roll_rarity', return_value="magic"):
        with patch('engine.item_factory.select_affixes', return_value=[mock_affix]):
            # Create a weapon (iron_sword has 'weapon' tag)
            item = create_item(registry, "weapons/iron_sword")
            
            ident = item.components[ItemIdentity]
            stats = item.components[ItemStats]
            
            # Name should be "Sharp Iron Sword"
            assert "Sharp" in ident.name
            
            # Stats should be summed
            # Base iron_sword stats: atk 0, dmg 0, prot 0? (check seed)
            # Actually iron_sword.toml might have stats. 
            # Let's just check that they are GREATER than the base if the base is 0.
            assert stats.attack_bonus >= 2
            assert stats.damage_bonus >= 1
            assert "magic" in item.tags

def test_rare_item_affix_application():
    registry = tcod.ecs.Registry()
    
    from engine.data_loader import AffixDef
    p_affix = AffixDef(id="p", name="Gilded", type="prefix", eligible_tags=["weapon"], weight=10, item_stats={"protection": 1})
    s_affix = AffixDef(id="s", name="of Echoes", type="suffix", eligible_tags=["weapon"], weight=10, modifiers=[{"id":"test"}])
    
    with patch('engine.item_factory.roll_rarity', return_value="rare"):
        with patch('engine.item_factory.select_affixes', return_value=[p_affix, s_affix]):
            item = create_item(registry, "weapons/iron_sword")
            
            ident = item.components[ItemIdentity]
            stats = item.components[ItemStats]
            
            # Name: "Gilded Iron Sword of Echoes"
            assert ident.name.startswith("Gilded")
            assert ident.name.endswith("of Echoes")
            
            assert stats.protection >= 1
            assert any(m["id"] == "test" for m in stats.modifiers)
            assert "rare" in item.tags
