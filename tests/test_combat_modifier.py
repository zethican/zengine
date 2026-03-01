import sys
import unittest

# Ensure we don't clobber an existing 'pydantic' module if tests are run in a suite.
# Only mock it if it's genuinely missing in this specific isolated test environment constraint.
_mocked_pydantic = False
if 'pydantic' not in sys.modules:
    class MockBaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class MockField:
        pass

    class MockPydantic:
        BaseModel = MockBaseModel
        Field = lambda *args, **kwargs: MockField()
        field_validator = lambda *args, **kwargs: lambda f: f

    sys.modules['pydantic'] = MockPydantic()
    _mocked_pydantic = True

from engine.combat import Modifier

class TestModifierExpiration(unittest.TestCase):
    """Tests for the Modifier self-expiring logic in engine/combat.py."""

    @classmethod
    def tearDownClass(cls):
        """Clean up the mock from sys.modules to prevent polluting other tests in a suite."""
        global _mocked_pydantic
        if _mocked_pydantic and 'pydantic' in sys.modules:
            del sys.modules['pydantic']
            _mocked_pydantic = False

    def test_expires_on_matching_event(self):
        """Test that a modifier expires after its trigger event fires max_triggers times."""
        mod = Modifier(
            name="Blessing of Might",
            stat_target="attack_bonus",
            value=2,
            expires_on=["EVT_TURN_ENDED"],
            max_triggers=1
        )

        self.assertFalse(mod.is_expired)

        # Fire matching event
        result = mod.on_event("EVT_TURN_ENDED")

        self.assertTrue(result) # Should return True indicating it just expired
        self.assertTrue(mod.is_expired)
        self.assertEqual(mod._trigger_count, 1)

    def test_ignores_non_matching_events(self):
        """Test that a modifier ignores events not in its expires_on list."""
        mod = Modifier(
            name="Shield",
            stat_target="defense_bonus",
            value=3,
            expires_on=["EVT_ON_DAMAGE"],
            max_triggers=1
        )

        # Fire non-matching events
        self.assertFalse(mod.on_event("EVT_TURN_STARTED"))
        self.assertFalse(mod.on_event("EVT_TURN_ENDED"))

        # Should not be expired
        self.assertFalse(mod.is_expired)
        self.assertEqual(mod._trigger_count, 0)

    def test_multiple_triggers(self):
        """Test that a modifier only expires after max_triggers are reached."""
        mod = Modifier(
            name="Absorb 3 Hits",
            stat_target="defense_bonus",
            value=5,
            expires_on=["EVT_ON_DAMAGE"],
            max_triggers=3
        )

        # Trigger 1
        self.assertFalse(mod.on_event("EVT_ON_DAMAGE"))
        self.assertFalse(mod.is_expired)
        self.assertEqual(mod._trigger_count, 1)

        # Trigger 2
        self.assertFalse(mod.on_event("EVT_ON_DAMAGE"))
        self.assertFalse(mod.is_expired)
        self.assertEqual(mod._trigger_count, 2)

        # Interleaved non-matching event
        self.assertFalse(mod.on_event("EVT_TURN_ENDED"))
        self.assertEqual(mod._trigger_count, 2)

        # Trigger 3 (should expire)
        self.assertTrue(mod.on_event("EVT_ON_DAMAGE"))
        self.assertTrue(mod.is_expired)
        self.assertEqual(mod._trigger_count, 3)

    def test_post_expiration_behavior(self):
        """Test that an expired modifier returns False on subsequent events and doesn't increment triggers."""
        mod = Modifier(
            name="One-Time Boost",
            stat_target="speed",
            value=10,
            expires_on=["EVT_TURN_STARTED"],
            max_triggers=1
        )

        # Expire the modifier
        self.assertTrue(mod.on_event("EVT_TURN_STARTED"))
        self.assertTrue(mod.is_expired)
        self.assertEqual(mod._trigger_count, 1)

        # Subsequent matching events should return False and not increment trigger count
        self.assertFalse(mod.on_event("EVT_TURN_STARTED"))
        self.assertTrue(mod.is_expired)
        self.assertEqual(mod._trigger_count, 1)

    def test_permanent_modifier(self):
        """Test that a modifier with an empty expires_on list never expires."""
        mod = Modifier(
            name="Permanent Boon",
            stat_target="max_hp",
            value=20,
            expires_on=[], # Empty list = permanent
            max_triggers=1
        )

        # Any event shouldn't affect it
        self.assertFalse(mod.on_event("EVT_TURN_ENDED"))
        self.assertFalse(mod.on_event("EVT_ON_DAMAGE"))
        self.assertFalse(mod.is_expired)
        self.assertEqual(mod._trigger_count, 0)

if __name__ == "__main__":
    unittest.main()
