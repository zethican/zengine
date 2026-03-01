"""
Tests for EventBus emission and error handling in engine/combat.py.
"""
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
import io

from engine.combat import EventBus, CombatEvent

class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.calls = []

        # Save stderr to avoid cluttering test output and to assert on it
        self.saved_stderr = sys.stderr
        self.mock_stderr = io.StringIO()
        sys.stderr = self.mock_stderr

    def tearDown(self):
        sys.stderr = self.saved_stderr

    def _success_handler_1(self, event):
        self.calls.append("success_1")

    def _success_handler_2(self, event):
        self.calls.append("success_2")

    def _fail_handler(self, event):
        self.calls.append("fail")
        raise ValueError("Intentional error for testing")

    def _wildcard_handler(self, event):
        self.calls.append("wildcard")

    def test_emit_continues_after_handler_exception(self):
        """
        Test that a failing handler does not prevent subsequent handlers from executing.
        """
        self.bus.subscribe("test.event", self._success_handler_1)
        self.bus.subscribe("test.event", self._fail_handler)
        self.bus.subscribe("test.event", self._success_handler_2)

        event = CombatEvent(event_key="test.event", source="test")
        self.bus.emit(event)

        self.assertEqual(self.calls, ["success_1", "fail", "success_2"])

    def test_emit_logs_error_to_stderr(self):
        """
        Test that handler exceptions are logged to stderr with the correct format.
        """
        self.bus.subscribe("test.error", self._fail_handler)

        event = CombatEvent(event_key="test.error", source="test")
        self.bus.emit(event)

        stderr_output = self.mock_stderr.getvalue()
        self.assertIn("[EventBus] Handler error on 'test.error': Intentional error for testing", stderr_output)

    def test_wildcard_handlers_execute_even_if_specific_handler_fails(self):
        """
        Test that wildcard '*' handlers are still executed if a specific key handler fails.
        """
        self.bus.subscribe("test.event", self._fail_handler)
        self.bus.subscribe("*", self._wildcard_handler)

        event = CombatEvent(event_key="test.event", source="test")
        self.bus.emit(event)

        self.assertEqual(self.calls, ["fail", "wildcard"])

    def test_specific_handlers_execute_even_if_wildcard_handler_fails(self):
        """
        Test that specific handlers are executed even if a wildcard handler throws an error.
        Because of dictionary ordering in python, specific key handlers are executed before
        wildcard handlers since `_subscribers.get(event.event_key, [])` comes before
        `_subscribers.get("*", [])`. We just test it doesn't blow up.
        """
        self.bus.subscribe("test.event", self._success_handler_1)
        self.bus.subscribe("*", self._fail_handler)
        self.bus.subscribe("test.event", self._success_handler_2)

        event = CombatEvent(event_key="test.event", source="test")
        self.bus.emit(event)

        self.assertEqual(self.calls, ["success_1", "success_2", "fail"])

if __name__ == '__main__':
    unittest.main()
