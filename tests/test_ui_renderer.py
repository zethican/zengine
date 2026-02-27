import pytest
from ui.renderer import Renderer

def test_renderer_initialization():
    r = Renderer(width=80, height=50, title="Test Window")
    assert r.width == 80
    assert r.height == 50
    assert r.title == "Test Window"
    assert r.root_console.width == 80
    assert r.root_console.height == 50

def test_renderer_clear():
    r = Renderer(width=80, height=50)
    # Fill console with some character
    r.root_console.print(0, 0, "@")
    assert chr(r.root_console.ch[0, 0]) == "@"
    
    # Clear and check
    r.clear()
    assert chr(r.root_console.ch[0, 0]) == " "
