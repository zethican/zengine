"""
ZEngine — build_exe.py
PyInstaller build script to compile the game into a standalone Windows .exe
Run via python build_exe.py
"""

import os
import sys
from pathlib import Path
import PyInstaller.__main__

def build():
    project_root = Path(__file__).parent.resolve()
    
    # Build the required PyInstaller arguments
    # Note: semicolon separates source and destination for Windows paths in --add-data
    args = [
        str(project_root / "run.py"),
        "--name", "ZEngine",
        "--onefile",
        "--windowed", # Suppress backend terminal on execution
        f"--add-data={project_root / 'data'};data", 
        "--clean",
        "-y" # automatically overwrite dist/ without asking
    ]
    
    print(f"Running PyInstaller with args: {args}")
    PyInstaller.__main__.run(args)
    print("\n✅ Build complete. Check the `dist/` folder for ZEngine.exe")

if __name__ == "__main__":
    build()
