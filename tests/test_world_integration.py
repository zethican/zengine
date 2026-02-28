import pytest
import tcod.ecs
import tempfile
from pathlib import Path
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, Faction, DialogueProfile
from engine.spawner import spawn_npc

def test_bespoke_chunk_faction_assignment():
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        sim.world.world_seed = 12345
        
        # 1. Find a bespoke chunk
        cx, cy = -1, -1
        for y in range(4):
            for x in range(4):
                c = sim.world.get_chunk(x, y)
                if c["terrain"] == "bespoke":
                    cx, cy = x, y
                    break
            if cx != -1: break
            
        assert cx != -1
        chunk = sim.world.get_chunk(cx, cy)
        fid = chunk.get("faction_id")
        assert fid is not None
        assert fid.startswith("village_")
        
        # 2. Trigger Spawning
        # Move player to chunk to trigger spawn
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
        player.components[Position] = Position(x=cx * 20 + 10, y=cy * 20 + 10)
        
        # Manually trigger spawn logic (usually handled in move_entity_ecs)
        from engine.spawner import spawn_bespoke_chunk
        print(f"Spawns in chunk: {chunk.get('spawns')}")
        spawn_bespoke_chunk(sim.registry, chunk)
        
        # 3. Verify NPCs have the faction_id
        npcs = []
        for ent in sim.registry.Q.all_of(components=[Position, Faction]):
            pos = ent.components[Position]
            if cx * 20 <= pos.x < (cx + 1) * 20 and cy * 20 <= pos.y < (cy + 1) * 20:
                npcs.append(ent)
                
        assert len(npcs) > 0
        for npc in npcs:
            assert npc.components[Faction].faction_id == fid

        # 4. Verify Social Conduction
        # Shift reputation of NPC1
        from engine.combat import EVT_SOCIAL_DISPOSITION_SHIFT, CombatEvent
        npc1_name = npcs[0].components[EntityIdentity].name
        sim.bus.emit(CombatEvent(
            event_key=EVT_SOCIAL_DISPOSITION_SHIFT,
            source=npc1_name,
            data={"delta": 1.0} # Max shift
        ))
        
        # Verify Faction standing shifted (1.0 * 0.5 = 0.5)
        assert sim.faction_standing[fid] == 0.5
        
        # Verify social system returns the faction-influenced reputation
        # SocialStateSystem.get_reputation returns individual rep if it exists
        assert sim.social_system.get_reputation(npc1_name) == 1.0

def test_wilderness_pack_faction_assignment():
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        sim.world.world_seed = 12345
        
        # 1. Find a wilderness chunk with population
        cx, cy = -1, -1
        target_chunk = None
        for y in range(10):
            for x in range(10):
                c = sim.world.get_chunk(x, y)
                if c["terrain"] == "wilderness" and c.get("population"):
                    cx, cy = x, y
                    target_chunk = c
                    break
            if cx != -1: break
            
        assert cx != -1
        fid = target_chunk.get("faction_id")
        assert fid is not None
        assert fid.startswith("warband_")
        
        # 2. Force spawn (since it's probabilistic in tick/move)
        from engine.spawner import spawn_wilderness_chunk
        # We need to mock rng to ensure spawn
        import random
        old_random = random.Random.random
        random.Random.random = lambda self: 0.0 # Force spawn
        
        spawn_wilderness_chunk(sim.registry, target_chunk)
        
        random.Random.random = old_random # Restore
        
        # 3. Verify NPCs have the faction_id
        npcs = []
        for ent in sim.registry.Q.all_of(components=[Position, Faction]):
            pos = ent.components[Position]
            if cx * 20 <= pos.x < (cx + 1) * 20 and cy * 20 <= pos.y < (cy + 1) * 20:
                npcs.append(ent)
                
        assert len(npcs) > 0
        for npc in npcs:
            assert npc.components[Faction].faction_id == fid

        # 4. Verify Social Conduction
        # Shift reputation of NPC1
        from engine.combat import EVT_SOCIAL_DISPOSITION_SHIFT, CombatEvent
        npc1_name = npcs[0].components[EntityIdentity].name
        sim.bus.emit(CombatEvent(
            event_key=EVT_SOCIAL_DISPOSITION_SHIFT,
            source=npc1_name,
            data={"delta": 1.0} # Max shift
        ))
        
        # Verify Faction standing shifted (1.0 * 0.5 = 0.5)
        assert sim.faction_standing[fid] == 0.5
        
        # Verify social system returns the faction-influenced reputation
        # SocialStateSystem.get_reputation returns individual rep if it exists
        assert sim.social_system.get_reputation(npc1_name) == 1.0
