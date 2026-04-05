"""Single-file entry point for PyInstaller exe build."""
import sys
import os

# Ensure the package root is on path when running as exe
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
    os.environ.setdefault("FORGEAGENT_HOME", os.path.dirname(sys.executable))

from forgeagent.__main__ import main

if __name__ == "__main__":
    main()
