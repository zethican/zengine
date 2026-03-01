import pytest
import tcod.ecs
from engine.spawner import spawn_npc, spawn_item, spawn_container, evaluate_condition, spawn_from_definition
from engine.ecs.components import EntityIdentity, Position, Attributes, ItemIdentity, CombatVitals, Disposition

def test_evaluate_condition_reputation():
    registry = tcod.ecs.Registry()
    player = registry.new_entity()
    player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
    player.components[Disposition] = Disposition(reputation=-0.5)
    
    assert evaluate_condition(registry, "reputation < 0") is True
    assert evaluate_condition(registry, "reputation > 0") is False
    assert evaluate_condition(registry, "reputation < -0.3") is True

def test_spawn_from_definition_chance():
    registry = tcod.ecs.Registry()
    # Chance 0 should never spawn
    spawn_def = {"type": "item", "id": "weapons/iron_sword", "chance": 0.0}
    result = spawn_from_definition(registry, spawn_def, 5, 5)
    assert result is None
    
    # Chance 1 should always spawn
    spawn_def = {"type": "item", "id": "weapons/iron_sword", "chance": 1.0}
    result = spawn_from_definition(registry, spawn_def, 5, 5)
    assert result is not None
    assert result.components[Position].x == 5

def test_spawn_npc_attributes():
    registry = tcod.ecs.Registry()
    npc = spawn_npc(registry, "foe_skirmisher", 10, 10)
    
    assert npc.components[EntityIdentity].name == "Skirmisher"
    assert npc.components[Position].x == 10
    assert npc.components[Position].y == 10
    assert npc.components[Attributes].scores["finesse"] == 14
    assert npc.components[CombatVitals].hp == 15

def test_spawn_item_position():
    registry = tcod.ecs.Registry()
    item = spawn_item(registry, "weapons/iron_sword", 5, 5)
    
    assert item.components[ItemIdentity].entity_id == "iron_sword"
    assert item.components[Position].x == 5
    assert item.components[Position].y == 5

def test_spawn_container_loot():
    registry = tcod.ecs.Registry()
    container = spawn_container(registry, "Loot Crate", 2, 2, ["weapons/iron_sword", "consumables/healing_potion"])
    
    assert container.components[Position].x == 2
    
    carried = list(container.relation_tags_many["IsCarrying"])
    assert len(carried) == 2
    
    names = [c.components[ItemIdentity].name for c in carried]
    assert any("Iron Sword" in name for name in names)
    assert any("Healing Potion" in name for name in names)
