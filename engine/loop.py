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
    MovementStats,
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
        """Closes the current tracking session but does NOT write a spatial snapshot."""
        self.inscriber.close_session()

    def save_session(self, snapshot_path: Optional[Path] = None) -> None:
        """
        Saves the critical world state to TOML, intentionally collapsing ephemeral context.
        Only the player, key named NPCs, and global time/world properties are persisted.
        """
        if snapshot_path is None:
            snapshot_path = Path("sessions/spatial_snapshot.toml")
            
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        lines = []
        lines.append("[world]")
        lines.append(f'era = "{self.clock.era}"')
        lines.append(f"cycle = {self.clock.cycle}")
        lines.append(f"tick = {self.clock.tick}")
        lines.append(f"world_seed = {self.world.world_seed}")
        lines.append("")
        
        for entity in self.registry.Q.all_of(components=[EntityIdentity, Position, CombatVitals]):
            ident = entity.components[EntityIdentity]
            
            # Context Collapse: Ephemeral random encounters are not saved.
            # They will be regenerated functionally by the Wilderness density driver.
            if not ident.is_player and ident.archetype in ["Skirmisher", "Minion"]:
                continue
                
            pos = entity.components[Position]
            vitals = entity.components[CombatVitals]
            
            stats = entity.components.get(CombatStats)
            atk = stats.attack_bonus if stats else 0
            dmg = stats.damage_bonus if stats else 0
            dfn = stats.defense_bonus if stats else 0
            
            mov = entity.components.get(MovementStats)
            speed = mov.speed if mov else 10.0
            
            lines.append("[[entities]]")
            lines.append(f"id = {ident.entity_id}")
            lines.append(f'name = "{ident.name}"')
            lines.append(f'archetype = "{ident.archetype}"')
            lines.append(f"is_player = {'true' if ident.is_player else 'false'}")
            lines.append(f"x = {pos.x}")
            lines.append(f"y = {pos.y}")
            lines.append(f"hp = {vitals.hp}")
            lines.append(f"max_hp = {vitals.max_hp}")
            lines.append(f"attack_bonus = {atk}")
            lines.append(f"damage_bonus = {dmg}")
            lines.append(f"defense_bonus = {dfn}")
            lines.append(f"speed = {speed}")
            lines.append("")
            
        with open(snapshot_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            
    def resume_session(self, snapshot_path: Optional[Path] = None) -> None:
        """
        Restores the world from the exact moment of a spatial_snapshot.toml save.
        """
        import tomllib
        
        if snapshot_path is None:
            snapshot_path = Path("sessions/spatial_snapshot.toml")
            
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Cannot resume, missing {snapshot_path}")
            
        with open(snapshot_path, "rb") as f:
            data = tomllib.load(f)
            
        # Restore world
        wdata = data.get("world", {})
        self.clock = GameTimestamp(era=wdata.get("era", "Recent"), cycle=wdata.get("cycle", 1), tick=wdata.get("tick", 1))
        self.inscriber.clock = self.clock
        # Rebuild ChunkManager with the saved seed
        self.world = ChunkManager(world_seed=wdata.get("world_seed", random.randint(1, 10000)))
        
        # Restore registry
        self.registry = tcod.ecs.Registry()
        
        for edata in data.get("entities", []):
            ent = self.registry.new_entity()
            ent.components[EntityIdentity] = EntityIdentity(
                entity_id=edata["id"],
                name=edata["name"],
                archetype=edata["archetype"],
                is_player=edata.get("is_player", False)
            )
            ent.components[Position] = Position(x=edata["x"], y=edata["y"])
            ent.components[CombatVitals] = CombatVitals(hp=edata["hp"], max_hp=edata["max_hp"])
            ent.components[CombatStats] = CombatStats(
                attack_bonus=edata.get("attack_bonus", 0),
                damage_bonus=edata.get("damage_bonus", 0),
                defense_bonus=edata.get("defense_bonus", 0)
            )
            ent.components[ActionEconomy] = ActionEconomy()
            ent.components[MovementStats] = MovementStats(speed=edata.get("speed", 10.0))
            
        self.open_session()

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
