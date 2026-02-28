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
        
        tile_type = self.world.get_tile(new_x, new_y)
        if tile_type == "wall":
            return # Collision prevents movement
            
        pos.x = new_x
        pos.y = new_y
        pos.terrain_type = tile_type

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

    def invoke_ability_ecs(self, attacker: tcod.ecs.Entity, ability_id: str, target: Optional[tcod.ecs.Entity] = None) -> None:
        """
        Executes a data-driven ability, replacing the hardcoded resolve_attack_ecs.
        Handles single target, self, and adjacent_all target types, as well as healing vs damage.
        """
        from engine.data_loader import get_ability_def
        try:
            ability = get_ability_def(ability_id)
        except FileNotFoundError:
            return
            
        attacker_name = attacker.components.get(EntityIdentity).name if EntityIdentity in attacker.components else str(attacker)
        
        # 1. Validate & Deduct AP via system
        payload = {"target": str(target) if target else "None"}
        if not action_resolution_system(self.registry, attacker, ability_id, payload, self.bus):
            return # Failed AP validation
            
        # 2. Determine Targets
        targets = []
        if ability.target_type == "self":
            targets = [attacker]
        elif ability.target_type == "single":
            if target is not None:
                targets = [target]
        elif ability.target_type == "adjacent_all":
            # Very basic proximity logic (Chebyshev distance of 1)
            if Position in attacker.components:
                ax, ay = attacker.components[Position].x, attacker.components[Position].y
                for ent in self.registry.Q.all_of(components=[Position, CombatVitals]):
                    if ent == attacker:
                        continue
                    px, py = ent.components[Position].x, ent.components[Position].y
                    if max(abs(px - ax), abs(py - ay)) <= 1:
                        targets.append(ent)
                        
        if not targets:
            return

        # 3. Apply Effects
        is_heal = (ability.damage_die < 0)
        atk_stat = attacker.components.get(CombatStats)
        atk_mod = atk_stat.attack_bonus if atk_stat else 0
        
        for t in targets:
            # Healing bypasses AC roll
            if is_heal:
                heal_amt = random.randint(1, abs(ability.damage_die)) + abs(ability.damage_bonus)
                if CombatVitals in t.components:
                    t_vitals = t.components[CombatVitals]
                    t_vitals.hp = min(t_vitals.max_hp, t_vitals.hp + heal_amt)
                    
                    target_name = t.components.get(EntityIdentity).name if EntityIdentity in t.components else str(t)
                    self.bus.emit(CombatEvent(
                        event_key=EVT_ON_DAMAGE, # Reusing event for health delta, logged via chronicle
                        source=attacker_name,
                        target=target_name,
                        data={"amount": -heal_amt, "hp_remaining": t_vitals.hp, "is_heal": True}
                    ))
                continue
                
            # Combat
            def_stat = t.components.get(CombatStats)
            def_mod = def_stat.defense_bonus if def_stat else 0
            
            dc = BASE_HIT_DC + def_mod
            roll_data = resolve_roll(modifier=atk_mod)
            outcome = roll_outcome_category(
                roll_data["total"], dc,
                roll_data["is_crit"], roll_data["is_fumble"]
            )
            
            damage = 0
            if outcome in ("hit", "critical", "graze"):
                raw = random.randint(1, max(1, ability.damage_die)) + ability.damage_bonus
                if outcome == "critical":
                    raw = ability.damage_die + ability.damage_bonus # Max die
                if outcome == "graze":
                    raw = max(1, raw // 2)
                damage = max(0, raw)
                self.apply_damage_ecs(t, damage)
                
        # 4. End Turn Emission
        self.bus.emit(CombatEvent(
            event_key=EVT_TURN_ENDED,
            source=attacker_name,
            data={"ap_spent": ability.ap_cost}
        ))
