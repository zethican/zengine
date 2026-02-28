"""
ZEngine — engine/loop.py
Main Simulation Loop: Wires ECS, EventBus, Chronicle, and Social systems.
========================================================================
Version:     0.6  (Phase 19 — Tag-Based Functional Overhaul)
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
    Position,
    Attributes,
    ItemIdentity,
    Equippable,
    ItemStats,
    Quantity,
    Usable,
    BehaviorProfile,
    Disposition,
    Stress,
    PendingAction,
    SocialAwareness,
    ActiveModifiers,
    Modifier
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
        
        # Faction Standings (Collective Memory)
        self.faction_standing: Dict[str, float] = {} # faction_id -> reputation
        
        # UI State Comms
        self.pending_social_popup: Optional[Dict[str, Any]] = None
        
        # Core systems
        self.inscriber = ChronicleInscriber(
            bus=self.bus,
            chronicle_path=chronicle_path,
            clock=self.clock,
            player_present=True
        )
        self.social_system = SocialStateSystem(self.bus, self.registry, self.faction_standing)
        
        # World Generation
        self.world = ChunkManager(world_seed=random.randint(1, 100000))

    
    def open_session(self) -> None:
        self.inscriber.open_session()

    def close_session(self) -> None:
        """Closes the current tracking session but does NOT write a spatial snapshot."""
        self.inscriber.close_session()

    def save_session(self, snapshot_path: Optional[Path] = None) -> None:
        """
        Saves the critical world state to TOML.
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

        lines.append("[faction_standing]")
        for fid, val in self.faction_standing.items():
            lines.append(f'{fid} = {val:.4f}')
        lines.append("")

        # Helper to serialize an entity
        def serialize_ent(entity: tcod.ecs.Entity, table_name: str) -> List[str]:
            ent_lines = []
            
            # Components
            if EntityIdentity in entity.components:
                id_comp = entity.components[EntityIdentity]
                ent_lines.append(f'id = {id_comp.entity_id}')
                ent_lines.append(f'name = "{id_comp.name}"')
                ent_lines.append(f'archetype = "{id_comp.archetype}"')
                ent_lines.append(f'is_player = {"true" if id_comp.is_player else "false"}')
                if id_comp.template_origin:
                    ent_lines.append(f'template_origin = "{id_comp.template_origin}"')

            if ItemIdentity in entity.components:
                item_id = entity.components[ItemIdentity]
                ent_lines.append(f'item_id = "{item_id.entity_id}"')
                ent_lines.append(f'item_name = "{item_id.name}"')
                ent_lines.append(f'item_description = "{item_id.description}"')

            if Position in entity.components:
                pos = entity.components[Position]
                ent_lines.append(f'x = {pos.x}')
                ent_lines.append(f'y = {pos.y}')
                ent_lines.append(f'terrain = "{pos.terrain_type}"')

            if CombatVitals in entity.components:
                v = entity.components[CombatVitals]
                ent_lines.append(f'hp = {v.hp}')
                ent_lines.append(f'max_hp = {v.max_hp}')

            if Attributes in entity.components:
                ent_lines.append(f'[{table_name}.attributes]')
                for k, val in entity.components[Attributes].scores.items():
                    ent_lines.append(f'{k} = {val}')
                ent_lines.append("")

            # Inventory
            carried = list(entity.relation_tags_many["IsCarrying"])
            if carried:
                for item in carried:
                    ent_lines.append(f'[[{table_name}.inventory]]')
                    ent_lines.extend(serialize_ent(item, f"{table_name}.inventory"))
            
            return ent_lines

        # Save all entities with Position (World-level)
        for entity in self.registry.Q.all_of(components=[Position]):
            # 1. Skip items inside containers
            if any(entity in parent.relation_tags_many["IsCarrying"] for parent in self.registry.Q.all_of(relations=[("IsCarrying", ...)])):
                continue
            
            # 2. Context Collapse: Cull ephemeral random encounters
            if EntityIdentity in entity.components:
                ident = entity.components[EntityIdentity]
                if not ident.is_player and ident.archetype in ["Skirmisher", "Minion"]:
                    continue
                
            lines.append("[[entities]]")
            lines.extend(serialize_ent(entity, "entities"))
            lines.append("")
            
        with open(snapshot_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            
    def resume_session(self, snapshot_path: Optional[Path] = None) -> None:
        """Restores the world from a snapshot."""
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
        self.world = ChunkManager(world_seed=wdata.get("world_seed", random.randint(1, 10000)))
        
        # Restore Faction Standings
        self.faction_standing = data.get("faction_standing", {})
        
        # Restore registry
        self.registry = tcod.ecs.Registry()
        
        def deserialize_ent(edata: Dict[str, Any]) -> tcod.ecs.Entity:
            ent = self.registry.new_entity()
            
            if "id" in edata:
                ent.components[EntityIdentity] = EntityIdentity(
                    entity_id=edata["id"],
                    name=edata["name"],
                    archetype=edata["archetype"],
                    is_player=edata.get("is_player", False),
                    template_origin=edata.get("template_origin")
                )
            
            if "item_id" in edata:
                ent.components[ItemIdentity] = ItemIdentity(
                    entity_id=edata["item_id"],
                    name=edata["item_name"],
                    description=edata["item_description"]
                )

            if "x" in edata:
                ent.components[Position] = Position(x=edata["x"], y=edata["y"], terrain_type=edata.get("terrain", "floor"))

            if "hp" in edata:
                ent.components[CombatVitals] = CombatVitals(hp=edata["hp"], max_hp=edata["max_hp"])
                ent.components[CombatStats] = CombatStats()
                ent.components[ActionEconomy] = ActionEconomy()
                ent.components[MovementStats] = MovementStats()

            if "attributes" in edata:
                ent.components[Attributes] = Attributes(scores=edata["attributes"])

            for idata in edata.get("inventory", []):
                item = deserialize_ent(idata)
                ent.relation_tags_many["IsCarrying"].add(item)
                
            return ent

        for edata in data.get("entities", []):
            deserialize_ent(edata)
            
        self.open_session()

    def tick(self) -> None:
        """Advance the simulation by one engine tick."""
        self.clock = self.clock.advance_tick()
        self.inscriber.clock = self.clock

        # Modifier Lifecycle (Decay old effects)
        from engine.ecs.systems import modifier_tick_system
        modifier_tick_system(self.registry)

        turn_resolution_system(self.registry)
        action_economy_reset_system(self.registry, self.bus)
        
        # Environmental Effects (Apply location-based effects)
        from engine.ecs.systems import environmental_modifier_system
        environmental_modifier_system(self.registry, self.world)
        
        if not hasattr(self, "ai_influence"):
            from engine.ai_system import InfluenceMapSystem
            self.ai_influence = InfluenceMapSystem()
            
        px, py = 0, 0
        player_ent = None
        for ent in self.registry.Q.all_of(components=[EntityIdentity, Position]):
            if ent.components[EntityIdentity].is_player:
                px, py = ent.components[Position].x, ent.components[Position].y
                player_ent = ent
                break
        
        from engine.ecs.systems import ai_decision_system
        ai_decision_system(self.registry, self.ai_influence, px, py, current_tick=self.clock.tick)
        
        # Check for Proactive Social Engagement
        self.pending_social_popup = self.check_proactive_social(player_ent)
        
        from engine.ecs.components import PendingAction
        for ent in list(self.registry.Q.all_of(components=[PendingAction])):
            pending = ent.components[PendingAction]
            if pending.action_type == "move":
                dx, dy = pending.payload.get("dx", 0), pending.payload.get("dy", 0)
                from engine.ecs.components import MovementStats, ActionEconomy
                mov = ent.components.get(MovementStats)
                econ = ent.components.get(ActionEconomy)
                cost = mov.movement_ap_cost if mov else 10
                
                if econ and econ.ap_pool >= cost:
                    self.move_entity_ecs(ent, dx, dy)
                    econ.ap_pool -= cost
                    econ.ap_spent_this_turn += cost
            elif pending.action_type == "use":
                self.invoke_ability_ecs(ent, "use", pending.target_entity)
            
            del ent.components[PendingAction]

    def check_proactive_social(self, player: tcod.ecs.Entity) -> Optional[Dict[str, Any]]:
        """Checks for adjacent NPCs who want to initiate dialogue."""
        if not player: return None
        
        ppos = player.components[Position]
        
        for npc in self.registry.Q.all_of(components=[Position, SocialAwareness, EntityIdentity]):
            if npc.components[EntityIdentity].is_player: continue
            
            npos = npc.components[Position]
            soc = npc.components[SocialAwareness]
            
            # Adjacent check
            dist = max(abs(npos.x - ppos.x), abs(npos.y - ppos.y))
            if dist == 1:
                # Cooldown check (2000 ticks)
                if self.clock.tick - soc.last_interaction_tick > 2000:
                    return {"type": "social_autopop", "target": npc}
                    
        return None

    def move_entity_ecs(self, entity: tcod.ecs.Entity, dx: int, dy: int) -> None:
        """Move entity within the world."""
        if Position not in entity.components:
            return
            
        pos = entity.components[Position]
        new_x, new_y = pos.x + dx, pos.y + dy
        
        tile_type = self.world.get_tile(new_x, new_y)
        if tile_type == "wall":
            return
            
        # Entity collision check
        for other in self.registry.Q.all_of(components=[Position]):
            if other == entity: continue
            opos = other.components[Position]
            if opos.x == new_x and opos.y == new_y:
                return # Occupied
            
        pos.x = new_x
        pos.y = new_y
        pos.terrain_type = tile_type
        
        chunk_x = new_x // self.world.chunk_size
        chunk_y = new_y // self.world.chunk_size
        chunk = self.world.get_chunk(chunk_x, chunk_y)
        if not chunk.get("is_spawned"):
            from engine.spawner import spawn_bespoke_chunk, spawn_wilderness_chunk
            if chunk["terrain"] == "bespoke":
                spawn_bespoke_chunk(self.registry, chunk)
            else:
                spawn_wilderness_chunk(self.registry, chunk)

    def interact_at(self, actor: tcod.ecs.Entity, x: int, y: int) -> Optional[Dict[str, Any]]:
        from engine.ecs.systems import interaction_system
        return interaction_system(self.registry, actor, x, y)

    def share_rumor(self, actor: tcod.ecs.Entity, source_npc: tcod.ecs.Entity) -> Optional[str]:
        rumor = self.world.get_next_rumor()
        if not rumor:
            return None
            
        source_name = source_npc.components[EntityIdentity].name if EntityIdentity in source_npc.components else "Someone"
        
        from engine.combat import EVT_SOCIAL_RUMOR_SHARED
        self.bus.emit(CombatEvent(
            event_key=EVT_SOCIAL_RUMOR_SHARED,
            source=source_name,
            data={"rumor_id": rumor.id, "rumor_name": rumor.name}
        ))
        
        return f"Have you heard? They say there's a {rumor.pol_type} called '{rumor.name}' somewhere nearby."

    def execute_trade(self, player: tcod.ecs.Entity, npc: tcod.ecs.Entity, p_items: List[tcod.ecs.Entity], n_items: List[tcod.ecs.Entity], is_generous: bool = False):
        """Atomsically swaps items between entities and applies reputation shift."""
        for item in p_items:
            player.relation_tags_many["IsCarrying"].remove(item)
            npc.relation_tags_many["IsCarrying"].add(item)
        for item in n_items:
            npc.relation_tags_many["IsCarrying"].remove(item)
            player.relation_tags_many["IsCarrying"].add(item)
            
        delta = 0.05
        disp = npc.components.get(Disposition, Disposition())
        if is_generous:
            if self.clock.tick - disp.last_gift_tick >= 1000:
                delta = 0.15
                disp.last_gift_tick = self.clock.tick
                npc.components[Disposition] = disp
                
        npc_name = npc.components[EntityIdentity].name if EntityIdentity in npc.components else "NPC"
        from engine.combat import EVT_SOCIAL_DISPOSITION_SHIFT
        self.bus.emit(CombatEvent(
            event_key=EVT_SOCIAL_DISPOSITION_SHIFT,
            source=npc_name,
            data={"delta": delta, "cause": "trade"}
        ))

    def apply_damage_ecs(self, target: tcod.ecs.Entity, amount: int) -> None:
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
            from engine.ecs.components import BlocksMovement, DoorState
            if BlocksMovement in target.components:
                del target.components[BlocksMovement]
            if DoorState in target.components:
                target.components[EntityIdentity].name = f"Shattered {target.components[EntityIdentity].name}"
            
            self.bus.emit(CombatEvent(
                event_key=EVT_ON_DEATH,
                source=target_name,
                data={"final_hp": vitals.hp, "is_structural": DoorState in target.components}
            ))

    def apply_effect(self, attacker: tcod.ecs.Entity, target: tcod.ecs.Entity, effect_def: "EffectDef") -> bool:
        """Applies a single functional effect to a target."""
        from engine.ecs.systems import evaluate_formula, get_effective_stats, apply_modifier_blueprint
        
        attacker_name = attacker.components.get(EntityIdentity).name if EntityIdentity in attacker.components else "Unknown"
        target_name = target.components.get(EntityIdentity).name if EntityIdentity in target.components else "Unknown"
        
        # 1. Evaluate Magnitude
        magnitude = evaluate_formula(effect_def.magnitude, attacker)
        
        # 2. Dispatch by Type
        if effect_def.effect_type == "damage":
            # 2d8 Resolution for Damage
            atk_stats = get_effective_stats(attacker)
            def_stats = get_effective_stats(target)
            
            dc = BASE_HIT_DC + def_stats.defense_bonus
            roll_data = resolve_roll(modifier=atk_stats.attack_bonus)
            outcome = roll_outcome_category(roll_data["total"], dc, roll_data["is_crit"], roll_data["is_fumble"])
            
            if outcome in ("hit", "critical", "graze"):
                raw = magnitude + atk_stats.damage_bonus
                if outcome == "critical": raw = raw * 2
                if outcome == "graze": raw = max(1, raw // 2)
                self.apply_damage_ecs(target, max(0, raw))
                
                # Apply On-Hit Modifiers from Items
                for item in attacker.relation_tags_many["IsEquipped"]:
                    if ItemStats in item.components:
                        for m_blue in item.components[ItemStats].modifiers:
                            apply_modifier_blueprint(target, m_blue)
                return True
            return False
            
        elif effect_def.effect_type == "heal":
            if CombatVitals in target.components:
                v = target.components[CombatVitals]
                v.hp = min(v.max_hp, v.hp + magnitude)
                self.bus.emit(CombatEvent(event_key=EVT_ON_DAMAGE, source=attacker_name, target=target_name, data={"amount": -magnitude, "hp_remaining": v.hp, "is_heal": True}))
                return True
                
        elif effect_def.effect_type == "apply_modifier":
            if effect_def.modifier_id:
                # We expect effect_def to have stat_field, magnitude, duration
                # For Phase 19 we'll assume stat_field is speed if missing
                stat_field = getattr(effect_def, "stat_field", "speed")
                
                apply_modifier_blueprint(target, {
                    "id": effect_def.modifier_id,
                    "magnitude": magnitude,
                    "duration": effect_def.duration or 5,
                    "stat_field": stat_field
                })
                return True
                
        return False

    def invoke_ability_ecs(self, attacker: tcod.ecs.Entity, ability_id: str, target: Optional[tcod.ecs.Entity] = None, **kwargs) -> bool:
        from engine.data_loader import get_ability_def
        is_builtin = ability_id in ["pickup", "drop", "equip", "craft", "use"]
        
        # 1. Action Resolution (AP Check & Event Emission)
        payload = {"target": str(target) if target else "None", "target_entity": target, **kwargs}
        if not action_resolution_system(self.registry, attacker, ability_id, payload, self.bus):
            return False
            
        # 2. Built-in Special Logic
        if is_builtin:
            if ability_id == "use":
                from engine.ecs.components import Usable, Quantity, ItemStats
                from engine.ecs.systems import apply_modifier_blueprint
                target_item = payload["target_entity"]
                usable = target_item.components[Usable]
                
                # Apply Modifiers from Item to User (Self-Application)
                if ItemStats in target_item.components:
                    i_stats = target_item.components[ItemStats]
                    for m_blue in i_stats.modifiers:
                        apply_modifier_blueprint(attacker, m_blue)
                
                success = self.invoke_ability_ecs(attacker, usable.ability_id, attacker)
                if success and usable.consumes:
                    if Quantity in target_item.components:
                        q = target_item.components[Quantity]
                        q.amount -= 1
                        if q.amount <= 0:
                            if target_item in attacker.relation_tags_many["IsCarrying"]:
                                attacker.relation_tags_many["IsCarrying"].remove(target_item)
                            target_item.clear()
                    else:
                        if target_item in attacker.relation_tags_many["IsCarrying"]:
                            attacker.relation_tags_many["IsCarrying"].remove(target_item)
                        target_item.clear()
                return success
            return True

        # 3. Functional Effect Pipeline
        ability = get_ability_def(ability_id)
        from engine.ecs.systems import resolve_effect_targets
        
        any_success = False
        for effect_def in ability.effects:
            targets = resolve_effect_targets(self.registry, attacker, target, effect_def.target_pattern)
            for t in targets:
                if self.apply_effect(attacker, t, effect_def):
                    any_success = True
                    
        return any_success
