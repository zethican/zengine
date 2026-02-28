"""
ZEngine — world/factions.py
Procedural Faction Generator: Creates unique faction identities per seed.
"""

from __future__ import annotations
import random
from typing import Dict
from engine.data_loader import FactionDef

class FactionGenerator:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.adjectives = [
            "Silent", "Iron", "Bloated", "Silver", "Cracked", 
            "Echoing", "Shattered", "Verdant", "Ashen", "Gilded"
        ]
        self.nouns = [
            "Borzai", "Starfish", "Keepers", "Warband", "Circle",
            "Root", "Heirs", "Vines", "Stalkers", "Legion"
        ]

    def generate_faction(self, faction_id: str) -> FactionDef:
        """Generates a unique FactionDef based on ID."""
        # Use faction_id to deterministicly seed the sub-roll
        local_rng = random.Random(hash(faction_id))
        adj = local_rng.choice(self.adjectives)
        noun = local_rng.choice(self.nouns)
        
        name = f"The {adj} {noun}"
        desc = f"A mysterious group known as {name}."
        
        return FactionDef(
            id=faction_id,
            name=name,
            description=desc,
            base_standing=0.0
        )
