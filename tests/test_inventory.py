# tests/test_inventory.py
import tcod.ecs
import pytest
from engine.item_factory import create_item
from engine.ecs.components import ItemIdentity

def test_create_item_entity():
    registry = tcod.ecs.Registry()
    item_entity = create_item(registry, "weapons/iron_sword")
    
    assert ItemIdentity in item_entity.components
    assert item_entity.components[ItemIdentity].name == "Iron Sword"
    assert item_entity.components[ItemIdentity].entity_id == "iron_sword"

def test_pickup_item_removes_position():
    from engine.ecs.systems import pickup_item_system
    from engine.ecs.components import Position
    
    registry = tcod.ecs.Registry()
    actor = registry.new_entity()
    actor.components[Position] = Position(1, 1)
    
    item = registry.new_entity()
    item.components[Position] = Position(1, 1)
    
    success = pickup_item_system(actor, item)
    
    assert success is True
    assert Position not in item.components
    assert item in actor.relation_tags_many["IsCarrying"]

def test_drop_item_adds_position():
    from engine.ecs.systems import pickup_item_system, drop_item_system
    from engine.ecs.components import Position
    
    registry = tcod.ecs.Registry()
    actor = registry.new_entity()
    actor.components[Position] = Position(2, 2)
    
    item = registry.new_entity()
    item.components[Position] = Position(2, 2)
    
    pickup_item_system(actor, item)
    success = drop_item_system(actor, item)
    
    assert success is True
    assert item not in actor.relation_tags_many["IsCarrying"]
    assert Position in item.components
    assert item.components[Position].x == 2
    assert item.components[Position].y == 2

def test_equip_item_checks_anatomy():
    from engine.ecs.systems import pickup_item_system, equip_item_system
    from engine.ecs.components import Position, Anatomy, Equippable
    
    registry = tcod.ecs.Registry()
    actor = registry.new_entity()
    actor.components[Position] = Position(0, 0)
    actor.components[Anatomy] = Anatomy(available_slots=["hand"])
    
    # Create two swords
    sword1 = registry.new_entity()
    sword1.components[Position] = Position(0, 0)
    sword1.components[Equippable] = Equippable(slot_type="hand")
    
    sword2 = registry.new_entity()
    sword2.components[Position] = Position(0, 0)
    sword2.components[Equippable] = Equippable(slot_type="hand")
    
    # Pickup both
    pickup_item_system(actor, sword1)
    pickup_item_system(actor, sword2)
    
    # Equip first - should succeed
    assert equip_item_system(actor, sword1) is True
    assert sword1 in actor.relation_tags_many["IsEquipped"]
    
    # Equip second - should fail (only one hand slot)
    assert equip_item_system(actor, sword2) is False
    assert sword2 not in actor.relation_tags_many["IsEquipped"]
