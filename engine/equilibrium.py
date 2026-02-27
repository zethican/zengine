"""
ZEngine — engine/equilibrium.py
Equilibrium System: World vitality, migration, and conduction logic.
====================================================================
Version:     0.1  (Phase 2 — canonical implementation)
Stack:       Python 3.14.3
Status:      Production-ready for Phase 2.
"""

from __future__ import annotations

EQUILIBRIUM_BASE_RESISTANCE: int = 40
CONDUCTION_COEFFICIENT: float = 0.3
CONDUCTION_ATTENUATION: float = 0.6

def compute_migration_risk(living_count: int, vitality: float) -> int:
    """
    Return the risk % (0-100) that migration/legacy conversion occurs.
    Taper formula: 100 - (BASE_RESISTANCE + (living_count * vitality))
    """
    taper_threshold = EQUILIBRIUM_BASE_RESISTANCE + (living_count * vitality)
    return int(100 - taper_threshold)

def calculate_conduction_magnitude(original_magnitude: float, distance: float) -> float:
    """
    Calculate the magnitude of a propagated mood spike.
    Formula: original * coefficient * (attenuation ** distance)
    """
    if CONDUCTION_COEFFICIENT <= 0.0:
        return 0.0
    return original_magnitude * CONDUCTION_COEFFICIENT * (CONDUCTION_ATTENUATION ** distance)
