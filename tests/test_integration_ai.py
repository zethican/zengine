import pytest
import tempfile
from pathlib import Path
import tcod.ecs
from engine.loop import SimulationLoop
from engine.ecs.components import EntityIdentity, Position, ActionEconomy, Disposition, BehaviorProfile, CombatVitals
from engine.item_factory import create_item

def test_npc_aggressive_movement_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # 1. Setup Player at (5,5)
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
        player.components[Position] = Position(x=5, y=5)
        player.components[Disposition] = Disposition(reputation=0.0)
        
        # 2. Setup Aggressive NPC at (7,7)
        npc = sim.registry.new_entity()
        npc.components[EntityIdentity] = EntityIdentity(entity_id=2, name="Foe", archetype="Brute")
        npc.components[Position] = Position(x=7, y=7)
        npc.components[ActionEconomy] = ActionEconomy(ap_pool=100)
        npc.components[BehaviorProfile] = BehaviorProfile(threat_weight=1.0) # Attracted to threat
        npc.components[Disposition] = Disposition(reputation=-1.0) # Player is enemy to them
        
        # We need the player to be a threat to the NPC.
        # Threat map seeds are entities with Reputation < -0.3.
        # For the NPC, the player's reputation needs to be checked.
        # Wait, the InfluenceMapSystem.update currently checks Reputation of all entities in registry.
        # But reputation is 'party standing with this NPC'.
        # For NPC to see Player as threat, we need to handle 'disposition towards others'.
        # For MVP: InfluenceMapSystem uses the Reputation component on entities.
        # If Player has Disposition(reputation=-1.0), NPCs will see them as threat?
        # Actually, Reputation component usually means 'how others see this entity'.
        player.components[Disposition].reputation = -1.0 
        
        sim.open_session()
        
        # 3. Tick
        sim.tick() # AI decisions + Resolution

        # 4. Verify movement
        new_pos = npc.components[Position]
        # NPC should have moved closer to (5,5) from (7,7)

        # Chebyshev distance: max(abs(7-5), abs(7-5)) = 2. 
        # New distance should be 1.
        assert max(abs(new_pos.x - 5), abs(new_pos.y - 5)) == 1
        
        sim.close_session()

def test_npc_healing_item_usage_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        chronicle_path = Path(tmpdir) / "chronicle.jsonl"
        sim = SimulationLoop(chronicle_path=chronicle_path)
        
        # 1. Setup Wounded NPC
        npc = sim.registry.new_entity()
        npc.components[EntityIdentity] = EntityIdentity(entity_id=2, name="Friend", archetype="NPC")
        npc.components[Position] = Position(x=5, y=5)
        npc.components[ActionEconomy] = ActionEconomy(ap_pool=100)
        npc.components[CombatVitals] = CombatVitals(hp=5, max_hp=20)
        npc.components[BehaviorProfile] = BehaviorProfile(urgency_weight=1.0)
        npc.components[Disposition] = Disposition(reputation=1.0)
        
        # 2. Give them a potion
        potion = create_item(sim.registry, "consumables/healing_potion")
        npc.relation_tags_many["IsCarrying"].add(potion)
        
        # 3. Setup Player (to avoid px,py=0,0 default)
        player = sim.registry.new_entity()
        player.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Player", archetype="Standard", is_player=True)
        player.components[Position] = Position(x=5, y=5)
        
        sim.open_session()
        
        # 4. Tick
        sim.tick()
        
        # 5. Verify healing
        assert npc.components[CombatVitals].hp > 5
        assert potion not in npc.relation_tags_many["IsCarrying"]
        
        sim.close_session()
