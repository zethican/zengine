"""
ZEngine — ui/screens.py
Implementations of the UI Screen States.
"""
from typing import Any, List, Optional, Dict, Tuple
import tcod
from tcod import libtcodpy

from ui.states import BaseState, Engine
from ui.renderer import Renderer
from engine.loop import SimulationLoop
from engine.ecs.components import (
    Position, 
    EntityIdentity, 
    CombatVitals, 
    CombatStats, 
    ActionEconomy, 
    MovementStats, 
    ItemIdentity,
    Attributes,
    DialogueProfile,
    Disposition,
    Faction,
    SocialAwareness
)
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
            alignment=libtcodpy.CENTER
        )
        renderer.root_console.print(renderer.width // 2, renderer.height // 2, "[N]ew Game", alignment=libtcodpy.CENTER)
        renderer.root_console.print(renderer.width // 2, renderer.height // 2 + 1, "[R]esume Session", alignment=libtcodpy.CENTER)
        renderer.root_console.print(renderer.width // 2, renderer.height // 2 + 2, "[Q]uit", alignment=libtcodpy.CENTER)
        
    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.Q:
            self.engine.running = False
        elif event.sym == tcod.event.KeySym.N:
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
            hero.components[Attributes] = Attributes(scores=hero_def.attributes)
            
            sim.open_session()
            self.engine.change_state(ExplorationState(self.engine, sim))
            
        elif event.sym == tcod.event.KeySym.R:
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
            
        renderer.root_console.print(1, renderer.height - 2, "[Arrows/WASD] Move   [f] Interact   [i] Inventory   [x] Char Sheet   [c] Craft   [ESC] Menu", fg=(150, 150, 150))
        
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
                
                # Fetch Biome Colors
                chunk_x = world_x // self.sim.world.chunk_size
                chunk_y = world_y // self.sim.world.chunk_size
                chunk = self.sim.world.get_chunk(chunk_x, chunk_y)
                biome = chunk["biome"]
                b_colors = biome.colors
                
                # Default character mapping
                char, fg = ".", (50, 50, 50)
                if tile == "wall":
                    char, fg = "#", tuple(b_colors.get("rubble", [120, 120, 120]))
                elif tile == "floor":
                    char, fg = ".", (70, 70, 70)
                elif tile == "grass":
                    char, fg = ",", tuple(b_colors.get("grass", [40, 140, 40]))
                elif tile == "tree":
                    char, fg = "T", tuple(b_colors.get("tree", [20, 100, 20]))
                elif tile == "water":
                    char, fg = "~", tuple(b_colors.get("water", [20, 40, 150]))
                
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
        elif event.sym == tcod.event.KeySym.I:
            self.engine.change_state(InventoryState(self.engine, self))
        elif event.sym == tcod.event.KeySym.X:
            self.engine.change_state(CharacterSheetState(self.engine, self))
        elif event.sym == tcod.event.KeySym.C:
            self.engine.change_state(CraftingState(self.engine, self))
        elif event.sym == tcod.event.KeySym.F:
            # Contextual Interact
            pos = self.player.components[Position]
            result = self.sim.interact_at(self.player, pos.x, pos.y)
            # Check neighbors too
            if not result:
                for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                    result = self.sim.interact_at(self.player, pos.x + dx, pos.y + dy)
                    if result: break
            
            if result and result["type"] == "entity_interaction":
                target = result["target"]
                verb = result["verb"]
                if verb == "talk":
                    self.engine.change_state(DialogueState(self.engine, self, target))
                else:
                    self.engine.change_state(LootState(self.engine, self, target))
            elif result and result["type"] == "door_interaction":
                from engine.ecs.systems import toggle_door_system
                toggle_door_system(result["target"])
            
        elif self.player:
            dx, dy = 0, 0
            if event.sym in (tcod.event.KeySym.UP, tcod.event.KeySym.W, tcod.event.KeySym.K):
                dy = -1
            elif event.sym in (tcod.event.KeySym.DOWN, tcod.event.KeySym.S, tcod.event.KeySym.J):
                dy = 1
            elif event.sym in (tcod.event.KeySym.LEFT, tcod.event.KeySym.A, tcod.event.KeySym.H):
                dx = -1
            elif event.sym in (tcod.event.KeySym.RIGHT, tcod.event.KeySym.D, tcod.event.KeySym.L):
                dx = 1
                
            if dx != 0 or dy != 0:
                self.sim.move_entity_ecs(self.player, dx, dy)
                self.sim.tick()
                
                # Check for Auto-Pop
                if self.sim.pending_social_popup:
                    target = self.sim.pending_social_popup["target"]
                    self.sim.pending_social_popup = None
                    # Update Cooldown
                    if SocialAwareness in target.components:
                        target.components[SocialAwareness].last_interaction_tick = self.sim.clock.tick
                    self.engine.change_state(DialogueState(self.engine, self, target))


class InventoryState(BaseState):
    """The paused inventory overlay."""
    
    def __init__(self, engine: Engine, parent_state: ExplorationState):
        super().__init__(engine)
        self.parent_state = parent_state
        self.player = parent_state.player
        self.inventory: List[tcod.ecs.Entity] = []
        self._refresh()

    def _refresh(self) -> None:
        self.inventory = list(self.player.relation_tags_many["IsCarrying"])
        
    def on_render(self, renderer: Renderer) -> None:
        self.parent_state.on_render(renderer)
        renderer.root_console.draw_frame(
            10, 10, renderer.width - 20, renderer.height - 20,
            "Inventory", clear=True, fg=(255, 255, 255), bg=(0, 0, 0)
        )
        if not self.inventory:
            renderer.root_console.print(12, 12, "(Empty)", fg=(128, 128, 128))
        else:
            for i, item in enumerate(self.inventory):
                name = item.components[ItemIdentity].name if ItemIdentity in item.components else "Unknown"
                renderer.root_console.print(12, 12 + i, f"- {name}")
                
        renderer.root_console.print(12, renderer.height - 12, "[ESC/I] to close", fg=(200, 200, 200))
        
    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.I):
            self.engine.change_state(self.parent_state)


class CharacterSheetState(BaseState):
    """The character sheet overlay."""
    
    def __init__(self, engine: Engine, parent_state: ExplorationState):
        super().__init__(engine)
        self.parent_state = parent_state
        self.player = parent_state.player

    def on_render(self, renderer: Renderer) -> None:
        self.parent_state.on_render(renderer)
        renderer.root_console.draw_frame(
            10, 5, renderer.width - 20, renderer.height - 10,
            "Character Sheet", clear=True, fg=(0, 255, 255), bg=(0, 0, 0)
        )
        
        if not self.player: return
            
        ident = self.player.components[EntityIdentity]
        vitals = self.player.components[CombatVitals]
        
        y = 7
        renderer.root_console.print(12, y, f"Name: {ident.name}", fg=(255, 255, 255))
        renderer.root_console.print(12, y+1, f"Archetype: {ident.archetype}", fg=(200, 200, 200))
        renderer.root_console.print(12, y+3, f"HP: {vitals.hp}/{vitals.max_hp}", fg=(0, 255, 0))
        
        y = 12
        renderer.root_console.print(12, y, "--- ATTRIBUTES ---", fg=(255, 255, 0))
        if Attributes in self.player.components:
            attrs = self.player.components[Attributes].scores
            renderer.root_console.print(12, y+1, f"Might:   {attrs.get('might', 10)}")
            renderer.root_console.print(12, y+2, f"Finesse: {attrs.get('finesse', 10)}")
            renderer.root_console.print(12, y+3, f"Resolve: {attrs.get('resolve', 10)}")
            
        y = 17
        renderer.root_console.print(12, y, "--- COMBAT MODIFIERS (Derived) ---", fg=(255, 255, 0))
        from engine.ecs.systems import get_effective_stats
        eff = get_effective_stats(self.player)
        renderer.root_console.print(12, y+1, f"Attack Bonus:  {eff.attack_bonus:+d}")
        renderer.root_console.print(12, y+2, f"Defense Bonus: {eff.defense_bonus:+d}")
        renderer.root_console.print(12, y+3, f"Damage Bonus:  {eff.damage_bonus:+d}")

        renderer.root_console.print(12, renderer.height - 7, "[ESC/X] to close", fg=(200, 200, 200))
        
    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.X):
            self.engine.change_state(self.parent_state)


class LootState(BaseState):
    """Screen for moving items between a container and player."""
    
    def __init__(self, engine: Engine, parent_state: ExplorationState, container: tcod.ecs.Entity):
        super().__init__(engine)
        self.parent_state = parent_state
        self.player = parent_state.player
        self.container = container
        self.cursor_pos = 0
        self.items: List[tcod.ecs.Entity] = []
        self._refresh()

    def _refresh(self) -> None:
        self.items = list(self.container.relation_tags_many["IsCarrying"])
        if self.cursor_pos >= len(self.items):
            self.cursor_pos = max(0, len(self.items) - 1)

    def on_render(self, renderer: Renderer) -> None:
        self.parent_state.on_render(renderer)
        title = self.container.components[ItemIdentity].name if ItemIdentity in self.container.components else "Container"
        renderer.root_console.draw_frame(
            15, 5, renderer.width - 30, renderer.height - 10,
            f"Loot: {title}", clear=True, fg=(255, 255, 0), bg=(0, 0, 0)
        )
        
        if not self.items:
            renderer.root_console.print(17, 7, "(Empty)", fg=(128, 128, 128))
        else:
            for i, item in enumerate(self.items):
                name = item.components[ItemIdentity].name if ItemIdentity in item.components else "Unknown"
                fg = (255, 255, 255)
                if i == self.cursor_pos:
                    fg = (0, 255, 255)
                renderer.root_console.print(17, 7 + i, f"[Enter] Take {name}", fg=fg)

        renderer.root_console.print(17, renderer.height - 7, "[ESC/F] to close", fg=(200, 200, 200))

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.F):
            self.engine.change_state(self.parent_state)
        elif event.sym in (tcod.event.KeySym.UP, tcod.event.KeySym.W):
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif event.sym in (tcod.event.KeySym.DOWN, tcod.event.KeySym.S):
            self.cursor_pos = min(len(self.items) - 1, self.cursor_pos + 1)
        elif event.sym == tcod.event.KeySym.RETURN:
            if self.items:
                item = self.items[self.cursor_pos]
                # Transactional move
                self.container.relation_tags_many["IsCarrying"].remove(item)
                self.player.relation_tags_many["IsCarrying"].add(item)
                self._refresh()


class DialogueState(BaseState):
    """The dedicated dialogue overlay."""
    
    def __init__(self, engine: Engine, parent_state: ExplorationState, npc: tcod.ecs.Entity):
        super().__init__(engine)
        self.parent_state = parent_state
        self.sim = parent_state.sim
        self.player = parent_state.player
        self.npc = npc
        self.text = ""
        self.options: List[Tuple[str, str]] = [] # [(label, action)]
        self._setup_dialogue()

    def _setup_dialogue(self) -> None:
        ident = self.npc.components[EntityIdentity]
        disp = self.npc.components.get(Disposition, Disposition())
        profile = self.npc.components.get(DialogueProfile, DialogueProfile())
        
        # 1. Determine Greeting based on reputation or faction standing
        rep = disp.reputation
        
        # Override with Faction Standing if member
        if Faction in self.npc.components:
            fid = self.npc.components[Faction].faction_id
            rep = self.sim.faction_standing.get(fid, rep)
            
        mood = "neutral"
        if rep > 0.4: mood = "friendly"
        elif rep < -0.3: mood = "hostile"
        
        self.text = profile.greetings.get(mood, f"Greetings, traveler. I am {ident.name}.")
        
        # 2. Setup Options
        self.options = [
            ("[1] Ask for news or rumors", "rumor"),
            ("[2] Trade items", "trade"),
            ("[3] Say goodbye", "exit")
        ]

    def on_render(self, renderer: Renderer) -> None:
        self.parent_state.on_render(renderer)
        
        # Draw window (centered)
        win_w, win_h = 50, 15
        x = (renderer.width - win_w) // 2
        y = (renderer.height - win_h) // 2
        
        ident = self.npc.components[EntityIdentity]
        renderer.root_console.draw_frame(
            x, y, win_w, win_h,
            f"Talk: {ident.name}", clear=True, fg=(255, 255, 0), bg=(0, 0, 0)
        )
        
        # NPC Speech
        # Simple wrapping
        import textwrap
        lines = textwrap.wrap(self.text, win_w - 4)
        for i, line in enumerate(lines):
            renderer.root_console.print(x + 2, y + 2 + i, line, fg=(255, 255, 255))
            
        # Options
        opt_y = y + win_h - len(self.options) - 2
        for i, (label, _) in enumerate(self.options):
            renderer.root_console.print(x + 2, opt_y + i, label, fg=(0, 255, 255))

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.engine.change_state(self.parent_state)
        elif event.sym == tcod.event.KeySym.N1:
            self._handle_action("rumor")
        elif event.sym == tcod.event.KeySym.N2:
            self._handle_action("trade")
        elif event.sym == tcod.event.KeySym.N3:
            self._handle_action("exit")

    def _handle_action(self, action: str) -> None:
        if action == "exit":
            self.engine.change_state(self.parent_state)
        elif action == "trade":
            self.engine.change_state(TradeState(self.engine, self.parent_state, self.npc))
        elif action == "rumor":
            # Call sim.share_rumor
            rumor_text = self.sim.share_rumor(self.player, self.npc)
            if rumor_text:
                self.text = rumor_text
            else:
                self.text = "I'm sorry, I haven't heard anything interesting lately."
            # Update options to remove rumor ask
            self.options = [("[1] Goodbye", "exit")]


class TradeState(BaseState):
    """Dual-column barter interface."""
    
    def __init__(self, engine: Engine, parent_state: ExplorationState, npc: tcod.ecs.Entity):
        super().__init__(engine)
        self.parent_state = parent_state
        self.sim = parent_state.sim
        self.player = parent_state.player
        self.npc = npc
        
        self.p_inv: List[tcod.ecs.Entity] = []
        self.n_inv: List[tcod.ecs.Entity] = []
        self.p_selected = set() # indices
        self.n_selected = set()
        
        self.active_col = 0 # 0 = player, 1 = npc
        self.cursor_pos = 0
        
        self.standing = 0.0
        if Faction in self.npc.components:
            fid = self.npc.components[Faction].faction_id
            self.standing = self.sim.faction_standing.get(fid, 0.0)
            
        self._refresh()

    def _refresh(self) -> None:
        self.p_inv = list(self.player.relation_tags_many["IsCarrying"])
        self.n_inv = list(self.npc.relation_tags_many["IsCarrying"])

    def on_render(self, renderer: Renderer) -> None:
        self.parent_state.on_render(renderer)
        
        win_w, win_h = 70, 20
        x = (renderer.width - win_w) // 2
        y = (renderer.height - win_h) // 2
        
        renderer.root_console.draw_frame(x, y, win_w, win_h, "Barter & Trade", clear=True)
        
        # Labels
        renderer.root_console.print(x + 2, y + 2, "Your Offer", fg=(0, 255, 255))
        renderer.root_console.print(x + win_w // 2 + 2, y + 2, "Their Items", fg=(255, 255, 0))
        
        from engine.ecs.systems import get_adjusted_value
        
        p_val = 0
        for i, item in enumerate(self.p_inv):
            val = get_adjusted_value(item, self.standing, is_npc_item=False)
            fg = (255, 255, 255)
            if self.active_col == 0 and self.cursor_pos == i: fg = (0, 255, 255)
            prefix = "[X] " if i in self.p_selected else "[ ] "
            if i in self.p_selected: p_val += val
            
            renderer.root_console.print(x + 2, y + 4 + i, f"{prefix}{item.components[ItemIdentity].name[:15]} ({val})", fg=fg)
            
        n_val = 0
        for i, item in enumerate(self.n_inv):
            val = get_adjusted_value(item, self.standing, is_npc_item=True)
            fg = (255, 255, 255)
            if self.active_col == 1 and self.cursor_pos == i: fg = (0, 255, 255)
            prefix = "[X] " if i in self.n_selected else "[ ] "
            if i in self.n_selected: n_val += val
            
            renderer.root_console.print(x + win_w // 2 + 2, y + 4 + i, f"{prefix}{item.components[ItemIdentity].name[:15]} ({val})", fg=fg)

        # Footer
        balance = p_val - n_val
        bal_fg = (0, 255, 0) if balance >= 0 else (255, 0, 0)
        renderer.root_console.print(x + 2, y + win_h - 3, f"Balance: {balance:+d}", fg=bal_fg)
        
        if balance >= 0 and (self.p_selected or self.n_selected):
            renderer.root_console.print(x + 20, y + win_h - 3, "[ENTER] Confirm Trade", fg=(255, 255, 255))
            
        # Generosity Check
        if balance > 0:
            disp = self.npc.components.get(Disposition, Disposition())
            if self.sim.clock.tick - disp.last_gift_tick >= 1000:
                renderer.root_console.print(x + 2, y + win_h - 2, "* Generosity Bonus Eligible", fg=(255, 215, 0))

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.engine.change_state(self.parent_state)
        elif event.sym in (tcod.event.KeySym.LEFT, tcod.event.KeySym.A):
            self.active_col = 0
            self.cursor_pos = min(self.cursor_pos, len(self.p_inv)-1) if self.p_inv else 0
        elif event.sym in (tcod.event.KeySym.RIGHT, tcod.event.KeySym.D):
            self.active_col = 1
            self.cursor_pos = min(self.cursor_pos, len(self.n_inv)-1) if self.n_inv else 0
        elif event.sym in (tcod.event.KeySym.UP, tcod.event.KeySym.W):
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif event.sym in (tcod.event.KeySym.DOWN, tcod.event.KeySym.S):
            limit = len(self.p_inv) if self.active_col == 0 else len(self.n_inv)
            self.cursor_pos = min(max(0, limit - 1), self.cursor_pos + 1)
        elif event.sym == tcod.event.KeySym.SPACE:
            if self.active_col == 0 and self.p_inv:
                if self.cursor_pos in self.p_selected: self.p_selected.remove(self.cursor_pos)
                else: self.p_selected.add(self.cursor_pos)
            elif self.active_col == 1 and self.n_inv:
                if self.cursor_pos in self.n_selected: self.n_selected.remove(self.cursor_pos)
                else: self.n_selected.add(self.cursor_pos)
        elif event.sym == tcod.event.KeySym.RETURN:
            self._confirm_trade()

    def _confirm_trade(self) -> None:
        from engine.ecs.systems import get_adjusted_value
        p_val = sum(get_adjusted_value(self.p_inv[i], self.standing, False) for i in self.p_selected)
        n_val = sum(get_adjusted_value(self.n_inv[i], self.standing, True) for i in self.n_selected)
        
        if p_val >= n_val and (self.p_selected or self.n_selected):
            p_items = [self.p_inv[i] for i in self.p_selected]
            n_items = [self.n_inv[i] for i in self.n_selected]
            self.sim.execute_trade(self.player, self.npc, p_items, n_items, p_val > n_val)
            self.engine.change_state(self.parent_state)


class CraftingState(BaseState):
    """The paused crafting overlay."""
    
    def __init__(self, engine: Engine, parent_state: ExplorationState):
        super().__init__(engine)
        self.parent_state = parent_state
        self.sim = parent_state.sim
        self.player = parent_state.player
        self.selected_indices: List[int] = []
        self.cursor_pos = 0
        self.inventory: List[tcod.ecs.Entity] = []
        self._refresh_inventory()

    def _refresh_inventory(self) -> None:
        """Fetch current items in player inventory."""
        self.inventory = list(self.player.relation_tags_many["IsCarrying"])

    def on_render(self, renderer: Renderer) -> None:
        # Render exploration state underneath
        self.parent_state.on_render(renderer)
        
        # Draw window
        renderer.root_console.draw_frame(
            15, 5, renderer.width - 30, renderer.height - 10,
            "Crafting Table", clear=True, fg=(255, 255, 0), bg=(0, 0, 0)
        )
        
        renderer.root_console.print(17, 7, "Select TWO items to combine:", fg=(200, 200, 200))
        
        if not self.inventory:
            renderer.root_console.print(17, 9, "(Inventory empty)", fg=(128, 128, 128))
        
        for i, item in enumerate(self.inventory):
            name = "Unknown Item"
            if ItemIdentity in item.components:
                name = item.components[ItemIdentity].name
            
            fg = (255, 255, 255)
            if i == self.cursor_pos:
                fg = (0, 255, 255) # Cursor highlight
            
            prefix = "[ ] "
            if i in self.selected_indices:
                prefix = "[X] "
                fg = (255, 255, 0) # Selected highlight
                
            renderer.root_console.print(17, 9 + i, f"{prefix}{name}", fg=fg)

        if len(self.selected_indices) == 2:
            renderer.root_console.print(17, renderer.height - 7, "[Enter] Combine Items", fg=(0, 255, 0))
        else:
            renderer.root_console.print(17, renderer.height - 7, "Pick 2 items...", fg=(100, 100, 100))

        renderer.root_console.print(17, renderer.height - 6, "[ESC/C] Cancel", fg=(200, 200, 200))
        
    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.C):
            self.engine.change_state(self.parent_state)
        elif event.sym in (tcod.event.KeySym.UP, tcod.event.KeySym.W, tcod.event.KeySym.K):
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif event.sym in (tcod.event.KeySym.DOWN, tcod.event.KeySym.S, tcod.event.KeySym.J):
            self.cursor_pos = min(len(self.inventory) - 1, self.cursor_pos + 1)
        elif event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER, tcod.event.KeySym.SPACE):
            if not self.inventory:
                return
                
            if self.cursor_pos in self.selected_indices:
                self.selected_indices.remove(self.cursor_pos)
            elif len(self.selected_indices) < 2:
                self.selected_indices.append(self.cursor_pos)
                
            if len(self.selected_indices) == 2 and event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
                self._attempt_craft()

    def _attempt_craft(self) -> None:
        item_a = self.inventory[self.selected_indices[0]]
        item_b = self.inventory[self.selected_indices[1]]
        
        # Use SimulationLoop to invoke the craft action
        success = self.sim.invoke_ability_ecs(self.player, "craft", item_a, second_target=item_b)
        
        if success:
            # Refresh and reset
            self._refresh_inventory()
            self.selected_indices = []
            self.cursor_pos = 0
