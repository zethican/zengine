import pytest
from engine.narrative import NarrativeGenerator
from engine.combat import EVT_ACTION_RESOLVED, EVT_ON_DEATH

def test_narrative_combat_hit():
    entry = {
        "actor_handle": "Aric",
        "payload": {
            "event_type": EVT_ACTION_RESOLVED,
            "verb": "attacked",
            "object": "Cave Crawler",
            "modifier": {"outcome": "hit", "damage": 5}
        }
    }
    text = NarrativeGenerator.entry_to_text(entry)
    assert text == "Aric struck Cave Crawler for 5 damage."

def test_narrative_death():
    entry = {
        "actor_handle": "Cave Crawler",
        "payload": {
            "event_type": EVT_ON_DEATH,
            "verb": "died",
            "object": "Cave Crawler"
        }
    }
    text = NarrativeGenerator.entry_to_text(entry)
    assert text == "Cave Crawler has perished."

def test_narrative_fallback():
    entry = {
        "actor_handle": "System",
        "payload": {
            "event_type": "unknown",
            "verb": "happened",
            "object": "world"
        }
    }
    text = NarrativeGenerator.entry_to_text(entry)
    assert text == "System happened world."
