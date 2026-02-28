import tomllib
import pytest
from pathlib import Path

def test_load_ability_toml():
    path = Path("data/abilities/basic_attack.toml")
    assert path.exists()
    
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    assert data["id"] == "basic_attack"
    assert data["ap_cost"] == 10
    assert "effects" in data

def test_load_entity_toml():
    path = Path("data/entities/hero_standard.toml")
    assert path.exists()
    
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    assert data["hp"] == 30
    assert data["archetype"] == "Standard"
    assert "basic_attack" in data["abilities"]

def test_load_world_rumors():
    path = Path("data/world/starting_rumors.toml")
    assert path.exists()
    
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    assert "rumors" in data
    assert len(data["rumors"]) == 2
    assert data["rumors"][0]["id"] == "pol_keep"
