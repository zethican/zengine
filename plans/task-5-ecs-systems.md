# Task 5: ECS System Migration Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate combat and movement logic from monolithic classes into formal ECS systems in `engine/ecs/systems.py`.

**Architecture:** Pure function-based ECS systems that operate on `tcod.ecs.Registry` and emit events to `EventBus`.

**Tech Stack:** Python 3.14.3, python-tcod-ecs.

---

### Task 5.1: Turn Resolution System
**Files:**
- Create: `engine/ecs/systems.py`
- Test: `tests/test_ecs_systems.py`

**Step 1: Write failing test for turn resolution**
```python
import tcod.ecs
import pytest
from engine.ecs.components import ActionEconomy, MovementStats
from engine.ecs.systems import turn_resolution_system

def test_turn_resolution():
    registry = tcod.ecs.Registry()
    actor = registry.new_entity()
    actor.components[ActionEconomy] = ActionEconomy(action_energy=0.0)
    actor.components[MovementStats] = MovementStats(speed=10.0)
    
    turn_resolution_system(registry)
    assert actor.components[ActionEconomy].action_energy == 10.0
```

**Step 2: Implement turn_resolution_system**
- Query: `all_of=[ActionEconomy, MovementStats]`.
- Increment `action_energy` by `speed`.

**Step 3: Verify and Commit**
- `py -m pytest tests/test_ecs_systems.py`
- `git commit -m "feat: implement ECS turn resolution system"`

### Task 5.2: Action Economy Reset System
**Files:**
- Modify: `engine/ecs/systems.py`
- Test: `tests/test_ecs_systems.py`

**Step 1: Write failing test for AP reset**
```python
from engine.combat import EventBus, EVT_TURN_STARTED, ENERGY_THRESHOLD

def test_ap_reset_on_energy_threshold():
    registry = tcod.ecs.Registry()
    bus = EventBus()
    actor = registry.new_entity()
    actor.components[ActionEconomy] = ActionEconomy(action_energy=ENERGY_THRESHOLD, ap_pool=0)
    
    # Track event
    events = []
    bus.subscribe(EVT_TURN_STARTED, lambda e: events.append(e))
    
    from engine.ecs.systems import action_economy_reset_system
    action_economy_reset_system(registry, bus)
    
    assert actor.components[ActionEconomy].ap_pool == 100
    assert len(events) == 1
```

**Step 2: Implement action_economy_reset_system**
- Reset `ap_pool` to 100 and emit `EVT_TURN_STARTED` for eligible actors.

**Step 3: Verify and Commit**
- `py -m pytest tests/test_ecs_systems.py`
- `git commit -m "feat: implement ECS action economy reset system"`

### Task 5.3: Action Resolution (Attack) System
**Files:**
- Modify: `engine/ecs/systems.py`
- Test: `tests/test_ecs_systems.py`

**Step 1: Implement attack logic**
- Support `action_type="attack"`.
- Deduct 50 AP.
- Emit `EVT_ACTION_RESOLVED`.

**Step 2: Verify and Commit**
- `py -m pytest tests/test_ecs_systems.py`
- `git commit -m "feat: implement ECS attack resolution system"`
