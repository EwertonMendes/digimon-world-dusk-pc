#!/usr/bin/env python3
"""Report local prerequisites without installing or modifying the computer."""
import platform
import shutil
import subprocess
from pathlib import Path
import json


def version(name):
    path = shutil.which(name)
    if not path:
        return None
    try:
        line = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
        return {"path": path, "version": (line.stdout or line.stderr).splitlines()[0][:150]}
    except (OSError, IndexError, subprocess.TimeoutExpired):
        return {"path": path}


names = ("git", "cmake", "ninja", "python", "python3", "clang++", "g++", "cl", "java", "javac", "node", "npm", "rea")
print(json.dumps({"platform": platform.platform(), "architecture": platform.machine(), "tools": {x: version(x) for x in names}, "cwd": str(Path.cwd())}, indent=2))
