import pytest
import tcod.ecs
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, CombatVitals

def test_jit_culling_and_materialization():
    sim = SimulationLoop()
    sim.world.world_seed = 12345
    
    # 1. Setup Player
    hero = sim.registry.new_entity()
    hero.components[EntityIdentity] = EntityIdentity(entity_id="hero", name="Hero", archetype="Standard", is_player=True)
    hero.components[Position] = Position(x=5, y=5)
    
    # 2. Setup a persistent NPC nearby
    npc = sim.registry.new_entity()
    npc.components[EntityIdentity] = EntityIdentity(entity_id="borzai", name="Persistent Borzai", archetype="Elite")
    npc.components[Position] = Position(x=6, y=6)
    npc.components[CombatVitals] = CombatVitals(hp=50, max_hp=50)
    
    # 3. Setup an ephemeral Skirmisher nearby
    mob = sim.registry.new_entity()
    mob.components[EntityIdentity] = EntityIdentity(entity_id="foe", name="Ephemeral Foe", archetype="Skirmisher")
    mob.components[Position] = Position(x=7, y=7)
    mob.components[CombatVitals] = CombatVitals(hp=10, max_hp=10)
    
    # Verify both are in registry
    assert EntityIdentity in npc.components
    assert EntityIdentity in mob.components
    
    # 4. Move player far away (CULL_DISTANCE is 3 chunks, each chunk is 20 units)
    # Move to x=100 (5 chunks away)
    sim.move_entity_ecs(hero, 95, 0)
    
    # Verify NPC and Mob are culled from active registry
    # (Note: clear() was called on them, so components are gone)
    assert EntityIdentity not in npc.components
    assert EntityIdentity not in mob.components
    
    # 5. Check virtual_entities
    # The chunk (0,0) should have the NPC but NOT the mob (because it was full health/ephemeral)
    assert (0, 0) in sim.virtual_entities
    virtual_ids = [e["identity"]["name"] for e in sim.virtual_entities[(0, 0)]]
    assert "Persistent Borzai" in virtual_ids
    assert "Ephemeral Foe" not in virtual_ids
    
    # 6. Move back to origin
    sim.move_entity_ecs(hero, -95, 0)
    
    # Verify NPC is restored
    found_npc = None
    for ent in sim.registry.Q.all_of(components=[EntityIdentity]):
        if ent.components[EntityIdentity].name == "Persistent Borzai":
            found_npc = ent
            break
            
    assert found_npc is not None
    assert found_npc.components[CombatVitals].hp == 50
    assert (0, 0) not in sim.virtual_entities # Should be cleared from virtual store

def test_jit_restores_damaged_mobs():
    sim = SimulationLoop()
    sim.world.world_seed = 12345
    
    # Setup Player
    hero = sim.registry.new_entity()
    hero.components[EntityIdentity] = EntityIdentity(entity_id="hero", name="Hero", archetype="Standard", is_player=True)
    hero.components[Position] = Position(x=5, y=5)
    
    # Setup damaged Mob
    mob = sim.registry.new_entity()
    mob.components[EntityIdentity] = EntityIdentity(entity_id="foe", name="Damaged Mob", archetype="Skirmisher")
    mob.components[Position] = Position(x=6, y=6)
    mob.components[CombatVitals] = CombatVitals(hp=5, max_hp=10) # DAMAGED
    
    # Move away
    sim.move_entity_ecs(hero, 100, 0)
    
    # Verify damaged mob was virtualized (not culled)
    assert (0, 0) in sim.virtual_entities
    virtual_ids = [e["identity"]["name"] for e in sim.virtual_entities[(0, 0)]]
    assert "Damaged Mob" in virtual_ids
    
    # Move back
    sim.move_entity_ecs(hero, -100, 0)
    
    # Verify restoration
    found_mob = None
    for ent in sim.registry.Q.all_of(components=[EntityIdentity]):
        if ent.components[EntityIdentity].name == "Damaged Mob":
            found_mob = ent
            break
    assert found_mob is not None
    assert found_mob.components[CombatVitals].hp == 5
