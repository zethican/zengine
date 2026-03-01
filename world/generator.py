"""
ZEngine — world/generator.py
Procedural Generation: Chunk-based open world with dynamic PoL resolution.
==========================================================================
Version:     0.2  (Phase 11 Step 3 — Bespoke Chunks)
Stack:       Python 3.14.3 | NumPy (limited)
Status:      Production-ready for Phase 11.
"""

from __future__ import annotations
import random
import tcod.noise
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from engine.data_loader import get_biome_defs, BiomeDef, get_module_defs, ModuleDef

class SettlementPlanner:
    """
    Assembles settlements from modular components.
    """
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.modules = get_module_defs()

    def plan_settlement(self, theme: str, chunk_size: int = 20) -> List[Tuple[ModuleDef, int, int]]:
        """
        Returns a list of (ModuleDef, x, y) placements for a settlement.
        """
        placements = []
        
        # 1. Select and place Heart
        # For now, we only have one heart 'tavern_heart'
        heart = self.modules.get("tavern_heart")
        if not heart: return []
        
        # Center-ish placement
        h_lines = heart.map.strip().split("\n")
        hw, hh = len(h_lines[0]), len(h_lines)
        hx = (chunk_size - hw) // 2
        hy = (chunk_size - hh) // 2
        placements.append((heart, hx, hy))
        
        # 2. Select and place Limbs (1-2)
        limb_ids = ["small_room", "garden_unit"]
        limb_count = self.rng.randint(1, 2)
        
        for _ in range(limb_count):
            lid = self.rng.choice(limb_ids)
            limb = self.modules.get(lid)
            if not limb: continue
            
            l_lines = limb.map.strip().split("\n")
            lw, lh = len(l_lines[0]), len(l_lines)
            
            # Try 10 times to find a non-overlapping spot near the heart
            for _ in range(10):
                # Jitter around heart
                nx = hx + self.rng.randint(-5, 5)
                ny = hy + self.rng.randint(-5, 5)
                
                # Bounding box check
                if 0 <= nx < chunk_size - lw and 0 <= ny < chunk_size - lh:
                    # Overlap check
                    overlap = False
                    for p_mod, px, py in placements:
                        p_lines = p_mod.map.strip().split("\n")
                        pw, ph = len(p_lines[0]), len(p_lines)
                        if self._rects_overlap(nx, ny, lw, lh, px, py, pw, ph):
                            overlap = True
                            break
                    
                    if not overlap:
                        placements.append((limb, nx, ny))
                        break
                        
        return placements

    def _rects_overlap(self, x1, y1, w1, h1, x2, y2, w2, h2) -> bool:
        return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)

class WorldBiomeEngine:
    """
    Uses global Simplex noise to determine regional biomes.
    """
    def __init__(self, seed: int):
        # Temperature Noise (Low frequency for broad regions)
        self.temp_noise = tcod.noise.Noise(
            dimensions=2,
            algorithm=tcod.noise.Algorithm.SIMPLEX,
            seed=seed
        )
        # Humidity Noise
        self.hum_noise = tcod.noise.Noise(
            dimensions=2,
            algorithm=tcod.noise.Algorithm.SIMPLEX,
            seed=seed + 12345
        )
        self.biomes = get_biome_defs()

    def get_biome(self, chunk_x: int, chunk_y: int) -> BiomeDef:
        """Determines the biome for a given chunk coordinate."""
        # Scale noise: broad regions span approx 20 chunks
        scale = 0.05
        t_val = (self.temp_noise.get_point(chunk_x * scale, chunk_y * scale) + 1.0) / 2.0
        h_val = (self.hum_noise.get_point(chunk_x * scale, chunk_y * scale) + 1.0) / 2.0
        
        # 1. Direct Range Matches
        for b in self.biomes:
            if b.id == "plains": continue # Default
            if (b.temp_range[0] <= t_val <= b.temp_range[1] and 
                b.hum_range[0] <= h_val <= b.hum_range[1]):
                return b
                
        # 2. Fallback to Plains
        for b in self.biomes:
            if b.id == "plains": return b
            
        return self.biomes[0] # Total fallback

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

from world.territory import TerritoryManager, TerritoryNode

class ChunkManager:
    """
    Manages the generation and caching of world chunks.
    """
    def __init__(self, world_seed: int, chunk_size: int = 20, territory: Optional[TerritoryManager] = None):
        self.world_seed = world_seed
        self.chunk_size = chunk_size
        self.territory = territory
        self.generated_chunks: Dict[ChunkKey, Dict[str, Any]] = {}
        self.rumor_queue: List[Rumor] = []
        self.bespoke_templates = [
            "cracked_spire", "wayfarers_hearth", "lithic_circle", 
            "smithy_refuse", "hermits_root", "hunters_lean_to"
        ]
        self.biome_engine = WorldBiomeEngine(world_seed)
        self.planner = SettlementPlanner(world_seed)

    def add_rumor(self, rumor: Rumor):
        """Add a pending point of light to the resolution queue."""
        self.rumor_queue.append(rumor)

    def get_next_rumor(self) -> Optional[Rumor]:
        """Pops the next available rumor from the queue."""
        if not self.rumor_queue:
            return None
        # Sort by significance
        self.rumor_queue.sort(key=lambda r: r.significance, reverse=True)
        return self.rumor_queue.pop(0)

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
        Implements Regional Blueprint using A Priori Topological Graphing (TerritoryManager).
        """
        # Create a deterministic seed for this specific chunk
        chunk_seed = hash((x, y, self.world_seed))
        rng = random.Random(chunk_seed)
        
        # Fetch Biome
        biome = self.biome_engine.get_biome(x, y)
        
        # Fetch Population
        from engine.data_loader import get_population_defs
        pop_defs = get_population_defs()
        biome_pop = pop_defs.biomes.get(biome.id, {}).get("entries", [])
        
        chunk_data = {
            "coords": (x, y),
            "biome": biome,
            "population": biome_pop,
            "pol": None,
            "terrain": "wilderness",
            "faction_id": None,
            "is_spawned": False
        }
        
        # Determine controlling faction from territory graph
        if self.territory:
            chunk_data["faction_id"] = self.territory.get_controlling_faction(x, y)
        else:
            chunk_data["faction_id"] = f"warband_{x}_{y}"
            
        # 1. Regional Blueprint (Points of Light via Territory Graph)
        territory_node = None
        if self.territory:
            territory_node = self.territory.get_node_at(x, y)
            
        # For legacy compatibility or testing without territory manager, fallback to stochastic
        poi_chunks = []
        if not self.territory:
            region_x = x // 4
            region_y = y // 4
            region_rng = random.Random(hash((region_x, region_y, self.world_seed)))
            poi_count = region_rng.randint(1, 2)
            for _ in range(poi_count):
                lx = region_rng.randint(0, 3)
                ly = region_rng.randint(0, 3)
                poi_chunks.append((region_x * 4 + lx, region_y * 4 + ly))
        
        is_poi = territory_node is not None or (not self.territory and (x, y) in poi_chunks)
            
        if is_poi:
            # Determine type
            poi_type = territory_node.poi_type if territory_node else "settlement"
            
            if poi_type == "settlement":
                chunk_data["terrain"] = "bespoke"
                if territory_node:
                    chunk_data["faction_id"] = territory_node.faction_id
                else:
                    anchor_x, anchor_y = poi_chunks[0]
                    chunk_data["faction_id"] = f"village_{anchor_x}_{anchor_y}"
                
                # Use SettlementPlanner to grow the area
                planned_modules = self.planner.plan_settlement("village", self.chunk_size)
                
                bespoke_tiles = {}
                spawns = []
                roads = []
                
                mid = self.chunk_size // 2
                
                for mdef, mx, my in planned_modules:
                    m_lines = mdef.map.strip().split("\n")
                    
                    # Stamp tiles
                    door_lx, door_ly = -1, -1
                    for ly, line in enumerate(m_lines):
                        for lx, char in enumerate(line):
                            tx, ty = mx + lx, my + ly
                            
                            ttype = "floor"
                            if char == "#": ttype = "wall"
                            elif char == "~": ttype = "water"
                            elif char == "+":
                                ttype = "floor"
                                door_lx, door_ly = tx, ty
                                spawns.append({"type": "door", "lx": tx, "ly": ty})
                            
                            bespoke_tiles[(tx, ty)] = ttype
                    
                    # Add spawns from module
                    for sdef in mdef.spawns:
                        s_copy = sdef.copy()
                        s_copy["lx"] += mx
                        s_copy["ly"] += my
                        spawns.append(s_copy)
                        
                    # Stitch: Road from Door to Center
                    if door_lx != -1:
                        # Simple L-path to center (mid, mid)
                        curr_x, curr_y = door_lx, door_ly
                        # 1. Horizontal to mid
                        step = 1 if mid > curr_x else -1
                        for rx in range(curr_x, mid + step, step):
                            roads.append((rx, curr_y))
                        # 2. Vertical to mid
                        step = 1 if mid > curr_y else -1
                        for ry in range(curr_y, mid + step, step):
                            roads.append((mid, ry))
    
                chunk_data["bespoke_tiles"] = bespoke_tiles
                chunk_data["spawns"] = spawns
                chunk_data["roads"] = roads
                return chunk_data
            elif poi_type == "dungeon":
                chunk_data["terrain"] = "structured_dungeon"
                dungeon_gen = BSPDungeonGenerator(width=40, height=40, seed=chunk_seed)
                chunk_data["dungeon_layout"] = dungeon_gen.generate()
                return chunk_data
            elif poi_type == "encampment":
                chunk_data["terrain"] = "wilderness" # Encampments are wilderness with specific spawns
                # Add a campfire in the middle
                chunk_data["bespoke_tiles"] = {(self.chunk_size//2, self.chunk_size//2): "floor"}
                chunk_data["spawns"] = [{"type": "prop", "id": "campfire", "lx": self.chunk_size//2, "ly": self.chunk_size//2}]
                chunk_data["roads"] = []
                return chunk_data

        # 2. Road Connectivity (Visual Breadcrumbs)
        # If adjacent to a POI chunk, 50% chance of a road cutting through center
        chunk_data["roads"] = [] # List of (lx, ly)
        
        # Check Neighbors
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            
            # Check if neighbor is POI
            is_neighbor_poi = False
            if self.territory:
                is_neighbor_poi = self.territory.get_node_at(nx, ny) is not None
            else:
                rn_x, rn_y = nx // 4, ny // 4
                rn_rng = random.Random(hash((rn_x, rn_y, self.world_seed)))
                pn_count = rn_rng.randint(1, 2)
                pn_chunks = []
                for _ in range(pn_count):
                    lnx = rn_rng.randint(0, 3)
                    lny = rn_rng.randint(0, 3)
                    pn_chunks.append((rn_x * 4 + lnx, rn_y * 4 + lny))
                is_neighbor_poi = (nx, ny) in pn_chunks
            
            if is_neighbor_poi and rng.random() < 0.5:
                # Add a road path from center to the edge of the neighbor
                mid = self.chunk_size // 2
                if dx == -1: # West
                    for lx in range(0, mid + 1): chunk_data["roads"].append((lx, mid))
                elif dx == 1: # East
                    for lx in range(mid, self.chunk_size): chunk_data["roads"].append((lx, mid))
                elif dy == -1: # North
                    for ly in range(0, mid + 1): chunk_data["roads"].append((mid, ly))
                elif dy == 1: # South
                    for ly in range(mid, self.chunk_size): chunk_data["roads"].append((mid, ly))

        # 3. Resolve rumors (for odd chunks or rare overrides)
        if self.rumor_queue and rng.random() < 0.1:
            self.rumor_queue.sort(key=lambda r: r.significance, reverse=True)
            resolved = self.rumor_queue.pop(0)
            chunk_data["pol"] = resolved
            chunk_data["terrain"] = f"structured_{resolved.pol_type}"
            
            if resolved.pol_type == "dungeon":
                dungeon_gen = BSPDungeonGenerator(width=40, height=40, seed=chunk_seed)
                chunk_data["dungeon_layout"] = dungeon_gen.generate()
            
        return chunk_data


    def get_tile(self, global_x: int, global_y: int) -> str:
        """Returns the specific string terrain type for a given coordinate."""
        chunk_x = global_x // self.chunk_size
        chunk_y = global_y // self.chunk_size
        chunk = self.get_chunk(chunk_x, chunk_y)
        
        # Local coordinates mapping within the chunk
        local_x = global_x % self.chunk_size
        local_y = global_y % self.chunk_size
        
        # Priority 1: Bespoke Tiles (Handcrafted)
        if chunk["terrain"] == "bespoke":
            bespoke = chunk.get("bespoke_tiles", {})
            if (local_x, local_y) in bespoke:
                return bespoke[(local_x, local_y)]
        
        # Priority 2: Dungeon Tiles
        if "dungeon_layout" in chunk:
            tiles = chunk["dungeon_layout"]["tiles"]
            if 0 <= local_y < len(tiles) and 0 <= local_x < len(tiles[0]):
                return tiles[local_y][local_x]
                
        # Priority 3: Roads
        if (local_x, local_y) in chunk.get("roads", []):
            return "floor" # Road is just a path
            
        # Priority 4: Biome-driven Procedural Wilderness
        biome = chunk["biome"]
        rng = random.Random(hash((global_x, global_y, self.world_seed)))
        roll = rng.random()
        
        if roll < biome.water_density: return "water"
        if roll < (biome.water_density + biome.tree_density): return "tree"
        if roll < (biome.water_density + biome.tree_density + biome.rubble_density): return "wall" # Rubble as wall
        if roll < (biome.water_density + biome.tree_density + biome.rubble_density + biome.grass_density): return "grass"
        
        return "floor" # Dirt/Floor fallback
