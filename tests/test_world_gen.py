import pytest
import tcod.ecs
from world.generator import ChunkManager
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, ItemIdentity
import tempfile
from pathlib import Path

def test_bespoke_chunk_modular_assembly():
    manager = ChunkManager(world_seed=123)
    
    # Find a bespoke chunk
    target_chunk = None
    for y in range(24):
        for x in range(24):
            c = manager.get_chunk(x, y)
            if c["terrain"] == "bespoke":
                target_chunk = c
                break
        if target_chunk: break
        
    assert target_chunk is not None
    assert "bespoke_tiles" in target_chunk
    assert "roads" in target_chunk
    
    # Check that it contains at least the tavern heart
    # (Since our current planner always seeds it)
    found_wall = False
    for ttype in target_chunk["bespoke_tiles"].values():
        if ttype == "wall":
            found_wall = True
            break
    assert found_wall is True
    
    # Verify roads list is populated
    assert len(target_chunk["roads"]) > 0

def test_bespoke_chunk_multiple_modules():
    # Use a specific seed known to produce limbs
    manager = ChunkManager(world_seed=10101)
    
    # Force check several chunks to find one with limbs
    found_limbs = False
    for y in range(24):
        for x in range(24):
            c = manager.get_chunk(x, y)
            if c["terrain"] == "bespoke":
                # Check for spawns from limbs
                # tavern_heart has Innkeeper
                # small_room has Footlocker
                # garden_unit has wooden_plank
                names = [s.get("name", "") for s in c["spawns"]]
                ids = [s.get("id", "") for s in c["spawns"]]
                if "Footlocker" in names or "materials/wooden_plank" in ids:
                    found_limbs = True
                    break
        if found_limbs: break
        
    assert found_limbs is True, "Could not find a settlement with multiple modules using seed 10101"

def test_bespoke_chunk_spawning_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # 1. Setup Player
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
        player.components[Position] = Position(x=0, y=0)
        
        sim.open_session()
        
        # 2. Find a bespoke chunk nearby (search in 8x8 macro region)
        target_chunk = None
        for y in range(40):
            for x in range(40):
                c = sim.world.get_chunk(x, y)
                if c["terrain"] == "bespoke":
                    target_chunk = c
                    break
            if target_chunk: break
            
        assert target_chunk is not None
        cx, cy = target_chunk["coords"]
        gx, gy = cx * 20 + 10, cy * 20 + 10
        
        # 3. Teleport player and manually trigger spawner (since move_entity_ecs is 1-tile at a time)
        from engine.spawner import spawn_bespoke_chunk
        player.components[Position] = Position(x=gx, y=gy)
        spawn_bespoke_chunk(sim.registry, target_chunk)
        
        # 4. Check for spawned entities
        found_bespoke = False
        for ent in sim.registry.Q.all_of(components=[Position]):
            if ent == player: continue
            pos = ent.components[Position]
            if cx * 20 <= pos.x < (cx + 1) * 20 and cy * 20 <= pos.y < (cy + 1) * 20:
                found_bespoke = True
                break
        
        assert found_bespoke is True
        sim.close_session()
