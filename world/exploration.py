"""
ZEngine — world/exploration.py
ExplorationManager: Persistent visibility and Fog of War for Phase 23.
Tracks seen tiles across an infinite world.
"""

from typing import Set, Tuple, List, Dict, Any

class ExplorationManager:
    def __init__(self):
        # A set of (world_x, world_y) coordinates that have been explored.
        self.explored_tiles: Set[Tuple[int, int]] = set()

    def mark_explored(self, x: int, y: int) -> None:
        """Marks a specific world coordinate as explored."""
        self.explored_tiles.add((x, y))

    def is_explored(self, x: int, y: int) -> bool:
        """Returns True if the coordinate has been explored."""
        return (x, y) in self.explored_tiles

    def get_state(self) -> Dict[str, Any]:
        """Returns serializable state for snapshots."""
        # Convert set of tuples to list of strings "x_y" for JSON efficiency
        return {
            "tiles": [f"{x}_{y}" for x, y in self.explored_tiles]
        }

    def load_state(self, data: Dict[str, Any]) -> None:
        """Restores state from serializable data."""
        self.explored_tiles = set()
        for tile_str in data.get("tiles", []):
            try:
                x, y = map(int, tile_str.split("_"))
                self.explored_tiles.add((x, y))
            except (ValueError, AttributeError):
                continue
