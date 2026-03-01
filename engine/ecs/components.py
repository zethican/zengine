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
    value: int = 10

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
    modifiers: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class Anatomy:
    available_slots: List[str] = field(default_factory=lambda: ["hand", "hand", "torso", "head"])

@dataclass
class Lineage:
    parent_ids: List[str] = field(default_factory=list)
    inherited_tags: List[str] = field(default_factory=list)

@dataclass
class Usable:
    ability_id: str
    consumes: bool = True

@dataclass
class Disposition:
    reputation: float = 0.0
    moral_weight: float = 0.5
    resilience: float = 1.0
    baseline_mood: str = "neutral"
    last_gift_tick: int = -1000

@dataclass
class Stress:
    stress_level: float = 0.0
    exodus_risk: float = 0.0

@dataclass
class BehaviorProfile:
    threat_weight: float = 1.0   # Positive = repulse, Negative = attract
    affinity_weight: float = 0.0 # Positive = attract
    urgency_weight: float = 0.0  # Positive = attract to safety/items

@dataclass
class PendingAction:
    action_type: str
    target_entity: Optional[tcod.ecs.Entity] = None
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Attributes:
    scores: Dict[str, int] = field(default_factory=dict)

@dataclass
class Interactable:
    verb: str = "interact" # "open", "search", "talk"
    action_type: str = "default"

@dataclass
class DoorState:
    is_open: bool = False
    is_locked: bool = False

@dataclass
class BlocksMovement:
    pass

@dataclass
class DialogueOption:
    text: str
    target_node: str = "exit"
    condition: Optional[str] = None
    action: Optional[str] = None

@dataclass
class DialogueNode:
    text: str
    options: List[DialogueOption] = field(default_factory=list)

@dataclass
class DialogueProfile:
    nodes: Dict[str, DialogueNode] = field(default_factory=dict)
    current_node_id: str = "start"
    rumor_response: str = "I heard something about..."

@dataclass
class Faction:
    faction_id: str

@dataclass
class SocialAwareness:
    engagement_range: int = 3
    last_interaction_tick: int = -2000
    is_proactive: bool = False # For Rumor/Trade carriers

@dataclass
class PartyMember:
    leader_id: int # EntityIdentity.entity_id of the leader

@dataclass
class Modifier:
    id: str
    name: str
    stat_field: str # e.g., "attack_bonus", "protection", "speed"
    magnitude: float
    duration: int # ticks remaining
    source_entity_id: Optional[int] = None

@dataclass
class ActiveModifiers:
    effects: List[Modifier] = field(default_factory=list)
