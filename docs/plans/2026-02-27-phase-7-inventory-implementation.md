# Phase 7: Inventory and Items Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a data-driven Inventory and Item system using ECS entities and relationship tags.

**Architecture:** Items are full ECS entities linked to actors via `IsCarrying` and `IsEquipped` relations. An `ItemFactory` handles TOML-based instantiation, and specialized systems manage item state transitions (pickup, drop, equip) while maintaining "Power of 10" safety rules.

**Tech Stack:** Python 3.14.3, python-tcod-ecs, Pydantic v2, tomllib.

---

### Task 1: Define Item Components

**Files:**
- Modify: `engine/ecs/components.py`
- Test: `tests/test_ecs_core.py`

**Step 1: Write the failing test**

```python
# tests/test_ecs_core.py
from engine.ecs.components import ItemIdentity, Equippable

def test_item_components_exist():
    ident = ItemIdentity(entity_id=1, name="Test Item", archetype="Item")
    equip = Equippable(slot_type="hand")
    assert ident.name == "Test Item"
    assert equip.slot_type == "hand"
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_ecs_core.py`
Expected: FAIL with `ImportError: cannot import name 'ItemIdentity'`

**Step 3: Write minimal implementation**

```python
# engine/ecs/components.py (append)
@dataclass
class ItemIdentity:
    entity_id: str
    name: str
    description: str
    template_origin: Optional[str] = None

@dataclass
class Quantity:
    amount: int = 1
    max_stack: int = 1

@dataclass
class Equippable:
    slot_type: str  # "head", "hand", "torso", etc.

@dataclass
class ItemStats:
    attack_bonus: int = 0
    damage_bonus: int = 0
    protection: int = 0

@dataclass
class Anatomy:
    available_slots: List[str] = field(default_factory=lambda: ["hand", "hand", "torso", "head"])

@dataclass
class Lineage:
    parent_ids: List[str] = field(default_factory=list)
    inherited_tags: List[str] = field(default_factory=list)
```

**Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_ecs_core.py`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/ecs/components.py tests/test_ecs_core.py
git commit -m "feat: add inventory and item ECS components"
```

---

### Task 2: Define Item Data Schemas and Loader

**Files:**
- Modify: `engine/data_loader.py`
- Create: `data/items/weapons/iron_sword.toml`
- Test: `tests/test_data_loader.py`

**Step 1: Write the failing test**

```python
# tests/test_data_loader.py
from engine.data_loader import get_item_def

def test_load_item_def():
    item = get_item_def("weapons/iron_sword")
    assert item.name == "Iron Sword"
    assert item.equippable["slot"] == "hand"
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_data_loader.py`
Expected: FAIL with `ImportError: cannot import name 'get_item_def'`

**Step 3: Create Sample Item TOML**

```toml
# data/items/weapons/iron_sword.toml
id = "iron_sword"
name = "Iron Sword"
description = "A standard-issue blade, notched but reliable."

[equippable]
slot = "hand"

[item_stats]
attack_bonus = 2
damage_bonus = 3

[tags]
is_sword = true
is_metallic = true
```

**Step 4: Write implementation**

```python
# engine/data_loader.py

class ItemDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    description: str
    equippable: Optional[Dict[str, str]] = None
    item_stats: Optional[Dict[str, int]] = None
    tags: Dict[str, bool] = Field(default_factory=dict)
    stackable: Optional[Dict[str, int]] = None

_ITEM_CACHE: Dict[str, ItemDef] = {}

def get_item_def(item_path: str) -> ItemDef:
    """JIT loads an item definition from TOML (e.g. 'weapons/iron_sword')."""
    if item_path in _ITEM_CACHE:
        return _ITEM_CACHE[item_path]
        
    path = DATA_DIR / "items" / f"{item_path}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Item definition not found: {path}")
        
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    item = ItemDef(**data)
    _ITEM_CACHE[item_path] = item
    return item
```

**Step 5: Run test to verify it passes**

Run: `py -m pytest tests/test_data_loader.py`
Expected: PASS

**Step 6: Commit**

```bash
git add engine/data_loader.py data/items/weapons/iron_sword.toml tests/test_data_loader.py
git commit -m "feat: add item data schema and JIT loader"
```

---

### Task 3: Implement Item Factory

**Files:**
- Create: `engine/item_factory.py`
- Test: `tests/test_inventory.py`

**Step 1: Write the failing test**

```python
# tests/test_inventory.py
import tcod.ecs
from engine.item_factory import create_item

def test_create_item_entity():
    registry = tcod.ecs.Registry()
    item_entity = create_item(registry, "weapons/iron_sword")
    from engine.ecs.components import ItemIdentity
    assert ItemIdentity in item_entity.components
    assert item_entity.components[ItemIdentity].name == "Iron Sword"
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_inventory.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.item_factory'`

**Step 3: Write implementation**

```python
# engine/item_factory.py
from typing import Optional
import tcod.ecs
from engine.data_loader import get_item_def
from engine.ecs.components import ItemIdentity, Equippable, ItemStats, Quantity

def create_item(registry: tcod.ecs.Registry, item_path: str) -> tcod.ecs.Entity:
    """Instantiates an item entity from a TOML blueprint."""
    item_def = get_item_def(item_path)
    entity = registry.new_entity()
    
    # 1. Identity
    entity.components[ItemIdentity] = ItemIdentity(
        entity_id=item_def.id,
        name=item_def.name,
        description=item_def.description,
        template_origin=item_path
    )
    
    # 2. Equippable
    if item_def.equippable:
        entity.components[Equippable] = Equippable(slot_type=item_def.equippable["slot"])
        
    # 3. Stats
    if item_def.item_stats:
        entity.components[ItemStats] = ItemStats(**item_def.item_stats)
        
    # 4. Quantity (if stackable)
    if item_def.stackable:
        entity.components[Quantity] = Quantity(
            amount=1, 
            max_stack=item_def.stackable.get("max", 1)
        )
        
    # 5. Tags
    for tag, value in item_def.tags.items():
        if value:
            entity.tags.add(tag)
            
    return entity
```

**Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_inventory.py`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/item_factory.py tests/test_inventory.py
git commit -m "feat: implement ItemFactory for TOML-based instantiation"
```

---

### Task 4: Implement Inventory State Transitions (Systems)

**Files:**
- Modify: `engine/ecs/systems.py`
- Test: `tests/test_inventory.py`

**Step 1: Write failing tests for Pickup/Drop**

```python
# tests/test_inventory.py
from engine.ecs.systems import pickup_item_system, drop_item_system
from engine.ecs.components import Position

def test_pickup_item_removes_position():
    registry = tcod.ecs.Registry()
    actor = registry.new_entity()
    actor.components[Position] = Position(1, 1)
    
    item = registry.new_entity()
    item.components[Position] = Position(1, 1)
    
    pickup_item_system(actor, item)
    
    assert Position not in item.components
    assert item in actor.relation_tags_many["IsCarrying"]
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_inventory.py`
Expected: FAIL with `ImportError: cannot import name 'pickup_item_system'`

**Step 3: Write implementation**

```python
# engine/ecs/systems.py

def pickup_item_system(actor: tcod.ecs.Entity, item: tcod.ecs.Entity) -> bool:
    """Moves item from Floor (Position) to Inventory (IsCarrying relation)."""
    if Position not in actor.components or Position not in item.components:
        return False
        
    actor_pos = actor.components[Position]
    item_pos = item.components[Position]
    
    if (actor_pos.x, actor_pos.y) != (item_pos.x, item_pos.y):
        return False # Too far away
        
    # Atomic transaction
    del item.components[Position]
    actor.relation_tags_many["IsCarrying"].add(item)
    return True

def drop_item_system(actor: tcod.ecs.Entity, item: tcod.ecs.Entity) -> bool:
    """Moves item from Inventory (IsCarrying) to Floor (Position)."""
    if item not in actor.relation_tags_many["IsCarrying"]:
        return False
        
    if Position not in actor.components:
        return False
        
    actor_pos = actor.components[Position]
    
    # Atomic transaction
    actor.relation_tags_many["IsCarrying"].remove(item)
    if item in actor.relation_tags_many["IsEquipped"]:
        actor.relation_tags_many["IsEquipped"].remove(item)
        
    item.components[Position] = Position(x=actor_pos.x, y=actor_pos.y)
    return True

def equip_item_system(actor: tcod.ecs.Entity, item: tcod.ecs.Entity) -> bool:
    """Equips an item if it's carried and a slot is available in Anatomy."""
    from engine.ecs.components import Anatomy, Equippable
    if item not in actor.relation_tags_many["IsCarrying"]:
        return False
    if Anatomy not in actor.components or Equippable not in item.components:
        return False
        
    anatomy = actor.components[Anatomy]
    item_equip = item.components[Equippable]
    
    # Count currently equipped items in this slot type
    equipped_in_slot = 0
    for e_item in actor.relation_tags_many["IsEquipped"]:
        if Equippable in e_item.components and e_item.components[Equippable].slot_type == item_equip.slot_type:
            equipped_in_slot += 1
            
    # Check anatomy limit
    max_slots = anatomy.available_slots.count(item_equip.slot_type)
    if equipped_in_slot >= max_slots:
        return False # Slot occupied
        
    actor.relation_tags_many["IsEquipped"].add(item)
    return True
```

**Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_inventory.py`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/ecs/systems.py tests/test_inventory.py
git commit -m "feat: implement Pickup, Drop, and Equip ECS systems"
```

---

### Task 5: Integration with Action Resolution

**Files:**
- Modify: `engine/ecs/systems.py`
- Test: `tests/test_integration_loop.py`

**Step 1: Write integration test**

```python
# tests/test_integration_loop.py
def test_action_resolution_pickup():
    # Setup registry, actor, item at same pos
    # call action_resolution_system(..., action_type="pickup", ...)
    # verify item is carried
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_integration_loop.py`
Expected: FAIL (pickup action not handled)

**Step 3: Update `action_resolution_system`**

```python
# engine/ecs/systems.py:action_resolution_system

    # ... inside action_resolution_system ...
    
    if action_type == "pickup":
        target_entity = action_payload.get("target_entity")
        if not target_entity: return False
        success = pickup_item_system(entity, target_entity)
        if success:
            bus.emit(CombatEvent(EVT_ACTION_RESOLVED, source=source_name, data={"action_type": "pickup"}))
        return success
    
    elif action_type == "equip":
        target_entity = action_payload.get("target_entity")
        if not target_entity: return False
        success = equip_item_system(entity, target_entity)
        if success:
            bus.emit(CombatEvent(EVT_ACTION_RESOLVED, source=source_name, data={"action_type": "equip"}))
        return success
```

**Step 4: Run tests**

Run: `py -m pytest tests/test_integration_loop.py`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/ecs/systems.py tests/test_integration_loop.py
git commit -m "feat: integrate inventory actions into CombatEngine"
```
