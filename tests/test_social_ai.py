import pytest
import tcod.ecs
import tempfile
from pathlib import Path
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, SocialAwareness, BehaviorProfile, ActionEconomy, MovementStats, DialogueProfile
from engine.spawner import spawn_npc

def test_social_ai_approach_and_autopop():
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        
        # 1. Setup Player
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
        player.components[Position] = Position(x=5, y=5)
        
        # 2. Setup Friendly NPC 3 tiles away
        npc = spawn_npc(sim.registry, "hero_standard", 8, 5) # Dist = 3
        npc.components[EntityIdentity].name = "Friendly Guard"
        npc.components[SocialAwareness] = SocialAwareness(engagement_range=3, last_interaction_tick=-2000)
        npc.components[BehaviorProfile] = BehaviorProfile(affinity_weight=1.0) # Attracted to affinity seeds
        
        sim.open_session()
        
        # 3. Tick several times. AI should closing distance.
        # Influence Map should have high affinity at player pos (5,5)
        for _ in range(12):
            sim.tick()
            
        # Verify NPC has moved closer
        npos = npc.components[Position]
        dist = max(abs(npos.x - 5), abs(npos.y - 5))
        assert dist < 3
        
        # 4. Tick until adjacent
        for _ in range(15):
            sim.tick()
            npos = npc.components[Position]
            dist = max(abs(npos.x - 5), abs(npos.y - 5))
            print(f"Tick: NPC at ({npos.x}, {npos.y}), dist={dist}, popup={sim.pending_social_popup}")
            if sim.pending_social_popup: break

            # Verify autopop is triggered
            assert sim.pending_social_popup is not None
            target = sim.pending_social_popup["target"]
            assert target.components[EntityIdentity].name == "Friendly Guard"
        sim.close_session()
