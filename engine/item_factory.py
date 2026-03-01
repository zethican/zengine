"""
ZEngine — engine/item_factory.py
ECS Entity Factory for Items and Crafting.
==============================================
Version:     0.3 (Phase 18 — Procedural Affixes)
Stack:       Python 3.14.3 | python-tcod-ecs
Status:      Transactional item instantiation, merging, and procedural augmentation.
"""

import random
from typing import Optional, List, Dict, Any
import tcod.ecs
from engine.data_loader import get_item_def, get_recipes, get_affixes, AffixDef
from engine.ecs.components import ItemIdentity, Equippable, ItemStats, Quantity, Lineage, Usable

def roll_rarity() -> str:
    """Determines item rarity tier (Common, Magic, Rare)."""
    roll = random.random()
    if roll < 0.05: return "rare"
    if roll < 0.30: return "magic"
    return "common"

def select_affixes(item_tags: set[str], count: int) -> List[AffixDef]:
    """Selects valid affixes based on item tags and weights."""
    all_affixes = get_affixes()
    
    # Filter by tags
    valid = [a for a in all_affixes if any(t in item_tags for t in a.eligible_tags)]
    if not valid: return []
    
    # Selection
    prefixes = [a for a in valid if a.type == "prefix"]
    suffixes = [a for a in valid if a.type == "suffix"]
    
    selected = []
    if count == 1:
        # Magic: 50% prefix, 50% suffix
        pool = prefixes if random.random() < 0.5 else suffixes
        if not pool: pool = prefixes or suffixes # fallback
        if pool:
            selected.append(random.choices(pool, weights=[a.weight for a in pool], k=1)[0])
    elif count == 2:
        # Rare: 1 prefix + 1 suffix
        if prefixes:
            selected.append(random.choices(prefixes, weights=[a.weight for a in prefixes], k=1)[0])
        if suffixes:
            selected.append(random.choices(suffixes, weights=[a.weight for a in suffixes], k=1)[0])
            
    return selected

def create_item(registry: tcod.ecs.Registry, item_path: str) -> tcod.ecs.Entity:
    """Instantiates an item entity from a TOML blueprint with procedural affixes."""
    item_def = get_item_def(item_path)
    entity = registry.new_entity()
    
    # 1. Base Tags
    for tag, value in item_def.tags.items():
        if value:
            entity.tags.add(tag)
            
    # 2. Rarity & Affixes
    rarity = roll_rarity()
    affixes = []
    if rarity == "magic":
        affixes = select_affixes(entity.tags, 1)
    elif rarity == "rare":
        affixes = select_affixes(entity.tags, 2)
        
    # 3. Identity (Procedural Name)
    prefix_str = ""
    suffix_str = ""
    for a in affixes:
        if a.type == "prefix": prefix_str = f"{a.name} "
        else: suffix_str = f" {a.name}"
        
    final_name = f"{prefix_str}{item_def.name}{suffix_str}"
    
    entity.components[ItemIdentity] = ItemIdentity(
        entity_id=item_def.id,
        name=final_name,
        description=item_def.description,
        template_origin=item_path,
        value=item_def.value
    )

    # 4. Equippable
    if item_def.equippable:
        entity.components[Equippable] = Equippable(slot_type=item_def.equippable["slot"])
        
    # 5. Stats & Modifiers (Summed)
    total_stats = item_def.item_stats.copy() if item_def.item_stats else {}
    total_modifiers = item_def.modifiers.copy()
    
    for a in affixes:
        # Sum Stats
        if a.item_stats:
            for k, val in a.item_stats.items():
                total_stats[k] = total_stats.get(k, 0) + val
        # Merge Modifiers
        total_modifiers.extend(a.modifiers)
        
    if total_stats or total_modifiers:
        entity.components[ItemStats] = ItemStats(
            attack_bonus=total_stats.get("attack_bonus", 0),
            damage_bonus=total_stats.get("damage_bonus", 0),
            protection=total_stats.get("protection", 0),
            modifiers=total_modifiers
        )
        
    # 6. Quantity (if stackable)
    if item_def.stackable:
        entity.components[Quantity] = Quantity(
            amount=1, 
            max_stack=item_def.stackable.get("max", 1)
        )
        
    # 7. Usable
    if item_def.usable:
        entity.components[Usable] = Usable(**item_def.usable)

    # Apply rarity tag for visual/logic
    entity.tags.add(rarity)
            
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
