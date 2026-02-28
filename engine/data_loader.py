"""
ZEngine — engine/data_loader.py
JIT Data Loaders for TOML seed data powered by Pydantic.
=============================================================================================
Version:     0.1 (Phase 4)
Stack:       Python 3.14.3 | Pydantic v2 | tomllib
Status:      Core data validation and loading layer.
"""

import tomllib
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

# ================================================================================
# SCHEMAS
# ================================================================================

class AbilityDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    id: str
    name: str
    ap_cost: int
    damage_die: int
    damage_bonus: int
    target_type: str

class EntityDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    id: str
    name: str
    hp: int
    speed: float
    archetype: str
    abilities: List[str]

class RumorDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    id: str
    name: str
    pol_type: str
    significance: int
    biome_requirement: Optional[str] = None

class RumorCollectionDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    rumors: List[RumorDef]

class ItemDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    description: str
    equippable: Optional[Dict[str, str]] = None
    item_stats: Optional[Dict[str, int]] = None
    tags: Dict[str, bool] = Field(default_factory=dict)
    stackable: Optional[Dict[str, int]] = None

class RecipeDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    part_a_tag: str
    part_b_tag: str
    result_template: str

# ================================================================================
# LOADERS & CACHE (JIT)
# ================================================================================

_ABILITY_CACHE: Dict[str, AbilityDef] = {}
_ENTITY_CACHE: Dict[str, EntityDef] = {}
_RUMORS_CACHE: Optional[RumorCollectionDef] = None
_ITEM_CACHE: Dict[str, ItemDef] = {}
_RECIPE_CACHE: Optional[List[RecipeDef]] = None

DATA_DIR = Path(__file__).parent.parent / "data"

def get_ability_def(ability_id: str) -> AbilityDef:
    # ... rest of file ...
    """JIT loads an ability definition from TOML."""
    if ability_id in _ABILITY_CACHE:
        return _ABILITY_CACHE[ability_id]
        
    path = DATA_DIR / "abilities" / f"{ability_id}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Ability definition not found: {path}")
        
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    ability = AbilityDef(**data)
    _ABILITY_CACHE[ability_id] = ability
    return ability

def get_entity_def(entity_id: str) -> EntityDef:
    """JIT loads an entity definition from TOML."""
    if entity_id in _ENTITY_CACHE:
        return _ENTITY_CACHE[entity_id]
        
    path = DATA_DIR / "entities" / f"{entity_id}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Entity definition not found: {path}")
        
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    entity = EntityDef(**data)
    _ENTITY_CACHE[entity_id] = entity
    return entity

def get_starting_rumors() -> List[RumorDef]:
    """Loads world starting rumors. Cached globally."""
    global _RUMORS_CACHE
    if _RUMORS_CACHE is not None:
        return _RUMORS_CACHE.rumors
        
    path = DATA_DIR / "world" / "starting_rumors.toml"
    if not path.exists():
        return []
        
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    _RUMORS_CACHE = RumorCollectionDef(**data)
    return _RUMORS_CACHE.rumors

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

def get_recipes() -> List[RecipeDef]:
    """Loads all item recipes from TOML. Cached globally."""
    global _RECIPE_CACHE
    if _RECIPE_CACHE is not None:
        return _RECIPE_CACHE
        
    _RECIPE_CACHE = []
    path = DATA_DIR / "recipes"
    if not path.exists():
        return []
        
    for file in path.glob("*.toml"):
        with open(file, "rb") as f:
            data = tomllib.load(f)
            _RECIPE_CACHE.append(RecipeDef(**data))
            
    return _RECIPE_CACHE
