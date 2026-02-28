"""
ZEngine — engine/item_factory.py
ECS Entity Factory for Items and Crafting.
==============================================
Version:     0.2 (Phase 8)
Stack:       Python 3.14.3 | python-tcod-ecs
Status:      Transactional item instantiation and merging.
"""

from typing import Optional, List
import tcod.ecs
from engine.data_loader import get_item_def, get_recipes
from engine.ecs.components import ItemIdentity, Equippable, ItemStats, Quantity, Lineage

def create_item(registry: tcod.ecs.Registry, item_path: str) -> tcod.ecs.Entity:
    """Instantiates an item entity from a TOML blueprint."""
    item_def = get_item_def(item_path)
    entity = registry.new_entity()
    
    # 1. Identity
    entity.components[ItemIdentity] = ItemIdentity(
        entity_id=item_def.id,
        name=item_def.name,
        description=item_def.description,
        template_origin=item_path
    )
    
    # 2. Equippable
    if item_def.equippable:
        entity.components[Equippable] = Equippable(slot_type=item_def.equippable["slot"])
        
    # 3. Stats
    if item_def.item_stats:
        entity.components[ItemStats] = ItemStats(**item_def.item_stats)
        
    # 4. Quantity (if stackable)
    if item_def.stackable:
        entity.components[Quantity] = Quantity(
            amount=1, 
            max_stack=item_def.stackable.get("max", 1)
        )
        
    # 5. Tags
    for tag, value in item_def.tags.items():
        if value:
            entity.tags.add(tag)
            
    return entity

def merge_items(registry: tcod.ecs.Registry, part_a: tcod.ecs.Entity, part_b: tcod.ecs.Entity) -> Optional[tcod.ecs.Entity]:
    """
    Attempts to combine two item entities based on available recipes.
    Returns the new entity on success, or None on failure.
    """
    recipes = get_recipes()
    matching_recipe = None
    
    # Check both orientations
    for r in recipes:
        if (r.part_a_tag in part_a.tags and r.part_b_tag in part_b.tags) or \
           (r.part_a_tag in part_b.tags and r.part_b_tag in part_a.tags):
            matching_recipe = r
            break
            
    if not matching_recipe:
        return None
        
    # Instantiate the result from template
    result_entity = create_item(registry, matching_recipe.result_template)
    
    # 1. Inherit Stats (Add bonuses from both parts to the base template stats)
    if ItemStats in result_entity.components:
        stats = result_entity.components[ItemStats]
        
        for part in [part_a, part_b]:
            if ItemStats in part.components:
                p_stats = part.components[ItemStats]
                stats.attack_bonus += p_stats.attack_bonus
                stats.damage_bonus += p_stats.damage_bonus
                stats.protection += p_stats.protection
                
    # 2. Inherit Lineage
    parent_ids = []
    for part in [part_a, part_b]:
        if ItemIdentity in part.components:
            parent_ids.append(part.components[ItemIdentity].entity_id)
            
    result_entity.components[Lineage] = Lineage(parent_ids=parent_ids)
    
    # 3. Clean up parents
    part_a.clear()
    part_b.clear()
    
    return result_entity
