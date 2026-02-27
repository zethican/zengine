"""
ZEngine — world/generator.py
Procedural Generation: Chunk-based open world with dynamic PoL resolution.
==========================================================================
Version:     0.1  (Phase 2 — canonical implementation)
Stack:       Python 3.14.3 | NumPy (limited)
Status:      Production-ready for Phase 2.

Architecture notes
------------------
- Lazy-loaded chunking (20x20 tiles).
- Deterministic RNG based on chunk coordinates and world seed.
- Rumor Layer: Pending Points of Light (PoLs) resolve on entry.
- PoL Hierarchy: Significance -> Biome -> Rarity.
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

@dataclass(frozen=True)
class ChunkKey:
    x: int
    y: int

@dataclass
class Rumor:
    id: str
    name: str
    pol_type: str # "dungeon" | "prefab" | "encampment"
    significance: int # 1-5
    biome_requirement: Optional[str] = None

@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

class BSPNode:
    def __init__(self, rect: Rect):
        self.rect = rect
        self.left: Optional[BSPNode] = None
        self.right: Optional[BSPNode] = None
        self.room: Optional[Rect] = None

    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

class BSPDungeonGenerator:
    """
    Phase 3 BSP dungeon generation.
    Splits space into a tree, carves rooms in leaves, and connects them.
    """
    def __init__(self, width: int, height: int, seed: int, min_room_size: int = 6):
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        self.min_room_size = min_room_size
        self.tiles = [["wall" for _ in range(self.width)] for _ in range(self.height)]
        self.rooms: List[Rect] = []
        
    def _split(self, node: BSPNode, iterations: int) -> None:
        if iterations == 0:
            return
            
        rect = node.rect
        split_horizontal = self.rng.choice([True, False])
        if rect.w > 1.25 * rect.h:
            split_horizontal = False
        elif rect.h > 1.25 * rect.w:
            split_horizontal = True
            
        max_split = (rect.h if split_horizontal else rect.w) - self.min_room_size
        if max_split <= self.min_room_size:
            return # Too small to split
            
        split = self.rng.randint(self.min_room_size, max_split)
        
        if split_horizontal:
            node.left = BSPNode(Rect(rect.x, rect.y, rect.w, split))
            node.right = BSPNode(Rect(rect.x, rect.y + split, rect.w, rect.h - split))
        else:
            node.left = BSPNode(Rect(rect.x, rect.y, split, rect.h))
            node.right = BSPNode(Rect(rect.x + split, rect.y, rect.w - split, rect.h))
            
        self._split(node.left, iterations - 1)
        self._split(node.right, iterations - 1)

    def _create_rooms(self, node: BSPNode) -> None:
        if node.is_leaf():
            pad_x = self.rng.randint(1, 2)
            pad_y = self.rng.randint(1, 2)
            
            w = max(3, node.rect.w - 2 * pad_x)
            h = max(3, node.rect.h - 2 * pad_y)
            
            # Ensure valid placement
            x_range = node.rect.w - w - 1
            y_range = node.rect.h - h - 1
            
            x = node.rect.x + (self.rng.randint(1, x_range) if x_range > 1 else 1)
            y = node.rect.y + (self.rng.randint(1, y_range) if y_range > 1 else 1)
            
            node.room = Rect(x, y, w, h)
            self.rooms.append(node.room)
            
            for cy in range(node.room.y, node.room.y + node.room.h):
                for cx in range(node.room.x, node.room.x + node.room.w):
                    if 0 <= cx < self.width and 0 <= cy < self.height:
                        self.tiles[cy][cx] = "floor"
        else:
            if node.left: self._create_rooms(node.left)
            if node.right: self._create_rooms(node.right)

    def _connect_rooms(self, node: BSPNode) -> Optional[Rect]:
        if node.is_leaf():
            return node.room
            
        left_room = self._connect_rooms(node.left) if node.left else None
        right_room = self._connect_rooms(node.right) if node.right else None
        
        if left_room and right_room:
            lx = left_room.x + left_room.w // 2
            ly = left_room.y + left_room.h // 2
            rx = right_room.x + right_room.w // 2
            ry = right_room.y + right_room.h // 2
            
            if self.rng.choice([True, False]):
                self._carve_h_corridor(lx, rx, ly)
                self._carve_v_corridor(ly, ry, rx)
            else:
                self._carve_v_corridor(ly, ry, lx)
                self._carve_h_corridor(lx, rx, ry)
                
            return self.rng.choice([left_room, right_room])
        
        return left_room or right_room

    def _carve_h_corridor(self, x1: int, x2: int, y: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.tiles[y][x] = "floor"

    def _carve_v_corridor(self, y1: int, y2: int, x: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.tiles[y][x] = "floor"

    def generate(self) -> Dict[str, Any]:
        """Runs the BSP algorithm and returns the dungeon layout."""
        root = BSPNode(Rect(0, 0, self.width, self.height))
        self._split(root, 4)
        self._create_rooms(root)
        self._connect_rooms(root)
        
        return {
            "type": "dungeon",
            "rooms": [{"x": r.x, "y": r.y, "w": r.w, "h": r.h} for r in self.rooms],
            "tiles": self.tiles
        }

class ChunkManager:
    """
    Manages the generation and caching of world chunks.
    """
    def __init__(self, world_seed: int, chunk_size: int = 20):
        self.world_seed = world_seed
        self.chunk_size = chunk_size
        self.generated_chunks: Dict[ChunkKey, Dict[str, Any]] = {}
        self.rumor_queue: List[Rumor] = []

    def add_rumor(self, rumor: Rumor):
        """Add a pending point of light to the resolution queue."""
        self.rumor_queue.append(rumor)

    def get_chunk(self, chunk_x: int, chunk_y: int) -> Dict[str, Any]:
        """Retrieve or generate a chunk at the given coordinates."""
        key = ChunkKey(chunk_x, chunk_y)
        if key not in self.generated_chunks:
            self.generated_chunks[key] = self._generate_chunk(chunk_x, chunk_y)
        return self.generated_chunks[key]

    def _generate_chunk(self, x: int, y: int) -> Dict[str, Any]:
        """
        Deterministic generation logic.
        Resolves rumors if conditions are met.
        """
        # Create a deterministic seed for this specific chunk
        chunk_seed = hash((x, y, self.world_seed))
        rng = random.Random(chunk_seed)
        
        chunk_data = {
            "coords": (x, y),
            "pol": None,
            "terrain": "wilderness"
        }
        
        # Resolve rumors
        # Logic: 10% chance to resolve a rumor if one is pending
        if self.rumor_queue and rng.random() < 0.1:
            # Simple priority: Significance -> First in queue
            self.rumor_queue.sort(key=lambda r: r.significance, reverse=True)
            resolved = self.rumor_queue.pop(0)
            chunk_data["pol"] = resolved
            chunk_data["terrain"] = f"structured_{resolved.pol_type}"
            
            # Phase 3 stub wiring
            if resolved.pol_type == "dungeon":
                dungeon_gen = BSPDungeonGenerator(width=40, height=40, seed=chunk_seed)
                chunk_data["dungeon_layout"] = dungeon_gen.generate()
            
        return chunk_data

# ============================================================
# SMOKE TEST
# ============================================================

if __name__ == "__main__":
    print("--- World Generator Smoke Test ---")
    manager = ChunkManager(world_seed=12345)
    
    # Add some rumors
    manager.add_rumor(Rumor("r1", "Obsidian Keep", "dungeon", significance=5))
    manager.add_rumor(Rumor("r2", "Old Shrine", "prefab", significance=3))
    
    print(f"Pending Rumors: {len(manager.rumor_queue)}")
    
    # "Explore" a few chunks
    for cx in range(5):
        for cy in range(5):
            chunk = manager.get_chunk(cx, cy)
            if chunk["pol"]:
                print(f"Resolved PoL at ({cx}, {cy}): {chunk['pol'].name} ({chunk['pol'].pol_type})")
                
    print(f"Pending Rumors remaining: {len(manager.rumor_queue)}")
    
    # Test consistency
    c1 = manager.get_chunk(0, 0)
    # Clear cache and regenerate
    manager.generated_chunks.clear()
    c2 = manager.get_chunk(0, 0)
    
    assert c1["terrain"] == c2["terrain"]
    print("✅ Generation consistency verified.")
