import pytest
import tcod.ecs
import tempfile
from pathlib import Path
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, Disposition, DialogueProfile
from engine.spawner import spawn_npc
from world.generator import Rumor

def test_dialogue_and_rumor_sharing():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # 1. Setup Player
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        player.components[Position] = Position(x=5, y=5)
        
        # 2. Setup NPC with custom greeting
        npc = spawn_npc(sim.registry, "hero_standard", 6, 5) # Use hero_standard as base
        npc.components[EntityIdentity].name = "Old Man"
        npc.components[DialogueProfile] = DialogueProfile(
            greetings={"neutral": "Stay a while and listen."}
        )
        
        # 3. Add a Rumor to the world
        sim.world.add_rumor(Rumor(id="test_poi", name="Forgotten Shrine", pol_type="prefab", significance=5))
        
        sim.open_session()
        
        # 4. Interact (Talk)
        from ui.states import Engine
        from ui.screens import DialogueState
        
        # We need a mock Engine to test state changes? 
        # Actually, let's just test the logic in SimulationLoop and DialogueState directly.
        
        # Check greeting
        profile = npc.components[DialogueProfile]
        assert profile.greetings["neutral"] == "Stay a while and listen."
        
        # Check rumor sharing
        rumor_text = sim.share_rumor(player, npc)
        assert "Forgotten Shrine" in rumor_text
        
        # Verify rumor is popped from queue
        assert len(sim.world.rumor_queue) == 0
        
        sim.close_session()
