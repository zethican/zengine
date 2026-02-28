"""
ZEngine — engine/spawner.py
Data-Driven Spawner: Instantiates NPCs, items, and containers from blueprints.
=============================================================================
Version:     0.2 (Phase 13 Step 0 — Structural Entities)
Stack:       Python 3.14.3 | python-tcod-ecs
Status:      Ready for testing.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
import random
import tcod.ecs

from engine.data_loader import get_entity_def, get_item_def
from engine.item_factory import create_item
from engine.ecs.components import (
    EntityIdentity, Position, CombatVitals, CombatStats, 
    ActionEconomy, MovementStats, BehaviorProfile, Attributes,
    ItemIdentity, DoorState, BlocksMovement, Interactable, Faction, SocialAwareness
)

def spawn_npc(registry: tcod.ecs.Registry, entity_id: str, x: int, y: int, name_override: Optional[str] = None, faction_id: Optional[str] = None, is_player: bool = False) -> tcod.ecs.Entity:
    """Instantiates an NPC entity from a TOML blueprint and places it at (x, y)."""
    entity_def = get_entity_def(entity_id)
    entity = registry.new_entity()
    
    # 1. Identity
    entity.components[EntityIdentity] = EntityIdentity(
        entity_id=entity_id,
        name=name_override if name_override else entity_def.name,
        archetype=entity_def.archetype,
        is_player=is_player,
        template_origin=f"entities/{entity_id}"
    )
    
    # 2. Position
    entity.components[Position] = Position(x=x, y=y)
    
    # 3. Combat/Vitals
    entity.components[CombatVitals] = CombatVitals(hp=entity_def.hp, max_hp=entity_def.hp)
    entity.components[CombatStats] = CombatStats() # Defaults, modified by attributes
    
    # 4. Economy / Movement
    entity.components[ActionEconomy] = ActionEconomy()
    entity.components[MovementStats] = MovementStats(speed=entity_def.speed)
    
    # 5. Attributes
    entity.components[Attributes] = Attributes(scores=entity_def.attributes)
    
    # 6. AI/Behavior
    if not is_player:
        # Default behavior: Aggressive to enemies
        entity.components[BehaviorProfile] = BehaviorProfile(threat_weight=1.0)
        entity.components[Interactable] = Interactable(verb="talk")
        
        # Faction
        if faction_id:
            entity.components[Faction] = Faction(faction_id=faction_id)
        
        # Social Awareness
        # Proactive if has items or (placeholder) rumor
        is_proactive = len(entity_def.inventory) > 0
        entity.components[SocialAwareness] = SocialAwareness(
            engagement_range=6 if is_proactive else 3,
            is_proactive=is_proactive
        )
        
        # Dialogue
        from engine.ecs.components import DialogueProfile
        if entity_def.dialogue:
            entity.components[DialogueProfile] = DialogueProfile(**entity_def.dialogue)
        else:
            entity.components[DialogueProfile] = DialogueProfile()
        
    # 7. Inventory (Initial Gear)
    for item_path in entity_def.inventory:
        item = create_item(registry, item_path)
        entity.relation_tags_many["IsCarrying"].add(item)
        
    return entity

def spawn_item(registry: tcod.ecs.Registry, item_path: str, x: int, y: int) -> tcod.ecs.Entity:
    """Instantiates an item and places it on the floor."""
    item = create_item(registry, item_path)
    item.components[Position] = Position(x=x, y=y)
    return item

def spawn_container(registry: tcod.ecs.Registry, name: str, x: int, y: int, items: List[str]) -> tcod.ecs.Entity:
    """Creates a container entity (like a chest) containing specified items."""
    container = registry.new_entity()
    container.components[ItemIdentity] = ItemIdentity(
        entity_id="container",
        name=name,
        description="A sturdy wooden crate."
    )
    container.components[Position] = Position(x=x, y=y)
    container.components[Interactable] = Interactable(verb="open")
    
    for item_path in items:
        item = create_item(registry, item_path)
        container.relation_tags_many["IsCarrying"].add(item)
        
    return container

def spawn_door(registry: tcod.ecs.Registry, x: int, y: int, is_locked: bool = False) -> tcod.ecs.Entity:
    """Instantiates a stateful door entity."""
    door = registry.new_entity()
    door.components[EntityIdentity] = EntityIdentity(
        entity_id="door",
        name="Wooden Door",
        archetype="Structure"
    )
    door.components[Position] = Position(x=x, y=y, terrain_type="floor")
    door.components[DoorState] = DoorState(is_open=False, is_locked=is_locked)
    door.components[BlocksMovement] = BlocksMovement()
    door.components[CombatVitals] = CombatVitals(hp=20, max_hp=20)
    return door

def spawn_window(registry: tcod.ecs.Registry, x: int, y: int) -> tcod.ecs.Entity:
    """Instantiates a destructible window entity."""
    window = registry.new_entity()
    window.components[EntityIdentity] = EntityIdentity(
        entity_id="window",
        name="Glass Window",
        archetype="Structure"
    )
    window.components[Position] = Position(x=x, y=y, terrain_type="floor")
    window.components[BlocksMovement] = BlocksMovement()
    window.components[CombatVitals] = CombatVitals(hp=5, max_hp=5)
    return window

def evaluate_condition(registry: tcod.ecs.Registry, condition: str) -> bool:
    """Evaluates a string condition against the current ECS state."""
    if not condition:
        return True
        
    from engine.ecs.components import Disposition, Stress
    player = None
    for ent in registry.Q.all_of(components=[EntityIdentity]):
        if ent.components[EntityIdentity].is_player:
            player = ent
            break
            
    if not player:
        return False
        
    parts = condition.split()
    if len(parts) != 3:
        return True
        
    var, op, val = parts
    try:
        threshold = float(val)
    except ValueError:
        return True
        
    current = 0.0
    if var == "reputation":
        if Disposition in player.components:
            current = player.components[Disposition].reputation
    elif var == "stress":
        if Stress in player.components:
            current = player.components[Stress].stress_level
            
    if op == "<": return current < threshold
    if op == ">": return current > threshold
    if op == "==": return current == threshold
    
    return True

def spawn_from_definition(registry: tcod.ecs.Registry, spawn_def: Dict[str, Any], x: int, y: int, faction_id: Optional[str] = None) -> Optional[tcod.ecs.Entity]:
    """Executes a spawn based on a dictionary definition."""
    chance = spawn_def.get("chance", 1.0)
    if random.random() > chance:
        return None
        
    condition = spawn_def.get("condition", "")
    if not evaluate_condition(registry, condition):
        return None
        
    etype = spawn_def.get("type", "npc")
    eid = spawn_def.get("id")
    name_override = spawn_def.get("name")
    
    if etype == "npc":
        return spawn_npc(registry, eid, x, y, name_override=name_override, faction_id=faction_id)
    elif etype == "item":
        return spawn_item(registry, eid, x, y)
    elif etype == "container":
        return spawn_container(registry, name_override if name_override else "Chest", x, y, spawn_def.get("items", []))
    elif etype == "door":
        return spawn_door(registry, x, y)
    elif etype == "window":
        return spawn_window(registry, x, y)
        
    return None

def spawn_bespoke_chunk(registry: tcod.ecs.Registry, chunk_data: Dict[str, Any]):
    """Spawns all entities defined in a bespoke chunk template."""
    if chunk_data.get("is_spawned"):
        return
        
    spawns = chunk_data.get("spawns", [])
    off_x, off_y = chunk_data.get("spawn_offset", (0, 0))
    chunk_x, chunk_y = chunk_data.get("coords", (0, 0))
    faction_id = chunk_data.get("faction_id")
    chunk_size = 20
    
    global_off_x = chunk_x * chunk_size
    global_off_y = chunk_y * chunk_size
    
    for sdef in spawns:
        lx = sdef.get("lx", 0) + off_x
        ly = sdef.get("ly", 0) + off_y
        gx = global_off_x + lx
        gy = global_off_y + ly
        spawn_from_definition(registry, sdef, gx, gy, faction_id=faction_id)
        
    chunk_data["is_spawned"] = True

def spawn_wilderness_chunk(registry: tcod.ecs.Registry, chunk_data: Dict[str, Any]):
    """Spawns ambient NPCs in a wilderness chunk."""
    if chunk_data.get("is_spawned"):
        return
        
    pop_entries = chunk_data.get("population", [])
    if not pop_entries:
        return
        
    chunk_x, chunk_y = chunk_data.get("coords", (0, 0))
    faction_id = chunk_data.get("faction_id")
    chunk_size = 20
    global_off_x = chunk_x * chunk_size
    global_off_y = chunk_y * chunk_size
    
    rng = random.Random(hash((chunk_x, chunk_y, 12345)))
    if rng.random() < 0.15:
        pack_size = rng.randint(1, 3)
        ids = [entry.id for entry in pop_entries]
        weights = [entry.weight for entry in pop_entries]
        species_id = rng.choices(ids, weights=weights, k=1)[0]
        
        for _ in range(pack_size):
            lx = rng.randint(2, chunk_size - 3)
            ly = rng.randint(2, chunk_size - 3)
            npc = spawn_npc(registry, species_id, global_off_x + lx, global_off_y + ly, faction_id=faction_id)
            from engine.ecs.components import Disposition
            if Disposition in npc.components:
                npc.components[Disposition].reputation = -1.0
                
    chunk_data["is_spawned"] = True
