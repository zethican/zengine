
import tcod.event
from engine.loop import SimulationLoop
from engine.ecs.components import CombatVitals, EntityIdentity
from ui.states import Engine
from ui.renderer import Renderer
from ui.screens import ExplorationState, GameOverState, MainMenuState

def test_game_over_transition():
    # Setup sim
    sim = SimulationLoop()
    hero = sim.registry.new_entity()
    hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Hero", archetype="Standard", is_player=True)
    hero.components[CombatVitals] = CombatVitals(hp=10, max_hp=10)
    
    # Setup UI Engine (Mock Renderer)
    renderer = Renderer(80, 50)
    engine = Engine(renderer, MainMenuState)
    
    # Switch to Exploration
    exploration = ExplorationState(engine, sim)
    engine.change_state(exploration)
    
    assert isinstance(engine.active_state, ExplorationState)
    
    # Force Death
    hero.components[CombatVitals].hp = 0
    
    # Render should trigger transition
    exploration.on_render(renderer)
    
    assert isinstance(engine.active_state, GameOverState)
    assert engine.active_state.sim == sim

def test_game_over_restart():
    # Setup
    sim = SimulationLoop()
    hero = sim.registry.new_entity()
    hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name="Hero", archetype="Standard", is_player=True)
    hero.components[CombatVitals] = CombatVitals(hp=0, max_hp=10)
    
    renderer = Renderer(80, 50)
    engine = Engine(renderer, MainMenuState)
    
    game_over = GameOverState(engine, sim)
    engine.change_state(game_over)
    
    # Press M to restart
    event = tcod.event.KeyDown(sym=tcod.event.KeySym.M, scancode=0, mod=tcod.event.Modifier.NONE)
    game_over.dispatch(event)
    
    assert isinstance(engine.active_state, MainMenuState)
