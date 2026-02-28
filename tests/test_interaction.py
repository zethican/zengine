import pytest
import tcod.ecs
import tempfile
from pathlib import Path
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, ItemIdentity
from engine.spawner import spawn_container

def test_contextual_interaction_at_container():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # 1. Setup Player
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        player.components[Position] = Position(x=5, y=5)
        
        # 2. Setup Container next to player
        container = spawn_container(sim.registry, "Chest", 6, 5, ["weapons/iron_sword"])
        
        # 3. Interact at 6,5
        result = sim.interact_at(player, 6, 5)
        
        assert result is not None
        assert result["type"] == "entity_interaction"
        assert result["target"] == container
        assert result["verb"] == "open"

def test_looting_and_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_path = Path(tmpdir) / "snapshot.toml"
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # 1. Setup Player and Container with item
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Aric", archetype="Standard", is_player=True)
        player.components[Position] = Position(x=5, y=5)
        
        container = spawn_container(sim.registry, "Chest", 6, 5, ["weapons/iron_sword"])
        item = list(container.relation_tags_many["IsCarrying"])[0]
        
        # 2. Move item to player (simulate Loot UI logic)
        container.relation_tags_many["IsCarrying"].remove(item)
        player.relation_tags_many["IsCarrying"].add(item)
        
        # 3. Save
        sim.save_session(snapshot_path)
        
        # 4. Resume in new simulation
        sim2 = SimulationLoop(chronicle_path=chronicle_path)
        sim2.resume_session(snapshot_path)
        
        # Find player in sim2
        player2 = None
        for ent in sim2.registry.Q.all_of(components=[EntityIdentity]):
            if ent.components[EntityIdentity].is_player:
                player2 = ent
                break
        
        assert player2 is not None
        carried = list(player2.relation_tags_many["IsCarrying"])
        assert len(carried) == 1
        assert carried[0].components[ItemIdentity].entity_id == "iron_sword"
        
        # Verify container is empty
        container2 = None
        for ent in sim2.registry.Q.all_of(components=[ItemIdentity]):
            if ent.components[ItemIdentity].name == "Chest":
                container2 = ent
                break
        assert container2 is not None
        assert len(list(container2.relation_tags_many["IsCarrying"])) == 0
