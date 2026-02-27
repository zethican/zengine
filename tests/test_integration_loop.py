"""
ZEngine — tests/test_integration_loop.py
Testing the Phase 2 full simulation loop.
"""

import pytest
import tempfile
from pathlib import Path

from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, CombatVitals, CombatStats, ActionEconomy, MovementStats
from world.generator import Rumor

def test_full_encounter_loop():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # 1. Gen: Initialize ChunkManager and seed entities.
        from engine.data_loader import get_starting_rumors
        rumors = get_starting_rumors()
        for r_def in rumors:
            sim.world.add_rumor(Rumor(r_def.id, r_def.name, r_def.pol_type, r_def.significance))
        
        from engine.data_loader import get_entity_def
        hero_def = get_entity_def("hero_standard")
        
        hero = sim.registry.new_entity()
        hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name=hero_def.name, archetype=hero_def.archetype, is_player=True)
        hero.components[Position] = Position(x=0, y=0)
        hero.components[CombatVitals] = CombatVitals(hp=hero_def.hp, max_hp=hero_def.hp)
        hero.components[CombatStats] = CombatStats(attack_bonus=5, damage_bonus=2)
        hero.components[ActionEconomy] = ActionEconomy()
        hero.components[MovementStats] = MovementStats(speed=hero_def.speed)
        
        from world.wilderness import FoeFactory
        foe = FoeFactory.create_skirmisher(sim.registry, x=2, y=0, level=1)
        
        sim.open_session()
        
        # 2. Explore: Move entity into a new chunk.
        sim.move_entity_ecs(hero, dx=20, dy=0)
        assert hero.components[Position].x == 20
        # If it triggers Rumor resolution, terrain will be structured_dungeon
        # (Though it's a 10% chance so not guaranteed, we just assert it doesn't crash)
        
        # Fast-forward until hero has AP
        while hero.components[ActionEconomy].ap_pool < 50:
            sim.tick()
        
        # 3. Combat: Trigger an attack action.
        sim.resolve_attack_ecs(hero, foe)
        
        # Foe likely tool damage.
        foe_vitals = foe.components[CombatVitals]
        # Depending on roll, foe might be damaged (95% chance to hit DC 8 with +5 bonus)
        
        # Let's forcefully kill the foe to trigger a Social Spike
        sim.apply_damage_ecs(foe, 100)
        
        # 4. Social Spike: Assert SocialStateSystem reacts to the combat event.
        # FoeFactory uses the TOML name "Cave Skirmisher L1" or similar
        foe_name = foe.components[EntityIdentity].name
        stress = sim.social_system.get_stress(foe_name)
        assert stress > 0.0 # Stress spike on damage and death
        
        sim.close_session()
        
        # 5. Chronicle Inscribe: Verify that the encounter produced a log
        from engine.chronicle import ChronicleReader
        reader = ChronicleReader(chronicle_path)
        entries = reader.all_entries()
        
        assert len(entries) >= 2 # At least session opened/closed, plus likely attack and death
        
        has_attack = any(e["payload"].get("event_type") == "combat.action_resolved" for e in entries)
        has_death = any(e["payload"].get("event_type") == "combat.on_death" for e in entries)
        
        assert has_attack or has_death, "Chronicle should record combat events"


def test_encounter_density_spawning():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        sim.open_session()
        
        # Write some fake deaths to chronicle to simulate a "legacy" zone
        from engine.combat import CombatEvent, EVT_ON_DEATH
        for i in range(5):
            sim.bus.emit(CombatEvent(
                event_key=EVT_ON_DEATH,
                source=f"Legacy_Actor_{i}",
                data={"final_hp": 0}
            ))
            
        sim.close_session()
        
        # Now simulate entering a node and calling the spawn system
        from world.wilderness import encounter_spawn_system
        from engine.chronicle import ChronicleReader
        
        reader = ChronicleReader(chronicle_path)
        spawn_count = encounter_spawn_system(
            registry=sim.registry,
            chronicle_reader=reader,
            chunk_coords=(10, 10),
            node_vitality=1.0, # Baseline vitality
            bus=sim.bus
        )
        
        # With 5 deaths (significance 3 each by default), density score should be high.
        # Should spawn 2-5 enemies.
        assert spawn_count >= 2, f"Expected higher spawn count in legacy zone, got {spawn_count}"
        
        # Verify entities were actually created in the ECS
        from engine.ecs.components import EntityIdentity
        foes = []
        for entity in sim.registry.Q.all_of(tags=[], components=[EntityIdentity]):
            id_comp = entity.components[EntityIdentity]
            if not id_comp.is_player:
                foes.append(entity)
                
        assert len(foes) == spawn_count, "ECS should contain the spawned foes"


def test_session_save_and_resume():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        snapshot_path = Path(tmpdir) / "spatial_snapshot.toml"
        
        sim1 = SimulationLoop(chronicle_path=chronicle_path)
        sim1.world.world_seed = 9999
        sim1.clock = sim1.clock.advance_tick() # tick = 2
        
        # Add player
        hero = sim1.registry.new_entity()
        from engine.ecs.components import EntityIdentity, Position, CombatVitals, CombatStats, ActionEconomy, MovementStats
        hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        hero.components[Position] = Position(x=10, y=10)
        hero.components[CombatVitals] = CombatVitals(hp=30, max_hp=30)
        hero.components[CombatStats] = CombatStats(attack_bonus=5, damage_bonus=2)
        hero.components[ActionEconomy] = ActionEconomy()
        hero.components[MovementStats] = MovementStats(speed=10.0)
        
        # Add ephemeral foe (should be culled)
        foe = sim1.registry.new_entity()
        foe.components[EntityIdentity] = EntityIdentity(entity_id=2, name="Crawler", archetype="Skirmisher", is_player=False)
        foe.components[Position] = Position(x=11, y=10)
        foe.components[CombatVitals] = CombatVitals(hp=10, max_hp=10)
        foe.components[CombatStats] = CombatStats(defense_bonus=-2)
        foe.components[ActionEconomy] = ActionEconomy()
        foe.components[MovementStats] = MovementStats(speed=8.0)
        
        sim1.open_session()
        sim1.save_session(snapshot_path)
        sim1.close_session()
        
        # Start a fresh engine instance
        sim2 = SimulationLoop(chronicle_path=chronicle_path)
        sim2.resume_session(snapshot_path)
        
        assert sim2.world.world_seed == 9999
        assert sim2.clock.tick == 2
        
        # Validate that context collapsed the ephemeral foe and kept the hero
        entities = list(sim2.registry.Q.all_of(components=[EntityIdentity]))
        assert len(entities) == 1
        
        hero2 = entities[0]
        ident = hero2.components[EntityIdentity]
        assert ident.name == "Aric"
        assert ident.is_player is True
        
        pos = hero2.components[Position]
        assert pos.x == 10 and pos.y == 10
        
        vitals = hero2.components[CombatVitals]
        assert vitals.hp == 30
        
        sim2.close_session()
