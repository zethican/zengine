"""
ZEngine — engine/ai_system.py
Influence Map System: Global Dijkstra-based heatmaps for tactical and social AI.
================================================================================
Version:     0.1  (Phase 10)
Stack:       Python 3.14.3 | NumPy | tcod.path
Status:      Experimental.
"""

from __future__ import annotations
import numpy as np
import tcod.path
import tcod.ecs
from typing import Dict, List, Tuple, Optional
from engine.ecs.components import Position, EntityIdentity, Disposition, Stress, CombatVitals

class InfluenceMapSystem:
    """
    Generates global tactical and social layers.
    Maps are 0.0 (hottest/seed) to 1.0 (coldest).
    """
    def __init__(self, width: int = 60, height: int = 60):
        self.width = width
        self.height = height
        self.off_x = 0
        self.off_y = 0
        
        # Manual Seeds (cleared each update)
        self._manual_affinity_seeds: List[Tuple[int, int]] = []
        
        # Layers
# ... (rest of method) ...
    def add_affinity_seed(self, global_x: int, global_y: int, weight: float = 1.0):
        """Manually adds a seed to the affinity layer (cleared after update)."""
        # We'll just store the global coords and map them during update
        self._manual_affinity_seeds.append((global_y, global_x))

    def update(self, registry: tcod.ecs.Registry, center_x: int, center_y: int, viewer: Optional[tcod.ecs.Entity] = None):
        """Recomputes all global layers based on current entity positions and states."""
        self.off_x = center_x - self.width // 2
        self.off_y = center_y - self.height // 2

        # 1. Gather Seeds
        threat_seeds = []
        affinity_seeds = []
        
        # Add Manual Seeds
        for gy, gx in self._manual_affinity_seeds:
            lx, ly = gx - self.off_x, gy - self.off_y
            if 0 <= lx < self.width and 0 <= ly < self.height:
                affinity_seeds.append((ly, lx))
        self._manual_affinity_seeds.clear() # Clear for next cycle
        
        for entity in registry.Q.all_of(components=[Position]):
            if entity == viewer:
                continue
                
            pos = entity.components[Position]
            lx, ly = pos.x - self.off_x, pos.y - self.off_y
            
            if not (0 <= lx < self.width and 0 <= ly < self.height):
                continue
                
            # Social seeds
            if Disposition in entity.components:
                disp = entity.components[Disposition]
                if disp.reputation < -0.3:
                    threat_seeds.append((ly, lx)) # NumPy uses (y, x)
                elif disp.reputation > 0.4:
                    affinity_seeds.append((ly, lx))

        # 2. Compute Dijkstra Layers
        self.threat_map = self._compute_normalized_dijkstra(threat_seeds)
        self.affinity_map = self._compute_normalized_dijkstra(affinity_seeds)
        
        # Urgency layer: combination of being away from threats and near health/safety
        # For MVP: Urgency is attracted to allies and repulsed by threats
        # Actually, let's just make it "Safety" (away from threats)
        self.urgency_map = 1.0 - self.threat_map # 0.0 at seeds, so 1.0 is far away

    def _compute_normalized_dijkstra(self, seeds: List[Tuple[int, int]]) -> np.ndarray:
        # Create distance array pre-filled with high values
        dist = np.full((self.height, self.width), 1000000, dtype=np.int32)
        
        if not seeds:
            return np.ones((self.height, self.width), dtype=np.float32)
            
        # Set seed points to 0
        for y, x in seeds:
            if 0 <= y < self.height and 0 <= x < self.width:
                dist[y, x] = 0
            
        # Cost map: uniform cost for now (1)
        cost = np.ones((self.height, self.width), dtype=np.int32)
        
        # Compute Dijkstra
        tcod.path.dijkstra2d(dist, cost, cardinal=1, diagonal=1, out=dist)
        
        # Normalize
        reachable = dist < 1000000
        if not np.any(reachable):
            return np.ones((self.height, self.width), dtype=np.float32)
            
        max_val = np.max(dist[reachable])
        if max_val == 0: max_val = 1.0
        
        # Clamp unreachable to max_val
        dist[~reachable] = max_val
        
        normalized = dist.astype(np.float32) / max_val
        return normalized

    def get_value(self, layer: str, global_x: int, global_y: int) -> float:
        """Helper to sample a layer at global coordinates."""
        lx, ly = global_x - self.off_x, global_y - self.off_y
        if 0 <= lx < self.width and 0 <= ly < self.height:
            if layer == "threat": return self.threat_map[ly, lx]
            if layer == "affinity": return self.affinity_map[ly, lx]
            if layer == "urgency": return self.urgency_map[ly, lx]
        return 1.0

    def get_desire_map(self, profile: BehaviorProfile) -> np.ndarray:
        """Sums global layers based on profile weights to create a personal desire map."""
        # Layer Convention: 0.0 at seed, 1.0 at max distance.
        # (1.0 - layer) gives 1.0 at seed, 0.0 at far.
        # Positive weight: Attracted to seed.
        # Negative weight: Repulsed from seed.
        
        t_desire = (1.0 - self.threat_map) * profile.threat_weight
        a_desire = (1.0 - self.affinity_map) * profile.affinity_weight
        u_desire = (1.0 - self.urgency_map) * profile.urgency_weight
        
        return t_desire + a_desire + u_desire
