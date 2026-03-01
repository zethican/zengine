import sys

# In an isolated environment without pydantic, mock it conditionally.
try:
    import pydantic
except ImportError:
    from unittest.mock import MagicMock
    mock_pydantic = MagicMock()
    class MockBaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    mock_pydantic.BaseModel = MockBaseModel
    sys.modules['pydantic'] = mock_pydantic

import unittest
from engine.combat import FoeFactory

class TestFoeFactorySecurity(unittest.TestCase):
    def test_threat_level_cannot_be_negative(self):
        """Test that negative threat levels are clamped to 0 to prevent underflow vulnerability."""
        foe = FoeFactory.generate(threat_level=-5, archetype="Brute")

        # Threat level -5 would be max(0, -5) = 0.
        # So base_bonus = 3 + 0 = 3
        # Brute atk_bonus = 0 -> min(10, 3 + 0) = 3
        # Brute def_bonus = -2 -> min(10, 3 - 2) = 1
        # Brute hp_mult = 1.5 -> int((10 + 0 * 5) * 1.5) = 15

        self.assertEqual(foe.get_stat("attack_bonus"), 3)
        self.assertEqual(foe.get_stat("defense_bonus"), 1)
        self.assertEqual(foe.max_hp, 15)
        self.assertEqual(foe.hp, 15)
        # Verify the name still reflects the clamped threat level for consistency
        self.assertEqual(foe.name, "Tier-0 Brute")

    def test_stats_cannot_be_negative(self):
        """Test that stats are clamped to a minimum of 0."""
        # For instance, if BASE_BONUS was modified or extreme archetypes existed
        # Brute def_bonus is -2. So at threat_level=0, base=3, def_bonus=1.
        # But let's verify if an archetype with -10 def_bonus is handled (mocking ARCHETYPES temporarily)
        original_archetypes = dict(FoeFactory.ARCHETYPES)
        try:
            FoeFactory.ARCHETYPES["Vulnerable"] = {
                "hp_mult": 1.0, "atk_bonus": -10, "def_bonus": -10, "dmg_bonus": 0, "speed": 10.0
            }

            foe = FoeFactory.generate(threat_level=0, archetype="Vulnerable")
            # Base=3, def_bonus=3-10=-7. Clamp to 0.
            self.assertEqual(foe.get_stat("attack_bonus"), 0)
            self.assertEqual(foe.get_stat("defense_bonus"), 0)
        finally:
            FoeFactory.ARCHETYPES = original_archetypes

    def test_hp_cannot_be_zero_or_negative(self):
        """Test that HP is clamped to a minimum of 1."""
        original_archetypes = dict(FoeFactory.ARCHETYPES)
        try:
            # Multiplier 0 should clamp HP to 1 instead of 0
            FoeFactory.ARCHETYPES["Ghost"] = {
                "hp_mult": 0.0, "atk_bonus": 0, "def_bonus": 0, "dmg_bonus": 0, "speed": 10.0
            }

            foe = FoeFactory.generate(threat_level=0, archetype="Ghost")
            self.assertEqual(foe.max_hp, 1)
            self.assertEqual(foe.hp, 1)
        finally:
            FoeFactory.ARCHETYPES = original_archetypes

if __name__ == '__main__':
    unittest.main()
