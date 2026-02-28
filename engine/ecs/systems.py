"""
ZEngine — engine/ecs/systems.py
ECS Systems: Pure functions for turn resolution, actions, and combat.
=====================================================================
Version:     0.2  (Phase 7 — inventory and crafting)
Stack:       Python 3.14.3 | python-tcod-ecs
Status:      Production-ready for Phase 7.

Architecture notes
------------------
- Systems are pure functions operating on a tcod.ecs.Registry.
- They communicate exclusively via EventBus.
- Dispatch order is authoritative (see SYSTEMS.md).
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional

import tcod.ecs
from engine.ecs.components import (
    ActionEconomy, 
    MovementStats, 
    CombatVitals, 
    CombatStats, 
    Position
)
from engine.combat import (
    EventBus, 
    CombatEvent, 
    EVT_TURN_STARTED, 
    EVT_ACTION_RESOLVED,
    ENERGY_THRESHOLD,
    AP_POOL_SIZE,
    AP_COST_PICKUP,
    AP_COST_DROP,
    AP_COST_EQUIP,
    AP_COST_CRAFT
)
from engine.item_factory import merge_items

# ============================================================
# TURN SYSTEMS
# ============================================================

def turn_resolution_system(registry: tcod.ecs.Registry) -> None:
    """
    Tick action_energy for all eligible actors.
    Query: all entities with [ActionEconomy, MovementStats]
    """
    for entity in registry.Q.all_of(components=[ActionEconomy, MovementStats]):
        economy = entity.components[ActionEconomy]
        stats = entity.components[MovementStats]
        economy.action_energy += stats.speed


def action_economy_reset_system(registry: tcod.ecs.Registry, bus: EventBus) -> None:
    """
    Reset AP pool and emit EVT_TURN_STARTED for eligible actors.
    Query: all entities with [ActionEconomy] where energy >= threshold
    """
    for entity in registry.Q.all_of(components=[ActionEconomy]):
        economy = entity.components[ActionEconomy]
        if economy.action_energy >= ENERGY_THRESHOLD:
            # Reset economy state
            economy.ap_pool = AP_POOL_SIZE
            economy.ap_spent_this_turn = 0
            
            # Emit turn start event
            source_name = str(entity)
            from engine.ecs.components import EntityIdentity
            if EntityIdentity in entity.components:
                source_name = entity.components[EntityIdentity].name
                
            bus.emit(CombatEvent(
                event_key=EVT_TURN_STARTED,
                source=source_name,
                data={"action_energy": economy.action_energy}
            ))


# ============================================================
# ACTION SYSTEMS
# ============================================================

def action_resolution_system(
    registry: tcod.ecs.Registry, 
    entity: tcod.ecs.Entity,
    action_type: str,
    action_payload: Dict[str, Any],
    bus: EventBus
) -> bool:
    """
    Execute a single action for a specific entity.
    Deducts AP and emits EVT_ACTION_RESOLVED.
    Returns True if the action was successfully paid for and validated, False otherwise.
    """
    if ActionEconomy not in entity.components:
        return False

    economy = entity.components[ActionEconomy]
    
    # 1. Handle Built-in Inventory Actions
    if action_type in ["pickup", "drop", "equip", "craft"]:
        ap_costs = {
            "pickup": AP_COST_PICKUP,
            "drop": AP_COST_DROP,
            "equip": AP_COST_EQUIP,
            "craft": AP_COST_CRAFT
        }
        ap_cost = ap_costs[action_type]
        
        if economy.ap_pool < ap_cost:
            return False
            
        success = False
        if action_type == "craft":
            part_a = action_payload.get("part_a")
            part_b = action_payload.get("part_b")
            if part_a and part_b:
                result = merge_items(registry, part_a, part_b)
                if result:
                    # Explicitly remove parents from the actor's inventory relation
                    if part_a in entity.relation_tags_many["IsCarrying"]:
                        entity.relation_tags_many["IsCarrying"].remove(part_a)
                    if part_b in entity.relation_tags_many["IsCarrying"]:
                        entity.relation_tags_many["IsCarrying"].remove(part_b)

                    entity.relation_tags_many["IsCarrying"].add(result)
                    success = True
        else:
            target_item = action_payload.get("target_entity")
            if not target_item:
                return False
                
            if action_type == "pickup":
                success = pickup_item_system(entity, target_item)
            elif action_type == "drop":
                success = drop_item_system(entity, target_item)
            elif action_type == "equip":
                success = equip_item_system(entity, target_item)
            
        if success:
            economy.ap_pool -= ap_cost
            economy.ap_spent_this_turn += ap_cost
            
            source_name = str(entity)
            from engine.ecs.components import EntityIdentity
            if EntityIdentity in entity.components:
                source_name = entity.components[EntityIdentity].name
            
            bus.emit(CombatEvent(
                event_key=EVT_ACTION_RESOLVED,
                source=source_name,
                target=action_payload.get("target"),
                data={"action_type": action_type, "ap_spent": ap_cost}
            ))
            return True
        return False

    # 2. Handle Ability-based Actions
    from engine.data_loader import get_ability_def
    try:
        ability = get_ability_def(action_type)
        ap_cost = ability.ap_cost
    except FileNotFoundError:
        # Fallback or invalid ability
        return False
        
    if economy.ap_pool < ap_cost:
        return False # Insufficient AP
        
    economy.ap_pool -= ap_cost
    economy.ap_spent_this_turn += ap_cost
    
    source_name = str(entity)
    from engine.ecs.components import EntityIdentity
    if EntityIdentity in entity.components:
        source_name = entity.components[EntityIdentity].name
        
    # Emit resolve event
    bus.emit(CombatEvent(
        event_key=EVT_ACTION_RESOLVED,
        source=source_name,
        target=action_payload.get("target"),
        data={"action_type": action_type, "ap_spent": ap_cost}
    ))
    return True


# ============================================================
# INVENTORY SYSTEMS
# ============================================================

def pickup_item_system(actor: tcod.ecs.Entity, item: tcod.ecs.Entity) -> bool:
    """Moves item from Floor (Position) to Inventory (IsCarrying relation)."""
    if Position not in actor.components or Position not in item.components:
        return False
        
    actor_pos = actor.components[Position]
    item_pos = item.components[Position]
    
    if (actor_pos.x, actor_pos.y) != (item_pos.x, item_pos.y):
        return False # Too far away
        
    # Atomic transaction
    del item.components[Position]
    actor.relation_tags_many["IsCarrying"].add(item)
    return True

def drop_item_system(actor: tcod.ecs.Entity, item: tcod.ecs.Entity) -> bool:
    """Moves item from Inventory (IsCarrying) to Floor (Position)."""
    if item not in actor.relation_tags_many["IsCarrying"]:
        return False
        
    if Position not in actor.components:
        return False
        
    actor_pos = actor.components[Position]
    
    # Atomic transaction
    actor.relation_tags_many["IsCarrying"].remove(item)
    if item in actor.relation_tags_many["IsEquipped"]:
        actor.relation_tags_many["IsEquipped"].remove(item)
        
    item.components[Position] = Position(x=actor_pos.x, y=actor_pos.y)
    return True

def equip_item_system(actor: tcod.ecs.Entity, item: tcod.ecs.Entity) -> bool:
    """Equips an item if it's carried and a slot is available in Anatomy."""
    from engine.ecs.components import Anatomy, Equippable
    if item not in actor.relation_tags_many["IsCarrying"]:
        return False
    if Anatomy not in actor.components or Equippable not in item.components:
        return False
        
    anatomy = actor.components[Anatomy]
    item_equip = item.components[Equippable]
    
    # Count currently equipped items in this slot type
    equipped_in_slot = 0
    for e_item in actor.relation_tags_many["IsEquipped"]:
        if Equippable in e_item.components and e_item.components[Equippable].slot_type == item_equip.slot_type:
            equipped_in_slot += 1
            
    # Check anatomy limit
    max_slots = anatomy.available_slots.count(item_equip.slot_type)
    if equipped_in_slot >= max_slots:
        return False # Slot occupied
        
    actor.relation_tags_many["IsEquipped"].add(item)
    return True
