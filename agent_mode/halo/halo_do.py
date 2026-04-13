"""
Halo MCC actuator — fires one action from the agent's vocabulary.

Usage:
    python halo_do.py <action> [duration_ms]

Actions map to Halo MCC default keybinds (PC):
    move_fwd      → w
    move_back     → s
    strafe_left   → a
    strafe_right  → d
    jump          → space
    crouch        → ctrl (hold)
    sprint        → shift (hold)
    fire          → left mouse button
    ads           → right mouse button
    reload        → r
    interact      → e
    grenade       → g
    melee         → f / v
    swap_weapon   → q
    look_left     → mouse rel (-200, 0)
    look_right    → mouse rel (+200, 0)
    look_up       → mouse rel (0, -120)
    look_down     → mouse rel (0, +120)
    pause         → esc
    noop          → nothing

Default duration 150ms. Safe ceiling 1500ms so a runaway call
can't hold a key forever. Emits a single JSON line on stdout with
the action + elapsed time.

Requires pyautogui. No other deps.
"""

import sys
import json
import time

try:
    import pyautogui
except Exception as e:
    sys.stderr.write("pyautogui import failed: " + str(e) + "\n")
    sys.exit(2)

# DirectInput-aware input. pyautogui sends Windows message key
# events which DirectInput-based games (Halo MCC, most FPS games)
# silently ignore. pydirectinput sends SendInput with scan codes
# so the game's input hook sees the presses as real hardware.
# Fall back to pyautogui only if pydirectinput isn't available.
try:
    import pydirectinput as pdi
    HAS_PDI = True
    # Disable pydirectinput's own failsafe + pause for same reason
    # as pyautogui — Ken needs predictable behavior.
    pdi.FAILSAFE = False
    pdi.PAUSE = 0
except Exception:
    pdi = None
    HAS_PDI = False

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

KEY_MAP = {
    "move_fwd":   ("hold", "w"),
    "move_back":  ("hold", "s"),
    "strafe_left":("hold", "a"),
    "strafe_right":("hold","d"),
    "jump":       ("tap",  "space"),
    "crouch":     ("hold", "ctrl"),
    "sprint":     ("hold", "shift"),
    "reload":     ("tap",  "r"),
    "interact":   ("tap",  "e"),
    "grenade":    ("tap",  "g"),
    "melee":      ("tap",  "v"),
    "swap_weapon":("tap",  "q"),
    "pause":      ("tap",  "esc"),
}

MOUSE_MAP = {
    "fire":        ("click", "left"),
    "ads":         ("click", "right"),
    "look_left":   ("rel", -220, 0),
    "look_right":  ("rel",  220, 0),
    "look_up":     ("rel", 0, -140),
    "look_down":   ("rel", 0,  140),
}


def _key_down(key):
    if HAS_PDI: pdi.keyDown(key)
    else:       pyautogui.keyDown(key)

def _key_up(key):
    if HAS_PDI: pdi.keyUp(key)
    else:       pyautogui.keyUp(key)

def _key_press(key):
    if HAS_PDI: pdi.press(key)
    else:       pyautogui.press(key)

def _mouse_down(button):
    if HAS_PDI: pdi.mouseDown(button=button)
    else:       pyautogui.mouseDown(button=button)

def _mouse_up(button):
    if HAS_PDI: pdi.mouseUp(button=button)
    else:       pyautogui.mouseUp(button=button)

def _mouse_move_rel(dx, dy):
    # pydirectinput.moveRel uses SendInput with MOUSEEVENTF_MOVE
    # which DirectInput games read. pyautogui's moveRel uses the
    # cursor API which games ignore for camera look.
    if HAS_PDI:
        try:
            pdi.moveRel(dx, dy, relative=True)
            return
        except Exception:
            pass
    pyautogui.moveRel(dx, dy, duration=0.08)


def fire(action, duration_ms):
    duration_ms = max(0, min(1500, int(duration_ms)))
    duration_s = duration_ms / 1000.0

    if action in KEY_MAP:
        kind, key = KEY_MAP[action]
        if kind == "hold":
            _key_down(key)
            time.sleep(duration_s if duration_s > 0 else 0.12)
            _key_up(key)
        else:
            _key_press(key)
        return ("pdi:" if HAS_PDI else "pag:") + "key:" + key + ":" + kind

    if action in MOUSE_MAP:
        spec = MOUSE_MAP[action]
        if spec[0] == "click":
            _mouse_down(spec[1])
            time.sleep(duration_s if duration_s > 0 else 0.08)
            _mouse_up(spec[1])
            return ("pdi:" if HAS_PDI else "pag:") + "mouse:" + spec[1] + ":click"
        if spec[0] == "rel":
            _mouse_move_rel(spec[1], spec[2])
            return ("pdi:" if HAS_PDI else "pag:") + "mouse:rel:{},{}".format(spec[1], spec[2])

    if action == "noop":
        time.sleep(0.05)
        return "noop"

    return "unknown:" + action


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: halo_do.py <action> [duration_ms]\n")
        sys.exit(2)
    action = sys.argv[1].strip().lower()
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    detail = fire(action, duration)
    sys.stdout.write(json.dumps({
        "action": action,
        "duration_ms": duration,
        "detail": detail,
    }) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
