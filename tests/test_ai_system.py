import pytest
import numpy as np
import tcod.ecs
from engine.ai_system import InfluenceMapSystem
from engine.ecs.components import Position, Disposition, EntityIdentity, BehaviorProfile

def test_get_desire_map_weighting():
    registry = tcod.ecs.Registry()
    ai_sys = InfluenceMapSystem(width=10, height=10)
    
    # 1. Setup Enemy at (0,0) and Ally at (9,9)
    enemy = registry.new_entity()
    enemy.components[Position] = Position(x=0, y=0)
    enemy.components[Disposition] = Disposition(reputation=-1.0)
    
    ally = registry.new_entity()
    ally.components[Position] = Position(x=9, y=9)
    ally.components[Disposition] = Disposition(reputation=1.0)
    
    ai_sys.update(registry, center_x=5, center_y=5)
    
    # 2. Aggressive Profile: Attracted to threat, ignores affinity
    aggro = BehaviorProfile(threat_weight=1.0, affinity_weight=0.0)
    # wait, in my get_desire_map logic:
    # t_heat = (1.0 - self.threat_map) * profile.threat_weight
    # Higher is better. So threat_weight=1.0 means attracted to threat seeds.
    
    d_map_aggro = ai_sys.get_desire_map(aggro)
    assert d_map_aggro[0, 0] > d_map_aggro[9, 9] # Hotter at enemy
    
    # 3. Friendly Profile: Ignores threat, attracted to affinity
    friendly = BehaviorProfile(threat_weight=0.0, affinity_weight=1.0)
    d_map_friendly = ai_sys.get_desire_map(friendly)
    assert d_map_friendly[9, 9] > d_map_friendly[0, 0] # Hotter at ally

def test_influence_map_generation():
    registry = tcod.ecs.Registry()
    ai_sys = InfluenceMapSystem(width=10, height=10)
    
    # 1. Setup Enemy
    enemy = registry.new_entity()
    enemy.components[Position] = Position(x=5, y=5)
    enemy.components[Disposition] = Disposition(reputation=-1.0)
    
    # 2. Update AI
    ai_sys.update(registry, center_x=5, center_y=5)
    
    # center_x=5, center_y=5 with 10x10 means off_x=0, off_y=0
    
    # Check threat at enemy pos (should be 0.0)
    assert ai_sys.get_value("threat", 5, 5) == 0.0
    
    # Check threat further away (should be > 0.0)
    assert ai_sys.get_value("threat", 0, 0) > 0.0
    assert ai_sys.get_value("threat", 0, 0) <= 1.0

def test_influence_map_normalization():
    registry = tcod.ecs.Registry()
    ai_sys = InfluenceMapSystem(width=10, height=10)
    
    # Two enemies at far ends
    e1 = registry.new_entity()
    e1.components[Position] = Position(x=0, y=0)
    e1.components[Disposition] = Disposition(reputation=-1.0)
    
    e2 = registry.new_entity()
    e2.components[Position] = Position(x=9, y=9)
    e2.components[Disposition] = Disposition(reputation=-1.0)
    
    ai_sys.update(registry, center_x=5, center_y=5)
    
    assert ai_sys.get_value("threat", 0, 0) == 0.0
    assert ai_sys.get_value("threat", 9, 9) == 0.0
    
    # Middle 5,5 is approx distance 5 (Chebyshev distance)
    # The max distance in 10x10 between 0,0 and 9,9 is 9.
    
    val_mid = ai_sys.get_value("threat", 5, 5)
    
    assert 0.0 < val_mid < 1.0
    # Distance from 0,0 to 5,5 is 5. Distance from 9,9 to 5,5 is 4.
    # Min dist is 4. 4/9 = 0.444
    assert 0.4 < val_mid < 0.5
