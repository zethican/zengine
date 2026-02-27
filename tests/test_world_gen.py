import pytest
from world.generator import ChunkManager, Rumor

def test_chunk_caching():
    manager = ChunkManager(world_seed=42)
    c1 = manager.get_chunk(0, 0)
    c2 = manager.get_chunk(0, 0)
    
    # Same object reference from cache
    assert c1 is c2

def test_generation_consistency():
    # Use same seed, different managers
    m1 = ChunkManager(world_seed=100)
    m2 = ChunkManager(world_seed=100)
    
    c1 = m1.get_chunk(5, 5)
    c2 = m2.get_chunk(5, 5)
    
    assert c1["coords"] == c2["coords"]
    assert c1["terrain"] == c2["terrain"]

def test_rumor_resolution_priority():
    manager = ChunkManager(world_seed=1)
    # Add low sig rumor
    manager.add_rumor(Rumor("r1", "Camp", "encampment", significance=1))
    # Add high sig rumor
    manager.add_rumor(Rumor("r2", "Keep", "dungeon", significance=5))
    
    # Force a resolution by finding a chunk that triggers it 
    # (or just test that if one resolves, it's the high significance one)
    # Since RNG is deterministic per chunk, we find one that triggers resolution
    found_pol = None
    for x in range(20):
        for y in range(20):
            chunk = manager.get_chunk(x, y)
            if chunk["pol"]:
                found_pol = chunk["pol"]
                break
        if found_pol: break
        
    assert found_pol is not None
    assert found_pol.name == "Keep" # Significance 5 prioritized over 1
