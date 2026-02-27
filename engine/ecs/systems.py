"""
ZEngine — engine/ecs/systems.py
ECS Systems: Pure functions for turn resolution, actions, and combat.
=====================================================================
Version:     0.1  (Phase 2 — canonical implementation)
Stack:       Python 3.14.3 | python-tcod-ecs
Status:      Production-ready for Phase 2.

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
    AP_POOL_SIZE
)

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
) -> None:
    """
    Execute a single action for a specific entity.
    Deducts AP and emits EVT_ACTION_RESOLVED.
    """
    if ActionEconomy not in entity.components:
        return

    economy = entity.components[ActionEconomy]
    
    if action_type == "attack":
        # AP cost logic (TODO: load from TOML; MVP: 50 AP)
        ap_cost = 50
        if economy.ap_pool < ap_cost:
            return # Insufficient AP
            
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
            data={"action_type": "attack", "ap_spent": ap_cost}
        ))
