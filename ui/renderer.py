"""
ZEngine — ui/renderer.py
TCOD Renderer: Terminal UI and view management.
===============================================
Version:     0.1  (Phase 2 — canonical implementation)
Stack:       Python 3.14.3 | tcod
Status:      Production-ready for Phase 2.
"""

from __future__ import annotations
from typing import Optional
import tcod

class Renderer:
    """
    Manages the tcod root console and rendering loop.
    """
    def __init__(self, width: int, height: int, title: str = "ZEngine"):
        self.width = width
        self.height = height
        self.title = title
        # Stub: TCOD font loading usually happens here
        self.root_console = tcod.console.Console(width, height)
        self.context: Optional[tcod.context.Context] = None

    def clear(self) -> None:
        """Clear the console with black."""
        self.root_console.clear()

    def present(self, context: tcod.context.Context) -> None:
        """Present the current console to the screen."""
        context.present(self.root_console)
