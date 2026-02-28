import pytest
import tcod.ecs
import tempfile
from pathlib import Path
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, ActiveModifiers, Attributes, CombatStats
from engine.ecs.systems import get_effective_stats, get_attr_mod

def test_terrain_modifiers():
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
        player.components[Position] = Position(x=0, y=0, terrain_type="floor")
        
        sim.open_session()
        
        # 1. Move to water
        player.components[Position].terrain_type = "water"
        sim.tick()
        
        # Modifier should be applied: env_wet
        assert ActiveModifiers in player.components
        effects = player.components[ActiveModifiers].effects
        assert any(e.id == "env_wet" for e in effects)
        
        # 2. Move back to floor
        player.components[Position].terrain_type = "floor"
        sim.tick()
        
        # Since env_wet has duration 1, it should be removed in the NEXT tick's decay phase
        # Tick N: Decay -> nothing. Apply water (dur 1).
        # Tick N+1: Decay (dur 1 -> 0, removed). Apply floor (nothing).
        assert not any(e.id == "env_wet" for e in player.components[ActiveModifiers].effects)

def test_biome_ambient_modifiers():
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        # Search exhaustively for a wasteland chunk
        cx, cy = -1, -1
        for y in range(20):
            for x in range(20):
                c = sim.world.get_chunk(x, y)
                if c["biome"].id == "wasteland":
                    cx, cy = x, y
                    break
            if cx != -1: break
            
        if cx == -1:
            pytest.skip("Could not find wasteland chunk in 20x20 area for this seed.")
        
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
        player.components[Attributes] = Attributes(scores={"resolve": 10})
        player.components[Position] = Position(x=cx * 20 + 5, y=cy * 20 + 5)
        
        sim.open_session()
        sim.tick()
        
        # Resolve should be reduced by 2 due to "Bleakness"
        # 10 - 2 = 8
        # Mod = (8 - 10) // 2 = -1
        assert get_attr_mod(player, "resolve") == -1
        
        sim.close_session()

def test_sticky_modifiers():
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
        player.components[Position] = Position(x=0, y=0, terrain_type="mud") # Mud has duration 10
        
        sim.open_session()
        sim.tick() # Tick 1: Apply (duration 10)
        
        # Verify modifier applied
        assert any(e.id == "env_muddy" for e in player.components[ActiveModifiers].effects)
        
        # Move to floor
        player.components[Position].terrain_type = "floor"
        sim.tick() # Tick 2: Decay (10 -> 9). Apply floor (nothing).
        
        # Should still be present
        assert any(e.id == "env_muddy" for e in player.components[ActiveModifiers].effects)
        assert player.components[ActiveModifiers].effects[0].duration == 9
        
        sim.close_session()
