"""
ZEngine — engine/ecs/systems.py
ECS Systems: Pure functions for turn resolution, actions, and combat.
=====================================================================
Version:     0.5  (Phase 13 Step 0 — Structural Entities)
Stack:       Python 3.14.3 | python-tcod-ecs
Status:      Production-ready.

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
    Position,
    ItemIdentity,
    ItemStats,
    BehaviorProfile,
    PendingAction,
    EntityIdentity,
    Attributes,
    Interactable,
    DoorState,
    BlocksMovement,
    SocialAwareness,
    ActiveModifiers,
    Modifier,
    PartyMember
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
    AP_COST_CRAFT,
    AP_COST_USE
)
from engine.item_factory import merge_items

# ============================================================
# INTERACTION SYSTEMS
# ============================================================

def toggle_door_system(door: tcod.ecs.Entity) -> bool:
    """Toggles a door's open/closed state."""
    if DoorState not in door.components:
        return False
        
    state = door.components[DoorState]
    if state.is_locked:
        return False
        
    state.is_open = not state.is_open
    
    if state.is_open:
        if BlocksMovement in door.components:
            del door.components[BlocksMovement]
    else:
        door.components[BlocksMovement] = BlocksMovement()
        
    return True

def interaction_system(registry: tcod.ecs.Registry, actor: tcod.ecs.Entity, x: int, y: int) -> Optional[Dict[str, Any]]:
    """
    Checks for interactable objects at (x, y).
    Returns a result dict if interaction occurs, else None.
    """
    # 1. Find entities at location
    targets = []
    for ent in registry.Q.all_of(components=[Position]):
        pos = ent.components[Position]
        if pos.x == x and pos.y == y:
            targets.append(ent)
            
    if not targets:
        return None
        
    # 2. Priority: Doors / Containers / Interactables
    for target in targets:
        if target == actor: continue
        
        # Door check
        if DoorState in target.components:
            return {
                "type": "door_interaction",
                "target": target,
                "verb": "close" if target.components[DoorState].is_open else "open"
            }
        
        # Container check (has items)
        if len(target.relation_tags_many["IsCarrying"]) > 0 or Interactable in target.components:
            verb = "interact"
            if Interactable in target.components:
                verb = target.components[Interactable].verb
            
            return {
                "type": "entity_interaction",
                "target": target,
                "verb": verb
            }
            
    return None

def recruit_npc_system(player: tcod.ecs.Entity, npc: tcod.ecs.Entity) -> bool:
    """Recruits an NPC into the player's party."""
    if EntityIdentity not in player.components or EntityIdentity not in npc.components:
        return False
        
    p_id = player.components[EntityIdentity].entity_id
    
    # Set PartyMember component
    npc.components[PartyMember] = PartyMember(leader_id=p_id)
    
    # Update Relation for easy querying
    npc.relation_tag["InPartyWith"] = player
    
    # Update AI Profile to be attracted to player
    if BehaviorProfile in npc.components:
        profile = npc.components[BehaviorProfile]
        profile.affinity_weight = 2.0 # Strong attraction
        profile.threat_weight = 0.0   # No fear of leader
        
    return True

def get_adjusted_value(item: tcod.ecs.Entity, standing: float, is_npc_item: bool) -> int:
    """Calculates item value adjusted by faction standing and buyer/seller role."""
    if ItemIdentity not in item.components:
        return 0
        
    base_val = item.components[ItemIdentity].value
    
    # Standing Brackets
    # Hostile: -1.0 to -0.3
    # Neutral: -0.3 to 0.4
    # Friendly: 0.4 to 1.0
    
    if standing < -0.3: # Hostile
        mult = 2.0 if is_npc_item else 0.5
    elif standing > 0.4: # Friendly
        mult = 0.8 if is_npc_item else 1.2
    else: # Neutral
        mult = 1.0
        
    return int(base_val * mult)

# ============================================================
# AI SYSTEMS
# ============================================================

def ai_decision_system(registry: tcod.ecs.Registry, ai_sys: "InfluenceMapSystem", px: int, py: int, current_tick: int = 0):
    """
    Selects best action for NPCs based on influence maps.
    Writes PendingAction component to chosen entities.
    """
    for entity in registry.Q.all_of(components=[ActionEconomy, BehaviorProfile, Position, EntityIdentity]):
        if entity.components[EntityIdentity].is_player:
            continue
            
        # 0. Social Awareness (Inject affinity if player is in range)
        if SocialAwareness in entity.components:
            soc = entity.components[SocialAwareness]
            pos = entity.components[Position]
            dist = max(abs(pos.x - px), abs(pos.y - py))
            
            # Check range and cooldown (2000 ticks)
            if dist <= soc.engagement_range and current_tick - soc.last_interaction_tick > 2000:
                # Force high affinity for player location
                ai_sys.add_affinity_seed(px, py, weight=10.0) # Very High pull
        
        # 0.5 Party Following (Phase 22)
        if PartyMember in entity.components:
            # Always attract to player if in party
            ai_sys.add_affinity_seed(px, py, weight=20.0) # Maximum pull
                
        # Update maps for THIS NPC (so it is not its own seed)
        ai_sys.update(registry, px, py, viewer=entity)
        
        economy = entity.components[ActionEconomy]
        if economy.ap_pool < 10: # Min cost for movement
            continue
            
        # Already has an action?
        if PendingAction in entity.components:
            continue
            
        profile = entity.components[BehaviorProfile]
        pos = entity.components[Position]
        
        # Get personal desire map
        desire_map = ai_sys.get_desire_map(profile)
        
        # 1. Evaluate Neighbors for Movement
        # Initialize with CURRENT tile value
        lx_curr, ly_curr = pos.x - ai_sys.off_x, pos.y - ai_sys.off_y
        if 0 <= lx_curr < ai_sys.width and 0 <= ly_curr < ai_sys.height:
            best_val = desire_map[ly_curr, lx_curr]
        else:
            best_val = -1000.0
            
        best_pos = (pos.x, pos.y)
        
        # Simple 1-tile lookahead
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = pos.x + dx, pos.y + dy
                lx, ly = nx - ai_sys.off_x, ny - ai_sys.off_y
                if 0 <= lx < ai_sys.width and 0 <= ly < ai_sys.height:
                    val = desire_map[ly, lx]
                    if val > best_val:
                        best_val = val
                        best_pos = (nx, ny)
        
        # 2. Queue Action
        success = False
        if best_pos != (pos.x, pos.y):
            dx, dy = best_pos[0] - pos.x, best_pos[1] - pos.y
            entity.components[PendingAction] = PendingAction(
                action_type="move",
                payload={"dx": dx, "dy": dy}
            )
            success = True
        else:
            # Maybe use item if health is low?
            if CombatVitals in entity.components:
                vitals = entity.components[CombatVitals]
                if vitals.hp / vitals.max_hp < 0.5:
                    # Look for potion in inventory
                    for item in entity.relation_tags_many["IsCarrying"]:
                        from engine.ecs.components import Usable
                        if Usable in item.components and item.components[Usable].ability_id == "heal":
                            entity.components[PendingAction] = PendingAction(
                                action_type="use",
                                target_entity=item
                            )
                            success = True
                            break
        
        if success:
            pass # We could deduct AP here if we wanted to block multiple AI systems, 
                 # but for now PendingAction resolution handles it.

# ============================================================
# STAT SYSTEMS
# ============================================================

def get_attr_mod(entity: tcod.ecs.Entity, attr_id: str) -> int:
    """Calculates attribute modifier using (score - 10) // 2."""
    if Attributes not in entity.components:
        return 0
    scores = entity.components[Attributes].scores
    val = scores.get(attr_id, 10) # default to 10
    
    # Add Active Modifiers to score
    if ActiveModifiers in entity.components:
        for mod in entity.components[ActiveModifiers].effects:
            if mod.stat_field == attr_id:
                val += int(mod.magnitude)
                
    return (val - 10) // 2

def get_effective_stats(entity: tcod.ecs.Entity) -> CombatStats:
    """
    Calculates total stats by summing base CombatStats, ItemStats, Attribute mods, and ActiveModifiers.
    Returns a new CombatStats object containing the aggregated values.
    """
    base = entity.components.get(CombatStats, CombatStats())
    
    # 1. Start with Base
    total_atk = base.attack_bonus
    total_dfn = base.defense_bonus
    total_dmg = base.damage_bonus
    
    # 2. Add Attribute Modifiers
    total_atk += get_attr_mod(entity, "finesse")
    total_dfn += get_attr_mod(entity, "finesse")
    total_dmg += get_attr_mod(entity, "might")
    
    # 3. Aggregate from equipped items
    from engine.ecs.components import ItemStats
    for item in entity.relation_tags_many["IsEquipped"]:
        if ItemStats in item.components:
            i_stats = item.components[ItemStats]
            total_atk += i_stats.attack_bonus
            total_dfn += i_stats.protection # Item protection maps to actor defense
            total_dmg += i_stats.damage_bonus
            
    # 4. Add Active Modifiers
    if ActiveModifiers in entity.components:
        for mod in entity.components[ActiveModifiers].effects:
            if mod.stat_field == "attack_bonus": total_atk += int(mod.magnitude)
            elif mod.stat_field == "defense_bonus" or mod.stat_field == "protection": total_dfn += int(mod.magnitude)
            elif mod.stat_field == "damage_bonus": total_dmg += int(mod.magnitude)
            
    return CombatStats(
        attack_bonus=total_atk,
        defense_bonus=total_dfn,
        damage_bonus=total_dmg
    )

# = ===========================================================
# MODIFIER SYSTEMS
# = ===========================================================

def modifier_tick_system(registry: tcod.ecs.Registry) -> None:
    """Decrements duration of all active modifiers and purges expired ones."""
    for entity in registry.Q.all_of(components=[ActiveModifiers]):
        active = entity.components[ActiveModifiers]
        # Iterate in reverse or filter to allow safe removal
        remaining = []
        for mod in active.effects:
            mod.duration -= 1
            if mod.duration > 0:
                remaining.append(mod)
        active.effects = remaining

def apply_modifier_blueprint(entity: tcod.ecs.Entity, m_blue: Dict[str, Any]):
    """Applies a modifier blueprint to an entity. Handles duration refreshing for duplicates."""
    if ActiveModifiers not in entity.components:
        entity.components[ActiveModifiers] = ActiveModifiers()
    
    active = entity.components[ActiveModifiers]
    
    # Option A: Refresh Duration if ID matches
    for existing in active.effects:
        if existing.id == m_blue["id"]:
            existing.duration = m_blue.get("duration", 100)
            return
            
    # Add new
    active.effects.append(Modifier(
        id=m_blue["id"],
        name=m_blue.get("name", m_blue["id"]),
        stat_field=m_blue["stat_field"],
        magnitude=m_blue["magnitude"],
        duration=m_blue.get("duration", 100)
    ))

def get_terrain_modifiers(terrain_type: str) -> List[Dict[str, Any]]:
    """Returns a list of modifier blueprints for a given terrain type."""
    registry = {
        "water": [{"id": "env_wet", "name": "Wet", "stat_field": "speed", "magnitude": -2.0, "duration": 1}],
        "grass": [], # Placeholder for future effects
        "mud": [{"id": "env_muddy", "name": "Muddy", "stat_field": "speed", "magnitude": -5.0, "duration": 10}]
    }
    return registry.get(terrain_type, [])

def environmental_modifier_system(registry: tcod.ecs.Registry, world_manager: "ChunkManager") -> None:
    """Applies modifiers based on current terrain and biome for all entities."""
    for entity in registry.Q.all_of(components=[Position, EntityIdentity]):
        pos = entity.components[Position]
        
        # 1. Terrain Modifiers
        t_mods = get_terrain_modifiers(pos.terrain_type)
        for m_blue in t_mods:
            apply_modifier_blueprint(entity, m_blue)
            
        # 2. Biome Ambient Modifiers
        chunk_x = pos.x // world_manager.chunk_size
        chunk_y = pos.y // world_manager.chunk_size
        chunk = world_manager.get_chunk(chunk_x, chunk_y)
        biome = chunk.get("biome")
        if biome:
            for m_blue in biome.ambient_modifiers:
                apply_modifier_blueprint(entity, m_blue)

def evaluate_formula(formula: str, entity: tcod.ecs.Entity) -> int:
    """
    Parses and evaluates a magnitude formula (e.g. '1d8 + @might_mod').
    Supported: 
      - NdM (Dice)
      - @stat_id (Attribute modifier)
      - Integers
    """
    import random
    import re
    
    parts = formula.replace(" ", "").split("+")
    total = 0
    
    for p in parts:
        if not p: continue
        
        # 1. Attribute Mod (@might_mod)
        if p.startswith("@"):
            attr_id = p[1:].replace("_mod", "")
            total += get_attr_mod(entity, attr_id)
            
        # 2. Dice (1d8)
        elif "d" in p:
            match = re.match(r"(\d+)d(\d+)", p)
            if match:
                num, sides = map(int, match.groups())
                for _ in range(num):
                    total += random.randint(1, sides)
                    
        # 3. Static Integer
        else:
            try:
                total += int(p)
            except ValueError:
                pass
                
    return total

def resolve_effect_targets(registry: tcod.ecs.Registry, attacker: tcod.ecs.Entity, primary_target: Optional[tcod.ecs.Entity], pattern: str) -> List[tcod.ecs.Entity]:
    """Resolves which entities are affected by an effect based on a pattern."""
    if pattern == "self":
        return [attacker]
    elif pattern == "primary_target":
        return [primary_target] if primary_target else []
    elif pattern == "adjacent_all":
        if Position not in attacker.components: return []
        ax, ay = attacker.components[Position].x, attacker.components[Position].y
        targets = []
        for ent in registry.Q.all_of(components=[Position, CombatVitals]):
            if ent == attacker: continue
            px, py = ent.components[Position].x, ent.components[Position].y
            if max(abs(px - ax), abs(py - ay)) <= 1:
                targets.append(ent)
        return targets
    return []

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
    if action_type in ["pickup", "drop", "equip", "craft", "use"]:
        ap_costs = {
            "pickup": AP_COST_PICKUP,
            "drop": AP_COST_DROP,
            "equip": AP_COST_EQUIP,
            "craft": AP_COST_CRAFT,
            "use": AP_COST_USE
        }
        ap_cost = ap_costs[action_type]
        
        if economy.ap_pool < ap_cost:
            return False
            
        success = False
        if action_type == "craft":
            # ... (craft logic) ...
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
        elif action_type == "use":
            target_item = action_payload.get("target_entity")
            from engine.ecs.components import Usable
            if target_item and target_item in entity.relation_tags_many["IsCarrying"] and Usable in target_item.components:
                success = True # loop handles the actual effect and consumption
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
