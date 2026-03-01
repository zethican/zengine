import pytest
from world.territory import TerritoryManager, TerritoryNode

def test_territory_manager_deterministic_generation():
    seed = 12345
    tm1 = TerritoryManager(world_seed=seed)
    tm2 = TerritoryManager(world_seed=seed)
    
    # Test that both managers generate the same node for macro-region 0,0
    node1 = tm1.get_node_at(tm1.MACRO_REGION_SIZE // 2, tm1.MACRO_REGION_SIZE // 2)
    # Actually, we don't know the exact chunk_x, chunk_y without generating it.
    # Let's generate it directly
    n1 = tm1._generate_node_for_region(0, 0)
    n2 = tm2._generate_node_for_region(0, 0)
    
    assert n1.id == n2.id
    assert n1.chunk_x == n2.chunk_x
    assert n1.chunk_y == n2.chunk_y
    assert n1.poi_type == n2.poi_type
    assert n1.faction_id == n2.faction_id
    
    # Different region should produce different node
    n3 = tm1._generate_node_for_region(1, 0)
    assert n1.id != n3.id
    assert n1.chunk_x != n3.chunk_x

def test_territory_manager_get_node_at():
    tm = TerritoryManager(world_seed=999)
    n = tm._generate_node_for_region(5, 5)
    
    # Querying the exact chunk should return the node
    found_node = tm.get_node_at(n.chunk_x, n.chunk_y)
    assert found_node is not None
    assert found_node.id == n.id
    
    # Querying an adjacent chunk should return None
    missing_node = tm.get_node_at(n.chunk_x + 1, n.chunk_y)
    assert missing_node is None

def test_territory_manager_capture_node():
    tm = TerritoryManager(world_seed=555)
    n = tm._generate_node_for_region(2, 2)
    
    original_faction = n.faction_id
    new_faction = "faction_999"
    
    # Capture the node
    success = tm.capture_node(n.chunk_x, n.chunk_y, new_faction)
    assert success is True
    
    # Verify override
    overridden_node = tm.get_node_at(n.chunk_x, n.chunk_y)
    assert overridden_node is not None
    assert overridden_node.faction_id == new_faction
    assert overridden_node.faction_id != original_faction
    
    # Verify controlling faction
    assert tm.get_controlling_faction(n.chunk_x, n.chunk_y) == new_faction
