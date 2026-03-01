import pytest
import tcod.ecs
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, CombatVitals, PartyMember, BehaviorProfile
from engine.ecs.systems import recruit_npc_system

def test_recruitment_logic():
    sim = SimulationLoop()
    
    # Setup Player
    player = sim.registry.new_entity()
    player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Hero", is_player=True)
    player.components[Position] = Position(x=5, y=5)
    
    # Setup NPC
    npc = sim.registry.new_entity()
    npc.components[EntityIdentity] = EntityIdentity(entity_id=2, name="Companion", archetype="NPC")
    npc.components[Position] = Position(x=6, y=6)
    npc.components[BehaviorProfile] = BehaviorProfile(affinity_weight=0.0)
    
    # Recruit
    success = recruit_npc_system(player, npc)
    assert success is True
    
    # Verify Party Status
    assert PartyMember in npc.components
    assert npc.components[PartyMember].leader_id == 1
    assert npc.relation_tag["InPartyWith"] == player
    
    # Verify AI Profile shift
    assert npc.components[BehaviorProfile].affinity_weight == 2.0
    assert npc.components[BehaviorProfile].threat_weight == 0.0

def test_party_persistence():
    sim = SimulationLoop()
    sim.world.world_seed = 12345
    
    # Setup and recruit
    player = sim.registry.new_entity()
    player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Hero", is_player=True)
    player.components[Position] = Position(x=5, y=5)
    player.components[CombatVitals] = CombatVitals(hp=10, max_hp=10)
    
    npc = sim.registry.new_entity()
    npc.components[EntityIdentity] = EntityIdentity(entity_id=2, name="Companion", archetype="NPC")
    npc.components[Position] = Position(x=6, y=6)
    npc.components[CombatVitals] = CombatVitals(hp=10, max_hp=10)
    recruit_npc_system(player, npc)
    
    # Save
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        snap_path = Path(tmpdir) / "snap.json"
        sim.save_session(snapshot_path=snap_path)
        
        # Resume in new loop
        sim2 = SimulationLoop()
        sim2.resume_session(snapshot_path=snap_path)
        
        # Find restored NPC
        restored_npc = None
        for ent in sim2.registry.Q.all_of(components=[EntityIdentity]):
            if ent.components[EntityIdentity].name == "Companion":
                restored_npc = ent
                break
        
        assert restored_npc is not None
        assert PartyMember in restored_npc.components
        assert restored_npc.components[PartyMember].leader_id == 1
