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
from engine.combat import (
    Combatant,
    EventBus,
    EVT_ON_DAMAGE,
    EVT_ON_DEATH,
    EVT_SOCIAL_STRESS_SPIKE
)

class TestCombatantDamage(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.emitted_events = []

        # Capture all events
        def capture_event(event):
            self.emitted_events.append(event)

        self.bus.subscribe("*", capture_event)

        self.combatant = Combatant(
            name="Target dummy",
            is_player=False,
            max_hp=50,
            stats={"defense_bonus": 0},
            speed=10.0
        )
        # Register the combatant with the bus
        self.combatant.register_with_bus(self.bus)

    def test_apply_damage_reduces_hp(self):
        """Test that apply_damage correctly reduces the combatant's HP."""
        initial_hp = self.combatant.hp
        damage_amount = 15

        self.combatant.apply_damage(damage_amount)

        self.assertEqual(self.combatant.hp, initial_hp - damage_amount)

    def test_apply_damage_negative_amount(self):
        """Test that a negative damage amount is clamped to 0."""
        initial_hp = self.combatant.hp

        self.combatant.apply_damage(-10)

        self.assertEqual(self.combatant.hp, initial_hp)

    def test_apply_damage_emits_on_damage(self):
        """Test that applying damage emits an EVT_ON_DAMAGE event with correct payload."""
        damage_amount = 20
        self.combatant.apply_damage(damage_amount)

        on_damage_events = [e for e in self.emitted_events if e.event_key == EVT_ON_DAMAGE]
        self.assertEqual(len(on_damage_events), 1)

        event = on_damage_events[0]
        self.assertEqual(event.source, self.combatant.name)
        self.assertEqual(event.target, self.combatant.name)
        self.assertEqual(event.data["amount"], damage_amount)
        self.assertEqual(event.data["hp_remaining"], 30)

        # Verify no death event was emitted since it didn't drop to 0
        death_events = [e for e in self.emitted_events if e.event_key == EVT_ON_DEATH]
        self.assertEqual(len(death_events), 0)

    def test_apply_damage_lethal_emits_death_and_stress(self):
        """Test that lethal damage emits EVT_ON_DEATH and EVT_SOCIAL_STRESS_SPIKE."""
        lethal_damage = 60
        self.combatant.apply_damage(lethal_damage)

        self.assertTrue(self.combatant.is_dead)
        self.assertEqual(self.combatant.hp, -10)

        death_events = [e for e in self.emitted_events if e.event_key == EVT_ON_DEATH]
        self.assertEqual(len(death_events), 1)
        self.assertEqual(death_events[0].source, self.combatant.name)
        self.assertEqual(death_events[0].data["final_hp"], -10)

        stress_events = [e for e in self.emitted_events if e.event_key == EVT_SOCIAL_STRESS_SPIKE]
        self.assertEqual(len(stress_events), 1)
        self.assertEqual(stress_events[0].source, self.combatant.name)
        self.assertEqual(stress_events[0].data["cause"], "combat_death")
        self.assertEqual(stress_events[0].data["magnitude"], 0.5)

    def test_apply_damage_with_explicit_bus(self):
        """Test that passing a specific bus overrides the registered bus."""
        explicit_bus = EventBus()
        explicit_events = []
        explicit_bus.subscribe("*", lambda e: explicit_events.append(e))

        self.combatant.apply_damage(10, bus=explicit_bus)

        # Events should be captured by the explicit bus, not the self.bus
        self.assertEqual(len(explicit_events), 1)
        self.assertEqual(explicit_events[0].event_key, EVT_ON_DAMAGE)

        self.assertEqual(len(self.emitted_events), 0)

    def test_apply_damage_without_any_bus(self):
        """Test that apply_damage works even if no bus is registered or provided."""
        unregistered_combatant = Combatant("Dummy", False, 10, {})

        # No exception should be raised
        unregistered_combatant.apply_damage(5)

        self.assertEqual(unregistered_combatant.hp, 5)

if __name__ == '__main__':
    unittest.main()
