import tcod.ecs
import pytest
from engine.ecs.components import ActionEconomy, MovementStats, CombatStats, ItemStats
from engine.combat import EventBus, EVT_TURN_STARTED, EVT_ACTION_RESOLVED, ENERGY_THRESHOLD, AP_POOL_SIZE
from engine.ecs.systems import turn_resolution_system, action_economy_reset_system, action_resolution_system, get_effective_stats

def test_turn_resolution():
    registry = tcod.ecs.Registry()
    actor = registry.new_entity()
    actor.components[ActionEconomy] = ActionEconomy(action_energy=0.0)
    actor.components[MovementStats] = MovementStats(speed=10.0)
    turn_resolution_system(registry)
    assert actor.components[ActionEconomy].action_energy == 10.0

def test_ap_reset_on_energy_threshold():
    registry = tcod.ecs.Registry()
    bus = EventBus()
    actor = registry.new_entity()
    actor.components[ActionEconomy] = ActionEconomy(action_energy=ENERGY_THRESHOLD, ap_pool=0)
    events = []
    bus.subscribe(EVT_TURN_STARTED, lambda e: events.append(e))
    action_economy_reset_system(registry, bus)
    assert actor.components[ActionEconomy].ap_pool == AP_POOL_SIZE
    assert len(events) == 1

def test_action_resolution_attack_success():
    registry = tcod.ecs.Registry()
    bus = EventBus()
    actor = registry.new_entity()
    actor.components[ActionEconomy] = ActionEconomy(ap_pool=100)
    events = []
    bus.subscribe(EVT_ACTION_RESOLVED, lambda e: events.append(e))
    # MUST provide a valid TOML ability id (e.g. "basic_attack")
    action_resolution_system(registry, actor, "basic_attack", {"target": "Foe"}, bus)
    assert actor.components[ActionEconomy].ap_pool == 90

    assert len(events) == 1
    assert events[0].target == "Foe"

def test_get_effective_stats_aggregation():
    registry = tcod.ecs.Registry()
    actor = registry.new_entity()
    actor.components[CombatStats] = CombatStats(attack_bonus=5, defense_bonus=10, damage_bonus=2)
    
    item = registry.new_entity()
    item.components[ItemStats] = ItemStats(attack_bonus=2, damage_bonus=3, protection=4)
    
    actor.relation_tags_many["IsEquipped"].add(item)
    
    effective = get_effective_stats(actor)
    assert effective.attack_bonus == 7 # 5 base + 2 item
    assert effective.defense_bonus == 14 # 10 base + 4 protection
    assert effective.damage_bonus == 5 # 2 base + 3 item
