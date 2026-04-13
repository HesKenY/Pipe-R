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


def fire(action, duration_ms):
    duration_ms = max(0, min(1500, int(duration_ms)))
    duration_s = duration_ms / 1000.0
    t0 = time.time()

    if action in KEY_MAP:
        kind, key = KEY_MAP[action]
        if kind == "hold":
            pyautogui.keyDown(key)
            time.sleep(duration_s if duration_s > 0 else 0.12)
            pyautogui.keyUp(key)
        else:
            pyautogui.press(key)
        return "key:" + key + ":" + kind

    if action in MOUSE_MAP:
        spec = MOUSE_MAP[action]
        if spec[0] == "click":
            pyautogui.mouseDown(button=spec[1])
            time.sleep(duration_s if duration_s > 0 else 0.08)
            pyautogui.mouseUp(button=spec[1])
            return "mouse:" + spec[1] + ":click"
        if spec[0] == "rel":
            pyautogui.moveRel(spec[1], spec[2], duration=0.08)
            return "mouse:rel:{},{}".format(spec[1], spec[2])

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
