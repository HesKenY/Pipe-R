"""
tools/win_subprocess.py

Drop-in subprocess helpers that ALWAYS set CREATE_NO_WINDOW
on Windows. Prevents every background shell spawn from
popping a visible cmd window and stealing focus from Halo.

Usage everywhere in KenAI:
    from tools.win_subprocess import run, popen

    run(["ollama", "run", model], capture_output=True, text=True)
    popen(["cmd", "/c", bat], stdout=subprocess.DEVNULL)

CREATE_NO_WINDOW = 0x08000000 — hides the subprocess console
entirely. Combine with CREATE_NEW_PROCESS_GROUP (0x00000200)
when you want a detached long-runner that doesn't cascade-die
on Ctrl+C to the parent.
"""

import os
import subprocess as _sp

CREATE_NO_WINDOW        = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200

IS_WINDOWS = os.name == "nt"


def run(*args, **kwargs):
    """
    Thin wrapper around subprocess.run that always adds
    CREATE_NO_WINDOW on Windows, and sets encoding/errors
    so cp1252 console garbage doesn't raise.
    """
    if IS_WINDOWS:
        existing = kwargs.get("creationflags", 0)
        kwargs["creationflags"] = existing | CREATE_NO_WINDOW
    # Only default encoding if text=True and the caller didn't override
    if kwargs.get("text"):
        kwargs.setdefault("encoding", "utf-8")
        kwargs.setdefault("errors", "replace")
    return _sp.run(*args, **kwargs)


def popen(*args, detached: bool = False, **kwargs):
    """
    Thin wrapper around subprocess.Popen with the same
    no-window guarantee. Pass detached=True for long-running
    background tasks that should survive Ctrl+C on the parent.
    """
    if IS_WINDOWS:
        existing = kwargs.get("creationflags", 0)
        existing |= CREATE_NO_WINDOW
        if detached:
            existing |= CREATE_NEW_PROCESS_GROUP
        kwargs["creationflags"] = existing
    return _sp.Popen(*args, **kwargs)


# Re-export for convenience so callers don't need to `import
# subprocess` separately just for DEVNULL / PIPE / STDOUT.
PIPE    = _sp.PIPE
STDOUT  = _sp.STDOUT
DEVNULL = _sp.DEVNULL
TimeoutExpired = _sp.TimeoutExpired
CalledProcessError = _sp.CalledProcessError
