"""
ZEngine — ui/states.py
State Machine defining the UI screens and event routing logic.
"""

from __future__ import annotations
from typing import Optional, Any
import tcod

from ui.renderer import Renderer

class BaseState(tcod.event.EventDispatch[Any]):
    """
    Protocol for a screen state.
    Intercepts tcod events and renders to the console.
    """
    def __init__(self, engine: "Engine"):
        super().__init__()
        self.engine = engine

    def on_render(self, renderer: Renderer) -> None:
        """Called every frame to draw to the console."""
        pass


class Engine:
    """
    Central loop controller handling TCOD context, Renderer, and State tracking.
    """
    def __init__(self, renderer: Renderer, initial_state_cls: type[BaseState]):
        self.renderer = renderer
        self.active_state: BaseState = initial_state_cls(self)
        self.running = True

    def change_state(self, new_state: BaseState) -> None:
        """Transitions to a new Active State."""
        self.active_state = new_state

    def run(self) -> None:
        """Main blocking event loop."""
        
        with tcod.context.new_terminal(
            self.renderer.width,
            self.renderer.height,
            title=self.renderer.title,
            vsync=True,
        ) as context:
            self.renderer.context = context
            
            while self.running:
                # 1. Render
                self.renderer.clear()
                self.active_state.on_render(self.renderer)
                self.renderer.present(context)
                
                # 2. Handle Inputs
                for event in tcod.event.wait():
                    context.convert_event(event) # Handle mouse resizes/clicks securely
                    
                    if isinstance(event, tcod.event.Quit):
                        self.running = False
                        break
                        
                    # Route to active state handler
                    self.active_state.dispatch(event)
