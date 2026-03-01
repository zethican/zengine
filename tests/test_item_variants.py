"""
Tests for generated item variants using TOML blueprints and the entity schema.
Covers: new weapon/armor blueprints, affix tag matching, EntityDef.tags, and
        the select_affixes variable-name fix.
"""
import pytest
import tcod.ecs
from unittest.mock import patch

from engine.data_loader import get_item_def, get_entity_def, get_affixes, AffixDef
from engine.item_factory import create_item, select_affixes
from engine.ecs.components import ItemIdentity, ItemStats, Equippable


# ---------------------------------------------------------------------------
# Blueprint loading
# ---------------------------------------------------------------------------

class TestNewWeaponBlueprints:
    def test_iron_dagger_loads(self):
        item = get_item_def("weapons/iron_dagger")
        assert item.id == "iron_dagger"
        assert item.equippable["slot"] == "hand"
        assert item.item_stats["attack_bonus"] == 3
        assert item.item_stats["damage_bonus"] == 1

    def test_war_axe_loads(self):
        item = get_item_def("weapons/war_axe")
        assert item.id == "war_axe"
        assert item.item_stats["damage_bonus"] == 6

    def test_wooden_club_loads(self):
        item = get_item_def("weapons/wooden_club")
        assert item.id == "wooden_club"
        assert item.tags.get("is_blunt") is True

    def test_all_weapons_have_weapon_tag(self):
        for path in ["weapons/iron_sword", "weapons/iron_dagger", "weapons/war_axe", "weapons/wooden_club"]:
            item = get_item_def(path)
            assert item.tags.get("weapon") is True, f"{path} missing 'weapon' tag"


class TestNewArmorBlueprints:
    def test_leather_vest_loads(self):
        item = get_item_def("armor/leather_vest")
        assert item.id == "leather_vest"
        assert item.equippable["slot"] == "torso"
        assert item.item_stats["protection"] == 2

    def test_iron_shield_loads(self):
        item = get_item_def("armor/iron_shield")
        assert item.id == "iron_shield"
        assert item.equippable["slot"] == "hand"
        assert item.item_stats["protection"] == 4

    def test_all_armor_have_armor_tag(self):
        for path in ["armor/leather_vest", "armor/iron_shield"]:
            item = get_item_def(path)
            assert item.tags.get("armor") is True, f"{path} missing 'armor' tag"


# ---------------------------------------------------------------------------
# Affix loading and tag matching
# ---------------------------------------------------------------------------

class TestNewAffixes:
    def test_all_new_affixes_load(self):
        ids = {a.id for a in get_affixes()}
        for expected in ("vicious", "swift", "of_warding", "of_fortitude", "runed", "of_flames"):
            assert expected in ids, f"Affix '{expected}' not found"

    def test_vicious_is_prefix_for_weapons(self):
        affixes = {a.id: a for a in get_affixes()}
        a = affixes["vicious"]
        assert a.type == "prefix"
        assert "weapon" in a.eligible_tags
        assert a.item_stats["damage_bonus"] == 3

    def test_swift_has_speed_modifier(self):
        affixes = {a.id: a for a in get_affixes()}
        a = affixes["swift"]
        assert any(m["stat_field"] == "speed" for m in a.modifiers)

    def test_of_warding_is_suffix_for_armor(self):
        affixes = {a.id: a for a in get_affixes()}
        a = affixes["of_warding"]
        assert a.type == "suffix"
        assert "armor" in a.eligible_tags

    def test_runed_eligible_for_weapon_and_armor(self):
        affixes = {a.id: a for a in get_affixes()}
        a = affixes["runed"]
        assert "weapon" in a.eligible_tags
        assert "armor" in a.eligible_tags

    def test_of_flames_has_both_stats_and_modifier(self):
        affixes = {a.id: a for a in get_affixes()}
        a = affixes["of_flames"]
        assert a.item_stats["damage_bonus"] == 2
        assert len(a.modifiers) == 1
        assert a.modifiers[0]["id"] == "burning"


# ---------------------------------------------------------------------------
# select_affixes correctness (the e→a bug fix)
# ---------------------------------------------------------------------------

class TestSelectAffixes:
    def test_weapon_tags_match_weapon_affixes(self):
        """Weapons with the 'weapon' tag should receive weapon-eligible affixes."""
        results = select_affixes({"weapon", "is_sword"}, count=1)
        # At least one affix must be returned (sharp, vicious, swift, runed, of_flames, etc.)
        assert len(results) == 1
        assert all("weapon" in a.eligible_tags for a in results)

    def test_armor_tags_match_armor_affixes(self):
        results = select_affixes({"armor", "is_leather"}, count=1)
        assert len(results) == 1
        assert all("armor" in a.eligible_tags for a in results)

    def test_no_match_returns_empty(self):
        results = select_affixes({"is_part", "is_blade"}, count=1)
        assert results == []

    def test_rare_tier_returns_up_to_two(self):
        results = select_affixes({"weapon"}, count=2)
        assert len(results) <= 2
        # Each must be eligible for weapons
        for a in results:
            assert "weapon" in a.eligible_tags


# ---------------------------------------------------------------------------
# create_item with new blueprints
# ---------------------------------------------------------------------------

class TestCreateItemVariants:
    def setup_method(self):
        self.registry = tcod.ecs.Registry()

    def test_iron_dagger_entity_created(self):
        entity = create_item(self.registry, "weapons/iron_dagger")
        ident = entity.components[ItemIdentity]
        assert "Dagger" in ident.name or "iron_dagger" in ident.entity_id

    def test_war_axe_entity_has_stats(self):
        with patch("engine.item_factory.roll_rarity", return_value="common"):
            entity = create_item(self.registry, "weapons/war_axe")
        stats = entity.components[ItemStats]
        assert stats.damage_bonus == 6

    def test_leather_vest_entity_equippable(self):
        with patch("engine.item_factory.roll_rarity", return_value="common"):
            entity = create_item(self.registry, "armor/leather_vest")
        eq = entity.components[Equippable]
        assert eq.slot_type == "torso"

    def test_iron_shield_protection(self):
        with patch("engine.item_factory.roll_rarity", return_value="common"):
            entity = create_item(self.registry, "armor/iron_shield")
        stats = entity.components[ItemStats]
        assert stats.protection == 4

    def test_magic_weapon_gets_affix_applied(self):
        mock_affix = AffixDef(
            id="vicious", name="Vicious", type="prefix",
            eligible_tags=["weapon"], weight=8,
            item_stats={"damage_bonus": 3, "attack_bonus": 1}
        )
        with patch("engine.item_factory.roll_rarity", return_value="magic"):
            with patch("engine.item_factory.select_affixes", return_value=[mock_affix]):
                entity = create_item(self.registry, "weapons/war_axe")
        ident = entity.components[ItemIdentity]
        assert ident.name.startswith("Vicious")
        stats = entity.components[ItemStats]
        # Base: dmg 6, atk 1 + affix: dmg 3, atk 1
        assert stats.damage_bonus == 9
        assert stats.attack_bonus == 2

    def test_magic_armor_gets_warding_affix(self):
        mock_affix = AffixDef(
            id="of_warding", name="of Warding", type="suffix",
            eligible_tags=["armor"], weight=9,
            item_stats={"protection": 3}
        )
        with patch("engine.item_factory.roll_rarity", return_value="magic"):
            with patch("engine.item_factory.select_affixes", return_value=[mock_affix]):
                entity = create_item(self.registry, "armor/leather_vest")
        ident = entity.components[ItemIdentity]
        assert ident.name.endswith("of Warding")
        stats = entity.components[ItemStats]
        assert stats.protection == 5  # base 2 + affix 3


# ---------------------------------------------------------------------------
# EntityDef tags field
# ---------------------------------------------------------------------------

class TestEntityDefTags:
    def test_borzai_tags_are_loaded(self):
        entity = get_entity_def("borzai")
        assert entity.tags.get("is_humanoid") is True
        assert entity.tags.get("is_scavenger") is True

    def test_shimmer_cat_tags_are_loaded(self):
        entity = get_entity_def("shimmer_cat")
        assert entity.tags.get("is_beast") is True
        assert entity.tags.get("is_predator") is True

    def test_foe_skirmisher_tags_are_loaded(self):
        entity = get_entity_def("foe_skirmisher")
        assert entity.tags.get("is_humanoid") is True

    def test_entity_without_tags_section_gets_empty_dict(self):
        # hero_standard has no [tags] section
        entity = get_entity_def("hero_standard")
        # Should be an empty dict, not an error
        assert isinstance(entity.tags, dict)


# ---------------------------------------------------------------------------
# Entity inventory references
# ---------------------------------------------------------------------------

class TestEntityInventory:
    def test_foe_skirmisher_carries_dagger(self):
        entity = get_entity_def("foe_skirmisher")
        assert "weapons/iron_dagger" in entity.inventory

    def test_borzai_carries_club_and_vest(self):
        entity = get_entity_def("borzai")
        assert "weapons/wooden_club" in entity.inventory
        assert "armor/leather_vest" in entity.inventory

    def test_hero_starting_inventory(self):
        entity = get_entity_def("hero_standard")
        assert "weapons/iron_sword" in entity.inventory
        assert "armor/iron_shield" in entity.inventory
        assert "consumables/healing_potion" in entity.inventory
