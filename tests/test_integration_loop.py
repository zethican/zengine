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
        sim.world.add_rumor(Rumor("r1", "Obsidian Keep", "dungeon", significance=5))
        
        hero = sim.registry.new_entity()
        hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        hero.components[Position] = Position(x=0, y=0)
        hero.components[CombatVitals] = CombatVitals(hp=30, max_hp=30)
        hero.components[CombatStats] = CombatStats(attack_bonus=5, damage_bonus=2)
        hero.components[ActionEconomy] = ActionEconomy()
        hero.components[MovementStats] = MovementStats(speed=10.0)
        
        foe = sim.registry.new_entity()
        foe.components[EntityIdentity] = EntityIdentity(entity_id=2, name="Crawler", archetype="Skirmisher", is_player=False)
        foe.components[CombatVitals] = CombatVitals(hp=10, max_hp=10)
        foe.components[CombatStats] = CombatStats(defense_bonus=-2) # Easy to hit
        foe.components[ActionEconomy] = ActionEconomy()
        foe.components[MovementStats] = MovementStats(speed=8.0)
        
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
        stress = sim.social_system.get_stress("Crawler")
        assert stress > 0.0 # Stress spike on damage and death
        
        sim.close_session()
        
        # 5. Chronicle Inscribe: Verify that the encounter produced a log
        from engine.chronicle import ChronicleReader
        reader = ChronicleReader(chronicle_path)
        entries = reader.all_entries()
        
        assert len(entries) >= 2 # At least session opened/closed, plus likely attack and death
        
        has_attack = any(e["payload"]["event_type"] == "combat.action_resolved" for e in entries)
        has_death = any(e["payload"]["event_type"] == "combat.on_death" for e in entries)
        
        assert has_attack or has_death, "Chronicle should record combat events"
