"""
ZEngine — tests/test_bsp_generator.py
Tests for the procedural BSP dungeon generator.
"""

from world.generator import BSPDungeonGenerator, Rect

def test_bsp_generator_bounds():
    gen = BSPDungeonGenerator(width=40, height=40, seed=123)
    layout = gen.generate()
    
    # Check return structure
    assert layout["type"] == "dungeon"
    assert "rooms" in layout
    assert "tiles" in layout
    
    # Check tile dimensions
    tiles = layout["tiles"]
    assert len(tiles) == 40
    assert all(len(row) == 40 for row in tiles)
    
    # Check that rooms are within bounds
    for room in layout["rooms"]:
        assert room["x"] >= 0
        assert room["y"] >= 0
        assert room["x"] + room["w"] <= 40
        assert room["y"] + room["h"] <= 40

def test_bsp_generator_determinism():
    gen1 = BSPDungeonGenerator(width=50, height=50, seed=456)
    layout1 = gen1.generate()
    
    gen2 = BSPDungeonGenerator(width=50, height=50, seed=456)
    layout2 = gen2.generate()
    
    assert layout1["rooms"] == layout2["rooms"], "Rooms should be identical for same seed"
    assert layout1["tiles"] == layout2["tiles"], "Tiles should be identical for same seed"

def test_bsp_generator_different_seeds():
    gen1 = BSPDungeonGenerator(width=50, height=50, seed=789)
    layout1 = gen1.generate()
    
    gen2 = BSPDungeonGenerator(width=50, height=50, seed=987)
    layout2 = gen2.generate()
    
    assert layout1["tiles"] != layout2["tiles"], "Different seeds should produce different tiles"
    
def test_bsp_rooms_have_floor():
    gen = BSPDungeonGenerator(width=30, height=30, seed=111)
    layout = gen.generate()
    tiles = layout["tiles"]
    
    for room in layout["rooms"]:
        # Sample middle of the room
        mx = room["x"] + room["w"] // 2
        my = room["y"] + room["h"] // 2
        assert tiles[my][mx] == "floor", "Room interiors should be floor tiles"
