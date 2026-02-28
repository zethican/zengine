import pytest
import tcod.ecs
import tempfile
from pathlib import Path
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, Disposition, Faction
from engine.combat import EVT_SOCIAL_DISPOSITION_SHIFT, CombatEvent

def test_faction_conduction():
    with tempfile.TemporaryDirectory() as tmpdir:
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        
        # 1. Setup two NPCs in the same faction
        npc1 = sim.registry.new_entity()
        npc1.components[EntityIdentity] = EntityIdentity(entity_id=10, name="Guard A", archetype="NPC")
        npc1.components[Faction] = Faction(faction_id="city_guard")
        
        npc2 = sim.registry.new_entity()
        npc2.components[EntityIdentity] = EntityIdentity(entity_id=11, name="Guard B", archetype="NPC")
        npc2.components[Faction] = Faction(faction_id="city_guard")
        
        sim.open_session()
        
        # 2. Shift reputation of NPC1
        # Use the event bus to trigger the shift
        sim.bus.emit(CombatEvent(
            event_key=EVT_SOCIAL_DISPOSITION_SHIFT,
            source="Guard A",
            data={"delta": 0.4}
        ))
        
        # 3. Verify Conduction
        # NPC1 should have +0.4
        assert npc1.components[Disposition].reputation == 0.4
        
        # Faction standing should have +0.2 (0.4 * 0.5 conduction factor)
        assert sim.faction_standing["city_guard"] == 0.2
        
        # NPC2 reputation (individual) is still 0.0
        # but SocialStateSystem.get_reputation should return the faction standing if no individual disposition exists
        # Wait, I implemented get_reputation to fallback.
        assert sim.social_system.get_reputation("Guard B") == 0.2
        
        sim.close_session()

def test_faction_serialization():
    with tempfile.TemporaryDirectory() as tmpdir:
        snap_path = Path(tmpdir) / "snapshot.toml"
        sim = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle.jsonl")
        
        sim.faction_standing["test_faction"] = 0.75
        sim.save_session(snapshot_path=snap_path)
        
        # Restore
        sim2 = SimulationLoop(chronicle_path=Path(tmpdir)/"chronicle2.jsonl")
        sim2.resume_session(snapshot_path=snap_path)
        
        assert sim2.faction_standing["test_faction"] == 0.75
