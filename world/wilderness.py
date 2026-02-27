"""
ZEngine — world/wilderness.py
Encounter Density Driver: Dynamic spawning based on Chronicle events and Equilibrium vitality.
=============================================================================================
Version:     0.1 (Phase 3)
Stack:       Python 3.14.3 | python-tcod-ecs
Status:      Encounter spawn density logic.
"""

from typing import Dict, Any, List
import tcod.ecs
import random

from engine.chronicle import ChronicleReader
from engine.combat import EventBus, CombatEvent
from engine.ecs.components import EntityIdentity, Position, CombatVitals, CombatStats, ActionEconomy, MovementStats

EVT_ENCOUNTER_SPAWNED = "world.encounter_spawned"

class FoeFactory:
    """Creates basic enemies for encounters."""
    @staticmethod
    def create_skirmisher(registry: tcod.ecs.Registry, x: int, y: int, level: int = 1) -> tcod.ecs.Entity:
        from engine.data_loader import get_entity_def
        
        # JIT Load stats from TOML
        foe_def = get_entity_def("foe_skirmisher")
        
        foe = registry.new_entity()
        foe.components[EntityIdentity] = EntityIdentity(
            entity_id=random.randint(1000, 9000), 
            name=f"{foe_def.name} L{level}", 
            archetype=foe_def.archetype, 
            is_player=False
        )
        foe.components[Position] = Position(x=x, y=y)
        
        # Scale HP by level, but base it on the TOML definition
        hp = foe_def.hp + (level * 2)
        foe.components[CombatVitals] = CombatVitals(hp=hp, max_hp=hp)
        
        # Scale combat stats by level, no base defined in minimalist seed atm so we extrapolate
        foe.components[CombatStats] = CombatStats(attack_bonus=level, defense_bonus=level - 1)
        
        foe.components[ActionEconomy] = ActionEconomy()
        foe.components[MovementStats] = MovementStats(speed=foe_def.speed)
        
        # Ability definitions are referenced by ID
        # foe.components[Abilities] = foe_def.abilities (Phase 4+ feature, ignored for now)
        
        return foe

def encounter_spawn_system(
    registry: tcod.ecs.Registry,
    chronicle_reader: ChronicleReader,
    chunk_coords: tuple[int, int],
    node_vitality: float,
    bus: EventBus
) -> int:
    """
    Spawns an encounter dynamically out in the wilderness, bypassing random spawn tables.
    Density is calculated directly from the Chronicle's history of deaths/legacy significance
    and the Equilibrium system's node_vitality.
    
    Returns the number of enemies spawned.
    """
    # 1. Query Chronicle for historical density in this approximate area.
    # In a full implementation, we'd query by spatial overlap. Here we'll query for
    # high-significance death events as a proxy for "dangerous legacy zone".
    all_events = chronicle_reader.all_entries()
    death_events = [e for e in all_events if e["payload"].get("event_type") == "combat.on_death"]
    
    # Calculate density score: Base vitality + (deaths * significance weight)
    # The more deaths, the larger the repopulation density (viral simulation).
    historical_density = sum(e.get("significance", 1) for e in death_events)
    
    # Density score formula. Let's say baseline is 1-2 enemies.
    density_score = node_vitality + (historical_density * 0.5)
    
    spawn_count = 0
    if density_score < 2.0:
        spawn_count = random.randint(0, 1)
    elif density_score < 5.0:
        spawn_count = random.randint(1, 3)
    else:
        # High density legacy/viral zone
        spawn_count = random.randint(2, 5)
        
    if spawn_count > 0:
        cx, cy = chunk_coords
        for _ in range(spawn_count):
            # Spawn roughly in the center of the chunk
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(-5, 5)
            # Level scales with density
            level = max(1, int(density_score // 2))
            FoeFactory.create_skirmisher(registry, cx * 20 + 10 + offset_x, cy * 20 + 10 + offset_y, level)
            
        bus.emit(CombatEvent(
            event_key=EVT_ENCOUNTER_SPAWNED,
            source="EncounterSpawnSystem",
            data={
                "chunk_coords": chunk_coords, 
                "spawn_count": spawn_count,
                "density_score": density_score
            }
        ))
        
    return spawn_count
