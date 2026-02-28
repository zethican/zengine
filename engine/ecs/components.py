"""
ZEngine — engine/ecs/components.py
ECS Component Definitions for python-tcod-ecs.
==============================================
Version:     0.1  (Phase 2 — canonical implementation)
Stack:       Python 3.14.3 | python-tcod-ecs
Status:      Production-ready for Phase 2.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

@dataclass
class EntityIdentity:
    entity_id: int
    name: str
    archetype: str                          # "Brute" | "Standard" | "Skirmisher" | "NPC" | "Legacy"
    is_player: bool = False
    legacy_actor_id: Optional[int] = None
    template_origin: Optional[str] = None

@dataclass
class Position:
    x: int
    y: int
    terrain_type: str = "floor"

@dataclass
class MovementStats:
    speed: float = 10.0
    movement_ap_cost: int = 10
    can_occupy_terrain: List[str] = field(default_factory=lambda: ["floor"])

@dataclass
class CombatVitals:
    hp: int
    max_hp: int
    is_dead: bool = False

@dataclass
class ActionEconomy:
    action_energy: float = 0.0
    ap_pool: int = 100
    ap_spent_this_turn: int = 0
    turn_number: int = 0

@dataclass
class CombatStats:
    attack_bonus: int = 0
    defense_bonus: int = 0
    damage_bonus: int = 0

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
