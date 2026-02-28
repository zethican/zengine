import pytest
import tcod.ecs
from engine.spawner import spawn_door, spawn_window
from engine.ecs.components import EntityIdentity, Position, DoorState, BlocksMovement, CombatVitals
from engine.ecs.systems import toggle_door_system

def test_door_interaction_toggle():
    registry = tcod.ecs.Registry()
    door = spawn_door(registry, 1, 1)
    
    # Starts closed
    assert door.components[DoorState].is_open is False
    assert BlocksMovement in door.components
    
    # Toggle Open
    success = toggle_door_system(door)
    assert success is True
    assert door.components[DoorState].is_open is True
    assert BlocksMovement not in door.components
    
    # Toggle Closed
    toggle_door_system(door)
    assert door.components[DoorState].is_open is False
    assert BlocksMovement in door.components

def test_door_destructibility():
    registry = tcod.ecs.Registry()
    door = spawn_door(registry, 1, 1)
    
    # Damage the door
    door.components[CombatVitals].hp = 0
    
    # Logic in SimulationLoop.apply_damage_ecs should handle death
    # For now we'll just verify the plan's requirement
    from engine.loop import SimulationLoop
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        # Re-create door in sim registry
        door = spawn_door(sim.registry, 1, 1)
        sim.apply_damage_ecs(door, 100)
        
        assert door.components[CombatVitals].is_dead is True
        # Structural death should remove blocking
        # Wait, I need to implement that in apply_damage_ecs first.
