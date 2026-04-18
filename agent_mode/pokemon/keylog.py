"""
Pokemon keylog — captures Ken's inputs while he plays so KenAI
can learn from imitation. Same architecture as halo_keylog.py.

Logs to pokemon-keylog.jsonl in ken-ai-latest memory dir.
Only captures when mGBA has focus (checks foreground window).
"""

import json, sys, time, os, ctypes
from datetime import datetime, timezone
from pathlib import Path

MEM_DIR = Path(__file__).parent.parent / "memories" / "ken-ai-latest"
LOG_FILE = MEM_DIR / "pokemon-keylog.jsonl"

try:
    import keyboard
    HAS_KB = True
except ImportError:
    HAS_KB = False

try:
    import mouse
    HAS_MOUSE = True
except ImportError:
    HAS_MOUSE = False


def is_mgba_focused():
    """Check if mGBA is the foreground window."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            return "mGBA" in title or "Crystal" in title or "Pokemon" in title
    except:
        pass
    return False


def log_event(entry):
    try:
        with open(str(LOG_FILE), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except:
        pass


def on_key(event):
    if not is_mgba_focused():
        return
    log_event({
        "at": datetime.now(timezone.utc).isoformat(),
        "kind": "key",
        "key": event.name,
        "dir": event.event_type,  # "down" or "up"
    })


def on_mouse_click(event=None):
    if not is_mgba_focused():
        return
    if hasattr(event, 'button'):
        log_event({
            "at": datetime.now(timezone.utc).isoformat(),
            "kind": "mouse",
            "button": event.button,
            "dir": event.event_type,
        })


def main():
    print(f"Pokemon keylog starting. Log: {LOG_FILE}")
    print("Captures only when mGBA is focused.")

    if HAS_KB:
        keyboard.hook(on_key)
        print("keyboard hook: active")
    else:
        print("keyboard module not found — pip install keyboard")

    if HAS_MOUSE:
        mouse.hook(on_mouse_click)
        print("mouse hook: active")
    else:
        print("mouse module not found — pip install mouse")

    stop_after = None
    for arg in sys.argv[1:]:
        if arg.startswith("--stop-after"):
            stop_after = int(arg.split("=")[1] if "=" in arg else sys.argv[sys.argv.index(arg)+1])

    try:
        if stop_after:
            time.sleep(stop_after)
        else:
            while True:
                time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if HAS_KB:
            keyboard.unhook_all()
        print("Pokemon keylog stopped.")


if __name__ == "__main__":
    main()
