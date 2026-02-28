"""
ZEngine — engine/data_loader.py
JIT Data Loaders for TOML seed data powered by Pydantic.
=============================================================================================
Version:     0.3 (Phase 18 — Procedural Affixes)
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

class EffectDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    effect_type: str # "damage", "heal", "apply_modifier", "move"
    target_pattern: str # "self", "primary_target", "adjacent", "adjacent_all"
    magnitude: str = "0" # e.g. "1d8 + @might_mod"
    tags: List[str] = Field(default_factory=list)
    # Fields for modifier application
    modifier_id: Optional[str] = None
    duration: Optional[int] = None

class AbilityDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    tags: List[str] = Field(default_factory=list)
    ap_cost: int
    target_type: str # UI primary target: "self", "single", "direction"
    effects: List[EffectDef] = Field(default_factory=list)

class EntityDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    id: str
    name: str
    hp: int
    speed: float
    archetype: str
    abilities: List[str]
    attributes: Dict[str, int] = Field(default_factory=dict)
    inventory: List[str] = Field(default_factory=list)
    dialogue: Optional[Dict[str, Any]] = None

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
    value: int = 10
    equippable: Optional[Dict[str, str]] = None
    modifiers: List[Dict[str, Any]] = Field(default_factory=list)
    item_stats: Optional[Dict[str, int]] = None
    tags: Dict[str, bool] = Field(default_factory=dict)
    stackable: Optional[Dict[str, int]] = None
    usable: Optional[Dict[str, Any]] = None

class RecipeDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    part_a_tag: str
    part_b_tag: str
    result_template: str

class AttributeDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    abbreviation: str
    description: str

class AttributeCollectionDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    attributes: List[AttributeDef]

class ChunkTemplateDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    description: str
    map: str
    spawns: List[Dict[str, Any]] = Field(default_factory=list)

class BiomeDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    description: str
    temp_range: List[float]
    hum_range: List[float]
    tree_density: float = 0.0
    grass_density: float = 0.0
    water_density: float = 0.0
    rubble_density: float = 0.0
    colors: Dict[str, List[int]] = Field(default_factory=dict)
    ambient_modifiers: List[Dict[str, Any]] = Field(default_factory=list)

class BiomeCollectionDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    biomes: List[BiomeDef]

class PopulationEntryDef(BaseModel):
    id: str
    weight: int

class PopulationDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    biomes: Dict[str, Dict[str, List[PopulationEntryDef]]]

class ModuleDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    map: str
    spawns: List[Dict[str, Any]] = Field(default_factory=dict)

class FactionDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    description: str
    base_standing: float = 0.0

class AffixDef(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    type: str # "prefix" or "suffix"
    eligible_tags: List[str]
    weight: int = 10
    item_stats: Optional[Dict[str, int]] = None
    modifiers: List[Dict[str, Any]] = Field(default_factory=list)

# ================================================================================
# LOADERS & CACHE (JIT)
# ================================================================================

_ABILITY_CACHE: Dict[str, AbilityDef] = {}
_ENTITY_CACHE: Dict[str, EntityDef] = {}
_RUMORS_CACHE: Optional[RumorCollectionDef] = None
_ITEM_CACHE: Dict[str, ItemDef] = {}
_RECIPE_CACHE: Optional[List[RecipeDef]] = None
_ATTRIBUTE_CACHE: Optional[List[AttributeDef]] = None
_CHUNK_TEMPLATE_CACHE: Dict[str, ChunkTemplateDef] = {}
_BIOME_CACHE: Optional[List[BiomeDef]] = None
_POPULATION_CACHE: Optional[PopulationDef] = None
_MODULE_CACHE: Dict[str, ModuleDef] = {}
_AFFIX_CACHE: Optional[List[AffixDef]] = None


DATA_DIR = Path(__file__).parent.parent / "data"

def get_ability_def(ability_id: str) -> AbilityDef:
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

def get_attribute_defs() -> List[AttributeDef]:
    """Loads attribute definitions from TOML. Cached globally."""
    global _ATTRIBUTE_CACHE
    if _ATTRIBUTE_CACHE is not None:
        return _ATTRIBUTE_CACHE
        
    path = DATA_DIR / "attributes.toml"
    if not path.exists():
        return []
        
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    collection = AttributeCollectionDef(**data)
    _ATTRIBUTE_CACHE = collection.attributes
    return _ATTRIBUTE_CACHE

def get_chunk_template(template_id: str) -> ChunkTemplateDef:
    """JIT loads a chunk template (bespoke area) from TOML."""
    if template_id in _CHUNK_TEMPLATE_CACHE:
        return _CHUNK_TEMPLATE_CACHE[template_id]
        
    path = DATA_DIR / "world" / "chunks" / f"{template_id}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Chunk template not found: {path}")
        
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    tmpl = ChunkTemplateDef(**data)
    _CHUNK_TEMPLATE_CACHE[template_id] = tmpl
    return tmpl

def get_biome_defs() -> List[BiomeDef]:
    """Loads all biome definitions from TOML. Cached globally."""
    global _BIOME_CACHE
    if _BIOME_CACHE is not None:
        return _BIOME_CACHE
        
    path = DATA_DIR / "biomes.toml"
    if not path.exists():
        return []
        
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    collection = BiomeCollectionDef(**data)
    _BIOME_CACHE = collection.biomes
    return _BIOME_CACHE

def get_population_defs() -> PopulationDef:
    """Loads all biome population tables from TOML. Cached globally."""
    global _POPULATION_CACHE
    if _POPULATION_CACHE is not None:
        return _POPULATION_CACHE
        
    path = DATA_DIR / "population.toml"
    if not path.exists():
        return PopulationDef(biomes={})
        
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    _POPULATION_CACHE = PopulationDef(**data)
    return _POPULATION_CACHE

def get_module_def(module_id: str) -> ModuleDef:
    """JIT loads a settlement component module from TOML."""
    if module_id in _MODULE_CACHE:
        return _MODULE_CACHE[module_id]
        
    path = DATA_DIR / "world" / "modules" / f"{module_id}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Module definition not found: {path}")
        
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    mdef = ModuleDef(**data)
    _MODULE_CACHE[module_id] = mdef
    return mdef

def get_module_defs() -> Dict[str, ModuleDef]:
    """Pre-loads all module definitions. Useful for the planner."""
    path = DATA_DIR / "world" / "modules"
    if not path.exists():
        return {}
        
    for file in path.glob("*.toml"):
        mid = file.stem
        if mid not in _MODULE_CACHE:
            get_module_def(mid)
            
    return _MODULE_CACHE

def get_affixes() -> List[AffixDef]:
    """Loads all item affixes from TOML. Cached globally."""
    global _AFFIX_CACHE
    if _AFFIX_CACHE is not None:
        return _AFFIX_CACHE
        
    _AFFIX_CACHE = []
    path = DATA_DIR / "items" / "affixes"
    if not path.exists():
        return []
        
    for file in path.glob("*.toml"):
        with open(file, "rb") as f:
            data = tomllib.load(f)
            _AFFIX_CACHE.append(AffixDef(**data))
            
    return _AFFIX_CACHE
