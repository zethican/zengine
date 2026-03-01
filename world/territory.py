"""
ZEngine — world/territory.py
TerritoryManager: A Priori Topological Graphing for Phase 20.
Defines deterministic nodes (POIs) and regional faction control across an infinite world.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
import random

@dataclass
class TerritoryNode:
    id: str
    chunk_x: int
    chunk_y: int
    poi_type: str # "settlement", "dungeon", "encampment"
    faction_id: str

class TerritoryManager:
    MACRO_REGION_SIZE = 8 # A macro-region is an 8x8 grid of chunks

    def __init__(self, world_seed: int):
        self.world_seed = world_seed
        self.rng = random.Random(world_seed)
        
        # Determine the global factions for this world
        self.factions = [f"faction_{i}" for i in range(1, 6)] # 5 active factions
        
        # Overrides for persistent changes (e.g. chunk captures)
        # Key: (chunk_x, chunk_y)
        self.overrides: Dict[Tuple[int, int], TerritoryNode] = {}

    def _generate_node_for_region(self, mx: int, my: int) -> TerritoryNode:
        """Deterministically generates the single node for a macro-region."""
        region_rng = random.Random(hash((self.world_seed, "macro_region", mx, my)))
        
        # Place node somewhere in the central 4x4 of the 8x8 region
        cx = (mx * self.MACRO_REGION_SIZE) + region_rng.randint(2, 5)
        cy = (my * self.MACRO_REGION_SIZE) + region_rng.randint(2, 5)
        
        poi_type = region_rng.choices(
            ["settlement", "dungeon", "encampment"],
            weights=[0.3, 0.4, 0.3],
            k=1
        )[0]
        
        faction_id = region_rng.choice(self.factions)
        
        node_id = f"node_{mx}_{my}"
        return TerritoryNode(id=node_id, chunk_x=cx, chunk_y=cy, poi_type=poi_type, faction_id=faction_id)

    def get_node_at(self, cx: int, cy: int) -> Optional[TerritoryNode]:
        """Returns a TerritoryNode if the given chunk is the center of a POI."""
        if (cx, cy) in self.overrides:
            return self.overrides[(cx, cy)]
            
        mx = cx // self.MACRO_REGION_SIZE
        my = cy // self.MACRO_REGION_SIZE
        
        node = self._generate_node_for_region(mx, my)
        if node.chunk_x == cx and node.chunk_y == cy:
            return node
            
        return None

    def get_controlling_faction(self, cx: int, cy: int) -> str:
        """Returns the faction that controls the macro-region the chunk is in."""
        mx = cx // self.MACRO_REGION_SIZE
        my = cy // self.MACRO_REGION_SIZE
        node = self._generate_node_for_region(mx, my)
        
        # Check if the node's faction was overridden
        override = self.overrides.get((node.chunk_x, node.chunk_y))
        if override:
            return override.faction_id
            
        return node.faction_id

    def capture_node(self, cx: int, cy: int, new_faction_id: str) -> bool:
        """Changes the controlling faction of a node. Returns True if successful."""
        node = self.get_node_at(cx, cy)
        if not node:
            return False
            
        # Create override
        new_node = TerritoryNode(
            id=node.id, 
            chunk_x=node.chunk_x, 
            chunk_y=node.chunk_y, 
            poi_type=node.poi_type, 
            faction_id=new_faction_id
        )
        self.overrides[(cx, cy)] = new_node
        return True
