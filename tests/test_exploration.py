import pytest
from world.exploration import ExplorationManager

def test_exploration_marking():
    em = ExplorationManager()
    assert em.is_explored(10, 10) is False
    
    em.mark_explored(10, 10)
    assert em.is_explored(10, 10) is True
    assert em.is_explored(11, 10) is False

def test_exploration_persistence():
    em = ExplorationManager()
    em.mark_explored(5, 5)
    em.mark_explored(-1, 2)
    
    state = em.get_state()
    assert "tiles" in state
    assert "5_5" in state["tiles"]
    assert "-1_2" in state["tiles"]
    
    em2 = ExplorationManager()
    em2.load_state(state)
    assert em2.is_explored(5, 5) is True
    assert em2.is_explored(-1, 2) is True
    assert em2.is_explored(0, 0) is False

def test_exploration_invalid_load():
    em = ExplorationManager()
    # Should not crash on malformed data
    em.load_state({"tiles": ["invalid", "1_2_3", None]})
    assert len(em.explored_tiles) == 0
