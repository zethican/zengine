import pytest
from engine.equilibrium import compute_migration_risk

def test_migration_risk_flourishing():
    # living_count = 10, vitality = 0.8
    # taper_threshold = 40 + (10 * 0.8) = 48
    # risk = 100 - 48 = 52
    assert compute_migration_risk(living_count=10, vitality=0.8) == 52

def test_migration_risk_collapsing():
    # living_count = 5, vitality = -0.5
    # taper_threshold = 40 + (5 * -0.5) = 40 - 2.5 = 37.5
    # risk = int(100 - 37.5) = 62
    assert compute_migration_risk(living_count=5, vitality=-0.5) == 62

def test_migration_risk_empty_node():
    # living_count = 0, vitality = 0.5
    # taper_threshold = 40 + (0 * 0.5) = 40
    # risk = 100 - 40 = 60
    assert compute_migration_risk(living_count=0, vitality=0.5) == 60
