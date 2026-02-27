"""
ZEngine — engine/loop.py
Main Simulation Loop: Wires ECS, EventBus, Chronicle, and Social systems.
========================================================================
Version:     0.1  (Phase 2 Integration)
Stack:       Python 3.14.3 | python-tcod-ecs
Status:      Integration entry point.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Any, Dict
import random

import tcod.ecs

from engine.combat import (
    EventBus, 
    CombatEvent, 
    EVT_TURN_ENDED, 
    EVT_ROUND_ENDED, 
    resolve_roll, 
    roll_outcome_category, 
    BASE_HIT_DC,
    COMBAT_ROLL_DISPLAY,
    EVT_ON_DAMAGE,
    EVT_ON_DEATH
)
from engine.ecs.systems import (
    turn_resolution_system, 
    action_economy_reset_system, 
    action_resolution_system
)
from engine.social_state import SocialStateSystem
from engine.chronicle import ChronicleInscriber, GameTimestamp
from engine.ecs.components import (
    CombatVitals, 
    ActionEconomy, 
    EntityIdentity, 
    CombatStats,
    Position
)
from world.generator import ChunkManager, Rumor

class SimulationLoop:
    """
    Core executor for the ZEngine game loop.
    Wires the EventBus, Registry, ChronicleInscriber, and SocialStateSystem.
    """
    def __init__(self, chronicle_path: Optional[Path] = None):
        if chronicle_path is None:
            chronicle_path = Path("sessions/chronicle.jsonl")

        self.registry = tcod.ecs.Registry()
        self.bus = EventBus()
        self.clock = GameTimestamp(era="Recent", cycle=1, tick=1)
        
        # Core systems
        self.inscriber = ChronicleInscriber(
            bus=self.bus,
            chronicle_path=chronicle_path,
            clock=self.clock,
            player_present=True
        )
        self.social_system = SocialStateSystem(self.bus)
        
        # World Generation
        self.world = ChunkManager(world_seed=random.randint(1, 100000))

    
    def open_session(self) -> None:
        self.inscriber.open_session()

    def close_session(self) -> None:
        self.inscriber.close_session()

    def tick(self) -> None:
        """Advance the simulation by one engine tick."""
        self.clock = self.clock.advance_tick()
        self.inscriber.clock = self.clock

        # 1. Turn Resolution (tick action energy)
        turn_resolution_system(self.registry)

        # 2. Action Economy Reset (grant AP if energy crossed threshold)
        action_economy_reset_system(self.registry, self.bus)

    def move_entity_ecs(self, entity: tcod.ecs.Entity, dx: int, dy: int) -> None:
        """Move entity within the world, updating Position and lazily loading chunks."""
        if Position not in entity.components:
            return
            
        pos = entity.components[Position]
        new_x, new_y = pos.x + dx, pos.y + dy
        
        chunk_x = new_x // self.world.chunk_size
        chunk_y = new_y // self.world.chunk_size
        chunk = self.world.get_chunk(chunk_x, chunk_y)
        
        pos.x = new_x
        pos.y = new_y
        pos.terrain_type = chunk["terrain"]

    def apply_damage_ecs(self, target: tcod.ecs.Entity, amount: int) -> None:
        """
        Standalone damage application, replacing Combatant.apply_damage for ECS entities.
        """
        if CombatVitals not in target.components:
            return
            
        vitals = target.components[CombatVitals]
        amount = max(0, amount)
        vitals.hp -= amount
        
        target_name = target.components.get(EntityIdentity).name if EntityIdentity in target.components else str(target)
        
        self.bus.emit(CombatEvent(
            event_key=EVT_ON_DAMAGE,
            source=target_name,
            target=target_name,
            data={"amount": amount, "hp_remaining": vitals.hp}
        ))
        
        if vitals.hp <= 0 and not vitals.is_dead:
            vitals.is_dead = True
            self.bus.emit(CombatEvent(
                event_key=EVT_ON_DEATH,
                source=target_name,
                data={"final_hp": vitals.hp}
            ))

    def resolve_attack_ecs(self, attacker: tcod.ecs.Entity, defender: tcod.ecs.Entity) -> None:
        """
        Perform an attack action. Follows the Phase 2 action_resolution_system + combat engine logic.
        """
        attacker_name = attacker.components.get(EntityIdentity).name if EntityIdentity in attacker.components else str(attacker)
        defender_name = defender.components.get(EntityIdentity).name if EntityIdentity in defender.components else str(defender)
        
        # Run base action tracking system
        payload = {"target": defender_name}
        action_resolution_system(self.registry, attacker, "attack", payload, self.bus)
        
        # Execute combat math
        atk_stat = attacker.components.get(CombatStats)
        def_stat = defender.components.get(CombatStats)
        
        atk_mod = atk_stat.attack_bonus if atk_stat else 0
        def_mod = def_stat.defense_bonus if def_stat else 0
        dmg_bonus = atk_stat.damage_bonus if atk_stat else 0
        
        dc = BASE_HIT_DC + def_mod
        
        roll_data = resolve_roll(modifier=atk_mod)
        outcome = roll_outcome_category(
            roll_data["total"], dc,
            roll_data["is_crit"], roll_data["is_fumble"]
        )
        
        damage = 0
        if outcome in ("hit", "critical", "graze"):
            raw = random.randint(1, 6) + dmg_bonus
            if outcome == "critical":
                raw = 6 + dmg_bonus
            if outcome == "graze":
                raw = max(1, raw // 2)
            damage = max(0, raw)
            self.apply_damage_ecs(defender, damage)
        
        # Turn end
        self.bus.emit(CombatEvent(
            event_key=EVT_TURN_ENDED,
            source=attacker_name,
            data={"ap_spent": 50}
        ))
