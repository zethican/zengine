"""
ZEngine — run.py
Main entry point for the ZEngine interactive application.
"""

import sys
from pathlib import Path

# Ensure we can import zengine packages
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

from ui.renderer import Renderer
from ui.states import Engine
from ui.screens import MainMenuState

def main():
    renderer = Renderer(width=80, height=50, title="ZEngine Interactive")
    engine = Engine(renderer=renderer, initial_state_cls=MainMenuState)
    engine.run()

if __name__ == "__main__":
    main()
