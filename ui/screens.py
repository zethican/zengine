"""
ZEngine — ui/screens.py
Implementations of the UI Screen States.
"""
from typing import Any
import tcod

from ui.states import BaseState, Engine
from ui.renderer import Renderer
from engine.loop import SimulationLoop
from engine.ecs.components import Position, EntityIdentity, CombatVitals, CombatStats, ActionEconomy, MovementStats
from engine.data_loader import get_entity_def, get_starting_rumors
from world.generator import Rumor


class MainMenuState(BaseState):
    """The title screen."""
    
    def on_render(self, renderer: Renderer) -> None:
        renderer.root_console.print(
            renderer.width // 2, 
            renderer.height // 2 - 5, 
            "ZEngine MVP", 
            fg=(255, 255, 0), 
            alignment=tcod.CENTER
        )
        renderer.root_console.print(renderer.width // 2, renderer.height // 2, "[N]ew Game", alignment=tcod.CENTER)
        renderer.root_console.print(renderer.width // 2, renderer.height // 2 + 1, "[R]esume Session", alignment=tcod.CENTER)
        renderer.root_console.print(renderer.width // 2, renderer.height // 2 + 2, "[Q]uit", alignment=tcod.CENTER)
        
    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.q:
            self.engine.running = False
        elif event.sym == tcod.event.KeySym.n:
            sim = SimulationLoop()
            sim.world.world_seed = 10101
            
            # Setup Rumors
            for r_def in get_starting_rumors():
                sim.world.add_rumor(Rumor(r_def.id, r_def.name, r_def.pol_type, r_def.significance))
            
            # Setup Player
            hero_def = get_entity_def("hero_standard")
            hero = sim.registry.new_entity()
            hero.components[EntityIdentity] = EntityIdentity(entity_id=1, name=hero_def.name, archetype=hero_def.archetype, is_player=True)
            hero.components[Position] = Position(x=0, y=0)
            hero.components[CombatVitals] = CombatVitals(hp=hero_def.hp, max_hp=hero_def.hp)
            hero.components[CombatStats] = CombatStats(attack_bonus=5, damage_bonus=2)
            hero.components[ActionEconomy] = ActionEconomy()
            hero.components[MovementStats] = MovementStats(speed=hero_def.speed)
            
            sim.open_session()
            self.engine.change_state(ExplorationState(self.engine, sim))
            
        elif event.sym == tcod.event.KeySym.r:
            try:
                sim = SimulationLoop()
                sim.resume_session()
                self.engine.change_state(ExplorationState(self.engine, sim))
            except Exception as e:
                print(f"Failed to resume session: {e}")


class ExplorationState(BaseState):
    """The main gameplay loop screen."""
    
    def __init__(self, engine: Engine, sim: SimulationLoop):
        super().__init__(engine)
        self.sim = sim
        self.player = None
        
        # Cache player entity reference
        for ent in self.sim.registry.Q.all_of(components=[EntityIdentity]):
            if ent.components[EntityIdentity].is_player:
                self.player = ent
                break

    def on_render(self, renderer: Renderer) -> None:
        """Draws the map and entities."""
        # Simple HUD
        if self.player and CombatVitals in self.player.components:
            hp = self.player.components[CombatVitals].hp
            max_hp = self.player.components[CombatVitals].max_hp
            renderer.root_console.print(1, 1, f"HP: {hp}/{max_hp}", fg=(0, 255, 0))
            
        renderer.root_console.print(1, renderer.height - 2, "[Arrows/WASD] Move   [i] Inventory   [ESC] Menu", fg=(150, 150, 150))
        
        # Camera centering based on player
        cam_x, cam_y = 0, 0
        if self.player and Position in self.player.components:
            cam_x = self.player.components[Position].x - renderer.width // 2
            cam_y = self.player.components[Position].y - renderer.height // 2
            
        # Draw Map
        for sy in range(renderer.height):
            for sx in range(renderer.width):
                world_x = cam_x + sx
                world_y = cam_y + sy
                
                tile = self.sim.world.get_tile(world_x, world_y)
                
                # Default character mapping
                char, fg = ".", (50, 50, 50)
                if tile == "wall":
                    char, fg = "#", (120, 120, 120)
                elif tile == "floor":
                    char, fg = ".", (70, 70, 70)
                elif tile == "grass":
                    char, fg = ",", (40, 140, 40)
                elif tile == "tree":
                    char, fg = "T", (20, 100, 20)
                
                renderer.root_console.print(sx, sy, char, fg=fg)
        
        # Draw entities
        for ent in self.sim.registry.Q.all_of(components=[Position, EntityIdentity]):
            pos = ent.components[Position]
            ident = ent.components[EntityIdentity]
                
            screen_x = pos.x - cam_x
            screen_y = pos.y - cam_y
            
            if 0 <= screen_x < renderer.width and 0 <= screen_y < renderer.height:
                if ident.is_player:
                    renderer.root_console.print(screen_x, screen_y, "@", fg=(0, 255, 255))
                else:
                    char = ident.archetype[0] if ident.archetype else "e"
                    renderer.root_console.print(screen_x, screen_y, char, fg=(255, 50, 50))


    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.sim.save_session()
            self.engine.change_state(MainMenuState(self.engine))
        elif event.sym == tcod.event.KeySym.i:
            self.engine.change_state(InventoryState(self.engine, self))
            
        elif self.player:
            dx, dy = 0, 0
            if event.sym in (tcod.event.KeySym.UP, tcod.event.KeySym.w):
                dy = -1
            elif event.sym in (tcod.event.KeySym.DOWN, tcod.event.KeySym.s):
                dy = 1
            elif event.sym in (tcod.event.KeySym.LEFT, tcod.event.KeySym.a):
                dx = -1
            elif event.sym in (tcod.event.KeySym.RIGHT, tcod.event.KeySym.d):
                dx = 1
                
            if dx != 0 or dy != 0:
                self.sim.move_entity_ecs(self.player, dx, dy)
                self.sim.tick()


class InventoryState(BaseState):
    """The paused inventory overlay."""
    
    def __init__(self, engine: Engine, parent_state: BaseState):
        super().__init__(engine)
        self.parent_state = parent_state
        
    def on_render(self, renderer: Renderer) -> None:
        # Render exploration state underneath
        self.parent_state.on_render(renderer)
        
        # Draw inventory window
        renderer.root_console.draw_frame(
            10, 10, renderer.width - 20, renderer.height - 20,
            "Inventory", clear=True, fg=(255, 255, 255), bg=(0, 0, 0)
        )
        renderer.root_console.print(12, 12, "Empty. No gear equipped.", fg=(128, 128, 128))
        renderer.root_console.print(12, renderer.height - 12, "[ESC/I] to close", fg=(200, 200, 200))
        
    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.i):
            self.engine.change_state(self.parent_state)
