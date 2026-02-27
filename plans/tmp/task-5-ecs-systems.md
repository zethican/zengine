# Task 5: ECS System Migration Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate turn and action logic into formal ECS systems.

**Architecture:** Pure functions in `engine/ecs/systems.py` operating on a `tcod.ecs.Registry`.

---

### Task 5.1: Turn Resolution System
**Files:**
- Create: `engine/ecs/systems.py`
- Test: `tests/test_ecs_systems.py`

**Step 1: Write failing test**
```python
def test_turn_resolution():
    registry = tcod.ecs.Registry()
    actor = registry.new_entity([ActionEconomy(action_energy=0.0), MovementStats(speed=10.0)])
    turn_resolution_system(registry)
    assert actor.components[ActionEconomy].action_energy == 10.0
```

**Step 2: Implement `turn_resolution_system`**
```python
def turn_resolution_system(registry):
    for entity in registry.Q.all_of(components=[ActionEconomy, MovementStats]):
        entity.components[ActionEconomy].action_energy += entity.components[MovementStats].speed
```

**Step 3: Verify and Commit**
- Run `pytest tests/test_ecs_systems.py`
- `git commit -m "feat: implement ECS turn resolution system"`
