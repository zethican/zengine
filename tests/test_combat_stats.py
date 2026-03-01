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
from engine.combat import Combatant, Modifier, EVT_TURN_ENDED

class TestCombatantStats(unittest.TestCase):
    def setUp(self):
        # Create a base combatant for tests
        self.combatant = Combatant(
            name="Test Hero",
            is_player=True,
            max_hp=100,
            stats={"strength": 10, "agility": 15},
            damage_bonus=2,
            speed=10.0
        )

    def test_get_stat_no_modifiers(self):
        """Test getting a stat that has no modifiers applied."""
        self.assertEqual(self.combatant.get_stat("strength"), 10)
        self.assertEqual(self.combatant.get_stat("agility"), 15)

    def test_get_stat_missing(self):
        """Test getting a stat that doesn't exist in base stats returns 0."""
        self.assertEqual(self.combatant.get_stat("wisdom"), 0)

    def test_get_stat_with_active_modifiers(self):
        """Test getting a stat with active modifiers applied computes correctly."""
        mod1 = Modifier(name="Strength Buff", stat_target="strength", value=5)
        mod2 = Modifier(name="Strength Debuff", stat_target="strength", value=-2)

        self.combatant.add_modifier(mod1)
        self.combatant.add_modifier(mod2)

        # Base 10 + 5 - 2 = 13
        self.assertEqual(self.combatant.get_stat("strength"), 13)

    def test_get_stat_ignores_expired_modifiers(self):
        """Test that expired modifiers are correctly ignored."""
        mod_active = Modifier(name="Agility Buff", stat_target="agility", value=3)
        mod_expired = Modifier(name="Agility Aura", stat_target="agility", value=10, expires_on=[EVT_TURN_ENDED])

        # Trigger expiry properly instead of mutating private fields
        mod_expired.on_event(EVT_TURN_ENDED)
        self.assertTrue(mod_expired.is_expired)

        self.combatant.add_modifier(mod_active)
        self.combatant.add_modifier(mod_expired)

        # Base 15 + 3 active (ignore 10 expired) = 18
        self.assertEqual(self.combatant.get_stat("agility"), 18)

    def test_get_stat_ignores_other_stats(self):
        """Test that modifiers for other stats don't affect the target stat."""
        mod_str = Modifier(name="Strength Buff", stat_target="strength", value=5)
        mod_agi = Modifier(name="Agility Buff", stat_target="agility", value=3)

        self.combatant.add_modifier(mod_str)
        self.combatant.add_modifier(mod_agi)

        self.assertEqual(self.combatant.get_stat("strength"), 15)
        self.assertEqual(self.combatant.get_stat("agility"), 18)
        self.assertEqual(self.combatant.get_stat("wisdom"), 0)

    def test_get_stat_mixed_modifiers(self):
        """Test stat calculation with a mix of base stat, active and expired modifiers."""
        self.combatant = Combatant(
            name="Test Mixed",
            is_player=True,
            max_hp=100,
            stats={"attack_bonus": 5},
            damage_bonus=2,
            speed=10.0
        )
        mod_active1 = Modifier(name="Sword Buff", stat_target="attack_bonus", value=2)
        mod_active2 = Modifier(name="Blessing", stat_target="attack_bonus", value=1)
        mod_expired = Modifier(name="Curse", stat_target="attack_bonus", value=-5, expires_on=[EVT_TURN_ENDED])
        mod_expired.on_event(EVT_TURN_ENDED)
        self.assertTrue(mod_expired.is_expired)

        self.combatant.add_modifier(mod_active1)
        self.combatant.add_modifier(mod_active2)
        self.combatant.add_modifier(mod_expired)

        # Base 5 + 2 + 1 = 8
        self.assertEqual(self.combatant.get_stat("attack_bonus"), 8)

if __name__ == '__main__':
    unittest.main()
