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
    Modifier,
    Faction,
    PartyMember
)
from world.generator import ChunkManager, Rumor
from world.territory import TerritoryManager, TerritoryNode
from world.exploration import ExplorationManager

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
        
        # JIT Virtual Registry (Phase 21)
        # Key: (chunk_x, chunk_y) -> List of serialized entity dicts
        self.virtual_entities: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        
        # Fog of War (Phase 23)
        self.exploration = ExplorationManager()
        
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
        _world_seed = random.randint(1, 100000)
        self.territory = TerritoryManager(world_seed=_world_seed)
        self.world = ChunkManager(world_seed=_world_seed, territory=self.territory)

    def _serialize_entity(self, entity: tcod.ecs.Entity) -> Dict[str, Any]:
        """Converts an ECS entity into a serializable dictionary."""
        data = {}
        
        if EntityIdentity in entity.components:
            id_comp = entity.components[EntityIdentity]
            data["identity"] = {
                "id": id_comp.entity_id,
                "name": id_comp.name,
                "archetype": id_comp.archetype,
                "is_player": id_comp.is_player,
                "template_origin": id_comp.template_origin
            }

        if ItemIdentity in entity.components:
            item_id = entity.components[ItemIdentity]
            data["item_identity"] = {
                "id": item_id.entity_id,
                "name": item_id.name,
                "description": item_id.description
            }

        if Position in entity.components:
            pos = entity.components[Position]
            data["position"] = {"x": pos.x, "y": pos.y, "terrain": pos.terrain_type}

        if CombatVitals in entity.components:
            v = entity.components[CombatVitals]
            data["vitals"] = {"hp": v.hp, "max_hp": v.max_hp, "is_dead": v.is_dead}

        if CombatStats in entity.components:
            s = entity.components[CombatStats]
            data["stats"] = {"attack_bonus": s.attack_bonus, "damage_bonus": s.damage_bonus, "defense_bonus": s.defense_bonus}

        if Attributes in entity.components:
            data["attributes"] = entity.components[Attributes].scores.copy()

        if Faction in entity.components:
            data["faction"] = {"id": entity.components[Faction].faction_id}

        if Disposition in entity.components:
            d = entity.components[Disposition]
            data["disposition"] = {"reputation": d.reputation, "last_gift_tick": d.last_gift_tick}

        if SocialAwareness in entity.components:
            sa = entity.components[SocialAwareness]
            data["social_awareness"] = {"engagement_range": sa.engagement_range, "last_interaction_tick": sa.last_interaction_tick, "is_proactive": sa.is_proactive}

        if PartyMember in entity.components:
            data["party_member"] = {"leader_id": entity.components[PartyMember].leader_id}

        # Inventory
        carried = list(entity.relation_tags_many["IsCarrying"])
        if carried:
            data["inventory"] = [self._serialize_entity(item) for item in carried]
            
        return data

    def _deserialize_entity(self, data: Dict[str, Any]) -> tcod.ecs.Entity:
        """Restores an ECS entity from a dictionary."""
        ent = self.registry.new_entity()
        
        if "identity" in data:
            d = data["identity"]
            ent.components[EntityIdentity] = EntityIdentity(
                entity_id=d["id"], name=d["name"], archetype=d["archetype"], 
                is_player=d.get("is_player", False), template_origin=d.get("template_origin")
            )
        
        if "item_identity" in data:
            d = data["item_identity"]
            ent.components[ItemIdentity] = ItemIdentity(entity_id=d["id"], name=d["name"], description=d["description"])

        if "position" in data:
            d = data["position"]
            ent.components[Position] = Position(x=d["x"], y=d["y"], terrain_type=d.get("terrain", "floor"))

        if "vitals" in data:
            d = data["vitals"]
            v = CombatVitals(hp=d["hp"], max_hp=d["max_hp"])
            v.is_dead = d.get("is_dead", False)
            ent.components[CombatVitals] = v

        if "stats" in data:
            d = data["stats"]
            ent.components[CombatStats] = CombatStats(attack_bonus=d["attack_bonus"], damage_bonus=d["damage_bonus"], defense_bonus=d["defense_bonus"])

        if "attributes" in data:
            ent.components[Attributes] = Attributes(scores=data["attributes"])

        if "faction" in data:
            ent.components[Faction] = Faction(faction_id=data["faction"]["id"])

        if "disposition" in data:
            d = data["disposition"]
            ent.components[Disposition] = Disposition(reputation=d["reputation"], last_gift_tick=d["last_gift_tick"])

        if "social_awareness" in data:
            d = data["social_awareness"]
            ent.components[SocialAwareness] = SocialAwareness(
                engagement_range=d["engagement_range"], 
                last_interaction_tick=d["last_interaction_tick"],
                is_proactive=d.get("is_proactive", False)
            )

        if "party_member" in data:
            ent.components[PartyMember] = PartyMember(leader_id=data["party_member"]["leader_id"])
            # Note: The 'InPartyWith' relation needs to be restored after all entities are loaded
            # if we want to link to the player object. 
            # For Phase 22, we'll handle this in a post-load pass if needed, 
            # but for now ai_decision_system just checks for the component.

        # Restore inventory
        if "inventory" in data:
            for idata in data["inventory"]:
                item = self._deserialize_entity(idata)
                ent.relation_tags_many["IsCarrying"].add(item)
                
        return ent

    
    def open_session(self) -> None:
        self.inscriber.open_session()

    def close_session(self) -> None:
        """Closes the current tracking session but does NOT write a spatial snapshot."""
        self.inscriber.close_session()

    def save_session(self, snapshot_path: Optional[Path] = None) -> None:
        """
        Saves the critical world state to JSON.
        """
        import json
        if snapshot_path is None:
            snapshot_path = Path("sessions/spatial_snapshot.json")
            
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare territory overrides
        t_overrides = {}
        if hasattr(self, "territory") and self.territory:
            for (cx, cy), node in self.territory.overrides.items():
                t_overrides[f"{cx}_{cy}"] = {"faction_id": node.faction_id, "poi_type": node.poi_type}

        # Prepare active entities (recursive)
        entities = []
        for entity in self.registry.Q.all_of(components=[Position]):
            # Skip items inside containers (they are serialized as part of the container)
            if any(entity in parent.relation_tags_many["IsCarrying"] for parent in self.registry.Q.all_of(relations=[("IsCarrying", ...)])):
                continue
            
            # Context Collapse: Cull ephemeral random encounters
            if EntityIdentity in entity.components:
                ident = entity.components[EntityIdentity]
                if not ident.is_player and ident.archetype in ["Skirmisher", "Minion"]:
                    continue
                
            entities.append(self._serialize_entity(entity))

        data = {
            "world": {
                "era": self.clock.era,
                "cycle": self.clock.cycle,
                "tick": self.clock.tick,
                "world_seed": self.world.world_seed
            },
            "faction_standing": self.faction_standing,
            "territory_overrides": t_overrides,
            "virtual_entities": {f"{k[0]}_{k[1]}": v for k, v in self.virtual_entities.items()},
            "exploration": self.exploration.get_state(),
            "entities": entities
        }
            
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
    def resume_session(self, snapshot_path: Optional[Path] = None) -> None:
        """Restores the world from a snapshot."""
        import json
        
        if snapshot_path is None:
            snapshot_path = Path("sessions/spatial_snapshot.json")
            
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Cannot resume, missing {snapshot_path}")
            
        with open(snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Restore world
        wdata = data.get("world", {})
        self.clock = GameTimestamp(era=wdata.get("era", "Recent"), cycle=wdata.get("cycle", 1), tick=wdata.get("tick", 1))
        self.inscriber.clock = self.clock
        _world_seed = wdata.get("world_seed", random.randint(1, 10000))
        self.territory = TerritoryManager(world_seed=_world_seed)
        
        # Restore territory overrides
        tdata = data.get("territory_overrides", {})
        for key, val in tdata.items():
            cx, cy = map(int, key.split("_"))
            faction_id = val["faction_id"]
            poi_type = val["poi_type"]
            node_id = f"node_{cx // TerritoryManager.MACRO_REGION_SIZE}_{cy // TerritoryManager.MACRO_REGION_SIZE}"
            self.territory.overrides[(cx, cy)] = TerritoryNode(
                id=node_id, chunk_x=cx, chunk_y=cy, poi_type=poi_type, faction_id=faction_id
            )
            
        self.world = ChunkManager(world_seed=_world_seed, territory=self.territory)
        
        # Restore virtual entities
        v_data = data.get("virtual_entities", {})
        self.virtual_entities = {}
        for key, ents in v_data.items():
            cx, cy = map(int, key.split("_"))
            self.virtual_entities[(cx, cy)] = ents
        
        # Restore Fog of War
        if "exploration" in data:
            self.exploration.load_state(data["exploration"])
        
        # Restore Faction Standings
        self.faction_standing = data.get("faction_standing", {})
        
        # Restore registry
        self.registry = tcod.ecs.Registry()
        for edata in data.get("entities", []):
            self._deserialize_entity(edata)
            
        self.open_session()

    def manage_entity_lifecycle(self, player_x: int, player_y: int) -> None:
        """
        JIT Materialization (Phase 21):
        - Dematerializes entities far from the player into virtual_entities.
        - Materializes chunks near the player from virtual_entities or spawner.
        """
        chunk_size = self.world.chunk_size
        px_chunk, py_chunk = player_x // chunk_size, player_y // chunk_size
        
        CULL_DISTANCE = 3 # chunks
        MATERIALIZATION_DISTANCE = 1 # chunks
        
        # 1. Dematerialization: Cull distant entities
        to_cull = []
        for entity in self.registry.Q.all_of(components=[Position, EntityIdentity]):
            ident = entity.components[EntityIdentity]
            if ident.is_player: continue
            
            pos = entity.components[Position]
            ex_chunk, ey_chunk = pos.x // chunk_size, pos.y // chunk_size
            
            dist = max(abs(ex_chunk - px_chunk), abs(ey_chunk - py_chunk))
            if dist >= CULL_DISTANCE:
                # Cull ephemeral random encounters without state
                # Context Collapse: Cull skirmishers/minions unless they have significant delta
                if ident.archetype in ["Skirmisher", "Minion"]:
                    # Only keep if they were damaged or have items
                    vitals = entity.components.get(CombatVitals)
                    has_delta = vitals and vitals.hp < vitals.max_hp
                    has_items = len(list(entity.relation_tags_many["IsCarrying"])) > 0
                    if not (has_delta or has_items):
                        to_cull.append((entity, None))
                        continue
                
                to_cull.append((entity, (ex_chunk, ey_chunk)))

        for entity, chunk_key in to_cull:
            if chunk_key:
                serialized = self._serialize_entity(entity)
                if chunk_key not in self.virtual_entities:
                    self.virtual_entities[chunk_key] = []
                self.virtual_entities[chunk_key].append(serialized)
            
            # Remove from active registry
            # We clear() to destroy the entity ID and components in this registry
            entity.clear()

        # 2. Materialization: Restore nearby chunks
        for dy in range(-MATERIALIZATION_DISTANCE, MATERIALIZATION_DISTANCE + 1):
            for dx in range(-MATERIALIZATION_DISTANCE, MATERIALIZATION_DISTANCE + 1):
                mx, my = px_chunk + dx, py_chunk + dy
                chunk = self.world.get_chunk(mx, my)
                
                # Check if we need to materialize
                # We use a flag 'is_materialized' in the chunk_data (temporary runtime state)
                if not chunk.get("is_materialized"):
                    # a) Restore from virtual registry
                    if (mx, my) in self.virtual_entities:
                        for edata in self.virtual_entities[(mx, my)]:
                            self._deserialize_entity(edata)
                        del self.virtual_entities[(mx, my)]
                    
                    # b) If never spawned, trigger initial spawn
                    elif not chunk.get("is_spawned"):
                        from engine.spawner import spawn_bespoke_chunk, spawn_wilderness_chunk
                        if chunk["terrain"] == "bespoke":
                            spawn_bespoke_chunk(self.registry, chunk)
                        else:
                            spawn_wilderness_chunk(self.registry, chunk)
                    
                    chunk["is_materialized"] = True

    def tick(self) -> None:
        """Advance the simulation by one engine tick."""
        self.clock = self.clock.advance_tick()
        self.inscriber.clock = self.clock

        # JIT Management (Phase 21)
        # Every 10 ticks, check lifecycle
        if self.clock.tick % 10 == 0:
            px, py = 0, 0
            for ent in self.registry.Q.all_of(components=[EntityIdentity, Position]):
                if ent.components[EntityIdentity].is_player:
                    px, py = ent.components[Position].x, ent.components[Position].y
                    break
            self.manage_entity_lifecycle(px, py)

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
        
        # JIT Materialization (Phase 21)
        if EntityIdentity in entity.components and entity.components[EntityIdentity].is_player:
            self.manage_entity_lifecycle(new_x, new_y)

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
